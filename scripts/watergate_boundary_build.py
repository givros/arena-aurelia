"""Add four supported quay gates; preserve all existing scene and character content.

CPU-only source integration. No rendering or layout-authority edits.
"""
from pathlib import Path
from array import array
import bpy, json, hashlib, shutil, struct
from mathutils import Vector
from mathutils.bvhtree import BVHTree

R = Path(__file__).resolve().parents[1]
SOURCE = R / 'Aurelia_Arena.blend'
EXPECTED = '633ad8544a1be92ecb72a904fc7cd75c21cac051d9705f80bca86cd64a49d2b8'
REVISION = 'watergate-bank-gates-1'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

before_hash = sha(SOURCE)
assert before_hash == EXPECTED, 'Unexpected source revision; do not overwrite it.'
backup = R / 'checkpoints/16_before_watergate_bank_gates.blend'
if backup.exists():
    assert sha(backup) == before_hash
else:
    shutil.copy2(SOURCE, backup)

protected_files = ['master_world_layout.json', 'master_world_boundary.json',
                   'street_life_layout.json', 'district_life_layout.json',
                   'civic_court_layout.json', 'arena_interior_life_layout.json',
                   'master_spine_life_layout.json', 'district_review_views.json',
                   'characters/runtime/crowd_manifest.json']
file_hashes = {name: sha(R / name) for name in protected_files}
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
bpy.context.scene.frame_set(1)
assert not bpy.data.collections.get('Watergate_Bank_Gates'), 'Already integrated.'

mesh_cache = {}
def mesh_digest(mesh):
    key = mesh.as_pointer()
    if key not in mesh_cache:
        h = hashlib.sha256()
        for values, prop, size, kind in [(mesh.vertices, 'co', 3, 'f'),
                                         (mesh.loops, 'vertex_index', 1, 'I'),
                                         (mesh.polygons, 'loop_start', 1, 'I'),
                                         (mesh.polygons, 'loop_total', 1, 'I'),
                                         (mesh.polygons, 'material_index', 1, 'I')]:
            data = array(kind, [0]) * (len(values) * size)
            values.foreach_get(prop, data)
            h.update(data.tobytes())
        for uv in mesh.uv_layers:
            data = array('f', [0]) * (len(uv.data) * 2)
            uv.data.foreach_get('uv', data)
            h.update(uv.name.encode()); h.update(data.tobytes())
        h.update('|'.join(m.name if m else '' for m in mesh.materials).encode())
        mesh_cache[key] = h.digest()
    return mesh_cache[key]

def signature(obj):
    h = hashlib.sha256((obj.name + '|' + obj.type).encode())
    h.update(struct.pack('<16d', *[v for row in obj.matrix_world for v in row]))
    h.update(json.dumps({key: str(obj[key]) for key in sorted(obj.keys())}, sort_keys=True).encode())
    h.update(str((obj.hide_render, obj.hide_viewport, obj.instance_type,
                  obj.instance_collection.name if obj.instance_collection else None,
                  tuple(c.name for c in obj.users_collection))).encode())
    if obj.type == 'MESH': h.update(mesh_digest(obj.data))
    if obj.type == 'CAMERA':
        h.update(str((obj.data.lens, obj.data.sensor_width, obj.data.sensor_height,
                      obj.data.clip_start, obj.data.clip_end, obj.data.shift_x, obj.data.shift_y)).encode())
    if obj.animation_data:
        h.update(str(obj.animation_data.action.name if obj.animation_data.action else None).encode())
    return h.hexdigest()

before = {o.name: signature(o) for o in bpy.data.objects}
before_scene_names = {o.name for o in bpy.context.scene.objects}
before_cameras = {o.name: before[o.name] for o in bpy.data.objects if o.type == 'CAMERA'}
before_population = {o.name: before[o.name] for o in bpy.data.objects if o.instance_type == 'COLLECTION' or o.type == 'ARMATURE'}
before_materials = set(bpy.data.materials.keys())
def material_signature(material):
    fields = [material.name, tuple(material.diffuse_color), material.use_nodes]
    if material.node_tree:
        for node in material.node_tree.nodes:
            fields.append((node.name, node.bl_idname,
                           getattr(getattr(node, 'image', None), 'name', None),
                           [(socket.name, str(socket.default_value)) for socket in node.inputs if hasattr(socket, 'default_value')]))
        fields.append([(link.from_node.name, link.from_socket.name, link.to_node.name, link.to_socket.name)
                       for link in material.node_tree.links])
    return hashlib.sha256(repr(fields).encode()).hexdigest()
