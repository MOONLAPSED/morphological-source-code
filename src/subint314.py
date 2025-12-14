from __future__ import annotations

#!/usr/bin/env -S uv run
# /* script
# requires-python = ">=3.14"
# dependencies = [
#     "uv==*.*",
# ]
# */
# <a href="https://github.com/Moonlapsed/Cognosis">Morphological Source Code</a> © 2023 by MOONLAPSED:MOONLAPSED@gmail.com CC BY
# Optional dependency handling (also add to '/* script..' comment, just above)
try:
    import flask

    USE_FLASK = True
    # if we omit "flask==*.*", or any non-std lib from the '/* script..' comment, then this should always fail
    pass
except ImportError:
    USE_FLASK = False

import concurrent.futures
from urllib.request import urlopen
import secrets
from types import SimpleNamespace
from contextlib import contextmanager

# IMPORTANT: Import the Executor and the queue factory function
from concurrent.futures import InterpreterPoolExecutor
from concurrent.interpreters import create_queue  # <-- Changed import

URLS = [
    'http://www.foxnews.com/',
    'http://www.cnn.com/',
    'http://europe.wsj.com/',
    'http://www.bbc.co.uk/',
]

# Dyadic Metric: SimpleNamespace for configs
# Convert this to a simple dictionary or tuple before passing to the interpreter
config_data = {'timeout': 60, 'max_workers': 5}
config = SimpleNamespace(**config_data)


@contextmanager
def managed_urlopen(url, timeout):
    """ContextManager for URL resources."""
    try:
        conn = urlopen(url, timeout=timeout)
        yield conn
    finally:
        if 'conn' in locals():
            conn.close()


# The function now accepts a shareable dictionary/tuple instead of SimpleNamespace
def load_url_in_interp(url, config_dict, result_queue):
    """Task in interpreter: Dyadic load + morph."""
    # Convert dict back to SimpleNamespace for convenience inside the function (optional)
    config = SimpleNamespace(**config_dict)
    try:
        with managed_urlopen(url, config.timeout) as conn:
            original = conn.read()
        # Dyadic evolution: (original len, metric with psi cost)
        metric_bw = secrets.randbits(8)  # ByteWord-like
        psi_cost = bin(metric_bw).count('1') / 8.0  # Chemistry-light decay
        evolved_len = len(original) + int(psi_cost * 10)  # Mock evolution

        # Shareable types (str, int, bytes) are put into the queue
        result_queue.put((url, (len(original), evolved_len, metric_bw)))
    except Exception as exc:
        # NOTE: Exceptions themselves are not shareable.
        # We must send a shareable representation (like the exception type and message).
        error_msg = f"{type(exc).__name__}: {exc}"
        result_queue.put((url, error_msg))


# Subgenerator and Delegating generator are not called inside the InterpreterPoolExecutor,
# so they don't need changes for shareability.

# Main: Morphic Executor with fallback
# IMPORTANT: Use the shareable queue factory function
result_queue = create_queue()
configs = [config_data for _ in URLS]  # Pass the shareable dictionary

with InterpreterPoolExecutor(max_workers=5) as executor:
    print("Running with InterpreterPoolExecutor (Python 3.14+) ")
    future_to_url = {
        # Pass the shareable dictionary (config_data) and shareable queue (result_queue)
        executor.submit(load_url_in_interp, url, cfg, result_queue): url
        for url, cfg in zip(URLS, configs)
    }

# The result processing remains largely the same
for future in concurrent.futures.as_completed(future_to_url):
    url = future_to_url[future]
    try:
        future.result()  # Wait for the task to complete
    except Exception as exc:
        # Catches any exceptions raised by the executor itself (e.g., submission errors)
        print(f'Executor error for {url!r}: {exc}')
        continue

    # Get the result from the shareable queue
    url_res, result = result_queue.get()

    # Check if the result is an error message (string) or the data tuple
    if isinstance(result, str):  # Error message is now a string
        print(f'{url_res!r} failed: {result}')
    else:
        orig_len, evol_len, metric = result
        print(
            f'{url_res!r} dyad: orig {orig_len} bytes, evol {evol_len} bytes, metric 0x{metric:02X}'
        )
