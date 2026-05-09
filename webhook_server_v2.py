#!/usr/bin/env python3
"""
XHS Webhook Server v2.1
修复：支持快捷指令合并的多图 base64 解析
"""
import http.server
import socketserver
import json
import os
import re
from datetime import datetime
import hashlib
import base64

PORT = 8888
WEBHOOK_DIR = "/tmp/xhs_webhook"
os.makedirs(WEBHOOK_DIR, exist_ok=True)

# 简单去重：记录最近 100 个请求的 hash
_seen = []
_SEEN_MAX = 100

def split_combined_base64(combined_str):
    """
    处理快捷指令合并的多图 base64
    
    快捷指令可能把多张图的 base64 用 \r\n 或 \n 分隔合并成一个字符串
    需要检测并拆分
    """
    images = []
    
    # 方法1: 按换行符分割（快捷指令常用这种方式）
    if '\r\n' in combined_str or '\n' in combined_str:
        parts = re.split(r'[\r\n]+', combined_str)
        for part in parts:
            part = part.strip()
            if part and len(part) > 100:  # 过滤掉太短的
                images.append(part)
        if len(images) > 1:
            print(f"[拆分] 检测到换行分隔，拆分为 {len(images)} 张图")
            return images
    
    # 方法2: 检测多个 JPEG 结束标记 \xff\xd9
    # JPEG 图片以 \xff\xd8 开始，\xff\xd9 结束
    try:
        decoded = base64.b64decode(combined_str)
        # 找所有 JPEG 结束标记的位置
        jpeg_end_markers = []
        pos = 0
        while True:
            pos = decoded.find(b'\xff\xd9', pos)
            if pos == -1:
                break
            jpeg_end_markers.append(pos + 2)  # 包含结束标记
            pos += 2
        
        if len(jpeg_end_markers) > 1:
            print(f"[拆分] 检测到 {len(jpeg_end_markers)} 个 JPEG 结束标记")
            # 按标记位置拆分
            start = 0
            for end in jpeg_end_markers:
                chunk = decoded[start:end]
                # 验证是否是有效的 JPEG（以 \xff\xd8 开头）
                if chunk.startswith(b'\xff\xd8'):
                    images.append(base64.b64encode(chunk).decode('ascii'))
                start = end
            if len(images) > 1:
                return images
    except Exception as e:
        print(f"[拆分] base64 解码失败: {e}")
    
    # 方法3: 检测多个 data:image 头
    if 'data:image' in combined_str:
        parts = combined_str.split('data:image')
        for i, part in enumerate(parts):
            if i == 0:
                continue  # 第一个是空的
            # 重新加上 data:image 前缀
            full = 'data:image' + part
            images.append(full)
        if len(images) > 1:
            print(f"[拆分] 检测到 {len(images)} 个 data:image 头")
            return images
    
    # 无法拆分，返回原始字符串
    return [combined_str] if combined_str else []

def extract_images_from_data(data):
    """
    从 webhook 数据中提取所有图片
    """
    images = []
    
    # 优先处理 images_base64（快捷指令专用字段）
    if 'images_base64' in data:
        img_data = data['images_base64']
        if isinstance(img_data, list):
            for item in img_data:
                if isinstance(item, str) and len(item) > 100:
                    # 检查是否是合并的多图
                    split_images = split_combined_base64(item)
                    images.extend(split_images)
        elif isinstance(img_data, str) and len(img_data) > 100:
            split_images = split_combined_base64(img_data)
            images.extend(split_images)
        print(f"[解析] images_base64: 发现 {len(images)} 张图")
    
    # 其他可能的图片字段
    other_paths = [
        'images',
        'media', 
        'pictures',
        'image_urls',
        'data.images',
        'data.media',
    ]
    
    for path in other_paths:
        parts = path.split('.')
        current = data
        try:
            for part in parts:
                current = current[part]
            if isinstance(current, list):
                for item in current:
                    if isinstance(item, str) and len(item) > 100:
                        if item not in images:
                            images.append(item)
                    elif isinstance(item, dict):
                        for key in ['url', 'src', 'link', 'uri', 'path', 'base64']:
                            if key in item and isinstance(item[key], str) and len(item[key]) > 100:
                                if item[key] not in images:
                                    images.append(item[key])
                                break
        except (KeyError, TypeError):
            continue
    
    # 去重
    seen = set()
    unique_images = []
    for img in images:
        if img and img not in seen:
            seen.add(img)
            unique_images.append(img)
    
    return unique_images

