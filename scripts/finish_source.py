import bpy,sys,json,math
from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'scripts'));import build_arena as B
bpy.ops.wm.open_mainfile(filepath=str(R/'Aurelia_Arena.blend'));B.mats()
# Continue the ground into low southern hills outside the exploration boundary.
# These close the reverse skyline without filling the protected approach avenue.
B.M['hills']=B.material('Distant ochre hills',(.28,.275,.16),1)
nx,ny=80,36;verts=[]
for j in range(ny+1):
    y=-239-j*421/ny;t=j/ny
    for i in range(nx+1):
        x=-500+i*1060/nx
        z=sum(h*math.exp(-((x-cx)/wx)**2-((y-cy)/wy)**2) for cx,cy,wx,wy,h in [(-340,-400,120,110,46),(-50,-395,150,90,32),(220,-420,130,110,54),(490,-430,160,125,43)])
        z*=min(1,t*9);verts.append((x,y,-.06+z+.7*math.sin(x*.03)*math.sin(t*math.pi)))
faces=[(j*(nx+1)+i,j*(nx+1)+i+1,(j+1)*(nx+1)+i+1,(j+1)*(nx+1)+i) for j in range(ny) for i in range(nx)]
B.mesh('LANDSCAPE/Southern hill continuity',verts,[tuple(reversed(f)) for f in faces],'hills','Landscape','none')
# The animated-role normalization helper is supplied after direct sampled animation QA.
from character_cleanup_helpers import normalize_animated_library
normalization=normalize_animated_library()
(R/'characters/source_animation_normalization.json').write_text(json.dumps(normalization,indent=2))
sp=json.loads((R/'scene_spec.json').read_text());sp['arena']['seatingPopulation']=12000;sp['foreground']=json.loads((R/'foreground_registry.json').read_text());sp['sceneryBeyondBounds']={'southHills':[-500,-660,560,-239],'collision':'none'}
for route in sp['routes']:
    if route['id']=='PATH_SPECTATOR':route['entryAnglesDegrees']=[45,225];route['upperAisles']=16;route['width']=2.6
(R/'scene_spec.json').write_text(json.dumps(sp,indent=2))
bpy.context.scene.frame_set(1);bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(R/'checkpoints/current.blend'));bpy.ops.wm.save_as_mainfile(filepath=str(R/'Aurelia_Arena.blend'))
print('SOURCE_FINISHED',flush=True)
