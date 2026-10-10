from PIL import Image,ImageDraw,ImageFont
from pathlib import Path
import sys
R=Path(__file__).resolve().parents[1];p=sys.argv[1] if len(sys.argv)>1 else '1'
names=['reference','top','approach','facade','seating','floor','vip','hypogeum','market']
try:f=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',20)
except:f=ImageFont.load_default()
sheet=Image.new('RGB',(1536,1236),'#191714');d=ImageDraw.Draw(sheet)
for i,n in enumerate(names):
    path=R/'renders'/f'pass{p}_{n}.png'
    if not path.exists():continue
    im=Image.open(path).convert('RGB');im.thumbnail((512,380));x=(i%3)*512;y=(i//3)*412;sheet.paste(im,(x+(512-im.width)//2,y+32));d.text((x+12,y+7),n.replace('_',' ').title(),font=f,fill='#e6d4b1')
sheet.save(R/'comparisons'/f'pass{p}_nine_views.jpg',quality=95)
ref=Image.open(R/'references/primary_reference.png').convert('RGB').resize((728,544))
our=Image.open(R/'renders'/f'pass{p}_reference.png').convert('RGB').resize((728,544))
comp=Image.new('RGB',(1456,588),'#191714');comp.paste(ref,(0,44));comp.paste(our,(728,44));d=ImageDraw.Draw(comp);d.text((16,10),'Primary reference — supplied image',font=f,fill='#e6d4b1');d.text((744,10),f'Constructed environment — pass {p}',font=f,fill='#e6d4b1')
comp.save(R/'comparisons'/f'pass{p}_reference_comparison.jpg',quality=96)
for label,im in [('reference',ref),('model',our)]:
    grid=im.copy();g=ImageDraw.Draw(grid)
    for x in [728//3,2*728//3]:g.line((x,0,x,544),fill='#ffcb66',width=2)
    for y in [544//3,2*544//3]:g.line((0,y,728,y),fill='#ffcb66',width=2)
    grid.save(R/'comparisons'/f'pass{p}_{label}_grid.png')
print('Saved nine views and matching reference grid comparison',p)
