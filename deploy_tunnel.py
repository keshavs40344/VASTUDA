"""
VASTUDA Cloudflare Tunnel Launcher (100% Free Public Live Deployment)
Exposes VASTUDA (http://localhost:5000) to the public internet securely using Cloudflare's Edge Network.
Cost: Rs 0 (Zero Rupee Forever, No Credit Card, No Account Required)
"""

import os
import sys
import time
import re
import subprocess

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

LOCAL_EXE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cloudflared.exe")


def start_tunnel(port=5000):
    if not os.path.exists(LOCAL_EXE):
        print("[Error] cloudflared.exe not found.")
        return

    print(f"[Cloudflare Tunnel] Connecting localhost:{port} to Cloudflare Global Edge Network...")
    cmd = [LOCAL_EXE, "tunnel", "--url", f"http://127.0.0.1:{port}"]

    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1
    )

    tunnel_url = None
    url_pattern = re.compile(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com")
    live_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "LIVE_URL.txt")

    for line in process.stdout:
        match = url_pattern.search(line)
        if match and not tunnel_url:
            tunnel_url = match.group(0)
            with open(live_file, "w", encoding="utf-8") as f:
                f.write(tunnel_url.strip())
            
            print("\n" + "=" * 64)
            print("  VASTUDA IS NOW LIVE WORLDWIDE ON THE INTERNET! (RS 0)")
            print(f"  Public Live URL: {tunnel_url}")
            print("  Encrypted HTTPS | Cloudflare Edge Protection | Free Forever")
            print("=" * 64 + "\n", flush=True)

    try:
        process.wait()
    except KeyboardInterrupt:
        print("\n[Cloudflare Tunnel] Tunnel terminated.")
        process.terminate()


if __name__ == "__main__":
    target_port = int(os.environ.get("PORT", 5000))
    start_tunnel(target_port)
