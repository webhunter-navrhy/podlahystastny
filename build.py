#!/usr/bin/env python3
"""Sestaví návrh webu podlahystastny.cz do složky site/ (obsah v _data/*.json)."""
import json, re, os, shutil, hashlib, html
from jinja2 import Environment, FileSystemLoader

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, 'site')
D = lambda n: json.load(open(os.path.join(ROOT, '_data', n), encoding='utf-8'))
S, H, PAGES = D('site.json'), D('home.json'), D('pages.json')
IMAP = D('pages_images_map.json'); IMAP.update(D('home_images_map.json'))
DOMAIN = S['domain']
# stránky, které klient nechce (značky už nevede) – nezobrazují se, stará URL přesměruje na rodiče
REMOVED = S.get('removed', {})
GONE = re.compile(r'moland|ter ?h[üu]rne|tarkett|amtico', re.I)

if os.path.exists(OUT): shutil.rmtree(OUT)
os.makedirs(OUT)
shutil.copytree(os.path.join(ROOT, 'assets'), os.path.join(OUT, 'assets'))
for n in ('style.css', 'main.js'): shutil.copy(os.path.join(ROOT, 'src', n), os.path.join(OUT, 'assets', n))
shutil.copytree(os.path.join(ROOT, 'img'), os.path.join(OUT, 'img'))
open(os.path.join(OUT, '.nojekyll'), 'w').close()
V = {k: hashlib.md5(open(os.path.join(OUT, 'assets', f), 'rb').read()).hexdigest()[:8] for k, f in (('css', 'style.css'), ('js', 'main.js'))}

by_path = {p['path']: p for p in PAGES}
by_id = {p['id']: p for p in PAGES}
kids = {}
for p in PAGES:
    if p['path'] not in REMOVED: kids.setdefault(p['parent'], []).append(p)
for v in kids.values(): v.sort(key=lambda p: (p['order'], p['title']))

def IM(u):
    m = IMAP.get(u)
    return {'p': 'img/wp/' + m['f'], 'w': m['w'], 'h': m['h']} if m else None

def make_L(R):
    def L(h):
        if not h: return '#'
        if h.startswith('@'): h = h[1:]
        if h.startswith('/'):
            path, frag = (h.split('#', 1) + [''])[:2]
            path = path.split('?')[0]
            if path in ('/', ''): return R + (('#' + frag) if frag else '') or './'
            if not path.endswith('/') and path + '/' in by_path: path += '/'
            if path in by_path: return R + path.lstrip('/') + (('#' + frag) if frag else '')
            return DOMAIN + h
        return h
    return L

def fix_inline(s, L):
    return re.sub(r'href="(@[^"]*|/[^"]*)"', lambda m: 'href="%s"' % html.escape(L(html.unescape(m.group(1)))), s)

def plain(s): return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', html.unescape(s))).strip()

JUNK = re.compile(r'ESSENTIAL GRID|^\s*aa\s*$', re.I)
def prep_blocks(p, L):
    out = []
    bl = [b for b in p['blocks'] if not (b['t'] == 'p' and (JUNK.search(b['h']) or not plain(b['h'])))]
    for i, b in enumerate(bl):
        b = dict(b)
        if b['t'] == 'p':
            b['h'] = fix_inline(b['h'], L); t = plain(b['h'])
            nxt = bl[i + 1] if i + 1 < len(bl) else None
            if len(t) <= 90 and '<a ' not in b['h'] and nxt and nxt['t'] in ('p', 'ul', 'ol', 'gallery', 'img') and (t.endswith('?') or t.endswith(':') or re.match(r'^\d+\.\s', t) or re.fullmatch(r'\s*<strong>.*</strong>\s*', b['h'])):
                b = {'t': 'sub', 'h': re.sub(r'</?strong>', '', b['h'])}
        elif b['t'] in ('ul', 'ol'):
            b['items'] = [fix_inline(x, L) for x in b['items']]
        elif b['t'] == 'table':
            b['rows'] = [[fix_inline(c, L) for c in r] for r in b['rows']]
        elif b['t'] == 'gallery':
            b['items'] = [it for it in b['items'] if IM(it['src'])]
            if not b['items']: continue
        elif b['t'] == 'img' and not IM(b['src']): continue
        elif b['t'] == 'cards':
            b['items'] = [c for c in b['items'] if c.get('title') and not GONE.search(c['title'] + ' ' + (c.get('href') or ''))]
        out.append(b)
    # ukázky prací bývají až pod dlouhým textem – kotva, ať se na ně dá skočit z hlavičky
    gi = next((i for i, b in enumerate(out) if b['t'] == 'gallery'), None)
    if gi is not None and gi > 6:
        hi = gi - 1 if out[gi - 1]['t'] in ('h', 'sub') else gi
        out[hi] = dict(out[hi], anchor='ukazky')
    return out

