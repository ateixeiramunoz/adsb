#!/usr/bin/env python3
"""
HTTP Server for ADS-B Map

Serves the map HTML and JSON data files via HTTP to avoid CORS issues.
This allows the map to fetch updates dynamically without page reload.

Usage:
    python3 serve_map.py [--port 8000] [--host 127.0.0.1]
"""

import argparse
import http.server
import os
import socketserver
import sys
from pathlib import Path


class CORSRequestHandler(http.server.SimpleHTTPRequestHandler):
    """HTTP request handler with CORS headers."""
    
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()
    
    def log_message(self, format, *args):
        # Suppress default logging, or customize as needed
        pass


def main():
    parser = argparse.ArgumentParser(
        description="Serve ADS-B map files via HTTP",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Serve on default port 8000
  python3 serve_map.py

  # Serve on custom port
  python3 serve_map.py --port 8080

  # Serve on all interfaces
  python3 serve_map.py --host 0.0.0.0
        """
    )
    
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to serve on (default: 8000)"
    )
    
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host to bind to (default: 127.0.0.1)"
    )
    
    args = parser.parse_args()
    
    # Change to the script directory to serve files from there
    os.chdir(Path(__file__).parent)
    
    handler = CORSRequestHandler
    
    try:
        with socketserver.TCPServer((args.host, args.port), handler) as httpd:
            print(f"Serving ADS-B map files at http://{args.host}:{args.port}")
            print(f"Open http://{args.host}:{args.port}/adsb_map.html in your browser")
            print("Press Ctrl+C to stop")
            httpd.serve_forever()
    except OSError as e:
        if "Address already in use" in str(e):
            print(f"Error: Port {args.port} is already in use.", file=sys.stderr)
            print(f"Try a different port: python3 serve_map.py --port {args.port + 1}", file=sys.stderr)
        else:
            print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\nServer stopped.")


if __name__ == "__main__":
    main()

