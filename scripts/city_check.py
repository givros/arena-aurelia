import bpy, sys, json, math
from mathutils import Vector
from pathlib import Path
root=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(root/'scripts'))
from city import build_city
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
result=build_city()
out=root/'comparisons'/'city'
out.mkdir(parents=True,exist_ok=True)
(out/'city_geometry.json').write_text(json.dumps(result,indent=2))
scene=bpy.context.scene
scene.render.engine='CYCLES'
scene.cycles.samples=20
scene.cycles.use_denoising=True
scene.world.color=(.60,.68,.80)
scene.world.use_nodes=True
scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.61,.70,.83,1)
scene.world.node_tree.nodes['Background'].inputs[1].default_value=.65
ld=bpy.data.lights.new('CityReviewSun','SUN')
lo=bpy.data.objects.new('CityReviewSun',ld)
scene.collection.objects.link(lo)
ld.energy=3
ld.angle=.12
lo.rotation_euler=(math.radians(28),math.radians(-24),math.radians(-32))
camera=bpy.data.cameras.new('CityReviewCamera')
co=bpy.data.objects.new('CityReviewCamera',camera)
scene.collection.objects.link(co)
scene.camera=co
co.location=(100,-255,205)
co.rotation_euler=(Vector((0,40,3))-co.location).to_track_quat('-Z','Y').to_euler()
camera.lens=32
camera.clip_end=2500
scene.view_settings.view_transform='AgX'
scene.render.resolution_x=1400
scene.render.resolution_y=1050
scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'
scene.render.filepath=str(out/'city_aerial.png')
bpy.ops.wm.save_as_mainfile(filepath=str(out/'city_check.blend'))
bpy.ops.render.render(write_still=True)
co.location=(61,85,42)
co.rotation_euler=(Vector((10,138,14))-co.location).to_track_quat('-Z','Y').to_euler()
camera.lens=35
scene.render.filepath=str(out/'city_temple.png')
bpy.ops.render.render(write_still=True)
print('CITY_VALIDATION',len([o for o in scene.objects if o.type=='MESH']),len(result['parcels']))
