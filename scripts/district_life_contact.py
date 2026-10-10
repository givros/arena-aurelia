"""Unretouched regional evidence sheets for the citywide life revision."""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import json,sys
R=Path(__file__).resolve().parents[1]
tag=sys.argv[1] if len(sys.argv)>1 else 'final'
d=json.loads((R/'district_life_layout.json').read_text())
font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',24)
title=ImageFont.truetype('C:/Windows/Fonts/georgia.ttf',34)
views=[(k,d['regions'][k.removeprefix('street_district_')]['label']) for k in d['cameras'] if k.startswith('street_district_')]
if (R/'civic_court_layout.json').exists():views.append(('street_district_civic_court','Fountain garden and shaded porticoes'))
views.extend([('street_district_gallery','Arena lower galleries'),('street_district_backstage','Gladiator service passages')])
cols=3;rows=(len(views)+2)//3
canvas=Image.new('RGB',(2400,125+rows*635),'#231e1a');draw=ImageDraw.Draw(canvas)
draw.text((30,28),'AURELIA / LIFE ACROSS THE DISTRICT',font=title,fill='#edddc5')
for i,(name,label) in enumerate(views):
    path=R/f'renders/district_life_{tag}_{name}.png'
    if not path.exists():raise FileNotFoundError(path)
    im=Image.open(path).convert('RGB');im.thumbnail((774,578),Image.Resampling.LANCZOS)
    x=15+(i%cols)*800;y=112+(i//cols)*635
    draw.text((x,y),label,font=font,fill='#daba90');canvas.paste(im,(x,y+39))
canvas.save(R/f'comparisons/district_life_{tag}_regional_sheet.jpg',quality=95)
canvas=Image.new('RGB',(2400,1010),'#231e1a');draw=ImageDraw.Draw(canvas)
draw.text((30,22),'AURELIA / WHOLE DISTRICT COMPARISON',font=title,fill='#edddc5')
for i,(stage,label) in enumerate([('baseline','Before citywide extension'),(tag,'Revised citywide environment')]):
    im=Image.open(R/f'renders/district_life_{stage}_world.png').convert('RGB');im.thumbnail((1160,868),Image.Resampling.LANCZOS)
    x=20+i*1200;draw.text((x,83),label,font=font,fill='#daba90');canvas.paste(im,(x,128))
canvas.save(R/f'comparisons/district_life_{tag}_world_comparison.jpg',quality=95)
canvas=Image.new('RGB',(2400,1040),'#231e1a');draw=ImageDraw.Draw(canvas)
draw.text((30,22),'AURELIA / THE SOUTHERN WARD',font=title,fill='#edddc5')
for i,(path,label) in enumerate([(R/'references/empty_outer_ward_feedback.png','User feedback: the empty outer ward'),(R/f'renders/district_life_{tag}_district_feedback_southern_ward.png','Same side of the completed city')]):
    im=Image.open(path).convert('RGB');im.thumbnail((1160,868),Image.Resampling.LANCZOS)
    x=20+i*1200;draw.text((x,83),label,font=font,fill='#daba90');canvas.paste(im,(x,128))
canvas.save(R/f'comparisons/district_life_{tag}_southern_ward_comparison.jpg',quality=95)
print('DISTRICT_EVIDENCE_SHEETS_READY',tag)
