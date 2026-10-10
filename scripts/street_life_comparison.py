"""Side-by-side unretouched evidence for the market-density revision."""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import sys
R=Path(__file__).resolve().parents[1]
tag=sys.argv[1] if len(sys.argv)>1 else 'final'
after=R/f'renders/street_life_{tag}_reference.png'
before=R/'renders/pass3_reference.png'
reference=R/'references/primary_reference.png'
font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',24)
title=ImageFont.truetype('C:/Windows/Fonts/georgia.ttf',32)
def fit(path,size):
    im=Image.open(path).convert('RGB');im.thumbnail(size,Image.Resampling.LANCZOS)
    return im
canvas=Image.new('RGB',(2400,1880),'#221e1a');d=ImageDraw.Draw(canvas)
d.text((36,24),'AURELIA / STREET LIFE',font=title,fill='#eadac4')
for n,path,label in [(0,reference,'Provided reference'),(1,before,'Previous district')]:
    x=24+n*1200;d.text((x,83),label,font=font,fill='#d9bd99')
    im=fit(path,(1152,864));canvas.paste(im,(x,126))
d.text((24,1020),'Revised district — same elevated camera as previous build',font=font,fill='#d9bd99')
im=fit(after,(2352,790));canvas.paste(im,((2400-im.width)//2,1072))
canvas.save(R/f'comparisons/street_life_{tag}_reference_comparison.jpg',quality=95)
print('STREET_LIFE_COMPARISON_READY',tag)
