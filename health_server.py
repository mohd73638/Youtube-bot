#!/usr/bin/env python3
"""
Health check server for UptimeRobot monitoring
This runs alongside the Telegram bot to provide a health endpoint
"""
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import time
import os

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/" or self.path == "/health":
            self.send_response(200)
            self.send_header("Content-type", "text/plain")
            self.end_headers()
            
            status_message = f"""🤖 YouTube Videos Saver Bot - Health Check
✅ Status: ONLINE
⏰ Time: {time.strftime( %Y-%m-%d %H:%M:%S UTC , time.gmtime())}
📱 Bot: @saveruvidbot
🔗 Channel: @atheraber
🎥 Supports: YouTube, Instagram, Facebook
"""
            self.wfile.write(status_message.encode())
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        # Suppress default logging to reduce noise
        pass

def start_health_server():
    """Start the health check server on port 5000"""
    try:
        server = HTTPServer(("0.0.0.0", 5000), HealthHandler)
        print("Health check server started on http://0.0.0.0:5000")
        server.serve_forever()
    except Exception as e:
        print(f"Failed to start health server: {e}")

if __name__ == "__main__":
    start_health_server()
