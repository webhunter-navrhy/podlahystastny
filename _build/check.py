import sys, asyncio
from playwright.async_api import async_playwright
base=sys.argv[1]; paths=sys.argv[2].split(','); out=sys.argv[3]; widths=[int(w) for w in (sys.argv[4] if len(sys.argv)>4 else '1440,390').split(',')]
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch()
        for w in widths:
            pg=await b.new_page(viewport={'width':w,'height':900 if w>500 else 844}, device_scale_factor=1)
            errs=[]; pg.on('pageerror',lambda e: errs.append(str(e)))
            for path in paths:
                await pg.goto(base+path, wait_until='networkidle')
                # scroll slowly to trigger reveals
                h=await pg.evaluate('document.body.scrollHeight')
                y=0
                while y<h:
                    y+=600; await pg.evaluate(f'window.scrollTo(0,{y})'); await pg.wait_for_timeout(120)
                    h=await pg.evaluate('document.body.scrollHeight')
                await pg.evaluate('window.scrollTo(0,0)'); await pg.wait_for_timeout(1600)
                ov=await pg.evaluate('''()=>{const W=document.documentElement.clientWidth;const bad=[];document.querySelectorAll('body *').forEach(e=>{const r=e.getBoundingClientRect();if(r.width&&r.right>W+1&&getComputedStyle(e).position!=='fixed'&&!e.closest('.marquee,.cat-preview,.announce__in')){bad.push(e.tagName+'.'+e.className.toString().slice(0,40)+' '+Math.round(r.right))}});return [document.documentElement.scrollWidth,W,bad.slice(0,8)]}''')
                print(w,path,'scrollW',ov[0],'W',ov[1],'overflow:',ov[2], 'errors:',errs[:3])
                name=out+'_'+(path.strip('/').replace('/','_') or 'home')+f'_{w}.jpg'
                await pg.screenshot(path=name,full_page=True,type='jpeg',quality=55)
            await pg.close()
        await b.close()
asyncio.run(main())
