import json,sys
from PIL import Image, ImageDraw
files=sys.argv[2:]; out=sys.argv[1]
W=6; S=240
rows=(len(files)+W-1)//W
sh=Image.new('RGB',(W*S,rows*(S+16)),'white'); d=ImageDraw.Draw(sh)
for i,f in enumerate(files):
    im=Image.open(f).convert('RGB'); im.thumbnail((S,S))
    x=(i%W)*S; y=(i//W)*(S+16)
    sh.paste(im,(x,y)); d.text((x+2,y+S),f"{i}:{f.split('/')[-1][:30]}",fill='black')
sh.save(out,quality=70)
