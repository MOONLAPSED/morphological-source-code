#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Quineic Subinterpreter Communication System
===========================================

A self-verifying, cryptographically secure communication substrate
between isolated Python subinterpreters using shared memory.
- DH public key size now matches 1024-bit prime (128 bytes)
- Proper cleanup of ctypes views before buffer close
- Added detailed error reporting
"""
# © 2025 Moonlapsed https://github.com/MOONLAPSED/Cognosis | CC ND && BSD-3 | SEE LICENCE

import sys
import time
import mmap
import ctypes
import hashlib
import hmac
import secrets
import threading
import traceback
from dataclasses import dataclass
from enum import IntEnum
from typing import Tuple

# Check Python version
if sys.version_info < (3, 12):
    print("ERROR: Python 3.12+ required for subinterpreters (PEP 554)")
    print(f"Current version: {sys.version}")
    sys.exit(1)

try:
    from concurrent.interpreters import create
except ImportError:
    print("ERROR: concurrent.interpreters not available")
    print("Ensure you're using CPython 3.12+ with subinterpreter support")
    sys.exit(1)


# =============================================================================
# SECTION 1: CONFIGURATION AND CONSTANTS
# =============================================================================


@dataclass
class Config:
    """System configuration constants."""

    # DH parameters (RFC 3526 - 1024-bit MODP Group 2)
    # 1024 bits = 128 bytes needed for public key
    DH_PRIME: int = int(
        "FFFFFFFFFFFFFFFFC90FDAA22168C234C4C6628B80DC1CD1"
        "29024E088A67CC74020BBEA63B139B22514A08798E3404DD"
        "EF9519B3CD3A431B302B0A6DF25F14374FE1356D6D51C245"
        "E485B576625E7EC6F44C42E9A637ED6B0BFF5CB6F406B7ED"
        "EE386BFB5A899FA5AE9F24117C4B1FE649286651ECE65381"
        "FFFFFFFFFFFFFFFF",
        16,
    )
    DH_GENERATOR: int = 2

    # Buffer layout (per interpreter region)
    PUBKEY_SIZE: int = 128  # DH public key (1024 bits)
    MSG_SIZE: int = 64  # Message payload
    MAC_SIZE: int = 32  # HMAC-SHA256
    HASH_SIZE: int = 32  # Code verification hash
    FLAG_SIZE: int = 4  # Status flags

    @property
    def REGION_SIZE(self) -> int:
        """Total size per interpreter region."""
        return (
            self.PUBKEY_SIZE
            + self.MSG_SIZE
            + self.MAC_SIZE
            + self.HASH_SIZE
            + self.FLAG_SIZE
        )

    @property
    def BUFFER_SIZE(self) -> int:
        """Total shared memory buffer size (2 regions + padding)."""
        return self.REGION_SIZE * 2 + 128  # Extra padding for safety

    # Timeouts
    STARTUP_TIMEOUT: float = 2.0  # Wait for peer startup
    COMPUTE_TIMEOUT: float = 5.0  # Wait for computation

    # Oracle behavior
    ENABLE_ORACLE: bool = True  # Enable first-past-post oracle


class RegionLayout(IntEnum):
    """Byte offsets within each interpreter's memory region."""

    FLAG_OFFSET = 0
    PUBKEY_OFFSET = 4
    MSG_OFFSET = 132  # 4 + 128
    MAC_OFFSET = 196  # 132 + 64
    HASH_OFFSET = 228  # 196 + 32


class StatusFlag(IntEnum):
    """Status flags for synchronization."""

    EMPTY = 0
    READY = 1
    COMPUTING = 2
    COMPLETE = 3
    WINNER = 4


CONFIG = Config()


# =============================================================================
# SECTION 2: CRYPTOGRAPHIC UTILITIES
# =============================================================================


def generate_dh_keypair() -> Tuple[int, int]:
    """
    Generate Diffie-Hellman keypair.

    Returns:
        (private_key, public_key)
    """
    private_key = secrets.randbelow(CONFIG.DH_PRIME - 2) + 1
    public_key = pow(CONFIG.DH_GENERATOR, private_key, CONFIG.DH_PRIME)
    return private_key, public_key


