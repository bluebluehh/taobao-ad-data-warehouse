"""Read-only dashboard server. Default binding is local loopback only."""
import argparse
import json
import mimetypes
import sqlite3
import time
import threading
import sys
from datetime import date
from functools import lru_cache
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from urllib.request import build_opener, ProxyHandler

from .metrics import GROUPS, bundle, connect

ROOT = Path(__file__).resolve().parents[1]


def check_connection(host, port):
    """Check the HTTP path, without inheriting an HTTP proxy."""
    url = f'http://{host}:{port}/api/health'
    try:
        opener = build_opener(ProxyHandler({}))
        with opener.open(url, timeout=5) as response:
            result = json.load(response)
        if not result.get('ok'):
            raise RuntimeError('Warehouse database not found')
        print(f'[HTTP CHECK OK] {url}', flush=True)
        print('Ready. Open the dashboard in your browser.', flush=True)
    except Exception as exc:
        print(f'[HTTP CHECK FAILED] {type(exc).__name__}: {exc}', flush=True)
        print('The socket was bound, but HTTP connectivity is NOT verified.', flush=True)
        print('If the browser also times out, this is before database queries.', flush=True)
        print('See output/midterm/dashboard_startup.log for diagnostics.', flush=True)


def validate_params(values):
    allowed = {'start','end','pid','campaign','category','gender','age','shopping','group','order','minimum'}
    if set(values) - allowed:
        raise ValueError('Unsupported query parameter')
    p = {key: value[-1] for key, value in values.items()}
    for key in ['start','end']:
        if p.get(key):
            date.fromisoformat(p[key])
    if p.get('start') and p.get('end') and p['start'] > p['end']:
        raise ValueError('开始日期不能晚于结束日期')
    if p.get('group','campaign') not in GROUPS:
        raise ValueError('Unsupported group')
    if p.get('order','clicks') not in ['clicks','ctr']:
        raise ValueError('Unsupported order')
    minimum = int(p.get('minimum','1000'))
    if not 0 <= minimum <= 1000000000:
        raise ValueError('Minimum outside range')
    return p


def handler(db_path):
    @lru_cache(maxsize=24)
    def query_cached(stamp, query):
        p = validate_params(parse_qs(query, keep_blank_values=True))
        group, order, minimum = p.pop('group','campaign'), p.pop('order','clicks'), int(p.pop('minimum','1000'))
        with connect(db_path) as db:
            db.execute('PRAGMA cache_size=-262144')
            result = bundle(db, p, group, order, minimum)
            result['meta'] = {row['key']: json.loads(row['value']) for row in db.execute('SELECT * FROM run_info')}
            result['options'] = {key: [r[0] for r in db.execute('SELECT DISTINCT '+col+' FROM v_exposure_detail WHERE '+col+' IS NOT NULL ORDER BY '+col)]
                                 for key,col in [('pid','pid'),('gender','gender_code'),('age','age_level'),('shopping','shopping_level')]}
        return json.dumps(result, ensure_ascii=False, allow_nan=False).encode('utf-8')

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            url = urlparse(self.path)
            try:
                if url.path == '/api/data':
                    payload = query_cached(db_path.stat().st_mtime_ns, url.query)
                    kind = 'application/json; charset=utf-8'
                elif url.path == '/api/health':
                    payload = json.dumps({'ok': db_path.is_file(), 'read_only': True}).encode()
                    kind = 'application/json'
                elif url.path in ('/', '/index.html', '/app.js', '/style.css'):
                    name = 'index.html' if url.path in ('/','/index.html') else url.path[1:]
                    path = ROOT / 'web' / name
                    payload = path.read_bytes()
                    kind = {'html':'text/html','js':'application/javascript','css':'text/css'}[path.suffix[1:]] + '; charset=utf-8'
                else:
                    self.send_error(404)
                    return
                self.send_response(200)
                self.send_header('Content-Type', kind)
                self.send_header('Content-Length',str(len(payload)))
                self.send_header('Cache-Control','no-store')
                self.send_header('X-Content-Type-Options','nosniff')
                self.end_headers()
                self.wfile.write(payload)
            except (ValueError, KeyError) as exc:
                data = json.dumps({'error':str(exc)},ensure_ascii=False).encode()
                self.send_response(400)
                self.send_header('Content-Type','application/json; charset=utf-8')
                self.send_header('Content-Length',str(len(data)))
                self.end_headers()
                self.wfile.write(data)
            except (OSError, sqlite3.Error) as exc:
                self.log_error('Request failed: %r',exc)
                self.send_error(500, 'Dashboard query unavailable; inspect server log')

    return Handler


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--db',type=Path,default=ROOT/'output/midterm/warehouse.sqlite3')
    p.add_argument('--port',type=int,default=8765)
    p.add_argument('--host',default='127.0.0.1')
    p.add_argument('--self-check', action='store_true')
    args=p.parse_args()
    if not args.db.is_file():
        p.error('Build warehouse first: python -m warehouse.build')
    if args.host not in ('127.0.0.1','localhost'):
        p.error('This development server only allows loopback; configure authentication before external deployment')
    server=ThreadingHTTPServer((args.host,args.port),handler(args.db))
    print(f'Python: {sys.executable}', flush=True)
    print(f'Database: {args.db.resolve()}', flush=True)
    print(f'Socket bound: {server.server_address}', flush=True)
    print(f'Dashboard: http://{args.host}:{args.port} (read-only; Ctrl+C to stop)',flush=True)
    if args.self_check:
        threading.Thread(target=check_connection, args=(args.host,args.port), daemon=True).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__=='__main__':
    main()
