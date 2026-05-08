#!/usr/bin/env python3
"""
Directory Watcher for Auto Image Compression

Watches /root/.openclaw/media/inbound/ for new images,
auto-compresses them, and moves to /root/.openclaw/media/compressed/

Usage:
    python3 /root/.openclaw/workspace/scripts/image_watch.py
    
Or run in background:
    nohup python3 /root/.openclaw/workspace/scripts/image_watch.py > /dev/null 2>&1 &
"""

import os
import sys
import time
import subprocess
from pathlib import Path

WATCH_DIR = Path("/root/.openclaw/media/inbound")
COMPRESSED_DIR = Path("/root/.openclaw/media/compressed")
COMPRESSOR_SCRIPT = Path("/root/.openclaw/workspace/scripts/image_compressor.py")

def process_file(filepath):
    """Process a single image file"""
    filepath = Path(filepath)
    if filepath.suffix.lower() not in ('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.heic'):
        return
    
    # Skip already compressed files
    if 'compressed' in filepath.name:
        return
    
    print(f"[WATCH] New image detected: {filepath.name}")
    
    output_path = COMPRESSED_DIR / f"{filepath.stem}.compressed.jpg"
    
    try:
        result = subprocess.run([
            sys.executable, str(COMPRESSOR_SCRIPT),
            str(filepath),
            '--output', str(output_path),
            '--target', '800'
        ], capture_output=True, text=True, timeout=30)
        
        if output_path.exists():
            print(f"[WATCH] Compressed: {output_path.name}")
        else:
            print(f"[WATCH] Compression failed for {filepath.name}")
    
    except Exception as e:
        print(f"[WATCH] Error processing {filepath.name}: {e}")

def watch_with_inotify():
    """Use inotifywait for efficient watching"""
    print(f"[WATCH] Watching {WATCH_DIR} for new images...")
    print(f"[WATCH] Press Ctrl+C to stop")
    
    # Process existing files first
    for f in sorted(WATCH_DIR.iterdir()):
        if f.is_file():
            process_file(f)
    
    try:
        import subprocess
        proc = subprocess.Popen([
            'inotifywait', '-m', '-e', 'create,moved_to',
            '--format', '%f', str(WATCH_DIR)
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        for line in proc.stdout:
            filename = line.strip()
            if filename:
                filepath = WATCH_DIR / filename
                # Small delay to ensure file is fully written
                time.sleep(0.5)
                if filepath.exists():
                    process_file(filepath)
    
    except FileNotFoundError:
        print("[WATCH] inotifywait not found, falling back to polling mode")
        watch_with_polling()
    
    except KeyboardInterrupt:
        print("\n[WATCH] Stopped.")

def watch_with_polling():
    """Fallback polling mode"""
    print(f"[WATCH] Polling {WATCH_DIR} every 2 seconds...")
    
    known_files = set(f.name for f in WATCH_DIR.iterdir() if f.is_file())
    
    try:
        while True:
            time.sleep(2)
            current_files = set(f.name for f in WATCH_DIR.iterdir() if f.is_file())
            new_files = current_files - known_files
            
            for filename in new_files:
                filepath = WATCH_DIR / filename
                if filepath.exists():
                    process_file(filepath)
            
            known_files = current_files
    
    except KeyboardInterrupt:
        print("\n[WATCH] Stopped.")

if __name__ == '__main__':
    WATCH_DIR.mkdir(parents=True, exist_ok=True)
    COMPRESSED_DIR.mkdir(parents=True, exist_ok=True)
    
    watch_with_inotify()
