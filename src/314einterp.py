#!/usr/bin/env -S uv run
# -*- coding: utf-8 -*-
# /* script
# requires-python = ">=3.14"
# dependencies = [
#     "uv==*.*",
# ]
# */
# Optional dependency handling (also add to '/* script..' comment, just above)
# ------------------------------------------------------------------------------
# © 2025 Moonlapsed https://github.com/MOONLAPSED/Cognosis | CC ND & BSD-3 | SEE LICENCE
# <!--- <a href="https://github.com/Moonlapsed/Cognosis">Morphological Source Code</a> © 2023-2025 by MOONLAPSED:MOONLAPSED@gmail.com ---!>
import asyncio
import mailbox
import os
import json

# The 3.14 Subinterpreter Magic
from concurrent.futures import InterpreterPoolExecutor

# --- ASYNCIO SERVER LOGIC (Runs in Main Interpreter) ---


class SMTPProtocol(asyncio.Protocol):
    def connection_made(self, transport):
        self.transport = transport
        self.buffer = b''
        self.state = 'INIT'
        self.transport.write(b'220 localhost SMTP ready\r\n')

    def data_received(self, data):
        self.buffer += data
        while b'\r\n' in self.buffer:
            line, self.buffer = self.buffer.split(b'\r\n', 1)
            self.process_line(line.decode(errors='ignore').strip())

    def process_line(self, line):
        if self.state == 'INIT':
            if line.upper().startswith(('HELO', 'EHLO')):
                self.transport.write(b'250 localhost\r\n')
                self.state = 'READY'
            else:
                self.transport.write(b'503 Bad sequence\r\n')
        elif self.state == 'READY':
            if line.upper().startswith('MAIL FROM:'):
                self.transport.write(b'250 OK\r\n')
                self.state = 'MAIL'
            elif line.upper() == 'QUIT':
                self.transport.write(b'221 Bye\r\n')
                self.transport.close()
            else:
                self.transport.write(b'503 Bad sequence\r\n')
        elif self.state == 'MAIL':
            if line.upper().startswith('RCPT TO:'):
                self.transport.write(b'250 OK\r\n')
                self.state = 'RCPT'
            else:
                self.transport.write(b'503 Bad sequence\r\n')
        elif self.state == 'RCPT':
            if line.upper() == 'DATA':
                self.transport.write(b'354 End data with <CRLF>.<CRLF>\r\n')
                self.state = 'DATA'
                self.data_buffer = b''
            elif line.upper().startswith('RCPT TO:'):
                self.transport.write(b'250 OK\r\n')
            else:
                self.transport.write(b'503 Bad sequence\r\n')
        elif self.state == 'DATA':
            self.data_buffer += (line + '\r\n').encode()
            if b'\r\n.\r\n' in self.data_buffer:
                msg_data = self.data_buffer.split(b'\r\n.\r\n', 1)[0]
                # File I/O is safe here because fcntl locking works across processes/interpreters
                mb = mailbox.mbox('inbox.mbox')
                mb.lock()
                try:
                    mb.add(msg_data)
                    mb.flush()
                finally:
                    mb.unlock()
                self.transport.write(b'250 OK\r\n')
                self.state = 'READY'
                self.data_buffer = b''


class IMAPProtocol(asyncio.Protocol):
    def connection_made(self, transport):
        self.transport = transport
        self.buffer = b''
        self.logged_in = False
        self.selected = None
        self.transport.write(b'* OK IMAP4 ready\r\n')

    def data_received(self, data):
        self.buffer += data
        while b'\r\n' in self.buffer:
            line, self.buffer = self.buffer.split(b'\r\n', 1)
            self.process_line(line.decode(errors='ignore').strip())

    def process_line(self, line):
        if not line:
            return
        parts = line.split()
        if not parts:
            return
        tag = parts[0]
        command = parts[1].upper()

        if command == 'CAPABILITY':
            self.transport.write(b'* CAPABILITY IMAP4\r\n')
            self.transport.write((tag + ' OK CAPABILITY completed\r\n').encode())
        elif command == 'LOGIN':
            self.logged_in = True
            self.transport.write((tag + ' OK LOGIN completed\r\n').encode())
        elif command == 'SELECT':
            if not self.logged_in:
                self.transport.write((tag + ' NO Login first\r\n').encode())
                return
            folder = parts[2].strip('"')
            if folder.lower() == 'inbox':
                self.selected = folder
                mb = mailbox.mbox('inbox.mbox')
                self.transport.write((f'* {len(mb)} EXISTS\r\n').encode())
                self.transport.write(
                    (tag + ' OK [READ-WRITE] SELECT completed\r\n').encode()
                )
            else:
                self.transport.write((tag + ' NO No such folder\r\n').encode())
        elif command == 'SEARCH':
            if not self.selected:
                self.transport.write((tag + ' NO Select first\r\n').encode())
                return

            # Basic parsing to support the client script
            criteria = ' '.join(parts[2:])
            search_val = None
            if 'SUBJECT' in criteria:
                import re

                m = re.search(r'SUBJECT "([^"]+)"', criteria)
                if m:
                    search_val = m.group(1)

            mb = mailbox.mbox('inbox.mbox')
            nums = []
            for i, msg in enumerate(mb, 1):
                sub = msg.get('subject', '')
                if search_val and search_val in sub:
                    nums.append(str(i))

            if nums:
                self.transport.write((f'* SEARCH {" ".join(nums)}\r\n').encode())
            else:
                self.transport.write(b'* SEARCH\r\n')
            self.transport.write((tag + ' OK SEARCH completed\r\n').encode())
        elif command == 'FETCH':
            num = parts[2]
            mb = mailbox.mbox('inbox.mbox')
            try:
                msg = mb[int(num) - 1]
                raw = msg.as_bytes()
                self.transport.write(
                    (f'* {num} FETCH (RFC822 {{{len(raw)}}}\r\n').encode()
                )
                self.transport.write(raw + b'\r\n')
                self.transport.write((tag + ' OK FETCH completed\r\n').encode())
            except:
                self.transport.write((tag + ' NO Error\r\n').encode())
        elif command == 'LOGOUT':
            self.transport.write(b'* BYE\r\n')
            self.transport.write((tag + ' OK LOGOUT\r\n').encode())
            self.transport.close()
        else:
            self.transport.write((tag + ' NO Command not supported\r\n').encode())


