#!/usr/bin/env python3
"""Airscanner-Server für den Mac mini.
Liefert die App aus und holt die Flugdaten (umgeht die CORS-Sperre).
Start:      python3 server.py            -> http://<IP-Mac-mini>:8080
Autostart:  python3 server.py --install  (startet bei jedem Login automatisch)
Entfernen:  python3 server.py --uninstall
"""
import os, sys, subprocess, urllib.request
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler

PORT = 8080
DIR = os.path.dirname(os.path.abspath(__file__))
UPSTREAM = {'/proxy/': 'https://api.adsb.lol/', '/proxy2/': 'https://api.airplanes.live/',
            '/proxy3/': 'https://api.planespotters.net/'}
LABEL = 'de.matthias.airscanner'
PLIST = os.path.expanduser(f'~/Library/LaunchAgents/{LABEL}.plist')

class H(SimpleHTTPRequestHandler):
    def __init__(self, *a, **k): super().__init__(*a, directory=DIR, **k)
    def log_message(self, *a): pass
    def do_GET(self):
        for pre, base in UPSTREAM.items():
            if self.path.startswith(pre):
                return self.proxy(base + self.path[len(pre):].lstrip('/'))
        return super().do_GET()
    def proxy(self, url):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'airscanner/1.0'})
            with urllib.request.urlopen(req, timeout=10) as r:
                body, code = r.read(), r.status
        except urllib.error.HTTPError as e:
            body, code = e.read(), e.code
        except Exception as e:
            body, code = str(e).encode(), 502
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(body)

def install():
    os.makedirs(os.path.dirname(PLIST), exist_ok=True)
    open(PLIST, 'w').write(f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
<key>Label</key><string>{LABEL}</string>
<key>ProgramArguments</key><array><string>{sys.executable}</string><string>{os.path.abspath(__file__)}</string></array>
<key>WorkingDirectory</key><string>{DIR}</string>
<key>RunAtLoad</key><true/><key>KeepAlive</key><true/>
</dict></plist>''')
    subprocess.run(['launchctl', 'unload', PLIST], capture_output=True)
    subprocess.run(['launchctl', 'load', PLIST])
    print('Autostart eingerichtet. Läuft auf Port', PORT)

if __name__ == '__main__':
    if '--install' in sys.argv: install(); sys.exit()
    if '--uninstall' in sys.argv:
        subprocess.run(['launchctl', 'unload', PLIST]); os.path.exists(PLIST) and os.remove(PLIST)
        print('Autostart entfernt.'); sys.exit()
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.connect(('8.8.8.8', 80)); ip = s.getsockname()[0]
    except Exception: ip = 'localhost'
    print(f'Airscanner läuft: http://{ip}:{PORT}  (Strg+C beendet)')
    ThreadingHTTPServer(('0.0.0.0', PORT), H).serve_forever()
