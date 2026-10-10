"""Template for an in-place structured or rigid CharacterBase garment update.

Copy this file beside the working project, implement build_geometry, and run
the copy with a schema-valid garment specification. The loaded .blend is the
single canonical working file; never edit the bundled template in place.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import sys

import bmesh
import bpy


def argument(flag, default=None):
    args = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    if flag in args:
        index = args.index(flag)
        if index + 1 < len(args):
            return args[index + 1]
    return default


def bridge_loops(faces, first, second, reverse=False):
    if len(first) != len(second):
        raise ValueError("Loops must have equal vertex counts")
    for index in range(len(first)):
        next_index = (index + 1) % len(first)
        face = [
            first[index],
            first[next_index],
            second[next_index],
            second[index],
        ]
        faces.append(list(reversed(face)) if reverse else face)


def ellipse_ring(vertices, center, radius_x, radius_y, z, segments=12, phase=0.0):
    indices = []
    for index in range(segments):
        angle = math.tau * index / segments + phase
        indices.append(len(vertices))
        vertices.append(
            (
                center[0] + math.cos(angle) * radius_x,
                center[1] + math.sin(angle) * radius_y,
                z,
            )
        )
    return indices


def build_geometry(source, spec):
    from mathutils import Vector
    name=spec['object_name']; vertices=[]; faces=[]
    def shell(predicate, offset):
        selected=[p for p in source.data.polygons if all(predicate(source.data.vertices[i].co) for i in p.vertices)]
        ids=sorted({i for p in selected for i in p.vertices})
        mapping={old:len(vertices)+i for i,old in enumerate(ids)}
        for i in ids:
            v=source.data.vertices[i]; vertices.append(tuple(v.co+v.normal*offset))
        faces.extend([[mapping[i] for i in p.vertices] for p in selected])
        return selected,mapping
    def box(center, size):
        offset=len(vertices); cx,cy,cz=center; sx,sy,sz=[v/2 for v in size]
        vertices.extend([(cx+x*sx,cy+y*sy,cz+z*sz) for x,y,z in [(-1,-1,-1),(-1,-1,1),(-1,1,1),(-1,1,-1),(1,-1,-1),(1,-1,1),(1,1,1),(1,1,-1)]])
        faces.extend([[offset+i for i in p] for p in [(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]])
    def cylinder_x(x0,x1,y,z,r0,r1,n=10):
        rings=[]
        for x,r in [(x0,r0),(x1,r1)]:
            ring=[]
            for i in range(n):
                angle=2*math.pi*i/n; ring.append(len(vertices)); vertices.append((x,y+math.cos(angle)*r,z+math.sin(angle)*r))
            rings.append(ring)
        bridge_loops(faces,*rings); faces.append(rings[0][::-1]); faces.append(rings[1])
    if name=='RomanTunic':
        selected,mapping=shell(lambda c:0.59<=c.z<=0.89 and abs(c.x)<=0.24,0.010)
        from collections import Counter
        counts=Counter(tuple(sorted((p.vertices[i],p.vertices[(i+1)%len(p.vertices)]))) for p in selected for i in range(len(p.vertices)))
        bottom=sorted({i for edge,n in counts.items() if n==1 for i in edge if source.data.vertices[i].co.z<0.62},key=lambda i:math.atan2(source.data.vertices[i].co.y,source.data.vertices[i].co.x))
        last=[mapping[i] for i in bottom]
        for z,rx,ry in [(0.51,0.132,0.098),(0.395,0.157,0.100)]:
            ring=[]
            for i in bottom:
                c=source.data.vertices[i].co; angle=math.atan2(c.y,c.x)
                ring.append(len(vertices)); vertices.append((math.cos(angle)*rx,math.sin(angle)*ry,z))
            bridge_loops(faces,last,ring); last=ring
    elif name=='LeatherBelt':
        a=ellipse_ring(vertices,(0,0.003),0.119,0.096,0.602,20)
        b=ellipse_ring(vertices,(0,0.003),0.116,0.093,0.630,20); bridge_loops(faces,a,b)
    elif name=='BronzeArmor':
        shell(lambda c:0.648<=c.z<=0.87 and abs(c.x)<=0.168,0.024)
    elif name=='RomanHelmet':
        rings=[ellipse_ring(vertices,(0,0),rx,ry,z,16) for z,rx,ry in [(0.981,0.078,0.089),(1.025,0.075,0.084),(1.068,0.040,0.048),(1.086,0.003,0.004)]]
        for a,b in zip(rings,rings[1:]): bridge_loops(faces,a,b)
        faces.append(rings[-1])
    elif name=='HairCap':
        rings=[ellipse_ring(vertices,(0,0),rx,ry,z,16) for z,rx,ry in [(0.998,0.069,0.076),(1.028,0.063,0.070),(1.059,0.030,0.039),(1.070,0.003,0.004)]]
        for a,b in zip(rings,rings[1:]): bridge_loops(faces,a,b)
        faces.append(rings[-1])
    elif name=='RomanSandals':
        shell(lambda c:c.z<0.036,0.005)
    elif name=='GuardShield':
        # Length along the T-pose arm becomes vertical after the arm lowers.
        box((0.46,-0.081,0.830),(0.38,0.026,0.235))
        box((0.46,-0.100,0.830),(0.048,0.024,0.048))
    elif name=='GuardSpear':
        cylinder_x(-0.78,0.48,-0.083,0.833,0.007,0.007)
        cylinder_x(0.48,0.62,-0.083,0.833,0.025,0.0006)
    elif name=='GladiatorSword':
        box((-0.63,-0.083,0.833),(0.29,0.015,0.035))
        box((-0.48,-0.083,0.833),(0.035,0.020,0.106))
        cylinder_x(-0.470,-0.413,-0.083,0.833,0.013,0.013)
    else: raise ValueError(name)
    if name=='HairCap':
        from mathutils.bvhtree import BVHTree
        tree=BVHTree.FromPolygons([v.co for v in source.data.vertices],[list(p.vertices) for p in source.data.polygons])
        corrected=[]
        for value in vertices:
            v=Vector(value)
            for attempt in range(5):
                p,n,i,d=tree.find_nearest(v);signed=(v-p).dot(n)
                if signed>=0.004:break
                v+=n*(0.0045-signed)
            corrected.append(tuple(v))
        vertices=corrected
    return vertices, faces

def file_sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def main():
    helper_dir = argument("--helper-dir")
    spec_arg = argument("--spec")
    working_arg = argument("--working-blend")
    action = argument("--action")
    expected_sha256 = argument("--expected-sha256")
    report_arg = argument("--report")
    builder_copy = os.path.abspath(__file__)
    if not helper_dir or not spec_arg or not working_arg or not action or not report_arg:
        raise ValueError(
            "--helper-dir, --spec, --working-blend, --action, and --report are required"
        )
    if action not in {"create", "update"}:
        raise ValueError("--action must be create or update")
    helper_dir = os.path.abspath(helper_dir)
    spec_path = os.path.abspath(spec_arg)
    working_blend = os.path.abspath(working_arg)
    report_path = os.path.abspath(report_arg)
    working_sha256_before = file_sha256(working_blend)
    if expected_sha256:
        expected_sha256 = expected_sha256.upper()
        if len(expected_sha256) != 64 or any(
            character not in "0123456789ABCDEF" for character in expected_sha256
        ):
            raise ValueError("--expected-sha256 must be a 64-digit SHA-256 value")
        if working_sha256_before != expected_sha256:
            raise RuntimeError(
                "Working Blender file hash mismatch before mutation: "
                f"expected={expected_sha256}, actual={working_sha256_before}"
            )

    paths = {
        "working_blend": working_blend,
        "builder": builder_copy,
        "spec": spec_path,
        "report": report_path,
    }
    seen = {}
    for role, path in paths.items():
        normalized = os.path.normcase(os.path.realpath(path))
        if normalized in seen:
            raise ValueError(f"Path collision between {seen[normalized]} and {role}: {path}")
        seen[normalized] = role
    if not working_blend.lower().endswith(".blend"):
        raise ValueError("--working-blend must end in .blend")
    if not report_path.lower().endswith(".json"):
        raise ValueError("--report must end in .json")
    with open(spec_path, "r", encoding="utf-8") as handle:
        spec = json.load(handle)

    strategy = spec.get("construction_strategy")
    if strategy not in {"cross_section", "rigid_closed", "draped_baked"}:
        raise ValueError(
            "Custom builder requires cross_section, rigid_closed, or draped_baked"
        )
    required = {
        "garment_id",
        "object_name",
        "mesh_name",
        "garment_type",
        "garment_slot",
        "reference_images",
        "reference_assets",
        "image_interpretation",
        "material",
        "visibility_property",
        "layering",
        "max_influences",
        "open_surface",
        "thickness",
    }
    missing = sorted(required - set(spec))
    if missing:
        raise ValueError("Garment specification is missing: " + ", ".join(missing))
    if int(spec["max_influences"]) < 1 or int(spec["max_influences"]) > 4:
        raise ValueError("max_influences must be between 1 and 4")
    if not spec["reference_images"] or not spec["reference_assets"]:
        raise ValueError("Reference images and copied reference assets are required")
    if bool(spec["open_surface"]) and float(spec["thickness"]) <= 0.0:
        raise ValueError("An open surface garment requires positive thickness")
    if not bool(spec["open_surface"]) and float(spec["thickness"]) != 0.0:
        raise ValueError("A closed rigid mesh must not receive Solidify thickness")

    for asset in spec["reference_assets"]:
        copied_path = os.path.abspath(asset["copied_path"])
        if not os.path.isfile(copied_path):
            raise FileNotFoundError(f"Copied reference asset is missing: {copied_path}")
        if file_sha256(copied_path) != str(asset["sha256"]).upper():
            raise RuntimeError(f"Reference asset hash mismatch: {copied_path}")

    if helper_dir not in sys.path:
        sys.path.insert(0, helper_dir)
    from validate_garment_spec import validate as validate_garment_spec_contract
    from clothing_helpers import (
        add_visibility_control,
        create_material,
        ensure_clothing_collection,
        managed_garments,
        mark_managed_garment,
        prepare_managed_garment_action,
        require_working_blend,
        safe_save_blend_in_place,
        transfer_weights_nearest_surface,
        validate_exact_character,
    )
    working_blend = require_working_blend(working_blend)
    spec_contract = validate_garment_spec_contract(spec, check_assets=True)

    source = bpy.data.objects.get("CharacterBase")
    rig = bpy.data.objects.get("CharacterRig")
    if source is None or rig is None:
        raise RuntimeError("CharacterBase or CharacterRig is missing")
    exact_before = validate_exact_character(source, rig)

    vertices, faces = build_geometry(source, spec)
    if not vertices or not faces:
        raise RuntimeError("build_geometry returned empty geometry")

    name = spec["object_name"]
    lifecycle = prepare_managed_garment_action(
        action=action,
        garment_id=spec["garment_id"],
        object_name=name,
        rig=rig,
        visibility_property=spec["visibility_property"],
    )

    mesh = bpy.data.meshes.new(spec["mesh_name"])
    mesh.from_pydata(vertices, [], faces)
    mesh.update(calc_edges=True)
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(mesh)
    bm.free()
    for polygon in mesh.polygons:
        polygon.use_smooth = False

    collection = ensure_clothing_collection()
    garment = bpy.data.objects.new(name, mesh)
    collection.objects.link(garment)
    garment.parent = rig
    garment.parent_type = "OBJECT"
    garment.matrix_parent_inverse = source.matrix_parent_inverse.copy()
    garment.location = source.location
    garment.rotation_mode = source.rotation_mode
    garment.rotation_euler = source.rotation_euler
    garment.scale = source.scale
    garment["garment_type"] = spec["garment_type"]
    garment["garment_slot"] = spec["garment_slot"]
    garment["concept_color"] = spec["material"]["color"].upper()
    garment["layering"] = spec["layering"]
    garment["construction_strategy"] = spec["construction_strategy"]
    garment["open_surface"] = bool(spec["open_surface"])

    weight_report = transfer_weights_nearest_surface(
        source,
        garment,
        maximum=int(spec["max_influences"]),
    )

    for vertex in mesh.vertices:
        for item in list(vertex.groups):
            if item.weight <= 0: garment.vertex_groups[item.group].remove([vertex.index])

    rigid_bone={'RomanHelmet':'head','HairCap':'head','GuardShield':'hand.L','GuardSpear':'hand.R','GladiatorSword':'hand.R'}.get(name)
    if rigid_bone:
        garment.vertex_groups.clear()
        garment.vertex_groups.new(name=rigid_bone).add(list(range(len(mesh.vertices))),1.0,'REPLACE')

    if spec["open_surface"]:
        solidify = garment.modifiers.new("Garment Thickness", "SOLIDIFY")
        solidify.thickness = float(spec["thickness"])
        solidify.offset = 0.0
        solidify.use_even_offset = True
        solidify.use_rim = True

    armature = garment.modifiers.new("Armature", "ARMATURE")
    armature.object = rig
    armature.use_deform_preserve_volume = False
    armature.use_vertex_groups = True
    armature.use_bone_envelopes = False

    material_spec = spec["material"]
    material = create_material(
        material_spec["name"],
        material_spec["color"],
        material_spec["roughness"],
        material_spec["metallic"],
    )
    mesh.materials.append(material)
    visibility_property = add_visibility_control(
        garment,
        rig,
        spec["visibility_property"],
    )
    mark_managed_garment(
        garment,
        garment_id=spec["garment_id"],
        revision=lifecycle["revision_after"],
        visibility_property=visibility_property,
    )
    rig[visibility_property] = lifecycle["visibility_value"]
    bpy.context.scene.update_tag()
    rig.update_tag(refresh={"OBJECT"})
    garment.update_tag(refresh={"OBJECT"})
    bpy.context.view_layer.update()
    bpy.context.evaluated_depsgraph_get().update()

    exact_after = validate_exact_character(source, rig)
    bpy.ops.object.select_all(action="DESELECT")
    garment.select_set(True)
    bpy.context.view_layer.objects.active = garment
    save_result = safe_save_blend_in_place(working_blend, compress=True)

    report = {
        "status": "ok",
        "working_blend": working_blend,
        "working_blend_sha256_before": working_sha256_before,
        "working_blend_sha256_after": save_result["sha256"],
        "action": action,
        "garment_id": spec["garment_id"],
        "revision_before": lifecycle["revision_before"],
        "revision_after": lifecycle["revision_after"],
        "updated_in_place": True,
        "builder": builder_copy,
        "builder_sha256": file_sha256(builder_copy),
        "spec": spec_path,
        "spec_sha256": file_sha256(spec_path),
        "spec_contract": spec_contract,
        "garment_spec": spec,
        "object": garment.name,
        "mesh": mesh.name,
        "vertices": len(mesh.vertices),
        "faces": len(mesh.polygons),
        "weight_transfer": weight_report,
        "modifiers": [[modifier.name, modifier.type] for modifier in garment.modifiers],
        "visibility_property": f'CharacterRig["{visibility_property}"]',
        "visibility_value_after": lifecycle["visibility_value"],
        "exact_character_contract_before": exact_before,
        "exact_character_contract_after": exact_after,
        "managed_garments": managed_garments(rig),
        "save": save_result,
        "external_3d_services": [],
    }
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, ensure_ascii=False)
    print("CUSTOM_GARMENT_RESULT=" + json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