def first_img(p):
    for b in p['blocks']:
        if b['t'] == 'img' and IM(b['src']): return b['src']
        if b['t'] == 'gallery':
            for it in b['items']:
                if IM(it['src']): return it['src']
        if b['t'] == 'cards':
            for c in b['items']:
                if c.get('img') and IM(c['img']): return c['img']
    return None

def excerpt(p, n=150):
    for b in p['blocks']:
        if b['t'] == 'p':
            t = plain(b['h'])
            if len(t) > 50 and 'ESSENTIAL' not in t: return t[:n].rsplit(' ', 1)[0] + '…' if len(t) > n else t
    return ''

env = Environment(loader=FileSystemLoader(os.path.join(ROOT, 'src')), autoescape=True, trim_blocks=True, lstrip_blocks=True)
LD = json.dumps({"@context": "https://schema.org", "@type": "HomeAndConstructionBusiness", "name": S['name'], "url": DOMAIN + '/',
    "telephone": S['phone'], "email": S['email'], "image": DOMAIN + '/wp-content/uploads/2021/01/IMG_6395.jpg',
    "address": {"@type": "PostalAddress", "streetAddress": S['address'], "addressLocality": "Praha 2 – Vinohrady", "postalCode": S['zip'], "addressCountry": "CZ"},
    "openingHours": ["Mo-Tu 09:00-18:00", "We-Th 09:00-17:00", "Fr 09:00-16:30"], "areaServed": "Praha a okolí"}, ensure_ascii=False)

def write(path, html_):
    fp = os.path.join(OUT, path.strip('/'), 'index.html') if path.strip('/') else os.path.join(OUT, 'index.html')
    os.makedirs(os.path.dirname(fp), exist_ok=True)
    open(fp, 'w', encoding='utf-8').write(html_)

# homepage
R = ''; L = make_L(R)
write('/', env.get_template('home.html').render(S=S, H=H, R=R, L=L, IM=IM, V=V, title=H['seo_title'], description=H['description'],
      og=DOMAIN + '/wp-content/uploads/2025/02/image51.jpeg', ld=LD, announce=H['announce'], body_class='home', active='/'))

