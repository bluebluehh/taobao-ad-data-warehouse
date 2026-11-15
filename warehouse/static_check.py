"""Check local page structure, separately from browser visual acceptance."""
import ast
import re
import shutil
import subprocess
from html.parser import HTMLParser

from .build import ROOT, now, write_json


def main():
    for p in (ROOT/'warehouse').glob('*.py'):
        ast.parse(p.read_text(encoding='utf-8'))
    html=(ROOT/'web/index.html').read_text(encoding='utf-8')
    js=(ROOT/'web/app.js').read_text(encoding='utf-8')
    ids=re.findall(r'id="([^"]+)"',html)
    refs=re.findall(r'''el\(['"]([^'"]+)['"]\)''',js)
    assert len(ids)==len(set(ids)), 'Duplicate HTML IDs'
    assert set(refs)<=set(ids), set(refs)-set(ids)
    HTMLParser().feed(html)
    preview_path=ROOT/'output/midterm/dashboard_preview.html'
    if not preview_path.exists():
        preview_path=ROOT/'examples/dashboard_preview.html'
    preview=preview_path.read_text(encoding='utf-8')
    assert 'window.STATIC_SNAPSHOT=' in preview
    assert '<script src=' not in preview and '<link rel="stylesheet"' not in preview
    node=shutil.which('node')
    if node:
        subprocess.run([node,'--check',str(ROOT/'web/app.js')],check=True,capture_output=True)
    report={'at':now(),'python_syntax':'passed','html_id_uniqueness':'passed',
            'javascript_element_targets':'passed','self_contained_preview':'passed',
            'javascript_syntax':'passed' if node else 'not_run_node_unavailable',
            'visual_check':'not_completed_browser_session_failed'}
    write_json(ROOT/'output/midterm/static_checks.json',report)
    print(report)


if __name__=='__main__':
    main()
