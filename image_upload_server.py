#!/usr/bin/env python3
"""
HTTP Image Upload Proxy for OpenClaw - iOS Safari Compatible
"""

import os
import sys
import json
import uuid
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler

UPLOAD_DIR = Path("/root/.openclaw/media/inbound")
COMPRESSED_DIR = Path("/root/.openclaw/media/compressed")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
COMPRESSED_DIR.mkdir(parents=True, exist_ok=True)

def compress_image(input_path, output_path, target_kb=800, max_dimension=1600):
    try:
        from PIL import Image
    except ImportError:
        return None, "Pillow not installed"
    
    try:
        img = Image.open(input_path)
    except Exception as e:
        return None, f"Cannot open image: {e}"
    
    if img.mode in ('RGBA', 'P'):
        img = img.convert('RGB')
    
    width, height = img.size
    if width > max_dimension or height > max_dimension:
        ratio = min(max_dimension / width, max_dimension / height)
        width = int(width * ratio)
        height = int(height * ratio)
        img = img.resize((width, height), Image.LANCZOS)
    
    target_bytes = target_kb * 1024
    quality = 95
    
    while quality >= 30:
        img.save(output_path, 'JPEG', quality=quality, optimize=True)
        if os.path.getsize(output_path) <= target_bytes:
            return output_path, None
        quality -= 5
    
    while os.path.getsize(output_path) > target_bytes and (width > 100 or height > 100):
        width = int(width * 0.8)
        height = int(height * 0.8)
        img_resized = img.resize((width, height), Image.LANCZOS)
        img_resized.save(output_path, 'JPEG', quality=85, optimize=True)
    
    return output_path, None

def parse_multipart(headers, body):
    content_type = headers.get('Content-Type', '')
    if not content_type.startswith('multipart/form-data'):
        return None
    
    parts = content_type.split('boundary=')
    if len(parts) < 2:
        return None
    boundary = parts[1].strip().strip('"')
    
    delimiter = f'--{boundary}'.encode()
    end_delimiter = f'--{boundary}--'.encode()
    
    parts_list = []
    start = body.find(delimiter)
    
    while start != -1:
        end = body.find(delimiter, start + len(delimiter))
        if end == -1:
            end = body.find(end_delimiter, start + len(delimiter))
        if end == -1:
            break
        
        part = body[start + len(delimiter):end]
        if part.startswith(b'\r\n'):
            part = part[2:]
        
        header_end = part.find(b'\r\n\r\n')
        if header_end == -1:
            start = end
            continue
        
        headers_text = part[:header_end].decode('utf-8', errors='replace')
        part_body = part[header_end + 4:]
        if part_body.endswith(b'\r\n'):
            part_body = part_body[:-2]
        
        filename = None
        name = None
        for line in headers_text.split('\r\n'):
            if line.lower().startswith('content-disposition:'):
                if 'name="' in line:
                    name_start = line.find('name="') + 6
                    name_end = line.find('"', name_start)
                    name = line[name_start:name_end]
                if 'filename="' in line:
                    fn_start = line.find('filename="') + 10
                    fn_end = line.find('"', fn_start)
                    filename = line[fn_start:fn_end]
        
        parts_list.append({'name': name, 'filename': filename, 'body': part_body})
        start = end
    
    return parts_list

class ImageUploadHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def do_GET(self):
        if self.path in ('/', '/index.html'):
            self.send_html_form()
        elif self.path == '/health':
            self.send_json({'status': 'ok'})
        else:
            self.send_error(404)
    
    def do_POST(self):
        if self.path == '/upload':
            self.handle_upload()
        else:
            self.send_error(404)
    
    def send_html_form(self):
        html = '''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <title>Upload</title>
    <style>
        * { -webkit-tap-highlight-color: transparent; box-sizing: border-box; }
        body { font-family: -apple-system, sans-serif; margin: 0; padding: 20px; background: #f2f2f7; }
        .wrap { max-width: 400px; margin: 0 auto; }
        h1 { font-size: 22px; margin: 0 0 8px; }
        p.desc { color: #666; font-size: 14px; margin: 0 0 20px; }
        
        #pickBtn {
            display: block; width: 100%; padding: 40px 20px;
            border: 2px dashed #007AFF; border-radius: 12px;
            background: #f0f7ff; text-align: center;
            font-size: 17px; color: #007AFF; font-weight: 500;
            margin-bottom: 16px; cursor: pointer;
        }
        #pickBtn:active { background: #e0efff; }
        
        #fileInput { position: absolute; left: -9999px; }
        
        #preview {
            width: 100%; max-height: 250px; object-fit: cover;
            border-radius: 12px; margin-bottom: 16px; display: none;
        }
        
        #upBtn {
            display: block; width: 100%; padding: 16px;
            background: #007AFF; color: white; border: none;
            border-radius: 12px; font-size: 17px; font-weight: 600;
            cursor: pointer;
        }
        #upBtn:disabled { background: #ccc; }
        #upBtn:active:not(:disabled) { opacity: 0.8; }
        
        #status {
            margin-top: 16px; padding: 16px; border-radius: 12px;
            font-size: 15px; line-height: 1.5; display: none;
        }
        #status.ok { background: #d4edda; color: #155724; display: block; }
        #status.err { background: #f8d7da; color: #721c24; display: block; }
        #status.info { background: #fff3cd; color: #856404; display: block; }
        
        .tip { color: #999; font-size: 13px; text-align: center; margin-top: 20px; }
    </style>
</head>
<body>
<div class="wrap">
    <h1>📤 Upload Image</h1>
    <p class="desc">Auto-compress for OpenClaw analysis</p>
    
    <button id="pickBtn" type="button">Tap to select photo</button>
    <input type="file" id="fileInput" accept="image/*">
    
    <img id="preview">
    <button id="upBtn" type="button" disabled>Upload</button>
    
    <div id="status"></div>
    
    <p class="tip">After upload, return to Clawket and send "analyze"</p>
</div>

<script>
(function() {
    'use strict';
    var pickBtn = document.getElementById('pickBtn');
    var fileInput = document.getElementById('fileInput');
    var preview = document.getElementById('preview');
    var upBtn = document.getElementById('upBtn');
    var status = document.getElementById('status');
    var file = null;
    
    function show(msg, cls) {
        status.className = cls || 'info';
        status.innerHTML = msg;
        status.style.display = 'block';
    }
    
    function hide() {
        status.style.display = 'none';
    }
    
    pickBtn.addEventListener('click', function() {
        hide();
        fileInput.click();
    });
    
    fileInput.addEventListener('change', function() {
        if (fileInput.files && fileInput.files.length > 0) {
            file = fileInput.files[0];
            var reader = new FileReader();
            reader.onload = function(e) {
                preview.src = e.target.result;
                preview.style.display = 'block';
                upBtn.disabled = false;
                show('Ready: ' + file.name + ' (' + Math.round(file.size/1024) + ' KB)', 'info');
            };
            reader.onerror = function() {
                show('Cannot read file', 'err');
            };
            reader.readAsDataURL(file);
        }
    });
    
    upBtn.addEventListener('click', function() {
        if (!file) return;
        
        upBtn.disabled = true;
        show('Uploading...', 'info');
        
        var formData = new FormData();
        formData.append('image', file, file.name);
        
        var xhr = new XMLHttpRequest();
        xhr.open('POST', 'upload', true);
        xhr.timeout = 60000;
        
        xhr.onload = function() {
            upBtn.disabled = false;
            if (xhr.status >= 200 && xhr.status < 300) {
                try {
                    var data = JSON.parse(xhr.responseText);
                    if (data.success) {
                        show('✅ Success!<br>Original: ' + data.original_size + '<br>Compressed: ' + data.compressed_size, 'ok');
                    } else {
                        show('❌ ' + (data.error || 'Failed'), 'err');
                    }
                } catch(e) {
                    show('❌ Parse error: ' + e.message, 'err');
                }
            } else {
                show('❌ HTTP ' + xhr.status, 'err');
            }
        };
        
        xhr.onerror = function() {
            upBtn.disabled = false;
            show('❌ Network error. Check connection.', 'err');
        };
        
        xhr.ontimeout = function() {
            upBtn.disabled = false;
            show('❌ Timeout. File too large?', 'err');
        };
        
        xhr.onabort = function() {
            upBtn.disabled = false;
            show('❌ Upload cancelled', 'err');
        };
        
        xhr.send(formData);
    });
})();
</script>
</body>
</html>'''
        
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(html.encode())
    
    def send_json(self, data, status=200):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())
    
    def handle_upload(self):
        content_length = int(self.headers.get('Content-Length', 0))
        if content_length == 0:
            self.send_json({'success': False, 'error': 'No content'}, 400)
            return
        
        body = self.rfile.read(content_length)
        parts = parse_multipart(self.headers, body)
        
        if not parts:
            self.send_json({'success': False, 'error': 'Invalid multipart data'}, 400)
            return
        
        image_part = None
        for part in parts:
            if part.get('name') == 'image' and part.get('filename'):
                image_part = part
                break
        
        if not image_part:
            self.send_json({'success': False, 'error': 'No image file found'}, 400)
            return
        
        filename = image_part['filename']
        ext = Path(filename).suffix.lower()
        if ext not in ('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.heic'):
            self.send_json({'success': False, 'error': 'File must be an image'}, 400)
            return
        
        uid = str(uuid.uuid4())[:8]
        original_path = UPLOAD_DIR / f"{uid}_original{ext}"
        compressed_path = COMPRESSED_DIR / f"{uid}_compressed.jpg"
        
        try:
            with open(original_path, 'wb') as f:
                f.write(image_part['body'])
            
            original_size = os.path.getsize(original_path)
            original_size_str = f"{original_size / 1024:.1f} KB" if original_size < 1024*1024 else f"{original_size / (1024*1024):.2f} MB"
            
            result_path, error = compress_image(original_path, compressed_path)
            
            if error:
                self.send_json({'success': False, 'error': error}, 500)
                return
            
            compressed_size = os.path.getsize(result_path)
            compressed_size_str = f"{compressed_size / 1024:.1f} KB"
            
            self.send_json({
                'success': True,
                'filename': compressed_path.name,
                'original_size': original_size_str,
                'compressed_size': compressed_size_str
            })
        
        except Exception as e:
            self.send_json({'success': False, 'error': str(e)}, 500)

def run_server(port=18080):
    server = HTTPServer(('127.0.0.1', port), ImageUploadHandler)
    print(f"Server running at http://127.0.0.1:{port}/")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")

if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 18080
    run_server(port)
