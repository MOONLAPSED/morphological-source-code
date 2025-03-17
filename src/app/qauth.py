import os
import subprocess
import json
import asyncio
from http.server import BaseHTTPRequestHandler, HTTPServer
from dataclasses import dataclass

PORT = 8080
KEYS_DIR = "keys"

os.makedirs(KEYS_DIR, exist_ok=True)

# 🔹 Utility: Generate PGP Challenge


def generate_challenge() -> str:
    return os.urandom(16).hex()

# 🔹 Utility: Run GPG in a subprocess


def verify_pgp_signature(signed_message: str) -> bool:
    """Uses GPG to verify the signed message."""
    try:
        proc = subprocess.run(
            ["gpg", "--verify"],
            input=signed_message.encode(),
            capture_output=True,
            text=True
        )
        return "Good signature" in proc.stderr
    except Exception:
        return False

# 🔹 DataClass for Rendering Responses


@dataclass
class PageRenderer:
    title: str
    content: str
    content_type: str = "text/html"

    def render(self) -> bytes:
        """Returns the formatted response as bytes."""
        if self.content_type == "application/json":
            return json.dumps({"title": self.title, "content": self.content}).encode()
        return f"<h1>{self.title}</h1><p>{self.content}</p>".encode()


# 🔹 Routing System (URL to Page Data)
SimpleRouter = {
    "/": PageRenderer("PGP Auth Server", "Try <code>/challenge</code> or <code>/verify</code>"),
    "/about": PageRenderer("About", "This is a minimal PGP authentication server."),
}

# 🔹 Async Aggregation


async def aggregator():
    state = []
    while True:
        event = await event_queue.get()
        state.append(event)
        print("Aggregated State:", state)

event_queue = asyncio.Queue()

# 🔹 HTTP Handler


class PGPAuthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path in SimpleRouter:
            page = SimpleRouter[self.path]
            self.send_response(200)
            self.send_header("Content-Type", page.content_type)
            self.end_headers()
            self.wfile.write(page.render())
        elif self.path == "/challenge":
            challenge = generate_challenge()
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(challenge.encode())
        else:
            self.send_error(404, "Not Found")

    def do_POST(self):
        if self.path == "/verify":
            content_length = int(self.headers["Content-Length"])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data)

            public_key = data.get("publicKey")
            signed_message = data.get("signedMessage")
            client_ip = self.client_address[0]

            if not public_key or not signed_message:
                self.send_response(400)
                self.end_headers()
                return

            key_path = os.path.join(KEYS_DIR, f"{client_ip}.key")
            if not os.path.exists(key_path):
                with open(key_path, "w") as f:
                    f.write(public_key)

            if verify_pgp_signature(signed_message):
                asyncio.create_task(event_queue.put(
                    {"ip": client_ip, "state": "Valid"}))
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"Authentication Successful!")
            else:
                self.send_response(403)
                self.end_headers()
                self.wfile.write(b"Authentication Failed!")

# 🔹 Start Server


async def start_server():
    server = HTTPServer(("0.0.0.0", PORT), PGPAuthHandler)
    print(f"Serving on port {PORT}")
    await asyncio.get_event_loop().run_in_executor(None, server.serve_forever)

# 🔹 Run Aggregator + Server


async def main():
    await asyncio.gather(start_server(), aggregator())
    SimpleRouter["/api/status"] = PageRenderer("Server Status", "Running OK", "application/json")
    SimpleRouter["/docs"] = PageRenderer("Documentation", str("# Welcome to the Docs!"))
asyncio.run(main())