# subpages
tpl = env.get_template('page.html')
for p in PAGES:
    if p['path'] == '/': continue
    if p['path'] in REMOVED:
        depth = len([x for x in p['path'].split('/') if x]); R = '../' * depth
        to = R + REMOVED[p['path']].lstrip('/')
        write(p['path'], '<!doctype html><meta charset="utf-8"><meta name="robots" content="noindex"><title>Přesměrování</title><link rel="canonical" href="%s"><meta http-equiv="refresh" content="0;url=%s"><a href="%s">Pokračovat</a>' % (DOMAIN + REMOVED[p['path']], to, to))
        continue
    depth = len([x for x in p['path'].split('/') if x])
    R = '../' * depth; L = make_L(R)
    blocks = prep_blocks(p, L)
    lead = None
    if blocks and blocks[0]['t'] == 'p' and 60 < len(plain(blocks[0]['h'])) < 420:
        lead = blocks.pop(0)['h']
    cover = None
    for i, b in enumerate(blocks[:4]):
        if b['t'] == 'img' and IM(b['src'])['w'] >= 1200 and IM(b['src'])['w'] > IM(b['src'])['h'] * 1.3:
            cover = b['src']; blocks.pop(i); break
    # drobečky + sekce
    crumbs, a = [], by_id.get(p['parent'])
    while a: crumbs.insert(0, a); a = by_id.get(a['parent'])
    top = crumbs[0] if crumbs else p
    section = None
    if kids.get(top['id']):
        items = [top]
        for c in kids[top['id']]:
            items.append(c)
            items += kids.get(c['id'], [])
        section = {'title': top['title'], 'items': [{'path': x['path'], 'title': x['title']} for x in items][:16]}
    children = [{'path': c['path'], 'title': c['title'], 'thumb': first_img(c), 'excerpt': excerpt(c)} for c in kids.get(p['id'], [])]
    if any(b['t'] == 'cards' for b in blocks): children = []
    reviews = None
    reno = by_path.get('/rekonstrukce-a-renovace-podlah/')
    if p['path'] == '/ukazky-nasi-prace/':
        reviews = H['reviews']
        if reno:
            gal = next(b for b in reno['blocks'] if b['t'] == 'gallery' and any(IM(it['src']) for it in b['items']))
            thumb = next(it['src'] for it in gal['items'] if IM(it['src']))
            children.append({'path': reno['path'] + '#ukazky', 'title': 'Renovace parket a dřevěných podlah', 'thumb': thumb, 'excerpt': 'Ukázky renovací starých parket a masivních dřevěných podlah.'})
    empty_note = None
    if not blocks and not children:
        if 'teras' in p['path']:
            empty_note = 'Dřevěné a WPC terasy najdete na našem samostatném webu <a href="https://www.terasy-drevoplast.cz/">terasy-drevoplast.cz</a>.'
        elif p['parent'] in kids:
            children = [{'path': c['path'], 'title': c['title'], 'thumb': first_img(c), 'excerpt': excerpt(c)} for c in kids[p['parent']] if c['id'] != p['id']]
    desc = p['description'] or excerpt(p, 155)
    if section and section['title'] == 'Reference' and reno:
        section['items'].insert(-1 if section['items'][-1]['title'] == 'Ke stažení' else len(section['items']), {'path': '/rekonstrukce-a-renovace-podlah/#ukazky', 'title': 'Renovace parket a dřevěných podlah'})
    jump = False  # tlačítko Ukázky na podstránkách zrušeno (10. 10. 2026, přání klienta)
    P = dict(p, blocks=blocks, reviews=reviews, jump=jump, lead=lead, cover=cover, crumbs=[{'path': c['path'], 'title': c['title']} for c in crumbs], section=section, children=children, empty_note=empty_note)
    nav_active = next((n['h'] for n in S['nav'] if n['h'] != '/' and p['path'].startswith(n['h'])), '')
    write(p['path'], tpl.render(S=S, P=P, R=R, L=L, IM=IM, V=V, title=p['seo_title'] or p['title'], description=desc,
          og=p.get('og_image') or '', ld=LD, announce=H['announce'], body_class='sub', active=nav_active))

# 404
R = '/podlahystastny/'; L = make_L(R)
P404 = {'path': '/404/', 'title': 'Stránka nenalezena', 'blocks': [{'t': 'p', 'h': 'Tuto stránku jsme nenašli. Zkuste prosím <a href="' + R + '">úvodní stránku</a> nebo nás kontaktujte.'}], 'lead': None, 'cover': None, 'crumbs': [], 'section': None, 'children': [], 'empty_note': None}
open(os.path.join(OUT, '404.html'), 'w', encoding='utf-8').write(tpl.render(S=S, P=P404, R=R, L=L, IM=IM, V=V, title='Stránka nenalezena – Podlahy Šťastný', description='', og='', ld=LD, announce=H['announce'], body_class='sub', active=''))
print('hotovo:', len(PAGES), 'stránek →', OUT)
