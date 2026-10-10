import bpy,sys,json,math
from mathutils import Vector
from pathlib import Path
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'scripts'))
from market_dressing import build_market
from city import CityGeometry,_material,_collection
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
result=build_market()
out=root/'comparisons'/'city'
out.mkdir(parents=True,exist_ok=True)
(out/'market_geometry.json').write_text(json.dumps(result,indent=2))
ground=CityGeometry()
ground.box('ground',(0,0,-.08),(330,290,.16))
ground.objects('ReviewGround',_collection('Review'),{'ground':_material('ground',(.52,.47,.39))},'walkable')
scene=bpy.context.scene
scene.render.engine='CYCLES'
scene.cycles.samples=24
scene.cycles.use_denoising=True
scene.world.use_nodes=True
scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.64,.71,.80,1)
scene.world.node_tree.nodes['Background'].inputs[1].default_value=.55
sun=bpy.data.lights.new('ReviewSun','SUN')
obj=bpy.data.objects.new('ReviewSun',sun)
scene.collection.objects.link(obj)
obj.rotation_euler=(math.radians(28),math.radians(-24),math.radians(-32))
sun.energy=3
sun.angle=.1
camera=bpy.data.cameras.new('ReviewCamera')
cam=bpy.data.objects.new('ReviewCamera',camera)
scene.collection.objects.link(cam)
scene.camera=cam
scene.view_settings.view_transform='AgX'
scene.view_settings.look='AgX - Medium High Contrast'
scene.render.resolution_x=1400
scene.render.resolution_y=1050
scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'
for name,pos,target,lens in [('market_detail',[-102,-70,7],[-110,-53,1.8],39),
                             ('market_aerial',[100,-230,160],[0,-22,0],34)]:
    cam.location=pos
    cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler()
    camera.lens=lens
    camera.clip_end=3000
    scene.render.filepath=str(out/(name+'.png'))
    bpy.ops.render.render(write_still=True)
print('MARKET_VALIDATION',len([o for o in scene.objects if o.type=='MESH']),result['stall_count'])
