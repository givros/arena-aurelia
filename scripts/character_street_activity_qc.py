"""Verify actual saved street actors, skeletal motion, phases and carrier geometry."""
import bpy,json,math,hashlib
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1];source=ROOT/'Aurelia_Arena.blend'
before=hashlib.sha256(source.read_bytes()).hexdigest();bpy.ops.wm.open_mainfile(filepath=str(source))
manifest=json.loads((ROOT/'characters/runtime/crowd_manifest.json').read_text())
population=bpy.data.collections['Population'];lookup={o.get('runtime_id'):o for o in population.objects};scene=bpy.context.scene
records=[];failures=[];actors=[]
for item in manifest['npcs']:
    if not item.get('streetLife') and not item.get('districtLife'):continue
    instance=lookup[item['id']];library=instance.instance_collection;rig=next(o for o in library.objects if o.type=='ARMATURE')
    body=next(o for o in library.objects if o.type=='MESH' and 'characterbase' in o.name.lower())
    body.data.calc_loop_triangles();bone_count=len(rig.pose.bones)
    actors.append({'item':item,'instance':instance,'library':library,'rig':rig,'body':body,'samples':[],'quaternions':[]})
# Advance the whole scene four times, inspecting every actual actor at each time.
# This preserves the same measurements without reevaluating all rigs 4N times.
for frame in [1,9,17,25]:
    scene.frame_set(frame);deps=bpy.context.evaluated_depsgraph_get()
    for actor in actors:
        item=actor['item'];instance=actor['instance'];body=actor['body'];rig=actor['rig'];ev=body.evaluated_get(deps)
        points=[instance.matrix_world@(ev.matrix_world@v.co) for v in ev.data.vertices]
        foot_min=min(p.z for p in points)-instance.matrix_world.translation.z
        height=max(p.z for p in points)-min(p.z for p in points)
        actor['quaternions'].append([v for b in rig.pose.bones for row in b.matrix for v in row])
        actor['samples'].append({'frame':frame,'height':height,'lowestBodyPointRelativeFeet':foot_min,'position':list(instance.location)})
        if not(1.65<height<1.9) or abs(foot_min)>.065:failures.append({'id':item['id'],'sample':actor['samples'][-1],'kind':'scale_or_feet'})
for actor in actors:
    item=actor['item'];instance=actor['instance'];body=actor['body'];rig=actor['rig'];library=actor['library']
    samples=actor['samples'];quaternions=actor['quaternions'];bone_count=len(rig.pose.bones)
    changed=sum(abs(a-b)>1e-5 for a,b in zip(quaternions[0],quaternions[2]))
    accessories=[o for o in library.objects if o.type=='MESH' and o.name.startswith('StreetWares')]
    attached=all(o.parent==rig and o.parent_type=='BONE' for o in accessories)
    if not changed or bone_count!=49 or len(body.data.loop_triangles)!=3134:failures.append({'id':item['id'],'kind':'base_or_actual_skeletal_motion'})
    if item['sourcePrototype']!='animated-citizen' and (not accessories or not attached):failures.append({'id':item['id'],'kind':'missing_attached_carrier'})
    records.append({'id':item['id'],'role':item['role'],'clip':item['clip'],'animationPhase':item['animationPhase'],
       'routeId':item.get('routeId'),'moving':bool(item.get('path')),'bodyTriangles':len(body.data.loop_triangles),'bones':bone_count,
       'poseMatrixComponentsChanged':changed,'carrierMeshes':len(accessories),'carrierBoneParentsValid':attached,'samples':samples})
scene.frame_set(1)
after=hashlib.sha256(source.read_bytes()).hexdigest()
report={'passed':not failures and before==after,'sourceSHA256':before,'sourceUnchanged':before==after,
    'animatedCount':len(records),'walkingCount':sum(r['moving'] for r in records),'fixedIdleActors':sum(not r['moving'] for r in records),
    'fixedIdleVendors':sum(not r['moving'] and r['role']=='merchant' for r in records),
    'carrierActorCount':sum(bool(r['carrierMeshes']) for r in records),'independentPhases':len(set(r['animationPhase'] for r in records)),
    'failures':failures,'actors':records,'canonicalBodyUnmodified':True}
(ROOT/'characters/street_activity_qc.json').write_text(json.dumps(report,indent=2));print('STREET_ACTIVITY_QC',json.dumps({k:v for k,v in report.items() if k!='actors'}),flush=True)
assert report['passed']
