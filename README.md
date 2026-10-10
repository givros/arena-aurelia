# Arena Aurelia

An explorable Roman amphitheater and inhabited city district, built in Blender and rendered with Three.js WebGPU. Includes stepped seating, galleries, backstage passages, markets, civic courts, city walls and a day/night cycle.

## Explore locally

Use Node.js 22.12 or newer and a desktop Chrome or Edge browser with WebGPU hardware acceleration.

```sh
npm run setup
npm run dev
```

Open http://127.0.0.1:4178/. Use WASD or ZQSD and the mouse to walk, Shift to run, and Escape to pause. Places, aerial views and time controls are available in the interface. Initial scene preparation can take roughly two minutes, depending on the device.

## Project files

- `Aurelia_Arena.blend`: editable environment.
- `viewer/`: explorer source and full-resolution runtime assets.
- `characters/`, `textures/`, `scripts/`: character assets, materials and construction tools.
- `scene_spec.json`, layout files and registries: world dimensions and authored placement.
- `references/`, `renders/`, `comparisons/`, `checkpoints/`: visual references and development evidence.
- `validation_report.md`: measured performance, navigation checks and known limits.

Large geometry files are stored as byte-preserving chunks in `repository-assets/`. Setup restores and verifies every file by SHA-256; build and dev restore only runtime data. After deliberately exporting changed geometry, run `npm run pack:assets` before committing. The rendered geometry is neither compressed nor simplified.

```sh
npm run build
npm run preview
```
