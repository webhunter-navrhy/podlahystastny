"""Převod obsahu WP stránek (REST content.rendered) na čisté bloky do _data/pages.json."""
import json, re, sys, html
from bs4 import BeautifulSoup, NavigableString, Tag

SITE = sys.argv[1]            # např. podlahystastny.cz
RAW = sys.argv[2]             # raw json ze scrape.py
OUT = sys.argv[3]             # _data/pages.json
DOMAIN_RE = re.compile(r'^https?://(www\.)?' + re.escape(SITE))
IMGS = {}

def norm_img(u):
    if not u: return None
    u = u.strip()
    if u.startswith('//'): u = 'https:' + u
    u = re.sub(r'/wp-content/uploads/cache/(\d{4}/\d{2})/([^/]+)/\d+\.(jpe?g|png|webp)$', r'/wp-content/uploads/\1/\2.\3', u)
    u = re.sub(r'-\d+x\d+(?=\.\w+$)', '', u)
    if 'wp-content/uploads' not in u: return None
    IMGS[u] = 1
    return u

def link(href):
    if not href: return None
    href = href.strip()
    if DOMAIN_RE.match(href):
        path = DOMAIN_RE.sub('', href) or '/'
        if 'wp-content/uploads' in path: return href
        return '@' + path
    return href

KEEP_INLINE = {'strong', 'b', 'em', 'i', 'a', 'br', 'big', 'span', 'u', 'sup', 'sub', 'small'}
def inline(el):
    out = []
    for c in el.children:
        if isinstance(c, NavigableString):
            out.append(html.escape(str(c), quote=False)); continue
        if not isinstance(c, Tag): continue
        n = c.name
        if n == 'br': out.append('<br>'); continue
        if n == 'img': continue
        inner = inline(c)
        if n in ('strong', 'b', 'big'): out.append(f'<strong>{inner}</strong>' if inner.strip() else inner)
        elif n in ('em', 'i'): out.append(f'<em>{inner}</em>' if inner.strip() else inner)
        elif n == 'a':
            h = link(c.get('href'))
            if h and inner.strip(): out.append(f'<a href="{html.escape(h)}">{inner}</a>')
            else: out.append(inner)
        else: out.append(inner)
    s = ''.join(out)
    s = re.sub(r'\s+', ' ', s).replace('\xa0', ' ')
    return s.strip()

def text(el): return re.sub(r'\s+', ' ', el.get_text(' ', strip=True)).replace('\xa0', ' ').strip()

def img_block(img):
    src = img.get('data-src-fg') or img.get('data-src') or img.get('src')
    # nejvetsi ze srcset
    ss = img.get('srcset') or img.get('data-srcset') or ''
    if ss:
        cands = [x.strip().split(' ')[0] for x in ss.split(',') if x.strip()]
        if cands: src = cands[-1]
    u = norm_img(src)
    if not u: return None
    w, h = img.get('width'), img.get('height')
    return {'t': 'img', 'src': u, 'alt': img.get('alt') or img.get('title') or '', 'w': int(w) if w and str(w).isdigit() else None, 'h': int(h) if h and str(h).isdigit() else None,
            'align': 'right' if 'alignright' in ' '.join(img.get('class', []) + (img.parent.get('class', []) if img.parent else [])) else ('left' if 'alignleft' in ' '.join(img.get('class', [])) else '')}

