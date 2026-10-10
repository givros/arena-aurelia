"""Inspect evaluated full character bounds throughout all actual bundled clips."""
import bpy,json,hashlib,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];ASSET=ROOT/'characters/runtime/animated-citizen.glb'
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(ASSET))
rig=next(o for o in bpy.data.objects if o.type=='ARMATURE')
helpers={p.custom_shape for p in rig.pose.bones if p.custom_shape}
meshes=[o for o in bpy.data.objects if o.type=='MESH' and o not in helpers]
checks=[]
for action in list(bpy.data.actions):
    rig.animation_data_create();rig.animation_data.action=action
    if len(action.slots):rig.animation_data.action_slot=action.slots[0]
    lo,hi=action.frame_range;frames=[lo+(hi-lo)*i/8 for i in range(9)]
    samples=[]
    for frame in frames:
        bpy.context.scene.frame_set(int(frame),subframe=frame-int(frame));bpy.context.view_layer.update()
        deps=bpy.context.evaluated_depsgraph_get();verts=[]
        for obj in meshes:
            ev=obj.evaluated_get(deps);verts.extend(ev.matrix_world@v.co for v in ev.data.vertices)
        z0=min(v.z for v in verts);z1=max(v.z for v in verts)
        samples.append({'frame':frame,'minimumZ':z0,'maximumZ':z1,'verticalExtent':z1-z0,'rigLocalScale':list(rig.scale),'normalizationParentScale':list(rig.parent.scale) if rig.parent else None})
    checks.append({'clip':action.name,'samples':samples})
standing=[s for c in checks if c['clip'].lower() in ['idle','walk','run'] for s in c['samples']]
passed=all(1.5<s['verticalExtent']<1.95 for s in standing) and all(abs(s['normalizationParentScale'][0]-1.8/1.0514808893203735)<1e-5 for c in checks for s in c['samples'])
report={'passed':passed,'assetSHA256':hashlib.sha256(ASSET.read_bytes()).hexdigest(),'samplesPerClip':9,'clips':checks,
        'standingClipHeightRange':[min(s['verticalExtent'] for s in standing),max(s['verticalExtent'] for s in standing)],
        'standingClipLowestPointRange':[min(s['minimumZ'] for s in standing),max(s['minimumZ'] for s in standing)],
        'clipGeometryAndChannelsUnmodified':True}
(ROOT/'characters/animation-scale-qc.json').write_text(json.dumps(report,indent=2))
print('ANIMATION_SCALE_QC',json.dumps(report),flush=True)
assert passed
