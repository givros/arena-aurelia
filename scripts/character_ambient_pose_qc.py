"""CPU-only visual check of the baked full-detail ambient poses."""
from pathlib import Path
import bpy,math
from mathutils import Vector
R=Path(__file__).resolve().parents[1];bpy.ops.wm.read_factory_settings(use_empty=True)
for index in range(4):
    before=set(bpy.data.objects);bpy.ops.import_scene.gltf(filepath=str(R/'characters/runtime'/f'citizen-idle-{index}.glb'))
    for obj in set(bpy.data.objects)-before:
        if obj.parent is None:obj.location.x+=(index-1.5)*1.4
mat=bpy.data.materials.new('Backdrop');mat.diffuse_color=(.16,.13,.105,1)
bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.025));bpy.context.object.data.materials.append(mat)
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=12;scene.cycles.use_denoising=True
scene.world=bpy.data.worlds.new('Ambient QC world');scene.world.use_nodes=True
scene.world.node_tree.nodes.get('Background').inputs['Color'].default_value=(.3,.3,.3,1)
bpy.ops.object.light_add(type='AREA',location=(0,-3,5));bpy.context.object.data.energy=900;bpy.context.object.data.shape='DISK';bpy.context.object.data.size=6
bpy.ops.object.camera_add(location=(.2,-8,3.0));camera=bpy.context.object;camera.rotation_euler=(Vector((0,0,.8))-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.type='ORTHO';camera.data.ortho_scale=6.1;scene.camera=camera
scene.render.resolution_x=1280;scene.render.resolution_y=540;scene.render.resolution_percentage=100
scene.render.filepath=str(R/'characters/ambient_pose_qc.png');bpy.ops.render.render(write_still=True)
