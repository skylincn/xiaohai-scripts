#!/usr/bin/env python3
"""
XHS Webhook Server v2.0
修复：支持多图片解析和保存
"""
import http.server
import socketserver
import json
import os
import re
from datetime import datetime
import hashlib
import urllib.request
import base64

PORT = 8888
WEBHOOK_DIR = "/tmp/xhs_webhook"
os.makedirs(WEBHOOK_DIR, exist_ok=True)

# 简单去重：记录最近 100 个请求的 hash
_seen = []
_SEEN_MAX = 100

def extract_images_from_data(data):
    """
    从 webhook 数据中提取所有图片 URL
    支持多种可能的字段格式
    """
    images = []
    
    # 可能的图片字段路径
    possible_paths = [
        'images',           # 直接 images 数组
        'media',            # media 数组
        'pictures',         # pictures 数组
        'data.images',      # data.images
        'data.media',       # data.media
        'content.images',   # content.images
        'post.images',      # post.images
        'image_urls',       # image_urls 数组
    ]
    
    for path in possible_paths:
        parts = path.split('.')
        current = data
        try:
            for part in parts:
                current = current[part]
            if isinstance(current, list):
                for item in current:
                    if isinstance(item, str):
                        images.append(item)
                    elif isinstance(item, dict):
                        # 可能是 {url: "..."} 或 {src: "..."} 格式
                        for key in ['url', 'src', 'link', 'uri', 'path']:
                            if key in item and isinstance(item[key], str):
                                images.append(item[key])
                                break
            elif isinstance(current, str):
                images.append(current)
        except (KeyError, TypeError):
            continue
    
    # 去重并保持顺序
    seen = set()
    unique_images = []
    for img in images:
        if img and img not in seen:
            seen.add(img)
            unique_images.append(img)
    
    return unique_images

def download_image(url, save_dir, index):
    """下载图片并保存"""
    try:
        # 处理 base64 编码的图片
        if url.startswith('data:image'):
            # data:image/png;base64,xxxx
            match = re.match(r'data:image/\w+;base64,(.+)', url)
            if match:
                img_data = base64.b64decode(match.group(1))
                ext = url.split(';')[0].split('/')[-1] or 'png'
                filename = f"image_{index+1}.{ext}"
                filepath = os.path.join(save_dir, filename)
                with open(filepath, 'wb') as f:
                    f.write(img_data)
                return filename
            return None
        
        # 处理普通 URL
        headers = {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15'
        }
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as response:
            img_data = response.read()
            
            # 判断文件扩展名
            content_type = response.headers.get('Content-Type', '')
            if 'jpeg' in content_type or 'jpg' in content_type:
                ext = 'jpg'
            elif 'png' in content_type:
                ext = 'png'
            elif 'gif' in content_type:
                ext = 'gif'
            elif 'webp' in content_type:
                ext = 'webp'
            else:
                ext = 'jpg'
            
            filename = f"image_{index+1}.{ext}"
            filepath = os.path.join(save_dir, filename)
            with open(filepath, 'wb') as f:
                f.write(img_data)
            return filename
            
    except Exception as e:
        print(f"[下载失败] 图片 {index+1}: {e}")
        return None

class WebhookHandler(http.server.SimpleHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        
        # 生成请求指纹用于去重
        req_hash = hashlib.md5(post_data).hexdigest()
        if req_hash in _seen:
            print(f"[去重] 跳过重复请求: {req_hash[:8]}")
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"success": True, "duplicate": True}).encode())
            return
        
        _seen.append(req_hash)
        if len(_seen) > _SEEN_MAX:
            _seen.pop(0)
        
        try:
            data = json.loads(post_data.decode('utf-8'))
        except Exception as e:
            data = {"raw": post_data.decode('utf-8', errors='ignore'), "error": str(e)}
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 创建本次请求的目录
        request_dir = f"{WEBHOOK_DIR}/xhs_{timestamp}"
        os.makedirs(request_dir, exist_ok=True)
        
        # 提取所有图片
        images = extract_images_from_data(data)
        print(f"[解析] 发现 {len(images)} 张图片")
        
        # 下载图片
        downloaded_images = []
        for i, img_url in enumerate(images):
            filename = download_image(img_url, request_dir, i)
            if filename:
                downloaded_images.append(filename)
                print(f"[下载] 图片 {i+1}: {filename}")
        
        # 保存原始 JSON
        json_file = f"{request_dir}/data.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump({
                "received_at": timestamp,
                "image_count": len(images),
                "downloaded_count": len(downloaded_images),
                "images": images,
                "data": data
            }, f, ensure_ascii=False, indent=2)
        
        # 保存文本摘要
        text_file = f"{request_dir}/summary.txt"
        with open(text_file, 'w', encoding='utf-8') as f:
            f.write(f"来源: {data.get('source', 'unknown')}\n")
            f.write(f"链接: {data.get('url', '')}\n")
            f.write(f"标题: {data.get('title', '')}\n")
            f.write(f"时间: {timestamp}\n")
            f.write(f"图片数量: {len(images)} 张\n")
            f.write(f"下载成功: {len(downloaded_images)} 张\n\n")
            
            if downloaded_images:
                f.write("图片文件:\n")
                for img in downloaded_images:
                    f.write(f"  - {img}\n")
                f.write("\n")
            
            f.write("内容:\n")
            f.write(f"{data.get('content', '')}\n")
            
            # 如果 content 里没有图片信息，但解析到了图片，额外列出
            if images and 'http' in str(data.get('content', '')):
                f.write("\n图片链接:\n")
                for i, img in enumerate(images, 1):
                    f.write(f"{i}. {img}\n")
        
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        response = {
            "success": True,
            "saved_dir": f"xhs_{timestamp}",
            "image_count": len(images),
            "downloaded": len(downloaded_images),
            "images": downloaded_images
        }
        self.wfile.write(json.dumps(response, ensure_ascii=False).encode())
        
        print(f"[完成] 数据已保存到 {request_dir}")
        print(f"       图片: {len(images)} 张, 下载成功: {len(downloaded_images)} 张")
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

if __name__ == '__main__':
    print(f"=" * 50)
    print(f"XHS Webhook Server v2.0")
    print(f"端口: {PORT}")
    print(f"保存目录: {WEBHOOK_DIR}")
    print(f"=" * 50)
    print("\n支持功能:")
    print("  - 自动解析多图片")
    print("  - 下载图片到本地")
    print("  - 保存原始 JSON 数据")
    print("  - 生成文本摘要\n")
    
    with socketserver.TCPServer(("", PORT), WebhookHandler) as httpd:
        print(f"服务器已启动，等待请求...")
        httpd.serve_forever()
