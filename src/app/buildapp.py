#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "flask==3.*",
# ]
# ///

import ctypes
import platform
from decimal import Decimal, getcontext
import sys
import os
import subprocess

# Check if we are in a managed environment
IN_UV_ENV = os.getenv("UV_VIRTUAL_ENV") is not None

# Optional self-bootstrap mode


def bootstrap():
    """Attempt to install 'uv' and rerun the script in a managed environment."""
    print("Bootstrapping: Checking for 'uv' package manager...")
    try:
        subprocess.run(["uv", "--version"], check=True,
                       stdout=subprocess.DEVNULL)
    except FileNotFoundError:
        print("Error: 'uv' is not installed. Please install it manually.")
        sys.exit(1)

    print("Re-executing script with 'uv run'...")
    os.execvp("uv", ["uv", "run", sys.executable] + sys.argv)


# Handle manual opt-in for bootstrapping
if "--bootstrap" in sys.argv:
    bootstrap()

# Import standard library components

# Optional dependency handling
try:
    import flask
    USE_FLASK = True
except ImportError:
    USE_FLASK = False

# Set decimal precision
getcontext().prec = 28

# Platform abstraction


class PlatformFactory:
    """Detect and return the current platform."""
    @staticmethod
    def get_platform():
        if os.name == 'nt':
            return "windows"
        elif os.name == 'posix':
            return "posix"
        raise NotImplementedError("Unsupported platform")

    @staticmethod
    def create_platform_instance():
        plat = PlatformFactory.get_platform()
        return WindowsPlatform() if plat == "windows" else LinuxPlatform()


class PlatformInterface:
    """Abstract base for platform-specific implementations."""

    def load_c_library(self):
        raise NotImplementedError()


class WindowsPlatform(PlatformInterface):
    def load_c_library(self):
        try:
            return ctypes.CDLL("msvcrt.dll")
        except OSError:
            return None


class LinuxPlatform(PlatformInterface):
    def load_c_library(self):
        try:
            return ctypes.CDLL("libc.so.6")
        except OSError:
            return None


# Run some platform-dependent code
platform_instance = PlatformFactory.create_platform_instance()
libc = platform_instance.load_c_library()

if USE_FLASK:
    print("Flask is available! Running with Flask support.")
else:
    print("Running without Flask.")

# Main entrypoint
if __name__ == "__main__":
    print("Script executed successfully.")
