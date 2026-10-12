#!/usr/bin/env python3
"""Fetch laws of North Macedonia from LDBIS, the legislation database of the Ministry of Justice
(https://ldbis.pravda.gov.mk - "База на закони, подзаконски акти и други прописи").

1. Run the site's basic search for the words "закон" and "устав" and walk the result grid
   (tab "Влезени во сила" = acts in force), page by page (ASP.NET/Telerik postbacks).
2. Keep acts whose title starts with Закон / Устав / Уставен закон / Амандман.
3. For each act fetch the record page (PregledNaZakon.aspx?id=N, metadata incl. status) and the
   PDF of the text that the page links (PdfFiles/<name>.pdf).

Usage: mk_fetch.py [RAW_DIR]
"""
import json, os, re, sys, time, html as htmlmod
from concurrent.futures import ThreadPoolExecutor
import requests
from bs4 import BeautifulSoup

RAW = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '_raw', 'mk')
BASE = 'https://ldbis.pravda.gov.mk/'
UA = 'LawCodex/1.0 (+https://github.com/LawCodex)'
DELAY = 0.5
KEEP = re.compile(r'^\s*(Закон|Законик|Устав|Уставен закон|Амандман)', re.I)


def req(s, method, url, **kw):
    for i in range(6):
        try:
            r = s.request(method, url, timeout=180, **kw)
            if r.status_code >= 500 or r.status_code == 429:
                raise requests.RequestException('HTTP %d' % r.status_code)
            time.sleep(DELAY)
            return r
        except requests.RequestException as e:
            w = 5 * 2 ** i
            print('  retry', url, e, w, file=sys.stderr, flush=True); time.sleep(w)
    raise SystemExit('give up ' + url)


def fields(text):
    s = BeautifulSoup(text, 'lxml')
    return {i['name']: i.get('value', '') for i in s.find_all('input')
            if i.get('name') and i.get('type') not in ('submit', 'image', 'checkbox', 'radio')}


def parse_rows(text):
    s = BeautifulSoup(text, 'lxml')
    g = s.find(id='Header_rgvDokumenti')
    rows = []
    if not g:
        return rows
    for tr in g.select('tr.rgRow, tr.rgAltRow'):
        td = [x.get_text(' ', strip=True) for x in tr.find_all('td', recursive=False)]
        while td and not td[0].isdigit():
            td = td[1:]
        if len(td) >= 6 and td[0].isdigit():
            rows.append({'id': int(td[0]), 'title': td[1], 'in_force': td[2], 'applies': td[3], 'gazette': td[4], 'version': td[5]})
    return rows


def search(term):
    s = requests.Session(); s.headers['User-Agent'] = UA
    r = req(s, 'GET', BASE)
    d = fields(r.text)
    btn = BeautifulSoup(r.text, 'lxml').find('input', attrs={'name': 'Header$btnPrebaraj'})
    d['Header$txtPrebaraj'] = term; d['Header$btnPrebaraj'] = btn.get('value', '')
    r = req(s, 'POST', BASE, data=d)
    url = BASE + 'Prebaruvanje.aspx'
    # 50 rows per page (RadGrid page-size command, as sent by the grid's own page-size selector)
    d = fields(r.text); d['__EVENTTARGET'] = 'Header$rgvDokumenti'
    d['__EVENTARGUMENT'] = 'FireCommand:Header$rgvDokumenti$ctl00;PageSize;50'
    r = req(s, 'POST', url, data=d)
    out, page = [], 1
    while True:
        rows = parse_rows(r.text)
        if not rows or (out and all(x in out for x in rows)):
            break
        out += rows
        nxt = BeautifulSoup(r.text, 'lxml').find('input', class_='rgPageNext')
        if not nxt or 'return false' in (nxt.get('onclick') or ''):
            break
        d = fields(r.text); d[nxt['name']] = nxt.get('value', ' ')
        r = req(s, 'POST', url, data=d)
        page += 1
        if page % 10 == 0:
            print(term, page, len(out), file=sys.stderr, flush=True)
    return out


def main():
    os.makedirs(RAW + '/rec', exist_ok=True); os.makedirs(RAW + '/pdf', exist_ok=True)
    lf = RAW + '/list.json'
    if os.path.exists(lf):
        rows = json.load(open(lf))
    else:
        rows = []
        for term in ('закон', 'устав'):
            rr = search(term)
            print(term, len(rr), file=sys.stderr, flush=True)
            rows += rr
        json.dump(rows, open(lf, 'w'), ensure_ascii=False)
    acts = {}
    for x in rows:
        if KEEP.match(x['title']):
            acts[x['id']] = x
    print(len(acts), 'acts', file=sys.stderr, flush=True)
    sessions = [requests.Session() for _ in range(4)]
    for s in sessions:
        s.headers['User-Agent'] = UA

    def one(args):
        n, aid = args
        s = sessions[n % 4]
        fn = RAW + '/rec/%d.html' % aid
        pf = RAW + '/pdf/%d.pdf' % aid
        if os.path.exists(fn) and (os.path.exists(pf) or os.path.exists(pf + '.none')):
            return
        r = req(s, 'GET', BASE + 'PregledNaZakon.aspx?id=%d' % aid)
        bs = BeautifulSoup(r.text, 'lxml')
        box = bs.find('form') or bs.body
        for t in box(['script', 'style']):
            t.decompose()
        open(fn, 'w').write(str(box))
        m = re.search(r'file=(/PdfFiles/[^\s"\']+\.pdf)', r.text)
        if m:
            p = req(s, 'GET', BASE.rstrip('/') + m.group(1))
            if p.status_code == 200 and p.content[:4] == b'%PDF':
                open(pf + '.tmp', 'wb').write(p.content); os.replace(pf + '.tmp', pf)
                return
        open(pf + '.none', 'w').write('no pdf')
    # base laws first, amending laws afterwards
    order = sorted(acts, key=lambda i: (bool(re.match(r'^\s*Закон\s+за\s+(изменување|дополнување|изменувања)', acts[i]['title'])), -i))
    with ThreadPoolExecutor(4) as ex:
        for n, _ in enumerate(ex.map(one, enumerate(order))):
            if n % 200 == 0:
                print('rec', n, file=sys.stderr, flush=True)
    print('done', file=sys.stderr)


if __name__ == '__main__':
    main()
