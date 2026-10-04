import json, sys, os, hashlib, re, io, urllib.request, concurrent.futures as cf
from PIL import Image, ImageOps
lst = json.load(open(sys.argv[1])); outdir = sys.argv[2]; maxw = int(sys.argv[3]) if len(sys.argv) > 3 else 1400
os.makedirs(outdir, exist_ok=True)
UA = {'User-Agent': 'Mozilla/5.0 (Macintosh) Chrome/127'}
mp = {}
def name(u):
    base = re.sub(r'\.\w+$', '', u.split('/')[-1]).lower()
    base = re.sub(r'[^a-z0-9_-]+', '-', base)[:40].strip('-')
    return f"{base}-{hashlib.md5(u.encode()).hexdigest()[:6]}.webp"
def go(u):
    fn = name(u); p = os.path.join(outdir, fn)
    if os.path.exists(p): 
        im = Image.open(p); return u, fn, im.size
    try:
        from urllib.parse import quote
        data = urllib.request.urlopen(urllib.request.Request(quote(u, safe=':/%?=&'), headers=UA), timeout=60).read()
        im = Image.open(io.BytesIO(data)); im = ImageOps.exif_transpose(im)
        if im.mode not in ('RGB', 'RGBA'): im = im.convert('RGBA' if 'A' in im.mode or im.mode == 'P' else 'RGB')
        if im.width > maxw: im = im.resize((maxw, round(im.height * maxw / im.width)), Image.LANCZOS)
        im.save(p, 'WEBP', quality=74, method=5)
        return u, fn, im.size
    except Exception as e:
        print('ERR', u, e); return u, None, None
with cf.ThreadPoolExecutor(16) as ex:
    for u, fn, sz in ex.map(go, lst):
        if fn: mp[u] = {'f': fn, 'w': sz[0], 'h': sz[1]}
json.dump(mp, open(sys.argv[1].replace('.json', '_map.json'), 'w'), indent=0)
print(len(mp), 'ok of', len(lst))
