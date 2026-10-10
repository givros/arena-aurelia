import bpy,math,json
from pathlib import Path
from mathutils import Vector
ROOT=Path('E:/Dev/underwater-colony/artifacts/roman-arena/characters')
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
scene=bpy.context.scene
roles=['citizen','merchant','worker','noble','seated-spectator','guard','gladiator']
for i,role in enumerate(roles):
    before=set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(ROOT/'runtime'/(role+'.glb')))
    imported=set(bpy.data.objects)-before
    for o in imported:
        if o.parent is None:o.location.x+=(i-3)*1.1
    curve=bpy.data.curves.new(role+'Label','FONT');curve.body=role.upper();curve.align_x='CENTER';curve.size=.12;curve.extrude=0
    text=bpy.data.objects.new(role+'Label',curve);scene.collection.objects.link(text)
    text.location=((i-3)*1.1,-.72,0.02);text.rotation_euler=(math.radians(64),0,0)
    mat=bpy.data.materials.get('Labels') or bpy.data.materials.new('Labels');mat.diffuse_color=(.08,.065,.05,1);curve.materials.append(mat)
bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.02));floor=bpy.context.object
mat=bpy.data.materials.new('WarmFloor');mat.diffuse_color=(.35,.31,.24,1);floor.data.materials.append(mat)
world=scene.world or bpy.data.worlds.new('World');scene.world=world;world.color=(.3,.3,.3)
scene.render.engine='BLENDER_WORKBENCH'
scene.display.shading.light='STUDIO';scene.display.shading.color_type='MATERIAL';scene.display.shading.show_shadows=True
scene.display.shading.show_cavity=True;scene.display.shading.cavity_type='BOTH';scene.display.shading.curvature_ridge_factor=1.1;scene.display.shading.curvature_valley_factor=1.0
scene.display.shading.background_type='WORLD';scene.display.shading.studiolight_rotate_z=.55
camera=bpy.data.cameras.new('QCCamera');o=bpy.data.objects.new('QCCamera',camera);scene.collection.objects.link(o);scene.camera=o
o.location=(3,-11,5.2);target=Vector((0,0,.83));o.rotation_euler=(target-o.location).to_track_quat('-Z','Y').to_euler();camera.type='ORTHO';camera.ortho_scale=8.6
scene.render.resolution_x=1720;scene.render.resolution_y=720;scene.render.resolution_percentage=100
scene.render.filepath=str(ROOT/'roman-roles-qc.png');bpy.ops.render.render(write_still=True)
for o in list(bpy.data.objects):
    if o.type=='MESH' and o != floor:
        o.hide_render=True
for role in ['seated-spectator','guard']:
    for o in bpy.data.objects:
        if o.type=='MESH' and o.name.startswith(role+'_'):o.hide_render=False
    if role=='seated-spectator':x=1.1
    else:x=2.2
    target=Vector((x,0,.90));o_cam=scene.camera;o_cam.location=(x+2,-3,2.2);o_cam.rotation_euler=(target-o_cam.location).to_track_quat('-Z','Y').to_euler();camera.ortho_scale=2.8
    scene.render.resolution_x=800;scene.render.resolution_y=800;scene.render.filepath=str(ROOT/(role+'-qc.png'));bpy.ops.render.render(write_still=True)
    for o in bpy.data.objects:
        if o.type=='MESH' and o!=floor:o.hide_render=True
print('ROLE_QC_COMPLETE')
