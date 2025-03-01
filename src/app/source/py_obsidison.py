import os
import json
import logging
import http.client
import socket
import asyncio

import websockets

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(message)s')

# Configuration Constants
DEFAULT_CONFIG_PATH = 'config.json'
WEBSOCKET_TIMEOUT = 5
DEFAULT_OBSIDIAN_PATH = r'C:\Users\DEV\scoop\apps\obsidian\current\obsidian.exe'
TS_SERVER_HOST = 'localhost'
TS_SERVER_PORT = 2112


class ConfigLoader:
    @staticmethod
    def load_config(config_path=DEFAULT_CONFIG_PATH):
        """Load configuration from a file."""
        if os.path.exists(config_path):
            with open(config_path, 'r') as file:
                config = json.load(file)
                logging.info(f"Loaded config from {config_path}.")
                return config
        else:
            raise FileNotFoundError(f"Configuration file '{config_path}' not found.")


class DenoBridge:
    def __init__(self, config):
        self.config = config
        self.deno_host = self.config.get('deno_host', 'localhost')
        self.deno_http_port = self.config.get('deno_http_port', 3000)
        self.deno_ws_port = self.config.get('deno_ws_port', 3001)
        logging.info("DenoBridge initialized.")

    def send_request(self, endpoint, data=None):
        """Send an HTTP request to the Deno server."""
        conn = http.client.HTTPConnection(self.deno_host, self.deno_http_port)
        headers = {'Content-Type': 'application/json'}
        json_data = json.dumps(data) if data else None
        conn.request("POST", f"/{endpoint}", body=json_data, headers=headers)
        response = conn.getresponse()
        response_data = response.read().decode()

        if response.status == 200:
            logging.info(f"Received response: {response_data}")
            return json.loads(response_data)
        else:
            logging.error(f"HTTP error {response.status}: {response_data}")
            response.raise_for_status()

    async def send_websocket_message(self, message):
        """Send a message via WebSocket to Deno."""
        uri = f"ws://{self.deno_host}:{self.deno_ws_port}"
        async with websockets.connect(uri) as ws:
            await ws.send(json.dumps(message))
            logging.info(f"Sent message to Deno WebSocket: {message}")
            try:
                response = await asyncio.wait_for(ws.recv(), timeout=WEBSOCKET_TIMEOUT)
                logging.info(f"Received WebSocket response: {response}")
                return json.loads(response)
            except asyncio.TimeoutError:
                logging.error("WebSocket response timed out.")

    def verify_plugin_installed(self):
        """Check if the Obsidian plugin is installed via Deno."""
        try:
            response = self.send_request('verify-plugin', {'plugin_name': 'obsidian-plugin'})
            return response.get('installed', False)
        except Exception as e:
            logging.error(f"Error verifying plugin: {e}")
            return False

    def install_plugin(self):
        """Install the plugin using Deno."""
        try:
            response = self.send_request('install-plugin', {'plugin_name': 'obsidian-plugin'})
            logging.info(f"Plugin installed successfully: {response}")
            return response
        except Exception as e:
            logging.error(f"Error installing plugin: {e}")
            return None

    async def execute_plugin_task(self, task_data):
        """Execute a plugin task via WebSocket."""
        response = await self.send_websocket_message({'task': 'execute', 'data': task_data})
        return response


def sanitize_path(path):
    """Sanitize paths by trimming and removing quotes."""
    path = path.strip()
    if path.startswith(("'", '"')) and path.endswith(("'", '"')):
        path = path[1:-1]
    return path


def verify_obsidian_path(path):
    """Verify if Obsidian is installed at the given path."""
    return os.path.exists(path)


def ping_ts_server(host, port=TS_SERVER_PORT, timeout=WEBSOCKET_TIMEOUT):
    """Ping the Obsidian TypeScript server."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            logging.info(f"Successfully connected to {host}:{port}")
            return True
    except (socket.timeout, socket.error) as e:
        logging.error(f"Error connecting to {host}:{port} - {e}")
        return False


def main():
    # Load configuration
    config = ConfigLoader.load_config(DEFAULT_CONFIG_PATH)
    
    # Initialize DenoBridge
    bridge = DenoBridge(config)
    
    # Verify Obsidian plugin
    if not bridge.verify_plugin_installed():
        logging.info("Plugin is not installed. Installing...")
        bridge.install_plugin()

    # Verify Obsidian installation path
    obsidian_path = config.get('obsidian_path', DEFAULT_OBSIDIAN_PATH)
    if not verify_obsidian_path(obsidian_path):
        user_input = input("Would you like to input the installation path manually? (Y/N): ").strip().lower()
        if user_input == 'y':
            obsidian_path = sanitize_path(input("Enter the full path to Obsidian: "))
            if not verify_obsidian_path(obsidian_path):
                logging.error(f"Invalid path: {obsidian_path}, path does not exist.")
                return
        else:
            logging.info("Please ensure Obsidian is installed correctly.")
            return

    # Ping the TS server
    if not ping_ts_server(TS_SERVER_HOST):
        logging.error("Obsidian TS-server is not reachable. Please start the server.")
        return

    # Example task execution via WebSocket
    task_data = {"action": "create_note", "note_title": "My New Note", "content": "This is the note content"}
    asyncio.run(bridge.execute_plugin_task(task_data))
    
    logging.info("Script completed successfully!")


if __name__ == "__main__":
    main()