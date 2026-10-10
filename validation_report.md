# Aurelia — living arena district

The editable Blender environment and local WebGPU explorer extend the reference arena into a coherent inhabited city. The original reference remains the architectural and atmospheric anchor. A generated continuation concept supports the unseen districts; it is not a render of the delivered model.

## Built changes

All 159 existing residential assemblies are reused in 12 curved street systems with 132 fitted courtyards. Complete houses move as rigid assemblies, preserving their geometry. The old common street grid and courtyard walls are replaced. Arena architecture, established market shops, original crowds and monumental infrastructure are preserved.

The arena edge has 84 detailed market stalls and 20 shop houses. Beyond it, 235 commercial assemblies include 90 complete infill shops and 64 supported shopfront awnings, with loading areas, goods, benches and warm lamps.

A complete L-shaped peristyle gives the eastern civic space a purpose: a fountain garden around retained cypresses, with planted herb beds, shaded resting benches and connected open circulation. Its 40 declared parts include structural columns, tiled roofs, rafters, level paving and supported lamps.

An irregular physical enclosure has four closed city gates, 2 arched watergates and complete watchtowers. The river continues into rolling outer terrain, with 248 grounded trees and 16 complete hillside villas. This landscape covers the former rectangular platform edge; closed gates define the playable boundary.

Four supported iron pedestrian gates close the narrow quay-cap passages beside the river arches. They prevent walking beyond the city to the technical safety clamp while preserving the central waterway. This local revision adds 148 meshes without changing any existing geometry, cameras, people or materials.

New activity extends through 10 regional areas. Full bodies, clothing and carried goods are retained for every human. The character-derived inventory has 15,688 instances, including 26 sculptural figures, the existing 12,000 seated spectators, 142 walking actors and 22 fixed animated staff. The latest citywide addition contributes 2,299 static residents and 124 animated actors, including arena galleries, backstage passages and arrival flow.

| Region | Commercial assemblies | Accepted new people | Moving routes |
| --- | ---: | ---: | ---: |
| Rear arena precinct | 15 | 148 | 2 |
| Temple and civic courts | 9 | 115 | 2 |
| Arena river quay | 11 | 140 | 2 |
| West bridge ward | 38 | 376 | 2 |
| Eastern trade streets | 22 | 280 | 2 |
| Eastern lodging lanes | 23 | 225 | 2 |
| Aqueduct ward | 21 | 188 | 4 |
| Northern residential streets | 28 | 280 | 2 |
| Upper city courts | 50 | 377 | 2 |
| Southern residential approaches | 18 | 166 | 2 |

The six-metre ceremonial axis remains clear. Narrow market passages and city connections use the shared authored routes; the complete facade circuit detours around the projecting entrance monument. Actual controller traversal is recorded against the final exported geometry.

## Visual and movement evidence

- Regional views: `comparisons/district_life_final_regional_sheet.jpg` and full-resolution `renders/district_life_final_*`.
- Whole-project before/after: `comparisons/district_life_final_world_comparison.jpg`.
- User-reported empty area: `comparisons/district_life_final_southern_ward_comparison.jpg`.
- Layout and dimensional checks: `comparisons/district_life_layout_map.png` and `comparisons/district_life_layout_audit.json`.
- Organic city reflow and physical edge: `comparisons/master_world_layout_map.png`, `comparisons/master_world_integration.json` and `comparisons/world_boundary_geometry.json`.
- Quay passage closure and preservation: `watergate_boundary_revision.json`, `comparisons/watergate_boundary_integration.json` and the final runtime boundary checks.
- Eastern fountain court: `comparisons/civic_court_layout_map.png` and its source render views.
- Actual source contacts, preserved actors and full triangle counts: `characters/district_life_population_validation.json` and the fresh character QC reports.
- Runtime views, continuous traversal, actor circulation/yielding and day/night: `viewer/runtime_validation.json` and its related route/activity reports.
- Final reference comparison and remaining visual limits: `comparisons/street_life_review.json`.

