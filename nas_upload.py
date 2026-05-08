#!/usr/bin/env python3
"""NAS共享盘上传脚本 - 通过DSM API上传文件到NAS共享目录"""
import os
import sys
import requests
import time
import random
import string

NAS_HOST = "152.136.61.172"
NAS_PORT = 7500
NAS_USER = "skyyz"
NAS_PASS = "Lin998007"
BASE_PATH = "/homes/skyyz/shared"  # DSM API的共享路径格式

COOKIE_FILE = "/tmp/nas_dsm_cookies.txt"
SID = None

def get_sid():
    """登录DSM获取SID"""
    url = f"http://{NAS_HOST}:{NAS_PORT}/webapi/entry.cgi"
    params = {
        "api": "SYNO.API.Auth",
        "method": "login",
        "version": "3",
        "account": NAS_USER,
        "passwd": NAS_PASS,
        "session": "FileStation",
        "format": "cookie"
    }
    try:
        r = requests.get(url, params=params, timeout=10)
        data = r.json()
        sid = data.get("data", {}).get("sid")
        if sid:
            # 保存cookies
            with open(COOKIE_FILE, "w") as f:
                f.write(sid)
            return sid
    except Exception as e:
        print(f"登录失败: {e}")
    return None

def load_sid():
    """加载缓存的SID"""
    if os.path.exists(COOKIE_FILE):
        with open(COOKIE_FILE) as f:
            sid = f.read().strip()
        # 验证SID是否有效
        url = f"http://{NAS_HOST}:{NAS_PORT}/webapi/entry.cgi"
        params = {"api": "SYNO.FileStation.List", "method": "list_share", "version": "1", "_sid": sid}
        try:
            r = requests.get(url, params=params, timeout=5)
            if r.json().get("success"):
                return sid
        except:
            pass
    return None

def get_sid_with_fallback():
    """获取SID，失败则重新登录"""
    sid = load_sid()
    if not sid:
        sid = get_sid()
    return sid

def list_dir(sid, path):
    """列出目录内容"""
    url = f"http://{NAS_HOST}:{NAS_PORT}/webapi/entry.cgi"
    params = {
        "api": "SYNO.FileStation.List",
        "method": "list",
        "version": "2",
        "folder_path": path,
        "_sid": sid
    }
    r = requests.get(url, params=params, timeout=10)
    data = r.json()
    if data.get("success"):
        return data.get("data", {}).get("files", [])
    return []

def upload_file(sid, local_path, remote_dir, remote_name=None):
    """上传文件到NAS共享盘"""
    url = f"http://{NAS_HOST}:{NAS_PORT}/webapi/entry.cgi"
    if remote_name is None:
        remote_name = os.path.basename(local_path)
    
    # 确保目录存在
    dir_path = f"{BASE_PATH}/{remote_dir}".replace("//", "/")
    
    files = {"file": (remote_name, open(local_path, "rb"), "application/octet-stream")}
    data = {
        "api": "SYNO.FileStation.Upload",
        "method": "upload",
        "version": "2",
        "path": dir_path,
        "overwrite": "true",
        "_sid": sid
    }
    try:
        r = requests.post(url, files=files, data=data, timeout=60)
        result = r.json()
        if result.get("success"):
            return True, f"上传成功: {remote_name}"
        else:
            error_code = result.get("error", {}).get("code", "unknown")
            return False, f"上传失败 code={error_code}"
    except Exception as e:
        return False, f"上传异常: {e}"
    finally:
        files["file"][1].close()

def main():
    if len(sys.argv) < 3:
        print("用法: nas_upload.py <本地文件> <目标目录> [远程文件名]")
        sys.exit(1)
    
    local_file = sys.argv[1]
    remote_dir = sys.argv[2]
    remote_name = sys.argv[3] if len(sys.argv) > 3 else None
    
    if not os.path.exists(local_file):
        print(f"文件不存在: {local_file}")
        sys.exit(1)
    
    sid = get_sid_with_fallback()
    if not sid:
        print("无法获取SID，登录失败")
        sys.exit(1)
    
    success, msg = upload_file(sid, local_file, remote_dir, remote_name)
    print(msg)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
