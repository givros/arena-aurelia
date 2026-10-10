"""Rebuild only city-owned collections in the agreed stage-nine checkpoint."""
import bpy,sys,json
from pathlib import Path
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'scripts'))
from city import build_city
checkpoint=root/'checkpoints'/'current.blend'
bpy.ops.wm.open_mainfile(filepath=str(checkpoint))
for name in ['City_Architecture','City_Infrastructure','City_Landscape']:
    collection=bpy.data.collections.get(name)
    if collection:
        for obj in list(collection.objects):bpy.data.objects.remove(obj,do_unlink=True)
        bpy.data.collections.remove(collection)
spec=json.loads((root/'scene_spec.json').read_text())
meta=build_city(None,spec)
(root/'city_registry.json').write_text(json.dumps(meta,indent=2))
spec['city']={k:v for k,v in meta.items() if k!='parcels'}
(root/'scene_spec.json').write_text(json.dumps(spec,indent=2))
scene=bpy.context.scene
scene.camera=bpy.data.objects.get('CAM_reference')
scene.render.filepath=str(root/'renders'/'checkpoint_09_refined.png')
bpy.ops.wm.save_as_mainfile(filepath=str(checkpoint))
bpy.ops.wm.save_as_mainfile(filepath=str(root/'checkpoints'/'09_city_refined.blend'))
bpy.ops.render.render(write_still=True)
print('CITY_REFINED',meta['building_count'],meta['tree_count'])