The first street revision remains documented by its own renders and comparison files. The original arena build validation remains in `checkpoints/12_before_street_life_validation.md`; its older exterior density/counts are historical.

## Source and performance verification

The saved scene was reopened in a fresh Blender process: 38,480 scene objects, 205 materials, 32 cameras and no missing packed dependencies or invalid transforms. The explorer transfers 6,690,777 complete architectural triangle instances and 78,613,716 human triangle instances without geometry compression, simplification, crowd billboards or LOD replacement.

Source SHA-256: `408daf3279785df7cdb0e62c3aae854c1524b406f307f5576891f8e1530f4d6a`. Source, transfer and runtime checks refer to this identical version; the runtime also binds the layout and character manifest hashes.

Tested backend: webgpu, 1440 × 1080 at DPR 1. Median reference-view frame interval: 66.6 ms (approximately 15 fps), 95th percentile 66.8 ms. Native resolution, full assets, 4× MSAA and full-detail shadows remain enabled. Per-view measurements are in the runtime report. The dedicated WebGPU optimization evidence in `viewer/performance_optimization.json` separates frame pacing, CPU work and available GPU timestamp measurements, with matching before/after quality and source. Frame interval is not presented as isolated GPU execution time. Its reference ledger is `viewer/performance_reference_ledger.json`.

| Fixed desktop scenario | 95th-percentile frame interval, before / after (ms) | Largest sampled frame interval, before / after (ms) |
| --- | ---: | ---: |
| reference | 66.8 / 66.8 | 100.0 / 83.5 |
| market still | 66.8 / 66.7 | 2983.3 / 66.9 |
| market walking | 66.7 / 66.7 | 3549.9 / 66.8 |
| aerial orbit | 283.3 / 66.8 | 383.4 / 83.6 |
| walking daynight | 83.3 / 66.7 | 550.1 / 83.3 |

Fresh isolated-context preparation took 105.9 seconds before and 104.2 seconds after optimization. Preparing the scene's main and shadow pipelines moves work into loading to reduce pauses during exploration. Browser/driver shader-cache state is not controlled; these are measured context loads, not guaranteed first-install times. Other applications were using the GPU during verification, so this is a shared-GPU measurement rather than an exclusive hardware benchmark; small throughput differences are not treated as conclusive. This full-detail scene remains demanding and does not promise a locked 60 fps. All raw samples, actual travel distances and the shared corrected movement code are recorded with the paired measurements.

The requested lighter fog now begins at 1,200 metres and ends at 4,500 metres, keeping the city clear and a light haze over the distant landscape. Both measured implementations use these same settings.

Clustered lighting now keeps its shader nodes and storage stable during ordinary window resizing. The reserved grid covers a native 3,840 × 2,160 framebuffer and uses 50,135,040 bytes, about 40.7 MB more than the original 1,440 × 1,080 allocation. Every light, depth slice and active cluster remains evaluated. The CPU, actual GPU light-list, pixel and production resize evidence is recorded in `viewer/stable_grid_validation.json`. Larger grids can grow geometrically within the device buffer limit and may recompile; outgoing storage remains allocated until renderer teardown. Resize stability is therefore bounded to the current allocation, without silently lowering resolution or removing lights.

## Scope and limits

This is ambient district life with walking, waiting, resting, carrying and staff animations; it does not simulate commerce or conversations. Static crowd groups are visual occupants rather than player collision barriers; moving actors yield along authored routes. Background residences remain largely exterior scenery, and the outer hills and villas continue the view beyond the enclosed playable city. Architecture, ornament and material variation are simplified relative to the supplied illustration; building modules, clothing and seated crowd patterns repeat more regularly, and the lighting is stylized. Visual comparisons record those differences without claiming photographic parity.

Local explorer: http://127.0.0.1:4178/. Walk with WASD or ZQSD and mouse, run with Shift, pause with Escape. Places, aerial views and time controls are available in the interface.
