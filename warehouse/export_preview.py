"""Create a standalone static dashboard snapshot; no external web assets."""
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def main():
    out=ROOT/'output/midterm'
    snapshot=json.loads((out/'ads_snapshot.json').read_text(encoding='utf-8'))
    html=(ROOT/'web/index.html').read_text(encoding='utf-8')
    css=(ROOT/'web/style.css').read_text(encoding='utf-8')
    js=(ROOT/'web/app.js').read_text(encoding='utf-8')
    data=json.dumps(snapshot,ensure_ascii=False,allow_nan=False).replace('</','<\\/')
    html=html.replace('<link rel="stylesheet" href="/style.css">','<style>'+css+'</style>')
    html=html.replace('<script src="/app.js"></script>','<script>window.STATIC_SNAPSHOT='+data+';</script><script>'+js+'</script>')
    target=out/'dashboard_preview.html'
    target.write_text(html,encoding='utf-8')
    print(target)


if __name__=='__main__':
    main()
