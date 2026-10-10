"""Bind manually inspected source/runtime views to the verified final build."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json

R = Path(__file__).resolve().parents[1]
def read(name):
    return json.loads((R / name).read_text(encoding='utf8'))
def sha(name):
    return hashlib.sha256((R / name).read_bytes()).hexdigest()

runtime = read('viewer/runtime_validation.json')
performance = read('viewer/performance_optimization.json')
bridge = read('viewer/watergate_boundary_revision_validation.json')
routes = read('viewer/route_validation.json')
stable_grid = read('viewer/stable_grid_validation.json')
profile = read('viewer/render_profile.json')
source = sha('Aurelia_Arena.blend')
assert runtime['status'] == performance['status'] == bridge['status'] == 'passed'
assert stable_grid['status'] == 'passed'
assert stable_grid['sourceSHA256'] == source
assert stable_grid['finalBuild'] == performance['finalBuild']
assert stable_grid['moduleSHA256'] == sha('viewer/src/stable-clustered-lighting.js')
assert profile['lighting']['fog']['nearMeters'] == 1200
assert profile['lighting']['fog']['farMeters'] == 4500
assert source == runtime['source']['blendSHA256'] == performance['sourceSHA256'] == bridge['finalSourceHash'] == routes['sourceHash']
assert len(routes['results']) == 118 and len(routes['boundaryResults']) == 14
assert not routes['errors'] and all(item['status'] == 'passed' for item in routes['results'] + routes['boundaryResults'])
assert routes['navigationSHA256'] == sha('viewer/src/navigation.ts')

views = {
    'viewer_reference_raw.png': 'The oval arena, stepped seating, imperial axis, warm stone and red canopy hierarchy remain intact. The left river/bridge, rear temple and right aqueduct maintain the reference composition. Materials and ornament remain simpler than the illustration.',
    'viewer_street_district_rear_precinct_raw.png': 'Close supported shop fronts, goods, resident groups and walkers occupy a rear commercial street, extending the activity beyond the front of the arena.',
    'viewer_street_district_gallery_raw.png': 'The runtime gallery has a readable floor, repeated masonry, a curved passage and a full walking character. Hemisphere fill makes this view clearer than the dark Blender gallery render.',
    'viewer_street_district_backstage_raw.png': 'Connected arched service openings, ceiling beams, floor and porters are readable. The lighting and wall finish are comparatively simple and flat.',
    'viewer_street_district_civic_court_raw.png': 'The former eastern void now contains a structurally complete portico, fountain garden and resident activity, with the aqueduct establishing its setting.',
    'viewer_district_entire_world_raw.png': 'The irregular physical enclosure, varied quarter orientations and continuing river/terrain are visible. The requested lighter fog keeps the city readable from the broad overview while retaining a distant landscape haze.',
    'viewer_night_raw.png': 'At night the arena silhouette, seating, floor and surrounding street edges remain readable, with warm braziers and entrances. This is stylized lighting rather than the reference image\'s global illumination.',
    'runtime_boundary_QuayGate_North_West_raw.png': 'The supported iron leaf and upper grille visibly close the quay path beside the river arch. The corresponding current-controller walking and jumping checks pass.',
}
review = read('comparisons/street_life_review.json')
review['status'] = 'Completed source and final WebGPU visual review; accepted with the documented visual and performance limits.'
district = review['finalDistrictCheckpoint']
assert district['sourceSHA256'] == bridge['previousSourceHash']
district['status'] = 'Source composition and thirteen regional eye-height views accepted; final runtime delta and readability reviewed separately below.'
district['rootApproval'] = 'approved with documented limits'
review['finalRuntimeCheckpoint'] = {
    'status': 'passed', 'reviewedAtUTC': datetime.now(timezone.utc).isoformat(),
    'sourceSHA256': source, 'backend': runtime['backend'],
    'runtimeReportSHA256': sha('viewer/runtime_validation.json'),
    'performanceReportSHA256': sha('viewer/performance_optimization.json'),
    'primaryReference': {'file': 'references/primary_reference.png', 'sha256': sha('references/primary_reference.png')},
    'stableGridEvidence': {'file': 'viewer/stable_grid_validation.json', 'sha256': sha('viewer/stable_grid_validation.json')},
    'requestedFogRevision': {'nearMeters': 1200, 'farMeters': 4500, 'scope': 'Same linear fog and day/night colors; substantially clearer city and distant-only haze.'},
    'sourceBridge': {'file': 'viewer/watergate_boundary_revision_validation.json', 'sha256': sha('viewer/watergate_boundary_revision_validation.json'),
                     'scope': 'All previous material instances, complete geometry, cameras, routes and population are unchanged; only the four quay gates and their metadata are added.'},
    'inspectedViews': [{'file': 'renders/' + name, 'sha256': sha('renders/' + name), 'observation': note} for name, note in views.items()],
    'movementEvidence': {'file': 'viewer/route_validation.json', 'sha256': sha('viewer/route_validation.json'),
                         'routes': 118, 'physicalBoundaries': 14, 'source': 'Fresh execution on the final source and corrected controller.'},
    'resolvedReadabilityConcern': 'The final WebGPU gallery and backstage captures establish navigable floor/doorway visibility; the historical Blender source render remains correctly described as underlit.',
    'remainingLimits': [note.replace('Final runtime interior readability requires separate evidence.', 'Final runtime readability has been verified separately.') for note in district['remainingLimits']] + [
        'The complete geometry remains expensive. Frame pacing and startup measurements are documented under shared-GPU conditions; a locked 60 fps is not claimed.'
    ],
    'historicalImagePolicy': 'Earlier images retain their actual source hashes. No source633ad render is relabeled as a source408daf image.',
}
(R / 'comparisons/street_life_review.json').write_text(json.dumps(review, indent=2), encoding='utf8')
print('FINAL_VISUAL_REVIEW_PASSED', source, len(views))
