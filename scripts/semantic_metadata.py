"""Derived semantic records from the frozen layout authorities; no file writes."""
from copy import deepcopy
import json


def current_semantic_fields(root, spec):
    read = lambda name: json.loads((root / name).read_text(encoding='utf-8'))
    master = read('master_world_layout.json')
    district = read('district_life_layout.json')
    civic = read('civic_court_layout.json')
    boundary = read('master_world_boundary.json')
    # Keep the original broad categories while explicitly declaring their child areas.
    nodes = [deepcopy(node) for node in spec['regions']
             if not node['id'].startswith('REG_DISTRICT_') and node['id'] != 'REG_CIVIC_COURT']
    for node in nodes:
        node['scope'] = 'aggregate spatial region; not an exact collision boundary'
        if node['id'] == 'REG_RIVER':
            node['bounds'] = [-197, min(g['center'][1] for g in boundary['watergates']),
                              -160, max(g['center'][1] for g in boundary['watergates'])]
            node['boundsScope'] = 'water corridor between the two city watergates; quay activity has district child regions'
            node['continuationAuthority'] = 'master_world_boundary.json'
    for key, region in district['regions'].items():
        nodes.append({'id': 'REG_DISTRICT_' + key.upper(), 'name': region['label'],
                      'parent': 'REG_CITY', 'center': region['center'], 'role': region['role'],
                      'source': 'district_life_layout.json', 'sourceRegion': key,
                      'scope': 'activity-area marker; not an exclusive parcel boundary'})
    roof_points = [point for part in civic['parts'] if part['kind'] == 'roof' for point in part['polygon']]
    bounds = [min(p[0] for p in roof_points), min(p[1] for p in roof_points),
              max(p[0] for p in roof_points), max(p[1] for p in roof_points)]
    nodes.append({'id': 'REG_CIVIC_COURT', 'name': 'Fountain garden and peristyle',
                  'parent': 'REG_CITY', 'color': '#64754c',
                  'center': [(bounds[0] + bounds[2]) / 2, (bounds[1] + bounds[3]) / 2],
                  'roofBounds': bounds, 'source': 'civic_court_layout.json',
                  'scope': 'public garden and covered portico; passages are authored separately'})
    foreground = deepcopy(spec.get('foreground', {}))
    placements = {item['id']: item for item in master['housePlacements']}
    for house in foreground.get('houses', []):
        current = placements[house['id']]
        house['originalCenter'] = current['sourceCenter']
        for key in ('center', 'rotation', 'quarter', 'full_dimensions', 'projection_envelope', 'polygon'):
            house[key] = deepcopy(current[key])
        house.pop('full_projection', None)
        house['placementAuthority'] = 'master_world_layout.json'
    foreground['placementNote'] = 'Legacy ForegroundHouse IDs are preserved; their complete assemblies now occupy organic city quarters.'
    foreground['projection_method'] = 'Current rotated reserved envelopes from master_world_layout.json; historical construction checks do not define current placement.'
    return {'regions': nodes, 'foreground': foreground,
            'regionMetadata': {'aggregateRegions': 8, 'districtAreas': len(district['regions']),
                               'civicCourts': 1, 'coordinateSystem': 'blender_xyz_z_up',
                               'scope': 'Nested semantic areas may overlap; use authored route and parcel authorities for traversal.'}}
