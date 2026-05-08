#!/usr/bin/env python3
"""
Auto Image Analyzer for OpenClaw

Watches /root/.openclaw/media/compressed/ for new images,
auto-analyzes them, and sends results back to user's session.

Usage:
    python3 /root/.openclaw/workspace/scripts/auto_image_analyzer.py
"""

import os
import sys
import time
import json
import subprocess
from pathlib import Path
from datetime import datetime

WATCH_DIR = Path("/root/.openclaw/media/compressed")
STATE_FILE = Path("/root/.openclaw/media/.analyzer_state.json")
LOG_FILE = Path("/root/.openclaw/logs/auto_image_analyzer.log")

def log(msg):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {msg}"
    print(line)
    with open(LOG_FILE, 'a') as f:
        f.write(line + '\n')

def load_state():
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"processed": []}

def save_state(state):
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f)

def analyze_image(image_path):
    """Analyze image using describe_image tool via OpenClaw CLI"""
    try:
        # Use the image tool via openclaw CLI or call API directly
        # For now, we'll write a marker file that the agent can detect
        marker_path = Path("/root/.openclaw/media/.pending_analysis")
        with open(marker_path, 'w') as f:
            f.write(str(image_path))
        return True
    except Exception as e:
        log(f"Error marking image for analysis: {e}")
        return False

def get_latest_image():
    """Get the most recently modified image in compressed directory"""
    images = [f for f in WATCH_DIR.iterdir() if f.is_file() and f.suffix.lower() in ('.jpg', '.jpeg', '.png')]
    if not images:
        return None
    return max(images, key=lambda f: f.stat().st_mtime)

def watch_and_analyze():
    """Main watch loop"""
    log("Auto Image Analyzer started")
    log(f"Watching: {WATCH_DIR}")
    
    state = load_state()
    
    try:
        while True:
            time.sleep(3)
            
            latest = get_latest_image()
            if not latest:
                continue
            
            # Skip already processed
            if str(latest) in state["processed"]:
                continue
            
            # Check if file is still being written (wait for compression to finish)
            time.sleep(1)
            
            log(f"New image detected: {latest.name}")
            
            # Mark for analysis
            marker_path = Path("/root/.openclaw/media/.pending_analysis")
            with open(marker_path, 'w') as f:
                f.write(str(latest))
            
            # Record as processed
            state["processed"].append(str(latest))
            # Keep only last 100 entries
            state["processed"] = state["processed"][-100:]
            save_state(state)
            
            log(f"Marked for analysis: {latest.name}")
    
    except KeyboardInterrupt:
        log("Stopped by user")
    except Exception as e:
        log(f"Error: {e}")

if __name__ == '__main__':
    WATCH_DIR.mkdir(parents=True, exist_ok=True)
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    watch_and_analyze()
