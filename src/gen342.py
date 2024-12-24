#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""PEP0342 generator/await coroutine-based 'trampoline' server."""
#------------------------------------------------------------------------------
# Standard Library Imports - 3.13 std libs **ONLY**
#------------------------------------------------------------------------------
import collections
import sys
import types
import socket
import select
import time
import collections


class SocketWrapper:
    def __init__(self, sock):
        if not sock:
            raise ValueError("Socket cannot be None")
        self.sock = sock
    
    def fileno(self):
        return self.sock.fileno()
    
    def send(self, data):
        return self.sock.send(data)
    
    def recv(self, size):
        return self.sock.recv(size)
    
    def accept(self):
        client, addr = self.sock.accept()
        return SocketWrapper(client), addr

def nonblocking_read(sock, chunk_size=8192):
    if not isinstance(sock, SocketWrapper):
        sock = SocketWrapper(sock)
    while True:
        try:
            ready = select.select([sock], [], [], 0.1)[0]
            if ready:
                data = sock.recv(chunk_size)
                if not data:
                    raise ConnectionLost()
                print(f"Received data: {data}")  # Debugging log
                return data
            yield None  # Yield control back to the event loop
        except socket.error:
            raise ConnectionLost()

def nonblocking_write(sock, data):
    if not isinstance(sock, SocketWrapper):
        sock = SocketWrapper(sock)
    while data:
        try:
            ready = select.select([], [sock], [], 0.1)[1]
            if ready:
                sent = sock.send(data)
                data = data[sent:]
                print(f"Sent data: {data}")  # Debugging log
            yield None
        except socket.error:
            raise ConnectionLost()

def nonblocking_accept(sock):
    if not isinstance(sock, SocketWrapper):
        sock = SocketWrapper(sock)
    while True:
        try:
            ready = select.select([sock], [], [], 0.1)[0]
            if ready:
                client_sock, addr = sock.accept()
                print(f"Accepted connection from: {addr}")  # Debugging log
                yield client_sock
                return  # Properly terminate the generator
            yield None
        except socket.error:
            raise ConnectionLost()

def listening_socket(host, port):
    # Create dual-stack socket that works for both IPv4 and IPv6
    sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    # Enable dual-stack socket
    sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
    sock.bind((host, port, 0, 0))  # The zeros are for flow info and scope id
    sock.listen(5)
    sock.setblocking(False)
    print(f"Listening on {host}:{port}")  # Debugging log
    return SocketWrapper(sock)

class ConnectionLost(Exception):
    pass

class Trampoline:
    """Manage communications between coroutines"""

    running = False

    def __init__(self):
        self.queue = collections.deque()

    def add(self, coroutine):
        """Request that a coroutine be executed"""
        self.schedule(coroutine)

    def run(self, single_tick=False):
        result = None
        self.running = True
        try:
            while self.running:
                if self.queue:
                    func = self.queue.popleft()
                    result = func()
                else:
                    # Only sleep if there are no coroutines to process
                    time.sleep(0.01)
                if single_tick:  # Allow for a single tick
                    break
            return result
        finally:
            self.running = False

    def stop(self):
        self.running = False

    def schedule(self, coroutine, stack=(), val=None, *exc):
        def resume():
            value = val
            try:
                if exc:
                    value = coroutine.throw(value,*exc)
                else:
                    value = coroutine.send(value)
            except:
                if stack:
                    # send the error back to the "caller"
                    self.schedule(
                        stack[0], stack[1], *sys.exc_info()
                    )
                else:
                    # Nothing left in this pseudothread to
                    # handle it, let it propagate to the
                    # run loop
                    raise

            if isinstance(value, types.GeneratorType):
                # Yielded to a specific coroutine, push the
                # current one on the stack, and call the new
                # one with no args
                self.schedule(value, (coroutine,stack))

            elif stack:
                # Yielded a result, pop the stack and send the
                # value to the caller
                self.schedule(stack[0], stack[1], value)

            # else: this pseudothread has ended

        self.queue.append(resume)

def echo_handler(sock):
    # Ensure socket is valid before starting
    if sock is None:
        raise ValueError("Socket must be initialized")
    wrapped_sock = SocketWrapper(sock)
    
    while True:
        try:
            data = yield from nonblocking_read(wrapped_sock)
            yield from nonblocking_write(wrapped_sock, data)
        except ConnectionLost:
            break
        except Exception as e:
            print(f"Error in echo_handler: {e}")  # Debugging log

def listen_on(trampoline, sock, handler):
    if sock is None:
        raise ValueError("Listening socket must be initialized")
    wrapped_sock = SocketWrapper(sock)
    
    while True:
        try:
            client_sock = yield from nonblocking_accept(wrapped_sock)
            if client_sock:
                handler_coro = handler(client_sock)
                trampoline.add(handler_coro)
        except ConnectionLost:
            break
        except Exception as e:
            print(f"Error in listen_on: {e}")  # Debugging log

try:
    # Create a scheduler to manage all our coroutines
    t = Trampoline()

    # Initialize server socket with explicit validation
    server_socket = listening_socket("localhost", 8008)
    if not server_socket:
        raise ValueError("Failed to create server socket")

    # Create server coroutine with validated socket
    server = listen_on(t, server_socket, echo_handler)

    # Add the coroutine to the scheduler
    t.add(server)

    # Run the event loop
    t.run(single_tick=True)
except KeyboardInterrupt:
    print("\nShutting down server...")
except Exception as e:
    print(f"Error: {e}")
finally:
    if 'server_socket' in locals():
        server_socket.sock.close()
        print("Server socket closed")  # Debugging log
# run gen342.ps1 to test/progress the generator
