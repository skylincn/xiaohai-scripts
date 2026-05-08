#!/usr/bin/env python3
"""
feishu_file_sender.py - 小海虾/小河虾通用版
上传文件到飞书群并发链接

用法：
  python3 feishu_file_sender.py <文件路径> [群ID]

配置：
  首次运行自动引导，或手动编辑 CONFIG_FILE
"""

import os
import sys
import json
import urllib.request
import urllib.parse
import argparse
from pathlib import Path
from datetime import datetime

# ============ 配置 ============
CONFIG_FILE = Path(__file__).parent / ".feishu_file_config.json"
DEFAULT_CHAT_ID = "oc_630adbadb3123a7dca268237206c42ad"  # 小虾米的小海鲜们
# =============================

def load_config():
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE) as f:
            return json.load(f)
    return {
        "feishu_app_id": "",
        "feishu_app_secret": "",
        "chat_id": DEFAULT_CHAT_ID
    }

def save_config(cfg):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(cfg, f, indent=2)

def get_token(app_id, app_secret):
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    data = json.dumps({"app_id": app_id, "app_secret": app_secret}).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        result = json.load(resp)
    if result.get("code") != 0:
        raise Exception(f"获取token失败: {result}")
    return result["tenant_access_token"]

def upload_and_send(file_path, chat_id, feishu_app_id, feishu_app_secret):
    """上传文件到飞书并发消息"""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"文件不存在: {file_path}")
    
    file_name = os.path.basename(file_path)
    file_size = os.path.getsize(file_path)
    ext = os.path.splitext(file_name)[1].lower()
    
    # 根据扩展名判断file_type
    mime_map = {
        ".pdf": "pdf", ".png": "png", ".jpg": "jpeg", ".jpeg": "jpeg",
        ".gif": "gif", ".mp4": "mp4", ".docx": "docx", ".xlsx": "xlsx",
        ".zip": "zip", ".txt": "txt", ".md": "markdown",
        ".stl": "stl", ".obj": "obj", ".3ds": "3ds",
        ".mp3": "mp3", ".wav": "wav", ".json": "json",
    }
    file_type = mime_map.get(ext, "file")
    
    print(f"[小海虾] 上传 {file_name} ({file_size/1024:.1f}KB)...")
    
    # 获取token
    token = get_token(feishu_app_id, feishu_app_secret)
    
    # 上传文件
    boundary = "----FeishuBoundary7o9r2n7d6b5k4h3j"
    
    body = b""
    body += f"--{boundary}\r\nContent-Disposition: form-data; name=\"file_name\"\r\n\r\n{file_name}\r\n".encode()
    body += f"--{boundary}\r\nContent-Disposition: form-data; name=\"file_type\"\r\n\r\n{file_type}\r\n".encode()
    body += f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{file_name}\"\r\n\r\n".encode()
    with open(file_path, "rb") as f:
        body += f.read()
    body += f"\r\n--{boundary}--\r\n".encode()
    
    url = "https://open.feishu.cn/open-apis/im/v1/files"
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Authorization": f"Bearer {token}"
        }
    )
    
    with urllib.request.urlopen(req, timeout=60) as resp:
        result = json.load(resp)
    
    if result.get("code") != 0:
        raise Exception(f"上传失败: {result}")
    
    file_key = result["data"]["file_key"]
    print(f"[小海虾] ✅ 上传成功，发送消息...")
    
    # 发送文件消息
    payload = {
        "receive_id": chat_id,
        "msg_type": "file",
        "content": json.dumps({"file_key": file_key, "file_name": file_name})
    }
    params = urllib.parse.urlencode({"receive_id_type": "chat_id"})
    send_url = f"https://open.feishu.cn/open-apis/im/v1/messages?{params}"
    
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        send_url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        }
    )
    
    with urllib.request.urlopen(req, timeout=10) as resp:
        send_result = json.load(resp)
    
    if send_result.get("code") != 0:
        raise Exception(f"发送失败: {send_result}")
    
    msg_id = send_result["data"]["message_id"]
    print(f"[小海虾] ✅ 消息已发！message_id: {msg_id}")
    return msg_id

def setup():
    """引导配置"""
    print("=" * 40)
    print("飞书文件上传器 - 配置向导")
    print("=" * 40)
    print()
    print("请提供飞书机器人凭证：")
    print("1. 打开 https://open.feishu.cn/")
    print("2. 创建应用，添加权限: im:resource, im:message:send_as_bot")
    print("3. 发布到「小虾米的小海鲜们」群")
    print("4. 获取 App ID 和 App Secret")
    print()
    
    app_id = input("App ID (cli_xxx): ").strip()
    app_secret = input("App Secret: ").strip()
    
    if not app_id or not app_secret:
        print("❌ App ID 和 Secret 不能为空！")
        sys.exit(1)
    
    config = {
        "feishu_app_id": app_id,
        "feishu_app_secret": app_secret,
        "chat_id": DEFAULT_CHAT_ID
    }
    save_config(config)
    print("✅ 配置已保存到:", CONFIG_FILE)
    return config

def main():
    parser = argparse.ArgumentParser(description="飞书文件上传器")
    parser.add_argument("file", nargs="?", help="要上传的文件路径")
    parser.add_argument("--chat-id", help=f"飞书群ID (默认: {DEFAULT_CHAT_ID})")
    parser.add_argument("--setup", action="store_true", help="重新配置")
    args = parser.parse_args()
    
    config = load_config()
    
    # 检查是否需要配置
    need_setup = not config.get("feishu_app_id") or args.setup
    
    if need_setup and not args.file:
        config = setup()
    elif not config.get("feishu_app_id"):
        print("❌ 未配置！请先运行 --setup 或提供文件")
        sys.exit(1)
    
    if args.chat_id:
        config["chat_id"] = args.chat_id
    
    if not args.file:
        print(f"用法: python3 {sys.argv[0]} <文件路径> [群ID]")
        print(f"当前配置: {CONFIG_FILE}")
        sys.exit(1)
    
    try:
        upload_and_send(
            file_path=args.file,
            chat_id=config["chat_id"],
            feishu_app_id=config["feishu_app_id"],
            feishu_app_secret=config["feishu_app_secret"]
        )
    except FileNotFoundError as e:
        print(f"❌ {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
