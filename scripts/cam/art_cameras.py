"""Stage 4 moving perspective cameras for the weather / parallax test clips (3 s each, frames 1-72 at 24 fps).

Each camera moves on a short eased path while tracking a fixed target empty, so foreground, middle and background
move against each other (parallax) and the rain, drips, ripples and haze are seen in motion. These are test shots
for stage 4, not the stage 5 film cameras.
"""
import bpy
from mathutils import Vector

FRAMES = (1, 72)


def _bounds(rid):
    lo, hi = Vector((1e9,) * 3), Vector((-1e9,) * 3)
    for o in bpy.data.objects:
        if o.get("cot_region") == rid and o.get("cot_s3") and o.type == "MESH" and o.get("cot_layer") not in ("ROCK", "CAVESHELL", "BACKDROP"):
            for c in o.bound_box:
                w = o.matrix_world @ Vector(c)
                lo, hi = Vector(map(min, lo, w)), Vector(map(max, hi, w))
    return lo, hi


def _from_cam(name, push, side=0.0, rise=0.0, look=30.0):
    cam = bpy.data.objects[name]
    loc = cam.matrix_world.translation.copy()
    q = cam.matrix_world.to_quaternion()
    fwd, right, up = q @ Vector((0, 0, -1)), q @ Vector((1, 0, 0)), q @ Vector((0, 1, 0))
    return loc, loc + fwd * push + right * side + up * rise, loc + fwd * look, cam.data.lens


def shots():
    c = (_bounds("LeftWell")[0] + _bounds("LeftWell")[1]) / 2
    out = [
        ("Plaza", "FountainPlaza", Vector((-7.0, -25.0, 2.4)), Vector((7.0, -22.5, 3.4)), Vector((0.5, 2.0, 4.5)), 30.0,
         "exterior rain, drips, puddle rings and parallax of the background towers in front of the fountain"),
        ("LeftWell", "LeftWell", c + Vector((-10.0, -62.0, -18.0)), c + Vector((6.0, -58.0, -8.0)), c + Vector((0.0, 0.0, -6.0)), 32.0,
         "rising move in the left rain well: rain columns, ground fog, depth haze and the towers behind"),
    ]
    for key, rid, cam, push, side, rise in (("Sanctum", "SoulSanctum", "CAM_S3_SoulSanctum_GreatHall", 5.0, 1.5, 0.6),
                                             ("Cave", "SouthwestCave", "CAM_S3_SouthwestCave_FromEast", 5.0, -1.2, 0.3)):
        if cam in bpy.data.objects:
            a, b, t, lens = _from_cam(cam, push, side, rise)
            out.append((key, rid, a, b, t, lens, "slow push inside the region at its representative view"))
    out.append(("Pleasure", "HouseOfPleasure", Vector((152.6, -5.6, 80.3)), Vector((156.4, -5.0, 80.5)), Vector((158.8, 8.0, 79.6)), 24.0,
                "slow lateral move inside the stage room: curtains, wall pattern, stage edge and stage light; no rain inside"))
    return out


def build(scene, coll):
    for o in [o for o in bpy.data.objects if o.get("cot_s4_cam")]:
        bpy.data.objects.remove(o, do_unlink=True)
    made = []
    for key, rid, a, b, target, lens, purpose in shots():
        name = f"CAM_S4_DYN_{key}"
        data = bpy.data.cameras.new(name + "_data")
        data.lens, data.sensor_width = lens, 36.0
        data.clip_start, data.clip_end = 0.1, 3000.0
        cam = bpy.data.objects.new(name, data)
        tgt = bpy.data.objects.new(name + "_Target", None)
        tgt.location = target
        tgt.empty_display_size = 0.5
        for o in (cam, tgt):
            o["cot_s4"] = True
            o["cot_s4_cam"] = True
            o["cot_region"] = rid
            coll.objects.link(o)
        con = cam.constraints.new("TRACK_TO")
        con.target = tgt
        con.track_axis, con.up_axis = "TRACK_NEGATIVE_Z", "UP_Y"
        cam.location = a
        cam.keyframe_insert("location", frame=FRAMES[0])
        cam.location = b
        cam.keyframe_insert("location", frame=FRAMES[1])
        cam["cot_kind"] = "dynamic"
        cam["cot_res"] = [1920, 1080]
        cam["cot_hide"] = ""
        cam["cot_frames"] = list(FRAMES)
        cam["cot_purpose"] = purpose
        made.append({"camera": name, "region": rid, "from": [round(v, 2) for v in a], "to": [round(v, 2) for v in b],
                     "target": [round(v, 2) for v in target], "lens": lens})
    return made
