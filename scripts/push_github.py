"""Push using existing Git settings or the current Windows system proxy."""
import argparse
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]


def system_proxy():
    if sys.platform != 'win32':
        return None
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                           r'Software\Microsoft\Windows\CurrentVersion\Internet Settings') as key:
            if not winreg.QueryValueEx(key, 'ProxyEnable')[0]:
                return None
            server = winreg.QueryValueEx(key, 'ProxyServer')[0].strip()
    except OSError:
        return None
    if '=' in server:
        values = dict(item.strip().split('=', 1) for item in server.split(';') if '=' in item)
        server = values.get('https') or values.get('http')
    if not server:
        return None
    return server if '://' in server else 'http://' + server


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--diagnose', action='store_true', help='Show connection mode without pushing')
    args = parser.parse_args()
    configured = subprocess.run(
        ['git', 'config', '--get-urlmatch', 'http.proxy', 'https://github.com/'],
        cwd=ROOT, text=True, capture_output=True)
    # An explicit Git proxy (including an explicit empty value) takes precedence.
    proxy = None if configured.returncode == 0 else system_proxy()
    command = ['git', '-c', 'http.lowSpeedLimit=1', '-c', 'http.lowSpeedTime=45']
    if proxy:
        parsed = urlsplit(proxy)
        print(f'Using current Windows proxy: {parsed.scheme}://{parsed.hostname}:{parsed.port}', flush=True)
        command += ['-c', 'http.proxy=' + proxy]
    else:
        print('Using existing Git/environment connection settings.', flush=True)
    command += ['push', '--progress', '-u', 'origin', 'main']
    if args.diagnose:
        print('Diagnostic only; no push attempted.', flush=True)
        return 0
    print('Connecting to GitHub. Complete browser sign-in if Git requests it.', flush=True)
    try:
        return subprocess.run(command, cwd=ROOT).returncode
    except KeyboardInterrupt:
        print('\nPush interrupted. Local commits are preserved.', flush=True)
        return 130


if __name__ == '__main__':
    raise SystemExit(main())
