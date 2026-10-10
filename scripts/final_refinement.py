import bpy,sys,json,math,bmesh
from pathlib import Path
from mathutils import Vector
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'scripts'));import build_arena as B
bpy.ops.wm.open_mainfile(filepath=str(R/'Aurelia_Arena.blend'));B.mats()
population=bpy.data.collections['Population'];population.hide_viewport=True
from foreground_refinement import relocate_foreground
foreground=relocate_foreground(B,B.SPEC)
(R/'foreground_registry.json').write_text(json.dumps(foreground,indent=2))
o=bpy.data.objects['CAM_market'];o.location=(42,-127,1.72);o.rotation_euler=(Vector((62,-117,3.2))-o.location).to_track_quat('-Z','Y').to_euler()
for o in bpy.data.objects:
    if o.type=='LIGHT' and o.name.startswith('Hypogeum lamp'):
        o.data.energy=1500;o.data.shadow_soft_size=.9;o.location.y=6;o.location.z=-3.1
# Solid retaining walls enclose both sides of the service ramp without narrowing it.
for o in list(bpy.data.objects):
    if o.name.startswith('HYPOGEUM/Ramp guard'):bpy.data.objects.remove(o,do_unlink=True)
for side in [-1,1]:B.box(f'HYPOGEUM/Ramp retaining side{side}',(55,side*3.7,-2.88),(18,.6,6.64),'stone',collection='Hypogeum')
# Exterior cornice remains intact but its inward overhang no longer blocks the upper promenade.
o=bpy.data.objects.get('FACADE/Continuous cornice.004')
if o:
    o.data=o.data.copy()
    for v in o.data.vertices:
        q=(v.co.x/102)**2+(v.co.y/79)**2
        if abs(q-1)<.0002:v.co.x*=103.65/102;v.co.y*=80.65/79
# Reserve the actual loggia interior in the seating solids, matching its crowd exclusion.
cutter=B.box('TEMP/Imperial room cut',(0,59.85,27.35),(19.8,16.7,17.3),'stone',collection='Imperial')
trimmed=[]
for o in list(bpy.context.scene.objects):
    if o.type!='MESH' or not o.name.startswith(('CAVEA/','STAIRS/')):continue
    corners=[o.matrix_world@Vector(v) for v in o.bound_box]
    low=[min(v[i] for v in corners) for i in range(3)];high=[max(v[i] for v in corners) for i in range(3)]
    if high[0]<=-9.9 or low[0]>=9.9 or high[1]<=51.5 or low[1]>=68.2 or high[2]<=18.70 or low[2]>=36:continue
    mod=o.modifiers.new('Imperial room clearance','BOOLEAN');mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=cutter
    if o.data.users>1:o.data=o.data.copy()
    bpy.context.view_layer.objects.active=o;bpy.ops.object.modifier_apply(modifier=mod.name);trimmed.append(o.name)
    print('ROOM_CLEARED',len(trimmed),o.name,flush=True)
bpy.data.objects.remove(cutter,do_unlink=True)
for x in [-.55,.55]:
    for y in [61.98,63.02]:B.box('VIP/Throne leg',(x,y,18.98),(.19,.19,.52),'gold',collection='ImperialDecor')
for x in [-.75,.75]:B.box('VIP/Throne arm support',(x,61.88,19.77),(.16,.16,.40),'gold',collection='ImperialDecor')
(R/'comparisons/imperial_room_clearance.json').write_text(json.dumps({'cutBounds':[[-9.9,51.5,18.7],[9.9,68.2,36]],'trimmedComponents':trimmed,'crowdExcludedAlready':True},indent=2))
# Draped valances and fine gold fringe give the imperial canopy its reference hierarchy.
for left,right in [(-10.5,-3.5),(-3.5,3.5),(3.5,10.5)]:
    vs=[];n=36
    for i in range(n+1):
        t=i/n;x=left+(right-left)*t;z=31.35-1.35*math.sin(math.pi*t)
        y=51.55-.18*math.sin(6*math.pi*t)
        vs.extend([(x,y,31.6),(x,y,z)])
    fs=[]
    for i in range(n):fs.extend([(2*i,2*i+2,2*i+3,2*i+1),(2*i+1,2*i+3,2*i+2,2*i)])
    B.mesh('VIP/Swag valance',vs,fs,'red','ImperialDecor','none')
    for i in range(n):
        t=(i+.5)/n;x=left+(right-left)*t;z=31.35-1.35*math.sin(math.pi*t)
        B.beam('VIP/Golden valance tassel',(x,51.32,z),(x,51.32,z-.25),.045,'gold','ImperialDecor')
# Source-only rig-display helpers must not become visible world props.
helper=R/'scripts/character_cleanup_helpers.py'
if helper.exists():
    import character_cleanup_helpers as C
    result=C.cleanup_imported_rig_helpers()
    (R/'characters/display_helper_cleanup.json').write_text(json.dumps(result,indent=2))
    C.ground_verified_instances()
# Recalculate normals for the new masonry solids only.
for name in ['HYPOGEUM/Ramp retaining side-1','HYPOGEUM/Ramp retaining side1']:
    me=bpy.data.objects[name].data;bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free()
population.hide_viewport=False
bpy.context.scene.frame_set(1);bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(R/'checkpoints/current.blend'));bpy.ops.wm.save_as_mainfile(filepath=str(R/'Aurelia_Arena.blend'))
print('FINAL_REFINEMENT_COMPLETE',flush=True)