material_hashes = {material.name: material_signature(material) for material in bpy.data.materials}

quay = bpy.data.objects['River_quay_walls/stone']
vertices = [quay.matrix_world @ v.co for v in quay.data.vertices]
floor = BVHTree.FromPolygons(vertices, [list(p.vertices) for p in quay.data.polygons])
gates = []
for end, y, start_y, beyond_y in [('North', 421.95, 417.0, 432.0),
                                    ('South', -225.55, -220.0, -233.0)]:
    for bank, x, extent in [('West', -199.0, [-201.2, -197.4]),
                             ('East', -159.0, [-160.6, -156.8])]:
        name = f'QuayGate_{end}_{bank}'
        supports = []
        for post_x in [x - 1.0, x + 1.0]:
            hit, normal, index, distance = floor.ray_cast(Vector((post_x, y, 2)), Vector((0, 0, -1)), 4)
            assert hit is not None and abs(hit.z - .2) < .0001 and normal.z > .99, (name, post_x, hit, normal)
            # Each full 0.22m frame foot remains inside the continuous 2.5m quay cap.
            assert x - 1.25 <= post_x - .11 and post_x + .11 <= x + 1.25
            supports.append({'position': list(hit), 'normal': list(normal), 'sourceObject': quay.name})
        test_x = -198.5 if bank == 'West' else -159.0
        gates.append({'id': name, 'center': [x, y, .2], 'xExtent': extent,
                      'height': 2.75, 'depth': .18, 'lowerSolidLeafHeight': 1.65,
                      'supports': supports, 'physicalState': 'closed',
                      'testPath': {'id': name, 'start': [test_x, start_y, 1.92],
                                   'towards': [test_x, beyond_y, 1.92],
                                   'expectedBarrierContains': 'WATERGATE_BANK/' + name}})

authority = {'revision': REVISION, 'coordinateSystem': 'blender_xyz_z_up',
             'beforeSourceSHA256': before_hash, 'protectedAuthorityHashes': file_hashes,
             'purpose': 'Close supported quay-cap bypasses at the two open river arches.',
             'gates': gates,
             'nominalWaterCorridorX': [-197, -160],
             'bankGateFreeWaterBandX': [-197, -160.6],
             'waterwayScope': 'The existing water surfaces, arched masonry and central pier remain unchanged. The east bank barrier projects 0.6m into the nominal channel; the main river arches stay broadly open. The water band also contains the pre-existing central pier, so it is not one uninterrupted boating opening.',
             'structuralLogic': 'Frame feet rest on the existing quay cap. Short fixed iron wings tie the closed leaf to the masonry side and cover the cap edge. The lower iron-clad leaf blocks walking and jumping; the upper grille remains visibly open.',
             'scope': 'Four local pedestrian barriers only. Existing water arches and surfaces, city gates, terrain, people, camera poses and frozen layouts remain unchanged.'}
(R / 'watergate_boundary_revision.json').write_text(json.dumps(authority, indent=2) + '\n')

collection = bpy.data.collections.new('Watergate_Bank_Gates')
bpy.context.scene.collection.children.link(collection)
material = bpy.data.materials.get('iron') or bpy.data.materials.get('City/iron')
assert material is not None, 'Use the existing iron palette without modifying materials.'
unit = bpy.data.meshes.new('Watergate_bank_gate_shared_unit_box')
unit.from_pydata([(-.5,-.5,-.5),(.5,-.5,-.5),(.5,.5,-.5),(-.5,.5,-.5),
                  (-.5,-.5,.5),(.5,-.5,.5),(.5,.5,.5),(-.5,.5,.5)], [],
                 [(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)])
unit.materials.append(material); unit.update()

def box(name, position, size, assembly):
    obj = bpy.data.objects.new(name, unit); collection.objects.link(obj)
    obj.location = position; obj.scale = size
    obj['semantic'] = 'world_boundary/quay_pedestrian_gate'
    obj['collision'] = 'solid'; obj['assembly_id'] = assembly
    obj['boundary_revision'] = REVISION
    return obj