def save_base64_image(base64_str, save_dir, index):
    """保存 base64 编码的图片"""
    try:
        # 处理 data:image/xxx;base64, 格式
        if base64_str.startswith('data:image'):
            match = re.match(r'data:image/(\w+);base64,(.+)', base64_str)
            if match:
                ext = match.group(1)
                if ext == 'jpeg':
                    ext = 'jpg'
                img_data = base64.b64decode(match.group(2))
            else:
                return None
        else:
            # 纯 base64，尝试解码
            img_data = base64.b64decode(base64_str)
            
            # 检测图片格式
            if img_data.startswith(b'\xff\xd8'):
                ext = 'jpg'
            elif img_data.startswith(b'\x89PNG'):
                ext = 'png'
            elif img_data.startswith(b'GIF8'):
                ext = 'gif'
            elif img_data.startswith(b'RIFF') and b'WEBP' in img_data[:12]:
                ext = 'webp'
            else:
                ext = 'jpg'  # 默认
        
        filename = f"image_{index+1}.{ext}"
        filepath = os.path.join(save_dir, filename)
        with open(filepath, 'wb') as f:
            f.write(img_data)
        
        # 打印图片大小
        size_kb = len(img_data) / 1024
        print(f"[保存] {filename} ({size_kb:.1f} KB)")
        return filename
        
    except Exception as e:
        print(f"[失败] 图片 {index+1}: {e}")
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
        print(f"\n{'='*50}")
        print(f"[请求] {timestamp}")
        print(f"[来源] {data.get('source', 'unknown')}")
        print(f"[标题] {data.get('title', '')[:50]}...")
        
        images = extract_images_from_data(data)
        print(f"[图片] 发现 {len(images)} 张")
        
        # 保存图片
        saved_images = []
        for i, img_data in enumerate(images):
            filename = save_base64_image(img_data, request_dir, i)
            if filename:
                saved_images.append(filename)
        
        print(f"[结果] 成功保存 {len(saved_images)}/{len(images)} 张")
        print(f"{'='*50}\n")
        
        # 保存原始 JSON
        json_file = f"{request_dir}/data.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            # 不保存完整的 base64（太大），只保存前100字符
            save_data = dict(data)
            if 'images_base64' in save_data and isinstance(save_data['images_base64'], list):
                save_data['images_base64_preview'] = [
                    img[:100] + '...' if len(img) > 100 else img 
                    for img in save_data['images_base64']
                ]
                save_data['images_base64_count'] = len(save_data['images_base64'])
            
            json.dump({
                "received_at": timestamp,
                "image_count": len(images),
                "saved_count": len(saved_images),
                "saved_images": saved_images,
                "data": save_data
            }, f, ensure_ascii=False, indent=2)
        
        # 保存文本摘要
        text_file = f"{request_dir}/summary.txt"
        with open(text_file, 'w', encoding='utf-8') as f:
            f.write(f"来源: {data.get('source', 'unknown')}\n")
            f.write(f"链接: {data.get('url', '')}\n")
            f.write(f"标题: {data.get('title', '')}\n")
            f.write(f"时间: {timestamp}\n")
            f.write(f"图片数量: {len(images)} 张\n")
            f.write(f"保存成功: {len(saved_images)} 张\n\n")
            
            if saved_images:
                f.write("图片文件:\n")
                for img in saved_images:
                    f.write(f"  - {img}\n")
                f.write("\n")
            
            f.write("内容:\n")
            f.write(f"{data.get('content', '')}\n")
        
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        response = {
            "success": True,
            "saved_dir": f"xhs_{timestamp}",
            "image_count": len(images),
            "saved_count": len(saved_images),
            "images": saved_images
        }
        self.wfile.write(json.dumps(response, ensure_ascii=False).encode())
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def log_message(self, format, *args):
        # 静默默认日志
        pass

if __name__ == '__main__':
    print("=" * 50)
    print("XHS Webhook Server v2.1")
    print(f"端口: {PORT}")
    print(f"保存目录: {WEBHOOK_DIR}")
    print("=" * 50)
    print("\n修复内容:")
    print("  - 支持快捷指令合并的多图 base64")
    print("  - 自动检测换行分隔的多图")
    print("  - 自动检测 JPEG 结束标记拆分")
    print("  - 支持 data:image 格式\n")
    
    with socketserver.TCPServer(("", PORT), WebhookHandler) as httpd:
        print("服务器已启动，等待请求...\n")
        httpd.serve_forever()