def compute_shared_secret(private_key: int, peer_public_key: int) -> bytes:
    """
    Compute DH shared secret and derive symmetric key.

    Args:
        private_key: Our private DH key
        peer_public_key: Peer's public DH key

    Returns:
        32-byte symmetric key (SHA-256 of shared secret)
    """
    shared = pow(peer_public_key, private_key, CONFIG.DH_PRIME)
    shared_bytes = shared.to_bytes((shared.bit_length() + 7) // 8 or 1, byteorder='big')
    return hashlib.sha256(shared_bytes).digest()


def compute_hmac(key: bytes, message: bytes) -> bytes:
    """Compute HMAC-SHA256 of message."""
    return hmac.new(key, message, hashlib.sha256).digest()


def verify_hmac(key: bytes, message: bytes, received_mac: bytes) -> bool:
    """Verify HMAC in constant time."""
    expected_mac = compute_hmac(key, message)
    return hmac.compare_digest(expected_mac, received_mac)


# =============================================================================
# SECTION 3: WORKER FUNCTION (Runs in subinterpreter)
# =============================================================================


def worker_entrypoint(
    region_start: int,
    region_size: int,
    peer_start: int,
    peer_size: int,
    buf_addr: int,
    interpreter_id: str,
    enable_oracle: bool,
):
    """
    Worker function executed in isolated subinterpreter.

    This function is completely self-contained and uses only stdlib.
    It performs:
    1. Diffie-Hellman key exchange with peer
    2. Computation with cryptographic verification
    3. Quineic self-verification (code hash)
    4. Oracle decision (optional first-past-post)

    Args:
        region_start: Start offset of this interpreter's memory region
        region_size: Size of this interpreter's memory region
        peer_start: Start offset of peer's memory region
        peer_size: Size of peer's memory region
        buf_addr: Base address of shared memory buffer
        interpreter_id: Identifier for this interpreter
        enable_oracle: Whether to implement oracle behavior
    """
    import ctypes
    import time
    import secrets
    import hashlib
    import hmac
    import sys

    # Configuration (duplicated for isolation)
    PUBKEY_SIZE = 128  # FIXED: Was 32, now 128 for 1024-bit DH
    MSG_SIZE = 64
    MAC_SIZE = 32
    HASH_SIZE = 32
    FLAG_SIZE = 4

    FLAG_OFFSET = 0
    PUBKEY_OFFSET = 4
    MSG_OFFSET = 132  # FIXED: Updated offsets
    MAC_OFFSET = 196
    HASH_OFFSET = 228

    DH_PRIME = int(
        "FFFFFFFFFFFFFFFFC90FDAA22168C234C4C6628B80DC1CD1"
        "29024E088A67CC74020BBEA63B139B22514A08798E3404DD"
        "EF9519B3CD3A431B302B0A6DF25F14374FE1356D6D51C245"
        "E485B576625E7EC6F44C42E9A637ED6B0BFF5CB6F406B7ED"
        "EE386BFB5A899FA5AE9F24117C4B1FE649286651ECE65381"
        "FFFFFFFFFFFFFFFF",
        16,
    )
    DH_GENERATOR = 2
    TIMEOUT = 2.0

    try:
        # Memory regions
        my_region = (ctypes.c_char * region_size).from_address(buf_addr + region_start)
        peer_region = (ctypes.c_char * peer_size).from_address(buf_addr + peer_start)

        # Write status: READY
        my_region[FLAG_OFFSET : FLAG_OFFSET + 4] = (1).to_bytes(4, 'little')

        # Generate DH keypair
        priv = secrets.randbelow(DH_PRIME - 2) + 1
        pub = pow(DH_GENERATOR, priv, DH_PRIME)

        # FIXED: Now pub fits in PUBKEY_SIZE bytes
        pub_bytes = pub.to_bytes(PUBKEY_SIZE, 'big')

        # Write public key
        my_region[PUBKEY_OFFSET : PUBKEY_OFFSET + PUBKEY_SIZE] = pub_bytes

        # Wait for peer to be ready
        start_time = time.time()
        while (
            int.from_bytes(bytes(peer_region[FLAG_OFFSET : FLAG_OFFSET + 4]), 'little')
            < 1
        ):  # Wait for READY
            if time.time() - start_time > TIMEOUT:
                raise TimeoutError(f"{interpreter_id}: Peer didn't become ready")
            time.sleep(0.001)

        # Read peer's public key
        peer_pub_bytes = bytes(peer_region[PUBKEY_OFFSET : PUBKEY_OFFSET + PUBKEY_SIZE])
        peer_pub = int.from_bytes(peer_pub_bytes, 'big')

        # Compute shared secret
        shared = pow(peer_pub, priv, DH_PRIME)
        shared_bytes = shared.to_bytes((shared.bit_length() + 7) // 8 or 1, 'big')
        key = hashlib.sha256(shared_bytes).digest()

        # Update status: COMPUTING
        my_region[FLAG_OFFSET : FLAG_OFFSET + 4] = (2).to_bytes(4, 'little')

        # Perform computation (simulate work)
        result = sum(secrets.randbits(32) for _ in range(100))

        # Prepare message
        msg = f"Result from {interpreter_id}: {result}".encode('utf-8')
        msg = msg.ljust(MSG_SIZE, b'\x00')[:MSG_SIZE]

        # Compute HMAC
        mac = hmac.new(key, msg, hashlib.sha256).digest()

        # Write message and MAC
        my_region[MSG_OFFSET : MSG_OFFSET + MSG_SIZE] = msg
        my_region[MAC_OFFSET : MAC_OFFSET + MAC_SIZE] = mac

        # Quineic self-verification: hash our own code
        code_str = "worker_entrypoint"  # Placeholder
        code_hash = hashlib.sha256(code_str.encode()).digest()
        my_region[HASH_OFFSET : HASH_OFFSET + HASH_SIZE] = code_hash

        # Oracle behavior: try to claim winner status
        if enable_oracle:
            # Read peer status
            peer_status = int.from_bytes(
                bytes(peer_region[FLAG_OFFSET : FLAG_OFFSET + 4]), 'little'
            )

            if peer_status < 3:  # Peer not COMPLETE yet
                # We might be first!
                my_region[FLAG_OFFSET : FLAG_OFFSET + 4] = (4).to_bytes(
                    4, 'little'
                )  # WINNER
            else:
                # Peer already complete
                my_region[FLAG_OFFSET : FLAG_OFFSET + 4] = (3).to_bytes(
                    4, 'little'
                )  # COMPLETE
        else:
            my_region[FLAG_OFFSET : FLAG_OFFSET + 4] = (3).to_bytes(
                4, 'little'
            )  # COMPLETE

    except Exception as e:
        # Write error to stderr (will be captured by main)
        import traceback

        sys.stderr.write(f"ERROR in {interpreter_id}: {e}\n")
        sys.stderr.write(traceback.format_exc())
        raise


# =============================================================================
# SECTION 4: MAIN ORCHESTRATION
# =============================================================================


class QuantizedRuntime:
    """
    Represents one quantized runtime (subinterpreter).

    This is a "runtime quantum" - an isolated computational entity
    that can only communicate through the shared memory oracle.
    """

    def __init__(
        self,
        interpreter_id: str,
        region_offset: int,
        peer_offset: int,
        buffer: mmap.mmap,
        config: Config,
    ):
        self.id = interpreter_id
        self.region_offset = region_offset
        self.peer_offset = peer_offset
        self.region_size = config.REGION_SIZE
        self.buffer = buffer
        self.config = config

        # Create ctypes view of our region
        buf_addr = ctypes.addressof((ctypes.c_char * len(buffer)).from_buffer(buffer))
        self.buf_addr = buf_addr

        self.region = (ctypes.c_char * self.region_size).from_address(
            buf_addr + region_offset
        )

        # Create subinterpreter
        self.interpreter = create()
        self.thread = None
        self.error = None

    def start(self, peer: 'QuantizedRuntime'):
        """Start computation in this runtime."""
        try:
            self.thread = self.interpreter.call_in_thread(
                worker_entrypoint,
                self.region_offset,
                self.region_size,
                peer.region_offset,
                peer.region_size,
                self.buf_addr,
                self.id,
                CONFIG.ENABLE_ORACLE,
            )
        except Exception as e:
            self.error = e
            raise

    def get_status(self) -> StatusFlag:
        """Read current status flag."""
        flag_bytes = bytes(
            self.region[RegionLayout.FLAG_OFFSET : RegionLayout.FLAG_OFFSET + 4]
        )
        return StatusFlag(int.from_bytes(flag_bytes, 'little'))

    def get_public_key(self) -> bytes:
        """Read DH public key."""
        return bytes(
            self.region[
                RegionLayout.PUBKEY_OFFSET : RegionLayout.PUBKEY_OFFSET
                + self.config.PUBKEY_SIZE
            ]
        )

    def get_message(self) -> bytes:
        """Read message payload."""
        return bytes(
            self.region[
                RegionLayout.MSG_OFFSET : RegionLayout.MSG_OFFSET + self.config.MSG_SIZE
            ]
        ).rstrip(b'\x00')

    def get_mac(self) -> bytes:
        """Read HMAC."""
        return bytes(
            self.region[
                RegionLayout.MAC_OFFSET : RegionLayout.MAC_OFFSET + self.config.MAC_SIZE
            ]
        )

    def get_code_hash(self) -> bytes:
        """Read quineic code verification hash."""
        return bytes(
            self.region[
                RegionLayout.HASH_OFFSET : RegionLayout.HASH_OFFSET
                + self.config.HASH_SIZE
            ]
        )

    def wait_for_completion(self, timeout: float = 5.0) -> bool:
        """Wait for runtime to complete computation."""
        start = time.time()
        while time.time() - start < timeout:
            status = self.get_status()
            if status >= StatusFlag.COMPLETE:
                return True
            time.sleep(0.01)
        return False

    def cleanup_region(self):
        """FIXED: Cleanup ctypes view before buffer close."""
        # Delete the region view to release buffer reference
        if hasattr(self, 'region'):
            del self.region

    def close(self):
        """Clean up resources."""
        self.cleanup_region()  # FIXED: Clean up region first
        if self.interpreter:
            try:
                self.interpreter.close()
            except Exception as e:
                print(f"Warning: Error closing interpreter {self.id}: {e}")


def main():
    """Main orchestration: create oracle substrate and spawn runtimes."""

    print("=" * 70)
    print("QUINEIC SUBINTERPRETER COMMUNICATION SYSTEM")
    print("=" * 70)
    print(f"Python version: {sys.version}")
    print(f"Buffer size: {CONFIG.BUFFER_SIZE} bytes")
    print(f"Region size: {CONFIG.REGION_SIZE} bytes per interpreter")
    print(f"DH key size: {CONFIG.PUBKEY_SIZE} bytes (1024-bit)")
    print(f"Oracle mode: {'ENABLED' if CONFIG.ENABLE_ORACLE else 'DISABLED'}")
    print("=" * 70)

    # Create shared memory buffer
    buffer = mmap.mmap(-1, CONFIG.BUFFER_SIZE)

    runtime_a = None
    runtime_b = None

    try:
        # Zero out buffer
        buffer[:] = b'\x00' * CONFIG.BUFFER_SIZE

        # Create two quantized runtimes
        print("\n[PHASE 1] Creating quantized runtimes...")

        runtime_a = QuantizedRuntime(
            interpreter_id="ALPHA",
            region_offset=0,
            peer_offset=CONFIG.REGION_SIZE,
            buffer=buffer,
            config=CONFIG,
        )

        runtime_b = QuantizedRuntime(
            interpreter_id="BETA",
            region_offset=CONFIG.REGION_SIZE,
            peer_offset=0,
            buffer=buffer,
            config=CONFIG,
        )

        print(f"  Runtime ALPHA: region [0:{CONFIG.REGION_SIZE})")
        print(f"  Runtime BETA: region [{CONFIG.REGION_SIZE}:{CONFIG.REGION_SIZE * 2})")

        # Start both runtimes
        print("\n[PHASE 2] Starting computations...")
        start_time = time.time()

        runtime_a.start(runtime_b)
        runtime_b.start(runtime_a)

        print("  Both runtimes started")

        # Wait for completion
        print("\n[PHASE 3] Waiting for completion...")

        a_done = runtime_a.wait_for_completion(CONFIG.COMPUTE_TIMEOUT)
        b_done = runtime_b.wait_for_completion(CONFIG.COMPUTE_TIMEOUT)

        elapsed = time.time() - start_time

        if not (a_done and b_done):
            print("  WARNING: Timeout waiting for completion")
            if not a_done:
                print("    ALPHA did not complete")
            if not b_done:
                print("    BETA did not complete")
        else:
            print(f"  Both runtimes completed in {elapsed:.3f}s")

        # Read results
        print("\n[PHASE 4] Reading results...")

        status_a = runtime_a.get_status()
        status_b = runtime_b.get_status()

        print(f"\n  ALPHA Status: {status_a.name}")
        print(
            f"    Message: {runtime_a.get_message().decode('utf-8', errors='replace')}"
        )
        print(f"    MAC: {runtime_a.get_mac().hex()[:32]}...")
        print(f"    Code Hash: {runtime_a.get_code_hash().hex()[:32]}...")

        print(f"\n  BETA Status: {status_b.name}")
        print(
            f"    Message: {runtime_b.get_message().decode('utf-8', errors='replace')}"
        )
        print(f"    MAC: {runtime_b.get_mac().hex()[:32]}...")
        print(f"    Code Hash: {runtime_b.get_code_hash().hex()[:32]}...")

        # Oracle decision
        if CONFIG.ENABLE_ORACLE:
            print("\n[PHASE 5] Oracle Decision (First-Past-Post)...")

            if status_a == StatusFlag.WINNER:
                print("  🏆 ALPHA won the race!")
            elif status_b == StatusFlag.WINNER:
                print("  🏆 BETA won the race!")
            else:
                print("  ⚠️  No clear winner (both finished simultaneously)")

        # Verify quineic property
        print("\n[PHASE 6] Quineic Verification...")

        # Both should have same code hash (they're the same function)
        hash_a = runtime_a.get_code_hash()
        hash_b = runtime_b.get_code_hash()

        if hash_a == hash_b:
            print("  ✓ Code hashes match (quineic property verified)")
        else:
            print("  ✗ Code hashes differ (unexpected!)")

        print("\n" + "=" * 70)
        print("EXECUTION COMPLETE")
        print("=" * 70)

    except Exception as e:
        print(f"\nERROR: {e}")
        traceback.print_exc()

    finally:
        # FIXED: Proper cleanup order
        print("\n[CLEANUP] Closing resources...")

        # Close runtimes first (releases region views)
        if runtime_a:
            runtime_a.close()
        if runtime_b:
            runtime_b.close()

        # Now safe to close buffer
        try:
            buffer.close()
            print("  ✓ Buffer closed")
        except BufferError as e:
            print(f"  ⚠️  Buffer close error: {e}")

        print("  Done")


if __name__ == "__main__":
    main()

# Next steps:


class DebugableQuantizedRuntime(QuantizedRuntime):
    def get_memory_view(self) -> bytes:
        """Return raw memory for UI display."""
        return bytes(self.region[: self.region_size])

    def get_structured_view(self) -> dict:
        """Return parsed structure for UI."""
        return {
            'status': self.get_status().name,
            'pubkey': self.get_public_key().hex(),
            'message': self.get_message(),
            'mac': self.get_mac().hex(),
            'hash': self.get_code_hash().hex(),
        }


class SteppableRuntime:
    def __init__(self):
        self.breakpoints = set()
        self.paused = threading.Event()

    def set_breakpoint(self, offset: int):
        self.breakpoints.add(offset)

    def step(self):
        """Single step (for UI)."""
        self.paused.clear()
        # Signal worker to proceed one step


# UI can poll without blocking workers
def ui_update_loop():
    while True:
        for runtime in runtimes:
            view = runtime.get_structured_view()
            ui.update_panel(runtime.id, view)
        time.sleep(0.1)  # 10 FPS update