async def run_servers():
    loop = asyncio.get_running_loop()
    if not os.path.exists('inbox.mbox'):
        with open('inbox.mbox', 'w'):
            pass

    server1 = await loop.create_server(
        SMTPProtocol, 'localhost', 1025, reuse_address=True
    )
    server2 = await loop.create_server(
        IMAPProtocol, 'localhost', 1143, reuse_address=True
    )

    print('Servers started on localhost:1025 (SMTP) and localhost:1143 (IMAP)')
    await asyncio.gather(server1.serve_forever(), server2.serve_forever())


# --- SUBINTERPRETER TASKS (Blocking Clients) ---

# NOTE: Functions running in subinterpreters must have LOCAL imports.
# Global scope is not shared.


def interp_send_mail(work_dict):
    """
    Runs in a subinterpreter.
    This blocks, but because it's in a subinterpreter, the main loop is fine.
    """
    import smtplib
    from email.mime.text import MIMEText

    try:
        msg = MIMEText(json.dumps(work_dict))
        msg['From'] = 'anonymous@example.com'
        msg['To'] = 'server@example.com'
        msg['Subject'] = f'[WORK] {work_dict.get("seq", 0)}'

        with smtplib.SMTP('localhost', 1025) as server:
            server.send_message(msg)
        return "Sent"
    except Exception as e:
        return f"Send Error: {e}"


def interp_recv_mail():
    """
    Runs in a subinterpreter.
    Polls IMAP synchronously, returns list of work items (dicts).
    """
    import imaplib
    import email

    results = []
    try:
        mail = imaplib.IMAP4('localhost', 1143)
        mail.login('server@gmail.com', 'app-password')
        mail.select('inbox')

        typ, data = mail.search(None, 'SUBJECT "[WORK]"')

        if data[0]:
            for num in data[0].split():
                typ, msg_data = mail.fetch(num, '(RFC822)')
                raw = msg_data[0][1]
                msg = email.message_from_bytes(raw)

                payload = None
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == 'text/plain':
                            payload = part.get_payload(decode=True)
                            break
                else:
                    payload = msg.get_payload(decode=True)

                if payload:
                    try:
                        work = json.loads(payload.decode())
                        results.append(work)
                        # In a real app, delete/move message here
                    except:
                        pass
        mail.logout()
    except Exception as e:
        return [f"Recv Error: {e}"]

    return results


# --- MAIN EXECUTOR ---


async def main():
    # 1. Start Servers (Background)
    server_task = asyncio.create_task(run_servers())
    await asyncio.sleep(1)  # Let servers bind

    # 2. Initialize Subinterpreter Pool
    # We use this instead of ThreadPoolExecutor.
    # Python 3.14+ manages the separate interpreters.
    print("Initializing InterpreterPoolExecutor...")

    with InterpreterPoolExecutor(max_workers=2) as executor:
        # --- SENDING WORK (Subinterpreter 1) ---
        print("Submitting Send Task to Subinterpreter...")
        test_work = {'seq': 42, 'task': 'Subinterpreter Logic', 'data': 'Alive'}

        # Submit task. Note: We must wrap the Future to await it in asyncio
        # We pass 'test_work' (a dict) which is shareable across interpreters
        future_send = executor.submit(interp_send_mail, test_work)

        # Await the result in the main loop
        send_result = await asyncio.wrap_future(future_send)
        print(f"Send Result: {send_result}")

        # --- POLLING WORK (Subinterpreter 2) ---
        print("Polling for work (using Subinterpreter)...")

        while True:
            # Submit the blocking receive task to the pool
            future_recv = executor.submit(interp_recv_mail)

            # Non-blocking wait for the subinterpreter to finish
            found_work = await asyncio.wrap_future(future_recv)

            if found_work:
                for item in found_work:
                    print(f"Main Loop Received: {item}")

            await asyncio.sleep(5)


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
