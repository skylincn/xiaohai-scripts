#!/usr/bin/env python3
import http.server
import socketserver
import json
import os
from datetime import datetime
import hashlib

PORT = 8888
WEBHOOK_DIR = "/tmp/xhs_webhook"
os.makedirs(WEBHOOK_DIR, exist_ok=True)

# 简单去重：记录最近 100 个请求的 hash
_seen = []
_SEEN_MAX = 100

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
        filename = "{}/xhs_{}.json".format(WEBHOOK_DIR, timestamp)
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump({
                "received_at": timestamp,
                "data": data
            }, f, ensure_ascii=False, indent=2)
        
        text_file = "{}/xhs_{}.txt".format(WEBHOOK_DIR, timestamp)
        with open(text_file, 'w', encoding='utf-8') as f:
            f.write("来源: {}\n".format(data.get('source', 'unknown')))
            f.write("链接: {}\n".format(data.get('url', '')))
            f.write("标题: {}\n".format(data.get('title', '')))
            f.write("时间: {}\n\n".format(timestamp))
            f.write("内容:\n{}\n".format(data.get('content', '')))
        
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        response = {"success": True, "saved": "xhs_{}.txt".format(timestamp)}
        self.wfile.write(json.dumps(response).encode())
        
        print("收到数据，已保存到 {}".format(text_file))
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

with socketserver.TCPServer(("", PORT), WebhookHandler) as httpd:
    print("Webhook服务器运行在端口 {}".format(PORT))
    httpd.serve_forever()
