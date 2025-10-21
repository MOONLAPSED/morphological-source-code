#!/usr/bin/env python3
"""
Morphic Quineic Triad Demo; struct+memoryview buffer layout, SCT flattening tied into final hash.

 1) Tangent-space / "c-flattening functor" (SCT-like bit/field transform).
 2) Memory layout using struct + memoryview (no ctypes.from_address pointer fiddling).
 3) Commit/reveal commit scheme for fairness and deterministic seeds.
 4) Deterministic quineic lifecycle hooks (canonical serialization + deterministic seed derivation).
 5) Header byte -> T/V/C mapping (pilot bit + variance bits + term bits).

Notes:
 - Uses only Python stdlib (no external crypto libs). Uses modular exponentiation for DH (demo only).
 - Uses a 2048-bit RFC3526 MODP prime (Group 14) for demonstration; still not recommended for production crypto.
 - Subinterpreters (PEP-554) attempted if available; falls back to threads.
 - Designed to be readable and auditable rather than hyper-optimized.
"""
from __future__ import annotations
import sys
import time
import struct
import mmap
import secrets
import hashlib
import hmac
import threading
import json
from dataclasses import dataclass
from typing import Tuple, Optional, List

# ----------------------------- Configuration ---------------------------------
@dataclass
class Config:
    NUM_RUNTIMES: int = 3
    PUBKEY_BYTES: int = 256       # make room for 2048-bit pubkey (256 bytes)
    MSG_BYTES: int = 64
    COMMIT_BYTES: int = 32        # SHA-256 commit
    NONCE_BYTES: int = 16
    MAC_BYTES: int = 32           # HMAC-SHA256
    HASH_BYTES: int = 32          # final score hash (SHA-256)
    FLAG_BYTES: int = 8           # we store a 64-bit header word for atomicity
    HEADER_FMT = "<B Q B B B"     # version(u8), seq(u64), flags(u8), actor_id(u8), header_byte(u8)
    PADDING: int = 64

    # Use RFC3526 2048-bit MODP Group (hex from RFC 3526) — demo only
    DH_PRIME_HEX: str = (
        "FFFFFFFFFFFFFFFFC90FDAA22168C234C4C6628B80DC1CD1"
        "29024E088A67CC74020BBEA63B139B22514A08798E3404DD"
        "EF9519B3CD3A431B302B0A6DF25F14374FE1356D6D51C245"
        "E485B576625E7EC6F44C42E9A637ED6B0BFF5CB6F406B7ED"
        "EE386BFB5A899FA5AE9F24117C4B1FE649286651ECE45B3D"
        "C2007CB8A163BF0598DA48361C55D39A69163FA8FD24CF5F"
        "83655D23DCA3AD961C62F356208552BB9ED529077096966D"
        "670C354E4ABC9804F1746C08CA237327FFFFFFFFFFFFFFFF"
    )
    DH_GENERATOR: int = 2

    STARTUP_TIMEOUT: float = 3.0
    COMPUTE_TIMEOUT: float = 8.0
    # an epoch constant for deterministic seeds (can be parameterized)
    GLOBAL_EPOCH: int = 0x20251001  # arbitrary "stable" epoch for deterministic runs

    @property
    def DH_PRIME(self) -> int:
        return int(self.DH_PRIME_HEX, 16)

    @property
    def HEADER_SIZE(self) -> int:
        return struct.calcsize(self.HEADER_FMT)

    @property
    def REGION_SIZE(self) -> int:
        # layout: HEADER | PUBKEY | MSG | COMMIT | NONCE | MACS (N-1) | HASH | padding
        macs_total = self.MAC_BYTES * (self.NUM_RUNTIMES - 1)
        return (
            self.HEADER_SIZE
            + self.PUBKEY_BYTES
            + self.MSG_BYTES
            + self.COMMIT_BYTES
            + self.NONCE_BYTES
            + macs_total
            + self.HASH_BYTES
            + self.PADDING
        )

    @property
    def BUFFER_SIZE(self) -> int:
        return self.REGION_SIZE * self.NUM_RUNTIMES

