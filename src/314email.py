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
import email
import os
import json
from email.mime.text import MIMEText
import smtplib
import imaplib

# Ensure inbox.mbox exists
if not os.path.exists('inbox.mbox'):
    with open('inbox.mbox', 'w') as f:
        pass


class SMTPProtocol(asyncio.Protocol):
    def connection_made(self, transport):
        self.transport = transport
        self.peer = transport.get_extra_info('peername')
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
                self.mail_from = line.split(':', 1)[1].strip()
                self.transport.write(b'250 OK\r\n')
                self.state = 'MAIL'
            elif line.upper() == 'QUIT':
                self.transport.write(b'221 Bye\r\n')
                self.transport.close()
            else:
                self.transport.write(b'503 Bad sequence\r\n')
        elif self.state == 'MAIL':
            if line.upper().startswith('RCPT TO:'):
                self.rcpt_to = line.split(':', 1)[1].strip()
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
            # Check for the end of data sequence
            if b'\r\n.\r\n' in self.data_buffer:
                msg_data = self.data_buffer.split(b'\r\n.\r\n', 1)[0]

                # Locking the mailbox is crucial for thread safety
                # (since we are now accessing it from multiple threads/loops context)
                mb = mailbox.mbox('inbox.mbox')
                mb.lock()
                try:
                    mb.add(msg_data)
                    mb.flush()  # Ensure write to disk
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
            if len(parts) < 4:
                self.transport.write((tag + ' NO Invalid arguments\r\n').encode())
                return
            user = parts[2].strip('"')
            passw = parts[3].strip('"')
            if user == 'server@gmail.com' and passw == 'app-password':
                self.logged_in = True
                self.transport.write((tag + ' OK LOGIN completed\r\n').encode())
            else:
                self.transport.write((tag + ' NO LOGIN failed\r\n').encode())
        elif command == 'SELECT':
            if not self.logged_in:
                self.transport.write((tag + ' NO Login first\r\n').encode())
                return
            if len(parts) < 3:
                self.transport.write((tag + ' NO Invalid arguments\r\n').encode())
                return
            folder = parts[2].strip('"')
            if folder.lower() == 'inbox':
                self.selected = folder
                mb = mailbox.mbox('inbox.mbox')
                num_msgs = len(mb)
                self.transport.write((f'* {num_msgs} EXISTS\r\n').encode())
                self.transport.write(b'* 0 RECENT\r\n')
                self.transport.write(b'* OK [UIDVALIDITY 1] UIDs valid\r\n')
                self.transport.write(
                    (tag + ' OK [READ-WRITE] SELECT completed\r\n').encode()
                )
            else:
                self.transport.write((tag + ' NO No such folder\r\n').encode())
        elif command == 'SEARCH':
            if not self.selected:
                self.transport.write((tag + ' NO Select first\r\n').encode())
                return

            # Simple parsing logic for the specific client query
            criteria = ' '.join(parts[2:])
            search_value = None
            if 'SUBJECT' in criteria:
                idx = criteria.find('SUBJECT')
                rest = criteria[idx + 7 :].strip()
                # Handle quoting loosely
                if rest.startswith('"') and rest.endswith('"'):
                    search_value = rest.strip('"')
                else:
                    search_value = rest.split()[0] if rest else ""

            mb = mailbox.mbox('inbox.mbox')
            nums = []
            try:
                for i, msg in enumerate(mb, 1):
                    subject = msg.get('subject', '')
                    if subject and search_value and search_value in subject:
                        nums.append(str(i))
            finally:
                pass

            if nums:
                self.transport.write((f'* SEARCH {" ".join(nums)}\r\n').encode())
            else:
                self.transport.write(b'* SEARCH\r\n')
            self.transport.write((tag + ' OK SEARCH completed\r\n').encode())
        elif command == 'FETCH':
            if not self.selected:
                self.transport.write((tag + ' NO Select first\r\n').encode())
                return
            num = parts[2]
            # Simple check for RFC822
            fetch_type = ' '.join(parts[3:]).strip('()')

            mb = mailbox.mbox('inbox.mbox')
            try:
                idx = int(num) - 1
                msg = mb[idx]
                msg_bytes = msg.as_bytes()
                size = len(msg_bytes)
                self.transport.write((f'* {num} FETCH (RFC822 {{{size}}}\r\n').encode())
                self.transport.write(msg_bytes + b'\r\n')
                self.transport.write((tag + ' OK FETCH completed\r\n').encode())
            except (IndexError, ValueError, KeyError):
                self.transport.write((tag + ' NO No such message\r\n').encode())
        elif command == 'LOGOUT':
            self.transport.write(b'* BYE IMAP4 logout\r\n')
            self.transport.write((tag + ' OK LOGOUT completed\r\n').encode())
            self.transport.close()
        elif command == 'NOOP':
            self.transport.write((tag + ' OK NOOP completed\r\n').encode())
        else:
            self.transport.write((tag + ' NO Command not supported\r\n').encode())


