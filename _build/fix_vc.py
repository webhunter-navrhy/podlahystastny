import json, sys, urllib.request
from bs4 import BeautifulSoup
f = sys.argv[1]; d = json.load(open(f))
for x in d:
    c = x['content']['rendered']
    if ('[vc_' in c or '[/vc' in c) and x['parent'] != 0 or (('[vc_' in c) and x['link'].rstrip('/').count('/') > 2):
        h = urllib.request.urlopen(urllib.request.Request(x['link'], headers={'User-Agent': 'Mozilla/5.0 (Macintosh) Chrome/127'}), timeout=60).read().decode()
        s = BeautifulSoup(h, 'html.parser'); pc = s.select_one('.post_content') or s.select_one('.entry-content')
        if pc:
            x['content']['rendered'] = str(pc); print('nahrazeno', x['link'], len(str(pc)))
json.dump(d, open(f, 'w'), ensure_ascii=False, indent=1)
