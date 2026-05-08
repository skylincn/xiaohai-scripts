#!/usr/bin/env python3
"""
Health Data Webhook Receiver for OpenClaw
Receives iOS HealthKit data via POST and stores for analysis
"""

import os
import json
import uuid
from datetime import datetime
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler

# Data storage directory
DATA_DIR = Path("/root/.openclaw/health_data")
DATA_DIR.mkdir(parents=True, exist_ok=True)

class HealthHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {args[0]}")

    def do_POST(self):
        if self.path != "/health-webhook/upload":
            self.send_error(404, "Not Found")
            return

        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            
            # Parse JSON
            data = json.loads(body.decode("utf-8"))
            
            # Add timestamp
            data["_received_at"] = datetime.now().isoformat()
            data["_device"] = self.headers.get("User-Agent", "unknown")
            
            # Save to file
            date_str = datetime.now().strftime("%Y-%m-%d")
            filename = DATA_DIR / f"health_{date_str}_{uuid.uuid4().hex[:8]}.json"
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            print(f"✅ Received health data: {filename}")
            
            # Respond success
            response = {"success": True, "received": len(body), "file": str(filename)}
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(response).encode("utf-8"))
            
        except json.JSONDecodeError:
            self.send_error(400, "Invalid JSON")
        except Exception as e:
            print(f"❌ Error: {e}")
            self.send_error(500, str(e))

    def do_GET(self):
        if self.path == "/health-webhook/status":
            # Return status and recent files
            files = sorted(DATA_DIR.glob("health_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)[:10]
            file_list = [{"name": f.name, "size": f.stat().st_size, "modified": datetime.fromtimestamp(f.stat().st_mtime).isoformat()} for f in files]
            
            response = {
                "status": "running",
                "data_dir": str(DATA_DIR),
                "recent_files": file_list,
                "total_files": len(list(DATA_DIR.glob("health_*.json")))
            }
            
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(response, ensure_ascii=False, indent=2).encode("utf-8"))
        else:
            self.send_error(404, "Not Found")

if __name__ == "__main__":
    PORT = 18420
    server = HTTPServer(("0.0.0.0", PORT), HealthHandler)
    print(f"🏥 Health Webhook Server running on port {PORT}")
    print(f"📁 Data directory: {DATA_DIR}")
    print(f"🔗 POST http://<your-server>:{PORT}/health-webhook/upload")
    print(f"🔗 GET  http://<your-server>:{PORT}/health-webhook/status")
    server.serve_forever()