async def run_servers():
    loop = asyncio.get_running_loop()

    # reuse_address=True helps in development to avoid "Address already in use"
    smtp_server = await loop.create_server(
        SMTPProtocol, 'localhost', 1025, reuse_address=True
    )
    imap_server = await loop.create_server(
        IMAPProtocol, 'localhost', 1143, reuse_address=True
    )

    print('Servers started on localhost:1025 (SMTP) and localhost:1143 (IMAP)')
    await asyncio.gather(smtp_server.serve_forever(), imap_server.serve_forever())


# -- SYNCHRONOUS CLIENT HELPERS --


def fetch_pending_work_sync():
    """Blocking IMAP work fetching, to be run in a thread."""
    results = []
    try:
        mail = imaplib.IMAP4('localhost', 1143)
        mail.login('server@gmail.com', 'app-password')
        mail.select('inbox')
        typ, data = mail.search(None, 'SUBJECT "[WORK]"')

        if data[0]:
            for num in data[0].split():
                typ, msg_data = mail.fetch(num, '(RFC822)')
                raw_email = msg_data[0][1]
                msg = email.message_from_bytes(raw_email)

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
                        # Optional: Mark as deleted so we don't process again
                        # mail.store(num, '+FLAGS', '\\Deleted')
                    except json.JSONDecodeError:
                        pass

            # mail.expunge() # Clean up deleted

        mail.logout()
    except Exception as e:
        print(f"IMAP Client Error: {e}")
    return results


def send_work_sync(work):
    """Blocking SMTP sending, to be run in a thread."""
    msg = MIMEText(json.dumps(work))
    msg['From'] = 'anonymous@example.com'
    msg['To'] = 'server@example.com'
    msg['Subject'] = f'[WORK] {work.get("seq", 0)}'

    try:
        with smtplib.SMTP('localhost', 1025) as server:
            server.send_message(msg)
    except Exception as e:
        print(f"SMTP Client Error: {e}")


# -- ASYNC MAIN --


async def main():
    # 1. Start servers in the background
    # We use create_task to let them run on the event loop
    server_task = asyncio.create_task(run_servers())

    # 2. Wait for servers to initialize
    await asyncio.sleep(1)

    print("Sending test work...")
    test_work = {'seq': 42, 'task': 'hello world', 'data': 'it works!'}

    # 3. Run blocking SMTP call in a separate thread
    await asyncio.to_thread(send_work_sync, test_work)
    print("Test work sent.")

    # 4. Poll for work
    while True:
        print('Polling for work...')
        # Run blocking IMAP call in a separate thread
        found_work = await asyncio.to_thread(fetch_pending_work_sync)

        if found_work:
            for work in found_work:
                print('Received work:', work)

        await asyncio.sleep(5)


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutting down.")