CONFIG = Config()

# ----------------------------- Offsets helpers --------------------------------
def offsets_for_region() -> dict:
    off = {}
    base = 0
    off['HEADER_OFFSET'] = 0
    off['PUBKEY_OFFSET'] = off['HEADER_OFFSET'] + CONFIG.HEADER_SIZE
    off['MSG_OFFSET'] = off['PUBKEY_OFFSET'] + CONFIG.PUBKEY_BYTES
    off['COMMIT_OFFSET'] = off['MSG_OFFSET'] + CONFIG.MSG_BYTES
    off['NONCE_OFFSET'] = off['COMMIT_OFFSET'] + CONFIG.COMMIT_BYTES
    off['MACS_OFFSET'] = off['NONCE_OFFSET'] + CONFIG.NONCE_BYTES
    off['HASH_OFFSET'] = off['MACS_OFFSET'] + CONFIG.MAC_BYTES * (CONFIG.NUM_RUNTIMES - 1)
    return off

OFF = offsets_for_region()

# ----------------------------- Header / T/V/C helpers -------------------------
# header byte layout: [ C | V2 V1 V0 | T3 T2 T1 T0 ]
def compose_header_byte(c_bit: int, v_bits: int, t_bits: int) -> int:
    assert 0 <= c_bit <= 1
    assert 0 <= v_bits < 8
    assert 0 <= t_bits < 16
    return (c_bit << 7) | ( (v_bits & 0b111) << 4 ) | (t_bits & 0b1111)

def decompose_header_byte(h: int) -> Tuple[int,int,int]:
    c = (h >> 7) & 1
    v = (h >> 4) & 0b111
    t = h & 0b1111
    return c, v, t

# ----------------------------- SCT / flattening functor ----------------------
def sct_flatten(header_byte: int, payload: bytes, context_key: bytes, width_bits: int = 32) -> bytes:
    """
    A cheap SCT-like invert/translate/invert mapping producing a 'tangent' blob.
    - header_byte: the 8-bit header
    - payload: arbitrary bytes (we'll mix a small hash of it)
    - context_key: key material (e.g., HMAC input) to produce the 'b' translate vector
    - width_bits: number of bits we produce for the tangent (must be multiple of 8)
    Returns a bytes object of length width_bits//8.
    Deterministic and reversible given same context_key (not cryptographically reversible).
    """
    assert width_bits % 8 == 0
    out_len = width_bits // 8

    # Build a small domain integer from header and payload hash
    payload_hash = hashlib.sha256(payload).digest()
    seed_material = bytes([header_byte]) + payload_hash + context_key
    # derive 'b' via HMAC-SHA256
    b_full = hmac.new(seed_material, b"morphic-sct-b", hashlib.sha256).digest()
    # interpret top out_len bytes as integer b_int
    b_bytes = b_full[:out_len]
    b_int = int.from_bytes(b_bytes, 'big')

    # E as integer from header + a few bytes of payload_hash
    # choose E_bits = width_bits. Pack header + first (out_len-1) hash bytes
    e_bytes = bytes([header_byte]) + payload_hash[:max(0, out_len-1)]
    E_int = int.from_bytes(e_bytes[:out_len], 'big') & ((1 << width_bits) - 1)

    # simple invert (bitwise within width)
    mask = (1 << width_bits) - 1
    E_inv = (~E_int) & mask
    mapped = (E_inv ^ b_int) & mask
    T_int = (~mapped) & mask

    return T_int.to_bytes(out_len, 'big')