for gate in gates:
    x, y, base = gate['center']; left, right = gate['xExtent']; prefix = 'WATERGATE_BANK/' + gate['id']
    # Both full feet have real source support. Fixed wings close the overlap to the existing jambs.
    for side in [-1, 1]:
        px = x + side
        box(prefix + f'/Frame foot{side}', (px, y, base + .08), (.22, .34, .16), gate['id'])
        box(prefix + f'/Frame post{side}', (px, y, base + 1.375), (.16, .18, 2.75), gate['id'])
    intervals = [(left, x - 1.08, 'Masonry-side fixed leaf'),
                 (x - 1.08, x + 1.08, 'Closed pedestrian leaf'),
                 (x + 1.08, right, 'Quay-edge fixed leaf')]
    for a, b, label in intervals:
        box(prefix + '/' + label, ((a+b)/2, y, base + .825), (b-a+.016, .12, 1.65), gate['id'])
    for i, z in enumerate([base + .13, base + 1.65, base + 2.69]):
        box(prefix + f'/Continuous rail{i}', ((left+right)/2, y, z), (right-left, .20, .12), gate['id'])
    count = max(2, int((right-left)/.19))
    for i in range(count+1):
        px = left + .055 + (right-left-.11)*i/count
        box(prefix + f'/Upper grille bar{i:02}', (px, y, base + 2.15), (.055, .10, 1.10), gate['id'])
    for side in [-1, 1]:
        for z in [base+.38, base+1.30, base+2.38]:
            box(prefix + f'/Hinge{side}_{z:.2f}', (x+side, y-.16, z), (.24, .14, .12), gate['id'])
    box(prefix + '/Closed latch', (x+.42, y-.13, base+1.08), (.38, .13, .11), gate['id'])

bpy.context.view_layer.update(); mesh_cache.clear()
after = {o.name: signature(o) for o in bpy.data.objects}
changed = [name for name, value in before.items() if after.get(name) != value]
assert not changed, 'Existing source changed: ' + repr(changed[:10])
assert before_materials == set(bpy.data.materials.keys())
assert material_hashes == {material.name: material_signature(material) for material in bpy.data.materials}
assert all(sha(R / name) == value for name, value in file_hashes.items())
added = sorted(set(after) - set(before))
assert len(added) > 0 and all(name.startswith('WATERGATE_BANK/') for name in added)
assert all(o.type == 'MESH' and o.get('collision') == 'solid' for o in collection.objects)
bpy.context.scene['watergate_boundary_revision'] = REVISION
bpy.context.scene['watergate_boundary_authority_sha256'] = sha(R / 'watergate_boundary_revision.json')
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_as_mainfile(filepath=str(R / 'checkpoints/current.blend'))
bpy.ops.wm.save_as_mainfile(filepath=str(SOURCE))
report = {'passed': True, 'beforeSourceSHA256': before_hash, 'sourceSHA256': sha(SOURCE),
          'backup': str(backup.relative_to(R)).replace('\\', '/'),
          'authority': 'watergate_boundary_revision.json', 'authoritySHA256': sha(R / 'watergate_boundary_revision.json'),
          'protectedExistingObjects': len(before), 'protectedSceneObjects': len(before_scene_names),
          'changedExistingComponents': changed, 'addedObjects': added,
          'cameraUnchanged': all(after[name] == value for name, value in before_cameras.items()),
          'populationUnchanged': all(after[name] == value for name, value in before_population.items()),
          'protectedPopulationObjects': len(before_population), 'protectedCameras': len(before_cameras),
          'oldMaterialsUnchanged': True, 'frozenLayoutAndCrowdFilesUnchanged': True,
          'newMeshObjects': len(collection.objects), 'newUniqueMeshes': 1,
          'supportChecks': 8, 'collision': 'actual closed iron leaves and frames; no invisible collision planes',
          'runtimeControllerTests': 'pending viewer export and four bank-gate paths'}
(R / 'comparisons/watergate_boundary_integration.json').write_text(json.dumps(report, indent=2) + '\n')
print('WATERGATE_BANK_GATES_SAVED', report['sourceSHA256'], len(added), flush=True)
