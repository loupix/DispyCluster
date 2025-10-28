"""Dashboard web minimal pour visualiser l'état.

Expose:
- GET /health: statut du service
- GET /nodes: liste JSON des noeuds connus (STATE)
"""

from http.server import BaseHTTPRequestHandler, HTTPServer
import json

STATE = {
    "nodes": [],
}


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok"}).encode())
            return
        if self.path == "/nodes":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(STATE).encode())
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        html = """
        <html><head><title>DispyCluster Dashboard</title></head>
        <body>
        <h1>DispyCluster Dashboard</h1>
        <p>Endpoints: <a href='/health'>/health</a> | <a href='/nodes'>/nodes</a></p>
        </body></html>
        """
        self.wfile.write(html.encode())


def run(port: int = 8080):
    """Démarre un serveur HTTP simple sur le port indiqué."""
    server = HTTPServer(("0.0.0.0", port), Handler)
    print(f"Dashboard en écoute sur {port}")
    server.serve_forever()


if __name__ == "__main__":
    run()

