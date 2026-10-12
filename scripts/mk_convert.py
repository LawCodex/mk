#!/usr/bin/env python3
"""Convert North Macedonian laws fetched by mk_fetch.py (LDBIS records + PDFs) to Markdown.

Usage: mk_convert.py RAW_DIR OUT_DIR
"""
import datetime, json, os, re, sys, unicodedata
from bs4 import BeautifulSoup
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mk_textmd import structure, pdftotext

RAW, OUT = sys.argv[1], sys.argv[2]
TODAY = datetime.date.today().isoformat()
MK = dict(zip('абвгдѓежзѕијклљмнњопрстќуфхцчџш',
              ['a', 'b', 'v', 'g', 'd', 'gj', 'e', 'zh', 'z', 'dz', 'i', 'j', 'k', 'l', 'lj', 'm', 'n', 'nj', 'o', 'p',
               'r', 's', 't', 'kj', 'u', 'f', 'h', 'c', 'ch', 'dj', 'sh']))
FIELDS = {'Наслов:': 'title', 'Вид на пропис:': 'kind', 'Верзија:': 'version', 'Институција:': 'institution',
          'Службено гласило:': 'gazette', 'Број на издание:': 'issue', 'Датум на објавување:': 'published',
          'Датум на стапување во сила:': 'in_force_from', 'Почеток на примена:': 'applies_from',
          'Датум на престанок на важење:': 'ended'}
VERSION = {'Изворен текст': 'original', 'Текст измена/дополна': 'amendment', 'Пречистен текст': 'official_consolidated',
           'Пречистена верзија': 'consolidated',
           'Консолидиран текст': 'consolidated', 'Исправка': 'correction'}


def slug(s, n=70):
    s = ''.join(MK.get(c, c) for c in s.lower())
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode()
    return re.sub(r'[^a-z0-9]+', '-', s).strip('-')[:n].rstrip('-')


def yq(s):
    return '"' + re.sub(r'\s+', ' ', s).strip().replace('\\', '\\\\').replace('"', '\\"') + '"'


def dmy(s):
    m = re.search(r'(\d{1,2})\.(\d{1,2})\.(\d{4})', s or '')
    if m:
        try:
            return datetime.date(int(m.group(3)), int(m.group(2)), int(m.group(1))).isoformat()
        except ValueError:
            return None


def record(fn):
    s = BeautifulSoup(open(fn).read(), 'lxml')
    parts = s.get_text(' | ', strip=True).split(' | ')
    rec = {}
    for i, p in enumerate(parts[:-1]):
        if p in FIELDS and FIELDS[p] not in rec:
            nxt = parts[i + 1]
            rec[FIELDS[p]] = '' if nxt in FIELDS else nxt
    return rec


def main():
    lst = {x['id']: x for x in json.load(open(os.path.join(RAW, 'list.json')))}
    counts, skipped = {}, {}
    for fn in sorted(os.listdir(os.path.join(RAW, 'rec'))):
        aid = int(fn.split('.')[0])
        r = record(os.path.join(RAW, 'rec', fn))
        if not r.get('title'):
            skipped['norecord'] = skipped.get('norecord', 0) + 1; continue
        if r.get('ended') and r['ended'] != 'Активен':
            skipped['ended'] = skipped.get('ended', 0) + 1; continue
        pf = os.path.join(RAW, 'pdf', '%d.pdf' % aid)
        if not os.path.exists(pf):
            skipped['nopdf'] = skipped.get('nopdf', 0) + 1; continue
        t = pdftotext(pf)
        if len(t.strip()) < 150:
            skipped['notext'] = skipped.get('notext', 0) + 1; continue
        md = structure(t)
        title = r['title']
        kind = r.get('kind', '')
        pub = dmy(r.get('published'))
        year = (pub or '0000')[:4]
        tl = title.lower()
        if kind.startswith('Устав') and not kind.startswith('Уставен') or tl.startswith('устав на') or tl.startswith('амандман'):
            sub, typ = 'ustav', 'constitution' if tl.startswith('устав') else 'constitutional_amendment'
        elif kind.startswith('Уставен закон'):
            sub, typ = 'ustav', 'constitutional_act'
        else:
            sub, typ = 'zakoni/%s' % year, 'act'
        r['version'] = re.sub(r'\s+', ' ', r.get('version', '')).strip()
        ver = VERSION.get(r.get('version', ''), slug(r.get('version', '')) or 'unknown')
        issue = r.get('issue', '')
        fname = '%s-%s-%d-%s.md' % (year, slug(issue, 8) or 'x', aid, slug(title, 70))
        path = os.path.join(OUT, sub, fname)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        fm = ['---', 'title: ' + yq(title),
              'identifier: ' + yq('%s %s/%s' % (r.get('gazette', 'Службен весник'), issue, year)),
              'ldbis_id: %d' % aid, 'type: ' + typ, 'jurisdiction: mk', 'language: mk']
        if pub:
            fm.append('date: ' + pub)
        if dmy(r.get('in_force_from')):
            fm.append('in_force_from: ' + dmy(r.get('in_force_from')))
        fm += ['status: in_force', 'text_version: ' + ver,
               'source: ' + yq('https://ldbis.pravda.gov.mk/PregledNaZakon.aspx?id=%d' % aid),
               'retrieved: ' + TODAY, '---']
        open(path, 'w').write('\n'.join(fm) + '\n\n# ' + title + '\n\n' + md + '\n')
        counts[(typ, ver)] = counts.get((typ, ver), 0) + 1
    print(skipped, file=sys.stderr)
    for k, v in sorted(counts.items()):
        print(k, v, file=sys.stderr)


if __name__ == '__main__':
    main()
