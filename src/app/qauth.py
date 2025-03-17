import os
import subprocess
import json
import asyncio
from http.server import BaseHTTPRequestHandler, HTTPServer

PORT = 8080
KEYS_DIR = "keys"

os.makedirs(KEYS_DIR, exist_ok=True)

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

# 🔹 Utility: Generate PGP Challenge


def generate_challenge() -> str:
    return os.urandom(16).hex()  # Secure random challenge

# 🔹 Async Aggregation (statistical state machine)


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
        if self.path == "/":
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(
                b"<h1>PGP Auth Server Running</h1><p>Try <code>/challenge</code> or <code>/verify</code></p>")
        elif self.path == "/challenge":
            client_ip = self.client_address[0]
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

            # Save new PGP public key
            key_path = os.path.join(KEYS_DIR, f"{client_ip}.key")
            if not os.path.exists(key_path):
                with open(key_path, "w") as f:
                    f.write(public_key)

            # Verify the signed challenge
            if verify_pgp_signature(signed_message):
                asyncio.create_task(event_queue.put(
                    {"ip": client_ip, "state": "Valid"}))
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b" Authentication Successful!")
            else:
                self.send_response(403)
                self.end_headers()
                self.wfile.write(b" Authentication Failed!")

# 🔹 Start Server


async def start_server():
    server = HTTPServer(("0.0.0.0", PORT), PGPAuthHandler)
    print(f"Serving on port {PORT}")
    await asyncio.get_event_loop().run_in_executor(None, server.serve_forever)

# 🔹 Run Aggregator + Server


async def main():
    await asyncio.gather(start_server(), aggregator())

asyncio.run(main())
