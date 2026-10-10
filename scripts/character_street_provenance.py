"""Rebind metadata after the verified navigation-only facade route correction."""
from pathlib import Path
import json, hashlib
R=Path(__file__).resolve().parents[1]; C=R/'characters'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def digest(v): return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':')).encode()).hexdigest()
BASELINE={"layout":"12e0f77c4fa734265dece8cc25f58da54b344c6bd1b9da8e1d9bef818f9022dd","layoutImmutable":{"stalls":"57ea99b61cb9fca7131d4462c538137068dcb62702d48d8b4a70bc5b373bbe1e","shops":"881e377619347d5870063799bac43d97b6b26e8f97ce0d30a804b758f0aef39a","vendors":"3c344d11fa0685b35afa4151cbb0e9f3c4fc07d751e7ca8ea107bb5f6caaaadc","anchors":"8f2c0ebaeed321f2d58857ca195a8168f539e2e4767c2aefc1456ce568cec9e5","routes":"6fdbeb0001ea7a7e7ea1f331c2497ec690dbab4b2dc8136a62fe7dfb3bd9afcf","footprint_obstacles":"9364c8f84ab4682c4d9c77855c659ef2afaff85f3f5ef4d317310395c3297829"},"manifest":"8aa81a3dd81a84316283087b1028ef23df64f47ff32444ee9ceb473b759e9046","manifestImmutable":"5c5734a35398160400bf53afd53720f113f5360194efb5dd7268ed20f28ea131","source":"a286224ac99a1624e246fb71769cebb963f9210a2231eec10622a61d8da52c6b"}
layout_path=R/'street_life_layout.json'; layout=json.loads(layout_path.read_text())
for key,value in BASELINE['layoutImmutable'].items():
    assert digest(layout[key])==value, f'Non-navigation layout changed: {key}'
target=C/'runtime/crowd_manifest.json'; crowd=json.loads(target.read_text())
def immutable(): return digest({k:crowd[k] for k in ['instances','npcs','assetHashes','prototypes','palette','materialOverrides','sourcePopulation']})
assert immutable()==BASELINE['manifestImmutable'], 'Population payload changed'
assert sha(R/'Aurelia_Arena.blend')==BASELINE['source'], 'Source changed during provenance-only revision'
new_layout=sha(layout_path)
crowd['streetLife'].setdefault('generationLayoutSHA256',crowd['streetLife']['layoutSHA256'])
crowd['streetLife']['layoutSHA256']=new_layout
crowd['streetLife']['layoutRevisionScope']='FacadeAmbulatory navigation metadata only; placement and motion paths unchanged'
target.write_text(json.dumps(crowd,separators=(',',':')),encoding='utf8'); new_manifest=sha(target)
updated=[]
def rebind(value):
    if isinstance(value,dict):
        if 'layoutSHA256' in value:
            value.setdefault('generationLayoutSHA256',value['layoutSHA256']);value['layoutSHA256']=new_layout
        if 'crowdManifestSHA256' in value:
            value.setdefault('generationCrowdManifestSHA256',value['crowdManifestSHA256']);value['crowdManifestSHA256']=new_manifest
        for child in list(value.values()): rebind(child)
    elif isinstance(value,list):
        for child in value: rebind(child)
for name in ['street_life_population_validation.json','street_entry_crowd_validation.json','street_empty_variant_repair.json','street_life_plan.json','population-source-qc.json','standing-ground-qc.json','street_activity_qc.json']:
    path=C/name; data=json.loads(path.read_text());rebind(data)
    data['currentLayoutSHA256']=new_layout;data['crowdManifestSHA256']=new_manifest
    data['provenanceRefresh']={'scope':'Navigation metadata only; measured transforms, geometry and motion unchanged','measuredManifestSHA256':BASELINE['manifest'],'sourceSHA256':BASELINE['source']}
    path.write_text(json.dumps(data,indent=2));updated.append(name)
assert immutable()==BASELINE['manifestImmutable']
report={'passed':True,'sourceUnchanged':sha(R/'Aurelia_Arena.blend')==BASELINE['source'],'sourceSHA256':BASELINE['source'],'beforeLayoutSHA256':BASELINE['layout'],'currentLayoutSHA256':new_layout,'beforeManifestSHA256':BASELINE['manifest'],'currentManifestSHA256':new_manifest,'geometryAndAllPlacementsAndMotionUnchanged':True,'updatedReports':updated}
(C/'street_provenance_refresh.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report))