def sct_reconstruct(header_byte: int, tangent: bytes, context_key: bytes) -> bytes:
    """
    Reconstruct approximate original E-derived bytes from tangent and context_key.
    This mirrors the forward function but returns the small e_bytes used in flatten.
    """
    out_len = len(tangent)
    b_full = hmac.new(bytes([header_byte]) + b"__reconstruct__" + context_key, b"morphic-sct-b", hashlib.sha256).digest()
    # Note: to be consistent with sct_flatten we must compute the same b_int,
    # but since sct_flatten used seed_material including payload_hash, perfect invert isn't possible
    # without payload_hash. This reconstruction is intentionally best-effort and should be treated
    # as a diagnostic helper rather than perfect inverse.
    b_int = int.from_bytes(b_full[:out_len], 'big')
    mask = (1 << (8*out_len)) - 1
    T_int = int.from_bytes(tangent, 'big')
    mapped = (~T_int) & mask
    E_inv = (mapped ^ b_int) & mask
    E_int = (~E_inv) & mask
    return E_int.to_bytes(out_len, 'big')

# ----------------------------- DH helpers (demo only) ------------------------
def dh_keypair() -> Tuple[int, int]:
    """
    Return (priv, pub) using pow for modular exponentiation in the demo prime group.
    priv is in [2, p-2], pub = g^priv mod p.
    """
    p = CONFIG.DH_PRIME
    g = CONFIG.DH_GENERATOR
    priv = secrets.randbelow(p - 3) + 2
    pub = pow(g, priv, p)
    return priv, pub