def walk(el, blocks):
    for c in el.children:
        if isinstance(c, NavigableString):
            t = str(c).strip()
            if t and len(t) > 2: blocks.append({'t': 'p', 'h': html.escape(t, quote=False)})
            continue
        if not isinstance(c, Tag): continue
        n = c.name; cls = ' '.join(c.get('class', []))
        if n in ('style', 'script', 'noscript', 'form', 'input', 'textarea', 'label', 'title', 'meta'):
            if n == 'form' or 'wpcf7' in cls: blocks.append({'t': 'form'})
            continue
        if 'wpcf7' in cls: blocks.append({'t': 'form'}); continue
        if 'foogallery' in cls.split() or ('foogallery-container' in cls):
            items = []
            for it in c.select('.fg-item'):
                a = it.find('a'); im = it.find('img')
                u = norm_img((a.get('href') if a else None) or (im.get('data-src-fg') if im else None))
                if not u: continue
                tt = it.select_one('.fg-caption-title'); dd = it.select_one('.fg-caption-desc')
                items.append({'src': u, 'title': text(tt) if tt else (a.get('data-caption-title', '') if a else ''), 'desc': text(dd) if dd else ''})
            if items: blocks.append({'t': 'gallery', 'items': items})
            continue
        if 'pt-cv-wrapper' in cls:
            items = []
            for it in c.select('.pt-cv-content-item'):
                a = it.select_one('.pt-cv-title a') or it.find('a'); im = it.find('img')
                ex = it.select_one('.pt-cv-content')
                exs = ''
                if ex:
                    for rm in ex.select('.pt-cv-rmwrap'): rm.decompose()
                    exs = text(ex)
                items.append({'href': link(a.get('href')) if a else None, 'title': text(it.select_one('.pt-cv-title')) if it.select_one('.pt-cv-title') else '', 'excerpt': exs,
                              'img': norm_img((im.get('srcset', '').split(',')[-1].strip().split(' ')[0] if im and im.get('srcset') else (im.get('src') if im else None)))})
            if items: blocks.append({'t': 'cards', 'items': items})
            continue
        if 'esg-grid' in cls or n == 'article' and 'esg' in cls:
            ims = [img_block(i) for i in c.find_all('img')]
            ims = [i for i in ims if i]
            if ims: blocks.append({'t': 'gallery', 'items': [{'src': i['src'], 'title': i['alt'], 'desc': ''} for i in ims]})
            continue
        if n in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
            for im in c.find_all('img'):
                b = img_block(im)
                if b: blocks.append(b)
            t = inline(c)
            if text(c): blocks.append({'t': 'h', 'l': max(2, min(int(n[1]), 4)) if n != 'h1' else 2, 'x': re.sub(r'<[^>]+>', '', t).strip(' :'), 'center': 'has-text-align-center' in cls})
            continue
        if n in ('p', 'big') and c.find(['div', 'p', 'h1', 'h2', 'h3', 'h4', 'ul', 'ol', 'table', 'figure']):
            walk(c, blocks); continue
        if n in ('p', 'big') or (n == 'div' and not c.find(['div', 'p', 'ul', 'ol', 'h2', 'h3', 'h4', 'table', 'figure', 'img', 'iframe']) and text(c)):
            for im in c.find_all('img'):
                b = img_block(im)
                if b: blocks.append(b)
            t = inline(c)
            if text(c): blocks.append({'t': 'p', 'h': t, 'center': 'has-text-align-center' in cls})
            continue
        if n in ('ul', 'ol'):
            items = [inline(li) for li in c.find_all('li', recursive=False) if text(li)]
            if items: blocks.append({'t': 'ul' if n == 'ul' else 'ol', 'items': items})
            continue
        if n == 'table':
            rows = []
            for tr in c.find_all('tr'):
                rows.append([inline(td) for td in tr.find_all(['td', 'th'])])
            if rows: blocks.append({'t': 'table', 'rows': rows})
            continue
        if n == 'img':
            b = img_block(c)
            if b: blocks.append(b)
            continue
        if n == 'iframe':
            s = c.get('src') or c.get('data-src') or ''
            if 'youtube' in s or 'vimeo' in s: blocks.append({'t': 'video', 'src': s})
            elif 'google.com/maps' in s: blocks.append({'t': 'map'})
            continue
        if n == 'video':
            so = c.find('source'); s = (so.get('src') if so else c.get('src'))
            if s: blocks.append({'t': 'mp4', 'src': s})
            continue
        if n == 'hr': blocks.append({'t': 'hr'}); continue
        if 'wp-block-button' in cls and n == 'div' and 'wp-block-buttons' not in cls:
            a = c.find('a')
            if a and text(a): blocks.append({'t': 'btn', 'href': link(a.get('href')), 'x': text(a)})
            continue
        if n == 'figure':
            im = c.find('img'); cap = c.find('figcaption')
            if im:
                b = img_block(im)
                if b:
                    if cap: b['cap'] = text(cap)
                    blocks.append(b)
            elif c.find('table'): walk(c, blocks)
            elif c.find('iframe'): walk(c, blocks)
            continue
        if n == 'a' and c.find('img') and not text(c):
            b = img_block(c.find('img'))
            if b: blocks.append(b)
            continue
        if n in ('a', 'span', 'strong', 'em', 'b', 'i') and text(c):
            blocks.append({'t': 'p', 'h': inline(c) if n != 'a' else f'<a href="{html.escape(link(c.get("href")) or "#")}">{inline(c)}</a>'}); continue
        walk(c, blocks)

def postprocess(blocks):
    out = []
    for b in blocks:
        # odstavce ✔ / • / – na zacatku → seznam
        if b['t'] == 'p':
            m = re.match(r'^(✔|✓|•|·|-|–|➤|►)\s*', b['h'])
            if m and len(b['h']) < 600:
                item = b['h'][m.end():]
                if out and out[-1]['t'] == 'ul' and out[-1].get('auto'):
                    out[-1]['items'].append(item)
                else:
                    out.append({'t': 'ul', 'items': [item], 'auto': True, 'check': m.group(1) in '✔✓'})
                continue
        if b['t'] == 'gallery' and out and out[-1]['t'] == 'gallery' and not out[-1].get('closed'):
            pass
        out.append(b)
    # slouceni po sobe jdoucich img v galerii
    res = []
    for b in out:
        if b['t'] == 'img' and res and res[-1]['t'] == 'img' and not b.get('cap'):
            prev = res.pop()
            res.append({'t': 'gallery', 'items': [{'src': prev['src'], 'title': prev.get('alt', ''), 'desc': ''}, {'src': b['src'], 'title': b.get('alt', ''), 'desc': ''}], 'loose': True})
            continue
        if b['t'] == 'img' and res and res[-1]['t'] == 'gallery' and res[-1].get('loose'):
            res[-1]['items'].append({'src': b['src'], 'title': b.get('alt', ''), 'desc': ''}); continue
        res.append(b)
    # dedupe obrazku v jedne strance (stejny src)
    return res

pages = json.load(open(RAW))
outp = []
for p in pages:
    path = DOMAIN_RE.sub('', p['link']) or '/'
    s = BeautifulSoup(p['content']['rendered'], 'html.parser')
    blocks = []
    walk(s, blocks)
    blocks = postprocess(blocks)
    title = html.unescape(p['title']['rendered'])
    outp.append({'id': p['id'], 'parent': p['parent'], 'order': p['menu_order'], 'path': path, 'title': title,
                 'seo_title': html.unescape(p.get('html_title', '')), 'description': html.unescape(p.get('meta_description', '')),
                 'og_image': norm_img(p.get('og_image')), 'blocks': blocks})
json.dump(outp, open(OUT, 'w'), ensure_ascii=False, indent=1)
json.dump(sorted(IMGS), open(OUT.replace('.json', '_images.json'), 'w'), indent=0)
print(len(outp), 'stránek,', len(IMGS), 'obrázků')