def dh_shared_secret(priv: int, peer_pub_int: int) -> bytes:
    """
    Compute shared secret and derive 32-byte key via SHA-256.
    """
    shared = pow(peer_pub_int, priv, CONFIG.DH_PRIME)
    b = shared.to_bytes((shared.bit_length() + 7) // 8 or 1, 'big')
    return hashlib.sha256(b).digest()

# ----------------------------- Canonical serialization -----------------------
def canonical_serialize(obj) -> bytes:
    """
    Deterministic JSON canonicalization (sorted keys, no extra whitespace).
    Good enough for demo provenance hashing.
    """
    return json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8')

# ----------------------------- Utility: struct pack/unpack -------------------
HEADER_STRUCT = struct.Struct(CONFIG.HEADER_FMT)
def write_header(buf_mv: memoryview, base: int, version: int, seq: int, flags: int, actor_id: int, header_byte: int):
    HEADER_STRUCT.pack_into(buf_mv, base + OFF['HEADER_OFFSET'], version, seq, flags, actor_id, header_byte)

def read_header(buf_mv: memoryview, base: int):
    return HEADER_STRUCT.unpack_from(buf_mv, base + OFF['HEADER_OFFSET'])

# ----------------------------- Worker routine --------------------------------
def worker_region_worker(region_index: int, buf_mv: memoryview, run_id: str, deterministic_epoch: int):
    """
    Worker acting on its region in shared memory. Protocol:
      - write header INIT (version, seq=region_index, flags=1)
      - generate DH keypair, write pubkey
      - compute commit (H(pub||nonce)) and write commit, then wait for all commits
      - publish nonce (reveal), wait for all reveals
      - read peers' pubkeys and compute shared secrets
      - compute per-peer MACs, write MACs
      - compute final hash including SCT tangent and deterministic seed, write final hash
      - write COMPLETE flag
    """
    try:
        region_size = CONFIG.REGION_SIZE
        base = region_index * region_size

        # convenience slices
        def slice_at(offset: int, size: int) -> memoryview:
            return buf_mv[base + offset : base + offset + size]

        # 1) write header INIT
        version = 1
        seq = region_index
        flags_init = 1  # simple flag states: 1=INIT, 2=COMMIT, 3=REVEAL, 4=MACS_DONE, 5=COMPLETE
        actor_id = region_index & 0xFF
        # choose T/V/C example: make controlling actor C=1 for actor 0, others 0
        c_bit = 1 if region_index == 0 else 0
        v_bits = region_index & 0b111
        t_bits = (region_index * 3) & 0b1111
        header_byte = compose_header_byte(c_bit, v_bits, t_bits)
        write_header(buf_mv, base, version, seq, flags_init, actor_id, header_byte)

        # 2) generate DH keypair and write pubkey
        priv, pub = dh_keypair()
        pub_bytes = pub.to_bytes(CONFIG.PUBKEY_BYTES, 'big')
        slice_at(OFF['PUBKEY_OFFSET'], CONFIG.PUBKEY_BYTES)[:] = pub_bytes

        # 3) commit-reveal: deterministic commit = H(pub || nonce). We generate nonce now but only write commit first.
        # choose deterministic nonce derived from pub and epoch for reproducibility.
        # But we also want some unpredictability per actor for variety in demo: incorporate secrets.token_bytes but store it.
        nonce = secrets.token_bytes(CONFIG.NONCE_BYTES)  # random secret per run
        commit = hashlib.sha256(pub_bytes + nonce).digest()
        # write commit
        slice_at(OFF['COMMIT_OFFSET'], CONFIG.COMMIT_BYTES)[:] = commit

        # flip flag to indicate COMMIT written
        write_header(buf_mv, base, version, seq, 2, actor_id, header_byte)

        # barrier: wait for all commits (check COMMIT_BYTES non-zero)
        t0 = time.monotonic()
        while True:
            all_committed = True
            for i in range(CONFIG.NUM_RUNTIMES):
                other_base = i * region_size
                other_commit = bytes(buf_mv[other_base + OFF['COMMIT_OFFSET'] : other_base + OFF['COMMIT_OFFSET'] + CONFIG.COMMIT_BYTES])
                if all(b == 0 for b in other_commit):
                    all_committed = False
                    break
            if all_committed:
                break
            if time.monotonic() - t0 > CONFIG.STARTUP_TIMEOUT:
                raise TimeoutError(f"{run_id}: timeout waiting for commits")
            time.sleep(0.002)

        # 4) write nonce (reveal)
        slice_at(OFF['NONCE_OFFSET'], CONFIG.NONCE_BYTES)[:] = nonce
        write_header(buf_mv, base, version, seq, 3, actor_id, header_byte)

        # barrier: wait for all nonces (reveal)
        t0 = time.monotonic()
        while True:
            all_revealed = True
            for i in range(CONFIG.NUM_RUNTIMES):
                other_base = i * region_size
                other_nonce = bytes(buf_mv[other_base + OFF['NONCE_OFFSET'] : other_base + OFF['NONCE_OFFSET'] + CONFIG.NONCE_BYTES])
                if all(b == 0 for b in other_nonce):
                    all_revealed = False
                    break
            if all_revealed:
                break
            if time.monotonic() - t0 > CONFIG.STARTUP_TIMEOUT:
                raise TimeoutError(f"{run_id}: timeout waiting for reveals")
            time.sleep(0.002)

        # 5) compute shared secrets with peers and produce MACs
        # read other pubkeys and nonces (we already placed our pub and nonce)
        peer_pubs = []
        peer_nonces = []
        for i in range(CONFIG.NUM_RUNTIMES):
            other_base = i * region_size
            pubb = bytes(buf_mv[other_base + OFF['PUBKEY_OFFSET'] : other_base + OFF['PUBKEY_OFFSET'] + CONFIG.PUBKEY_BYTES])
            nonc = bytes(buf_mv[other_base + OFF['NONCE_OFFSET'] : other_base + OFF['NONCE_OFFSET'] + CONFIG.NONCE_BYTES])
            peer_pubs.append(pubb)
            peer_nonces.append(nonc)

        # message to authenticate: include deterministic epoch and region_index to be reproducible
        message_struct = {
            "runtime": run_id,
            "epoch": deterministic_epoch,
            "region": region_index
        }
        message_bytes = canonical_serialize(message_struct)
        message_bytes = message_bytes.ljust(CONFIG.MSG_BYTES, b'\x00')[:CONFIG.MSG_BYTES]
        slice_at(OFF['MSG_OFFSET'], CONFIG.MSG_BYTES)[:] = message_bytes

        # compute MACs (slot ordering: peers in increasing index order skipping self)
        slot = 0
        macs = []
        for i in range(CONFIG.NUM_RUNTIMES):
            if i == region_index:
                continue
            peer_pub_int = int.from_bytes(peer_pubs[i], 'big')
            shared = dh_shared_secret(priv, peer_pub_int)  # 32 bytes
            # incorporate peer nonce and our nonce into HKDF-like derivation (simple concat+hash)
            key_input = shared + peer_nonces[i] + nonce
            mac_key = hashlib.sha256(key_input).digest()
            mac = hmac.new(mac_key, message_bytes, hashlib.sha256).digest()
            macs.append(mac)
            # write MAC to our MAC slot
            mac_slot_off = OFF['MACS_OFFSET'] + slot * CONFIG.MAC_BYTES
            slice_at(mac_slot_off, CONFIG.MAC_BYTES)[:] = mac
            slot += 1

        write_header(buf_mv, base, version, seq, 4, actor_id, header_byte)  # MACS_DONE

        # 6) compute SCT tangent (use header_byte + message + HMAC seed derived from all pubkeys)
        # context key: H(concat of all pubkeys || epoch)
        pub_concat = b"".join(peer_pubs)
        context_key = hashlib.sha256(pub_concat + deterministic_epoch.to_bytes(8, 'big')).digest()
        tangent = sct_flatten(header_byte, message_bytes, context_key, width_bits=32)  # 4 bytes tangent

        # 7) compute deterministic seed for oracle: H(pub || nonce || region || epoch)
        seed_input = pub_bytes + nonce + region_index.to_bytes(2,'big') + deterministic_epoch.to_bytes(8,'big')
        seed = hashlib.sha256(seed_input).digest()[:8]

        # 8) final score hash: bind MACs || tangent || seed || commit || nonce to produce final hash
        concat = b"".join(macs) + tangent + seed + commit + nonce
        final_hash = hashlib.sha256(concat).digest()
        slice_at(OFF['HASH_OFFSET'], CONFIG.HASH_BYTES)[:] = final_hash

        # 9) mark COMPLETE
        write_header(buf_mv, base, version, seq, 5, actor_id, header_byte)

    except Exception as exc:
        # Write a best-effort failure marker in header flags field (flags=255)
        try:
            write_header(buf_mv, base, version if 'version' in locals() else 1, seq if 'seq' in locals() else region_index, 255, actor_id if 'actor_id' in locals() else region_index, header_byte if 'header_byte' in locals() else 0)
        except Exception:
            pass
        sys.stderr.write(f"[{run_id}] worker exception: {exc}\n")

# ----------------------------- Coordinator / Main ----------------------------
def main():
    print("\n=== Morphic Quineic Triad Demo ===\n")
    print(f"Region size: {CONFIG.REGION_SIZE} bytes")
    print(f"Total buffer size: {CONFIG.BUFFER_SIZE} bytes\n")

    # create shared memory backing (try multiprocessing.shared_memory if available, else mmap)
    try:
        from multiprocessing import shared_memory
        shm = shared_memory.SharedMemory(create=True, size=CONFIG.BUFFER_SIZE)
        buf_mv = shm.buf  # memoryview-like
        print("Using multiprocessing.shared_memory for backing buffer.")
    except Exception:
        mm = mmap.mmap(-1, CONFIG.BUFFER_SIZE)
        buf_mv = memoryview(mm)
        print("Using mmap-backed buffer (fallback).")

    # zero the buffer for clarity
    buf_mv[:] = b'\x00' * CONFIG.BUFFER_SIZE

    # try to use subinterpreters if available (PEP 554)
    use_subinterpreters = False
    try:
        from concurrent.interpreters import create as sub_create
        iv = sub_create()
        iv.close()
        use_subinterpreters = True
    except Exception:
        use_subinterpreters = False

    threads: List[threading.Thread] = []
    interpreters = []

    # Launch workers (either as thread or subinterpreter thread)
    for i in range(CONFIG.NUM_RUNTIMES):
        run_id = f"R{i}"
        if use_subinterpreters:
            # API surface for real subinterpreters varies; for portability we fall back to threads.
            # Here we just spawn a thread — if you run in an interpreter supporting call_in_thread,
            # you can adapt this area to use it.
            t = threading.Thread(target=worker_region_worker, args=(i, buf_mv, run_id, CONFIG.GLOBAL_EPOCH), daemon=True)
            t.start()
            threads.append(t)
        else:
            t = threading.Thread(target=worker_region_worker, args=(i, buf_mv, run_id, CONFIG.GLOBAL_EPOCH), daemon=True)
            t.start()
            threads.append(t)

    # Wait for COMPLETE or timeout
    deadline = time.monotonic() + CONFIG.COMPUTE_TIMEOUT
    all_complete = False
    while time.monotonic() < deadline:
        statuses = []
        for i in range(CONFIG.NUM_RUNTIMES):
            base = i * CONFIG.REGION_SIZE
            # read header flags field (unpack)
            try:
                version, seq, flags, actor_id, header_byte = read_header(buf_mv, base)
            except struct.error:
                flags = 0
            statuses.append(flags)
        if all(s >= 5 for s in statuses):
            all_complete = True
            break
        time.sleep(0.01)

    if not all_complete:
        print("WARNING: Not all runtimes reached COMPLETE within timeout. Partial results may be present.")
    else:
        print("All runtimes COMPLETE — collecting scores...")

    # collect and sort scores
    scores = []
    for i in range(CONFIG.NUM_RUNTIMES):
        base = i * CONFIG.REGION_SIZE
        hash_bytes = bytes(buf_mv[base + OFF['HASH_OFFSET'] : base + OFF['HASH_OFFSET'] + CONFIG.HASH_BYTES])
        score_int = int.from_bytes(hash_bytes, 'big')
        scores.append((i, score_int, hash_bytes))

    scores_sorted = sorted(scores, key=lambda x: x[1])
    winner_idx, winner_score, winner_hash = scores_sorted[0]
    print("\nScores (lower is better):")
    for idx, s_int, hb in scores_sorted:
        print(f"  R{idx}: {s_int}  (hash={hb.hex()[:20]}...)")
    print(f"\nWinner: R{winner_idx} (score {winner_score})\n")

    # show per-runner messages, commit/reveal, and MACs
    for i in range(CONFIG.NUM_RUNTIMES):
        base = i * CONFIG.REGION_SIZE
        # header
        try:
            version, seq, flags, actor_id, header_byte = read_header(buf_mv, base)
        except struct.error:
            version, seq, flags, actor_id, header_byte = (0,0,0,0,0)
        c,v,t = decompose_header_byte(header_byte)
        print(f"R{i} header: version={version}, seq={seq}, flags={flags}, actor={actor_id}, C={c}, V={v}, T={t}")
        msgb = bytes(buf_mv[base + OFF['MSG_OFFSET'] : base + OFF['MSG_OFFSET'] + CONFIG.MSG_BYTES]).rstrip(b'\x00')
        print(f"  message: {msgb.decode('utf-8',errors='replace')}")
        commitb = bytes(buf_mv[base + OFF['COMMIT_OFFSET'] : base + OFF['COMMIT_OFFSET'] + CONFIG.COMMIT_BYTES])
        nonceb = bytes(buf_mv[base + OFF['NONCE_OFFSET'] : base + OFF['NONCE_OFFSET'] + CONFIG.NONCE_BYTES])
        print(f"  commit: {commitb.hex()[:32]}... nonce (hex): {nonceb.hex()[:16]}...")
        macs = []
        for slot in range(CONFIG.NUM_RUNTIMES - 1):
            macb = bytes(buf_mv[base + OFF['MACS_OFFSET'] + slot*CONFIG.MAC_BYTES : base + OFF['MACS_OFFSET'] + (slot+1)*CONFIG.MAC_BYTES])
            macs.append(macb)
        print(f"  macs: {[m.hex()[:12]+'...' for m in macs]}")
        hb = bytes(buf_mv[base + OFF['HASH_OFFSET'] : base + OFF['HASH_OFFSET'] + CONFIG.HASH_BYTES])
        print(f"  final-hash: {hb.hex()}\n")

    # cleanup
    try:
        if 'shm' in locals():
            shm.close()
            shm.unlink()
        else:
            mm.close()
    except Exception:
        pass

if __name__ == "__main__":
    main()
