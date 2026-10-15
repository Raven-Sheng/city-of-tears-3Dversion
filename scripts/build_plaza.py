"""Build the stage 2 fountain plaza sample on top of the stage 1 city greybox.

Run from the project root:
  blender -b --factory-startup --python scripts/build_plaza.py -- [--checkpoint] [--from-master] [--sample FILE]

  * Opens scenes/plaza_sample.blend if it exists (unless --from-master), otherwise scenes/city_master.blend.
    The master file is never written by this script.
  * Rebuilds only objects carrying the cot_s2 flag; hand-made objects and the greybox stay.
  * Greybox objects replaced by sample assets are hidden and tagged cot_s2_superseded (not deleted).
  * Same code + config/plaza.json gives the same result (fixed seeds).
"""
import json
import math
import shutil
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import cot_assets as A  # noqa: E402
import cot_look as L  # noqa: E402
from cot_geo import Geo, IronCurves, TAU, catmull, instance, lerp, place, resample, rng, smoothstep  # noqa: E402
from cot_statue import build_statue  # noqa: E402

CFG = json.loads((ROOT / "config" / "plaza.json").read_text(encoding="utf-8"))
PROJECT = json.loads((ROOT / "config" / "project.json").read_text(encoding="utf-8"))
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
SAMPLE = ROOT / CFG["sample_file"]
if "--sample" in argv:            # tests run against a copy instead of the real sample file
    SAMPLE = Path(argv[argv.index("--sample") + 1])
MASTER = ROOT / PROJECT["master_file"]
source = SAMPLE if (SAMPLE.exists() and "--from-master" not in argv) else MASTER
bpy.ops.wm.open_mainfile(filepath=str(source))
scene = bpy.context.scene

GZ = CFG["ground_z"]
WZ = CFG["water_z"]
QY = CFG["quay_y"]
CAM = CFG["reference"]["camera"]
PX = CFG["reference"]["px_per_unit_at_2000"]
SX, SY = CFG["reference"]["statue_px"]
L.TUNE.update(CFG["look"])
L.TUNE["rain_z_clip"] = CFG["rain"]["z_clip"]
LK = CFG["look"]["lights"]
mats = L.material


def xa(px):
    return (px - SX) / PX


def za(py):
    return GZ + (SY - py) / PX


def W(x_app, z_app, y):
    """World point whose image in the reference camera matches play-plane coordinates (x_app, z_app)."""
    s = (y - CAM["y"]) / (0.0 - CAM["y"])
    return (CAM["x"] + (x_app - CAM["x"]) * s, y, CAM["z"] + (z_app - CAM["z"]) * s)


def WX(x_app, y):
    return W(x_app, 0.0, y)[0]


def WZ_(z_app, y):
    return W(0.0, z_app, y)[2]


# --------------------------------------------------------------------------- collections
def collection(name, parent=None):
    coll = bpy.data.collections.get(name) or bpy.data.collections.new(name)
    holder = parent if parent is not None else scene.collection
    if coll.name not in holder.children:
        holder.children.link(coll)
    return coll


for obj in [o for o in bpy.data.objects if o.get("cot_s2")]:
    data = obj.data
    bpy.data.objects.remove(obj, do_unlink=True)
    if data is not None and data.users == 0:
        for store in (bpy.data.meshes, bpy.data.curves, bpy.data.cameras, bpy.data.lights):
            if data.name in store and store[data.name] == data:
                store.remove(data)
                break
for act in [a for a in bpy.data.actions if a.users == 0]:
    bpy.data.actions.remove(act)

C_ROOT = collection("COT_S2")
C_STATUE = collection("COT_S2_STATUE", C_ROOT)
C_PLAZA = collection("COT_S2_PLAZA", C_ROOT)
C_KIT = collection("COT_S2_KIT", C_ROOT)
C_HOUSE = collection("COT_S2_HOUSE", C_ROOT)
C_BACK = collection("COT_S2_BACKGROUND", C_ROOT)
C_LIGHTS = collection("COT_S2_LIGHTS", C_ROOT)
C_WEATHER = collection("COT_S2_WEATHER", C_ROOT)
C_CAMS = collection("COT_S2_CAMERAS", C_ROOT)

REF_MAIN = "11_Lower_City/Lower_City_statue.jpg"
REF_UR = "11_Lower_City/Lower_City_statue_upper_right.jpg"
REF_M1 = "12_Materials/Materials_01.jpg"
REF_M2 = "12_Materials/Materials_02.jpg"
REF_M3 = "12_Materials/20260911201846_1.jpg"
REF_L1 = "13_Lighting/Lighting_01.jpg"
REF_VID = "14_Rain/Rain_video.mp4"

# --------------------------------------------------------------------------- supersede greybox placeholders
SUPERSEDE = ("COT_FountainPlaza_", "COT_PlazaEastHouse_House_", "COT_PlazaEastHouse_Terrace", "COT_PlazaEastHouse_Canopy",
             "COT_PlazaEastHouse_GlassPillar", "COT_CentralWell_Water", "COT_CentralWell_FreeTower_", "COT_CentralWell_IronArches",
             "COT_CentralWell_EastTower_", "COT_CentralWell_BackTowerA_", "COT_CentralWell_BackTowerB_", "COT_CentralWell_BackTowerC_", "COT_CentralWell_BackTowerD_",
             "COT_CentralBlock_GroundGallery_", "COT_CentralWell_FrontTowerA_", "COT_CentralWell_FrontTowerB_", "COT_TopCavern_FrontTowerA_")
superseded = []
for obj in bpy.data.objects:
    if obj.get("cot_s2"):
        continue
    if any(obj.name.startswith(p) for p in SUPERSEDE):
        obj.hide_render = True
        obj.hide_viewport = True
        obj["cot_s2_superseded"] = True
        superseded.append(obj.name)

# --------------------------------------------------------------------------- statue (hero)
statue_objs = build_statue(C_STATUE, mats, A.P("FountainStatue", "A", f"{REF_MAIN}; {REF_UR}; {REF_M2}; {REF_VID}"))
S_M = Matrix.Translation((0.0, 0.0, GZ)) @ Matrix.Scale(CFG["statue"]["scale"], 4)
for o in statue_objs:
    o.matrix_world = S_M

# --------------------------------------------------------------------------- plaza ground
NOTCHES = ((-8.87, -6.14), (6.75, 9.08))
NOTCH_BACK = -3.7
X_W, X_E = -20.0, 25.5          # paved extent along X
HOUSE_X, HOUSE_Y0, HOUSE_Y1 = 10.4, -1.6, 15.5
VIA_Y0, VIA_Y1 = 12.0, 15.5

g = Geo().use("stone_dark")
g.box(X_W, HOUSE_X, NOTCH_BACK, VIA_Y1 + 16.0, -2.7, GZ - 0.17)                   # main slab (continues behind the viaduct)
QUAY_E = 40.0
g.box(HOUSE_X, QUAY_E, QY + 0.3, HOUSE_Y0, -2.7, GZ - 0.17)                     # quay strip in front of the house and beyond
segments = []
cursor = X_W
for a, b in NOTCHES:
    segments.append((cursor, a))
    cursor = b
segments.append((cursor, HOUSE_X))
for a, b in segments:
    g.box(a, b, QY + 0.3, NOTCH_BACK, -2.7, GZ - 0.17)
for a, b in NOTCHES:                                                            # spillway floors and lips
    g.box(a, b, QY + 0.3, NOTCH_BACK, -2.7, 0.5)
    g.box(a, b, QY - 0.06, QY + 0.5, 0.2, 0.6)
for (a, b), seed in zip(((-9.75, -8.87), (-6.14, -5.5), (6.15, 6.75), (9.08, 9.72), (X_W, X_W + 0.9)), range(5)):
    A.add_stone_course(g, a, b, QY - 0.16, QY + 0.8, -2.3, GZ, block=0.55, seed=seed)
plaza_base = g.to_object("COT_Plaza_Base", C_PLAZA, mats, A.P("PlazaGround", "A", REF_MAIN, cot_note="depth and spillway notches are completion (C)"))

g = Geo()
exclude = [(-3.5, 3.5, -3.05, 3.05), (HOUSE_X, 99, HOUSE_Y0, 99), (-99, 99, VIA_Y0 + 0.2, 99)]
exclude += [(a, b, -99, NOTCH_BACK) for a, b in NOTCHES]
n_cobbles = A.add_cobbles(g, X_W, QUAY_E, QY + 0.62, VIA_Y0 + 0.2, GZ, exclude=exclude, seed=CFG["seed"] % 1000)
rand = rng(41)
g.use("cobble")
x = X_W
while x < QUAY_E:                                                                 # heavier edge course along the quay
    w = rand(0.62, 0.95)
    cx = x + w / 2
    x += w
    if any(a - 0.1 <= cx <= b + 0.1 for a, b in NOTCHES):
        continue
    g.ellipsoid((cx, QY + 0.3, GZ - 0.16), (w * 0.5, 0.42, 0.18), segs=10, steps=5, e=0.55)
n_cobbles += A.add_cobbles(g, X_W, HOUSE_X, VIA_Y1 + 0.5, VIA_Y1 + 16.0, GZ, exclude=[(-99, -22.0, 16.0, 99)],
                           size=(0.95, 0.75), seed=CFG["seed"] % 1000 + 7)       # behind the viaduct (C)
cobbles = g.to_object("COT_Plaza_Cobbles", C_PLAZA, mats, A.P("PlazaCobbles", "A", f"{REF_MAIN}; {REF_M2}", cot_count=n_cobbles))

g = Geo().use("water")
g.box(-70, 70, -126, QY + 0.3, WZ - 0.6, WZ)
water = g.to_object("COT_Plaza_Water", C_PLAZA, mats, A.P("WellWater", "A", REF_MAIN))

g = Geo()
fall_rand = rng(57)
for a, b in NOTCHES:
    g.use("waterfall")                                                          # strands of falling water with gaps
    x = a + 0.08
    while x < b - 0.08:
        rad = fall_rand(0.022, 0.06)
        reach = fall_rand(0.1, 0.24)
        g.tube([(x, QY - 0.03, 0.63), (x, QY - 0.07 - reach * 0.3, 0.45), (x + fall_rand(-0.02, 0.02), QY - 0.07 - reach * 0.8, -0.05),
                (x + fall_rand(-0.03, 0.03), QY - 0.07 - reach, WZ - 0.03)], [rad, rad, rad * 0.8, rad * 0.55], segs=5)
        if fall_rand() < 0.55:                                                  # froth where the strand meets the water
            g.ellipsoid((x, QY - 0.09 - reach, WZ + 0.02), (fall_rand(0.07, 0.14), fall_rand(0.07, 0.12), 0.05), segs=6, steps=4)
        x += rad * 2 + fall_rand(0.0, 0.11)
    g.use("puddle")
    g.box(a + 0.03, b - 0.03, QY - 0.05, NOTCH_BACK, 0.56, 0.64)
g.use("puddle")
for cx, cy, rx, ry in ((-4.7, -2.3, 2.3, 1.2), (4.9, -3.9, 2.4, 0.9), (5.9, 1.2, 1.5, 1.1), (-7.3, 0.4, 1.8, 1.4), (0.4, -4.45, 2.6, 0.55),
                       (12.8, -3.6, 2.0, 1.0), (-2.4, 5.4, 2.0, 1.3), (-14.5, -1.8, 2.2, 1.5), (8.2, 6.0, 1.6, 1.2)):
    g.revolve([(0.05, GZ - 0.2), (1.0, GZ - 0.2), (1.0, GZ - 0.072), (0.05, GZ - 0.072)], segs=24, sx=rx, sy=ry, m=place(cx, cy, 0))
wet = g.to_object("COT_Plaza_WaterSheets", C_PLAZA, mats, A.P("PlazaPuddlesAndSpillways", "A", f"{REF_MAIN}; {REF_M3}",
                                                               cot_note="puddle placement is completion (C)"))

drain = A.build_drain_ring(C_PLAZA, mats, props=A.P("DrainRing", "A", REF_MAIN))
DRAIN_X = (-1.3, 0.03, 4.13, 10.2, -11.5, 15.0)
A.place_all(drain, [place(x, QY + 0.27, 0.22) for x in DRAIN_X], C_PLAZA, "drain")
g = Geo().use("waterfall")
for x in (DRAIN_X[0], DRAIN_X[2], DRAIN_X[3]):
    g.tube([(x, QY + 0.2, 0.0), (x, QY + 0.16, WZ)], 0.05, segs=6)
g.to_object("COT_Plaza_DrainStreams", C_PLAZA, mats, A.P("DrainStreams", "A", REF_MAIN))

post = A.build_ring_post(C_PLAZA, mats, "COT_RingPost_Short", 1.0, A.P("RingPostShort", "A", REF_MAIN))
short_spots = [W(xa_, 0, y)[:2] for xa_, y in ((-10.8, 5.6), (-9.4, 6.2), (-7.0, 3.4), (-6.45, 4.0), (5.55, 4.4), (6.26, 2.4), (7.26, 4.8), (8.48, 2.2))]
A.place_all(post, [place(x, y, GZ) for x, y in short_spots], C_PLAZA, "post")
tall = A.build_ring_post(C_PLAZA, mats, "COT_RingPost_Tall", 2.9, A.P("RingPostTall", "A", f"{REF_MAIN}; {REF_L1}", cot_note="positions are completion (C)"))
A.place_all(tall, [place(x, y, -2.5, s=0.86) for x, y in ((-2.7, -10.2), (3.5, -10.8), (9.0, -9.8), (-9.2, -11.5), (14.5, -11.0), (-15.0, -9.6), (20.0, -10.4))],
            C_PLAZA, "post")

# --------------------------------------------------------------------------- lamps, signs
lamp = A.build_lamp(C_KIT, mats, props=A.P("LampDouble", "A", f"{REF_M1}; {REF_L1}; {REF_MAIN}"))
LAMPS = [(-4.65, 0.0), (4.65, 0.0)]
A.place_all(lamp, [place(x, y, GZ) for x, y in LAMPS], C_KIT, "lamp")
sign_o = A.build_sign_oval(C_KIT, mats, props=A.P("SignOval", "A", f"{REF_MAIN}; {REF_L1}"))
A.place_all(sign_o, [place(WX(-4.87, 1.6), 1.6, GZ), place(10.05, -2.0, GZ, s=0.6)], C_KIT, "sign")
sign_s = A.build_sign_spear(C_KIT, mats, props=A.P("SignSpear", "A", f"{REF_MAIN}; {REF_M2}"))
A.place_all(sign_s, [place(WX(3.81, -4.2), -4.2, GZ)], C_KIT, "sign")

# --------------------------------------------------------------------------- iron scaffolds
# West scaffold, read again from the main reference in round 4. A middle bay of full arches (apex 6.0 / 11.7 / 17.4
# above the play plane), a return bay running back from its right post whose arches show half a tier higher and
# fall away to the right, and one half arch rising to its left post. Only the front plane carries arches: the
# reference shows one clean band per tier, the doubled back-plane arches of rounds 1-3 are gone.
SC_Y0, SC_Y1 = 1.0, 5.9
A.build_scaffold(C_KIT, mats, "COT_Scaffold_West",
                 posts=[(-12.26, SC_Y0, GZ - 0.1, 31.0), (-8.3, SC_Y0, GZ - 0.1, 31.0), (-8.3, SC_Y1, GZ - 0.1, 28.5), (-14.27, SC_Y0, 6.0, 14.2)],
                 bays=[(-12.26, SC_Y0, -8.3, SC_Y0, [5.33, 11.15, 16.99, 22.8, 28.6], None, None, None),
                       (-8.3, SC_Y0, -8.3, SC_Y1, [8.15, 13.85, 19.5, 25.2], None, None, 0.5),
                       (-14.27, SC_Y0, -12.26, SC_Y0, [13.2], "L", 0.87, 0.5)],
                 props=A.P("ScaffoldWest", "A", REF_MAIN, cot_note="the return bay depth and the tiers above the image are completion (C)"))
# East scaffold beside the house: a wide bay of full arches and, on its left post, half arches rising to the post.
SB_Y = -2.6
A.build_scaffold(C_KIT, mats, "COT_Scaffold_East",
                 posts=[(x, SB_Y, GZ - 0.1, 30.0) for x in (9.56, 11.24, 14.53)],
                 bays=[(9.56, SB_Y, 11.24, SB_Y, [10.1, 15.2, 23.0], "L", 1.05, 0.34),
                       (11.24, SB_Y, 14.53, SB_Y, [18.8, 27.0], None, 1.3, 0.42)],
                 props=A.P("ScaffoldEast", "A", f"{REF_MAIN}; {REF_UR}", cot_note="standing plane is completion (C)"))

# --------------------------------------------------------------------------- shell mounds and the fountain screen
g = Geo()
# Two kinds, as drawn in the main reference: low loaves whose segments lie along their length (left of the
# fountain and in front on the right) and tall beehive domes ringed by bands (behind the right lamp, the big one
# further right, one behind the fountain). Sizes and tops re-measured in round 4.
LOAVES = [  # x, y, half length, half width, height, rotation, lobes, slant
    (-11.18, 6.8, 2.62, 1.5, 2.48, 0.1, 4, 0.3), (7.02, 3.0, 1.46, 1.15, 1.6, -0.15, 4, 0.3),
    (-6.6, 10.0, 1.8, 1.3, 2.2, 0.4, 3, 0.25), (-15.4, 9.3, 1.7, 1.3, 1.9, -0.5, 3, 0.25)]
DOMES = [  # x, y, half width X, half width Y, height, bands, tilt, turn
    (2.64, 6.6, 1.9, 1.6, 3.96, 4, 0.06, 0.4), (7.29, 8.6, 1.7, 1.6, 5.45, 5, 0.1, 3.14), (-4.13, 6.6, 2.1, 1.6, 3.37, 4, 0.06, 2.6),
    (10.09, -3.4, 0.75, 0.75, 2.05, 3, 0.05, 0.3)]
for mx, my, rx, ry, rz, rot, lobes, slant in LOAVES:
    A.add_shell_mound(g, place(mx, my, GZ - 0.05, rz=rot), rx, ry, rz, lobes, slant=slant)
for mx, my, rx, ry, h, bands, tilt, turn in DOMES:
    A.add_shell_dome(g, place(mx, my, GZ - 0.05, rz=turn), rx, ry, h, bands=bands, tilt=tilt)
g.to_object("COT_ShellMounds", C_BACK, mats, A.P("ShellMounds", "A", f"{REF_MAIN}; {REF_M3}", cot_note="the last two loaves and all depths are completion (C)"))

screen = A.build_fountain_screen(C_BACK, mats, props=A.P("FountainScreen", "B", f"{REF_MAIN}; {REF_UR}; {REF_M2}; {REF_VID}",
                                                         cot_note="separate object behind the statue by cross-image parallax; depth is completion (C)"))
for o in screen:
    o.matrix_world = place(0.4, 9.1, GZ, s=0.97)

# --------------------------------------------------------------------------- viaduct with railing
CENTRES = [6.26 - 4.57 * k for k in range(6, -1, -1)]
A.build_viaduct(C_BACK, mats, "COT_Viaduct", -23.4, HOUSE_X, VIA_Y0, VIA_Y1, GZ - 0.3, 9.94, CENTRES, arch_w=2.4, spring=7.96,
                props=A.P("BackViaduct", "B", f"{REF_MAIN}; {REF_VID}", cot_note="deck level tied to the terrace level; depth is completion (C)"))
bay = A.railing_bay_curves().to_object("COT_Railing_Bay", C_BACK, mats("iron"), bevel=0.02,
                                       props=A.P("RailingOrnate", "A", f"{REF_M1}; {REF_MAIN}"))
rail_m = []
n_bays = int((HOUSE_X + 23.4) / 1.05)
for yy in (VIA_Y0 - 0.25, VIA_Y1 + 0.25):
    for i in range(n_bays):
        rail_m.append(place(-23.4 + 1.05 * i, yy, 9.94))
A.place_all([bay], rail_m, C_BACK, "rail")

# --------------------------------------------------------------------------- house on the east side
HP = A.P("PlazaEastHouse", "A", f"{REF_MAIN}; {REF_UR}", cot_note="south and north faces, interior walls and all depths are completion (C)")
TER_Z = 9.94
g = Geo().use("house_wall")
g.box(HOUSE_X, X_E, HOUSE_Y0, HOUSE_Y1, -2.7, TER_Z - 0.6)                        # lower body
g.box(14.2, X_E, HOUSE_Y0, HOUSE_Y1, TER_Z, WZ_(14.6, HOUSE_Y0))                # upper body behind the loggia
g.use("stone")
g.box(HOUSE_X, X_E, HOUSE_Y0 - 0.25, HOUSE_Y1, TER_Z - 0.6, TER_Z)               # terrace / loggia floor
g.box(8.73, HOUSE_X, HOUSE_Y0 - 0.25, 1.8, TER_Z - 0.6, TER_Z)                  # cantilevered tip
g.box(8.9, HOUSE_X, HOUSE_Y0, 1.8, 5.37, 5.97)                                  # mid ledge under the glass pillar
for z in (TER_Z - 0.08, TER_Z - 0.52):
    g.tube([(8.7, HOUSE_Y0 - 0.27, z), (X_E, HOUSE_Y0 - 0.27, z)], 0.09, segs=6)
    g.tube([(8.7, HOUSE_Y0 - 0.27, z), (8.7, 1.82, z), (HOUSE_X, 1.82, z)], 0.09, segs=6)
g.tube([(8.87, HOUSE_Y0 - 0.02, 5.9), (8.87, 1.82, 5.9)], 0.09, segs=6)
g.tube([(8.87, HOUSE_Y0 - 0.02, 5.42), (8.87, 1.82, 5.42)], 0.08, segs=6)
# feathered corbels: one under the terrace tip, one under the mid ledge, one under the roof tip (A: main reference)
A.add_corbel_wing(g, place(8.95, HOUSE_Y0 + 0.2, TER_Z - 0.62, rz=math.pi), length=1.25, blades=4, key="louvre_frame")
A.add_corbel_wing(g, place(9.1, HOUSE_Y0 + 0.2, 5.35, rz=math.pi), length=1.1, blades=4, key="louvre_frame")
A.add_corbel_wing(g, place(11.5, HOUSE_Y0 - 0.1, WZ_(14.6, HOUSE_Y0) - 0.1, rz=math.pi), length=1.3, blades=4, key="louvre_frame")
# column with a round arch to the wall at the east end of the terrace fence (A: main reference)
for cy in (1.9,):
    g.use("stone")
    g.revolve([(0.26, TER_Z), (0.22, TER_Z + 0.2), (0.15, TER_Z + 0.34), (0.14, 12.2), (0.24, 12.4), (0.28, 12.6), (0.2, 12.66)], segs=14,
              m=place(13.85, cy, 0))
    arc = [(13.85 + 0.5 - 0.5 * math.cos(math.pi * k / 12), cy, 12.66 + 0.6 * math.sin(math.pi * k / 12)) for k in range(7)]
    g.tube(arc, 0.15, 0.2, segs=8, ref=(0, 1, 0))
    g.box(13.85 - 0.2, 14.2, cy - 0.2, cy + 0.2, 13.2, WZ_(14.6, HOUSE_Y0))
# herringbone shaft panel and a baluster urn on the dark south wall of the upper body
g.use("stone")
for k in range(9):
    z = TER_Z + 0.3 + 0.48 * k
    for sx, x0 in ((1, 14.65), (-1, 16.45)):
        g.box(-0.5, 0.5, -0.05, 0.05, -0.09, 0.09, m=place(15.1 if sx > 0 else 16.0, HOUSE_Y0 - 0.04, z, ry=-sx * 0.5))
g.revolve([(0.3, TER_Z), (0.34, TER_Z + 0.15), (0.16, TER_Z + 0.4), (0.3, TER_Z + 0.85), (0.34, TER_Z + 1.2), (0.14, TER_Z + 1.55), (0.2, TER_Z + 1.7)],
          segs=14, m=place(17.3, HOUSE_Y0 + 0.6, 0))
# south and west facade relief of the lower house body (completion C; the reference shows this area masked black)
g.use("stone_dark")
PIL = [12.4, 16.1, 19.8, 23.5]
for px in PIL + [HOUSE_X + 0.3, X_E - 0.3]:
    g.box(px - 0.3, px + 0.3, HOUSE_Y0 - 0.22, HOUSE_Y0, -2.7, TER_Z - 0.6)
g.tube([(HOUSE_X, HOUSE_Y0 - 0.12, 5.6), (X_E, HOUSE_Y0 - 0.12, 5.6)], 0.14, segs=6)
g.tube([(HOUSE_X, HOUSE_Y0 - 0.12, 1.6), (X_E, HOUSE_Y0 - 0.12, 1.6)], 0.12, segs=6)
gw_f, gw_g = Geo(), Geo()
bays = list(zip([HOUSE_X + 0.3] + PIL, PIL + [X_E - 0.3]))
for bi, (xa_, xb_) in enumerate(bays):
    cxb = (xa_ + xb_) / 2
    hwb = (xb_ - xa_) / 2 - 0.55
    for zb_, zs_ in ((1.9, 3.9), (6.0, 7.7)):
        pts = [(cxb - hwb, HOUSE_Y0 - 0.08, zb_), (cxb - hwb, HOUSE_Y0 - 0.08, zs_)]
        pts += [(cxb - hwb * math.cos(math.pi * k / 10) ** 1.0, HOUSE_Y0 - 0.08, zs_ + hwb * 1.15 * math.sin(math.pi * k / 10) ** 0.8) for k in range(1, 10)]
        pts += [(cxb + hwb, HOUSE_Y0 - 0.08, zs_), (cxb + hwb, HOUSE_Y0 - 0.08, zb_)]
        g.tube(pts, 0.1, segs=6, ref=(0, 1, 0))
    A.add_leaf_window(gw_f, gw_g, place(cxb, HOUSE_Y0 - 0.05, 7.2), 0.9, 2.3, index=40 + bi, bulge=0.1, ribs=3, glass_key="glass_room")
for wy in (4.5, 9.0):
    g.box(HOUSE_X - 0.22, HOUSE_X, wy - 0.3, wy + 0.3, -2.7, TER_Z - 0.6)
    A.add_leaf_window(gw_f, gw_g, place(HOUSE_X - 0.05, wy + 2.2, 7.2, rz=-math.pi / 2), 0.9, 2.3, index=50 + int(wy), bulge=0.1, ribs=3, glass_key="glass_room")
gw_f.to_object("COT_House_RoomWindowFrames", C_HOUSE, mats, HP)
gw_g.to_object("COT_House_RoomWindowGlass", C_HOUSE, mats, HP)
A.add_curtain(g, 11.5, 14.1, HOUSE_Y0 - 0.1, WZ_(14.6, HOUSE_Y0) - 0.24, 2.4, seed=3)
A.add_curtain(g, HOUSE_Y0, 2.6, 11.45, WZ_(14.6, HOUSE_Y0) - 0.24, 2.0, seed=4, axis="Y")
A.add_curtain(g, 10.45, 12.2, HOUSE_Y0 - 0.12, TER_Z - 0.6, 1.3, seed=6)
house = g.to_object("COT_House_Body", C_HOUSE, mats, HP, smooth_angle=35)
A.build_glass_pillar(C_HOUSE, mats, "COT_House_GlassPillar", 0.78, 5.97, TER_Z - 0.6, A.P("GlassPillar", "A", REF_MAIN))[0].matrix_world = place(9.62, 0.1, 0)
ROOF_ZB, ROOF_ZT, ROOF_X0 = WZ_(14.6, HOUSE_Y0), WZ_(17.76, HOUSE_Y0), WX(11.45, HOUSE_Y0)
# The roof has a shallow porch bay over the terrace (the reference shows open air and glow behind the terrace
# fence) and a main part that starts at the upper body, so the west walkway behind the porch is open to the sky.
PORCH_Y1 = 2.6
A.build_louvre_roof(C_HOUSE, mats, "COT_House_LouvreRoof", ROOF_X0, X_E, ROOF_ZB, ROOF_ZT, HOUSE_Y0, PORCH_Y1, bays=3, curve_end="W",
                    props=A.P("LouvreRoof", "A", f"{REF_UR}; {REF_MAIN}", cot_note="porch depth is completion (C)"))
A.build_louvre_roof(C_HOUSE, mats, "COT_House_LouvreRoof_Main", 14.2, X_E, ROOF_ZB, ROOF_ZT, PORCH_Y1 + 0.2, HOUSE_Y1, bays=3, curve_end="W",
                    props=A.P("LouvreRoof", "C", f"{REF_UR}; {REF_MAIN}", cot_note="main roof behind the porch bay is completion (C)"))
fence = A.fence_web_curves(1.675).to_object("COT_Fence_Web", C_HOUSE, mats("iron_scaffold"), bevel=0.026, props=A.P("FenceWeb", "A", f"{REF_L1}; {REF_M3}; {REF_MAIN}"))
A.place_all([fence], [place(10.28, 1.7, TER_Z), place(11.955, 1.7, TER_Z)], C_HOUSE, "fence")
# iron arch standing over the terrace fence (A: main reference, above the fence behind the character)
ic = IronCurves()
g = Geo()
for x in (10.28, 13.63):
    ic.add([(x, 1.7, TER_Z), (x, 1.7, TER_Z + 1.75)], r=1.6, smooth=False)
A.add_truss(ic, g, 13.63 - 10.28, place(10.28, 1.7, TER_Z + 1.75), rise=1.55, depth=0.3)
A.add_truss(ic, g, 13.63 - 10.28 - 0.9, place(10.73, 1.7, TER_Z + 1.3), rise=1.0, depth=0.22, spikes=False)
TAP = A.P("TerraceArch", "A", REF_MAIN, cot_note="standing plane is completion (C)")
ic.to_object("COT_Terrace_IronArch", C_HOUSE, mats("iron_scaffold"), bevel=0.028, props=TAP)
g.to_object("COT_Terrace_IronArch_Plates", C_HOUSE, mats, TAP)
spear = A.build_spear_post(C_HOUSE, mats, props=A.P("SpearPost", "A", f"{REF_MAIN}; {REF_L1}"))
A.place_all(spear, [place(9.15, 1.45, TER_Z), place(9.75, 1.5, TER_Z, s=0.85)], C_HOUSE, "spear")
g = Geo().use("sign")
ic = IronCurves()
for hx, hz in ((10.9, 13.9), (11.18, 13.72)):
    rows, uvs = [], []
    for i in range(9):
        t = i / 8
        rr = max(0.01, 0.11 * math.sin(math.pi * t) ** 0.5)
        rows.append([(hx + rr * math.cos(TAU * k / 8), HOUSE_Y0 - 0.3 + 0.05 * math.sin(TAU * k / 8), hz - 0.42 + 0.84 * t) for k in range(8)])
        uvs.append([(0.5 + 0.5 * math.cos(TAU * k / 8), t) for k in range(8)])
    g.grid(rows, close_u=True, cap_start=True, cap_end=True, uvs=uvs)
    ic.add([(hx, HOUSE_Y0 - 0.3, hz + 0.42), (hx, HOUSE_Y0 - 0.3, 14.5)], r=0.6, smooth=False)
ic.add([(11.5, HOUSE_Y0 - 0.3, 14.5), (11.0, HOUSE_Y0 - 0.3, 14.56), (10.7, HOUSE_Y0 - 0.3, 14.5), (10.6, HOUSE_Y0 - 0.3, 14.36)], r=1.0, taper="end")
g.to_object("COT_House_HangingSigns", C_HOUSE, mats, A.P("HangingSigns", "A", REF_MAIN))
ic.to_object("COT_House_HangingSigns_Iron", C_HOUSE, mats("iron"), bevel=0.022, props=A.P("HangingSigns", "A", REF_MAIN))

# --------------------------------------------------------------------------- west gallery end (CentralBlock)
GP = A.P("WestGalleryEnd", "B", REF_MAIN, cot_note="stage 1 ground gallery replaced by an open bay; depth is completion (C)")
g = Geo().use("stone_far")
g.box(-69.3, -19.0, -4.0, 6.0, -0.4, 6.0)
g.use("stone")
GAL_ZB, GAL_ZT = WZ_(za(760), HOUSE_Y0), WZ_(za(650), HOUSE_Y0)
g.box(-19.0, -11.7, HOUSE_Y0, 3.0, GAL_ZB - 0.45, GAL_ZB)
A.add_stone_course(g, -12.6, -11.7, -1.35, -0.35, GZ - 0.1, GAL_ZB - 0.45, block=0.9, seed=21)
A.add_stone_course(g, -16.2, -15.3, -1.35, -0.35, GZ - 0.1, GAL_ZB - 0.45, block=0.9, seed=23)
A.add_stone_course(g, -16.2, -15.3, 1.9, 2.9, GZ - 0.1, GAL_ZB - 0.45, block=0.9, seed=24)
A.add_corbel_wing(g, place(-11.75, -0.85, GAL_ZB - 0.5), length=1.0, blades=4, key="stone")
g.to_object("COT_WestGallery_Bay", C_HOUSE, mats, GP, smooth_angle=35)
A.build_louvre_roof(C_HOUSE, mats, "COT_WestGallery_LouvreRoof", -19.0, -11.9, GAL_ZB, GAL_ZT, HOUSE_Y0, 0.4, bays=2, curve_end="E",
                    props=A.P("LouvreRoofWest", "A", REF_MAIN, cot_note="only the tip is visible in the reference"))
g = Geo().use("sign")
rows, uvs = [], []
for k in range(7):
    a = -math.pi / 2 + math.pi * k / 6
    s = max(0.04, math.cos(a))
    rows.append([(-11.0 + 0.3 * s * math.cos(TAU * i / 20), -1.0 + 0.05 * math.sin(a), 6.05 + 0.38 * s * math.sin(TAU * i / 20)) for i in range(20)])
    uvs.append([(0.5 + 0.5 * s * math.cos(TAU * i / 20), 0.5 + 0.5 * s * math.sin(TAU * i / 20)) for i in range(20)])
g.grid(rows, close_u=True, cap_start=True, cap_end=True, uvs=uvs)
g.to_object("COT_WestGallery_Sign", C_HOUSE, mats, A.P("SignHanging", "A", REF_MAIN))
ic = IronCurves()
ic.add([(-11.0 + 0.32 * math.cos(TAU * i / 20), -1.0, 6.05 + 0.4 * math.sin(TAU * i / 20)) for i in range(20)], r=1.2, cyclic=True)
ic.add([(-11.9, -1.0, 7.0), (-11.4, -1.0, 7.05), (-11.05, -1.0, 6.9), (-11.0, -1.0, 6.46)], r=1.1)
ic.spike(-11.0, 5.65, 5.2, r=1.2, y=-1.0)
ic.to_object("COT_WestGallery_Sign_Iron", C_HOUSE, mats("iron"), bevel=0.024, props=A.P("SignHanging", "A", REF_MAIN))

# --------------------------------------------------------------------------- towers (three depth layers behind the viaduct)
def tower_windows(cx, cy, r, front_y, listed, w_app, h_app, extra_seed, extra=6, z_range=(8.0, 50.0)):
    """Windows seen in the reference (apparent x, z) plus completion windows around the back."""
    s = (front_y - CAM["y"]) / (0.0 - CAM["y"])
    out = []
    for x_app, z_app in listed:
        wx, _, wz = W(x_app, z_app, front_y)
        dx = max(-0.96, min(0.96, (wx - cx) / (r * A.WINDOW_R + 0.06)))
        out.append((math.asin(dx), wz, w_app * s, h_app * s))
    rand = rng(extra_seed)
    for i in range(extra):
        out.append((rand(1.7, 4.6), rand(*z_range), w_app * s, h_app * s))
    return out


TA = dict(cx=-16.0, cy=46.9, r=4.9, front=42.0)
A.build_tower(C_BACK, mats, "COT_BackTower_A", TA["cx"], TA["cy"], -2.0, 58.0, TA["r"], 9.0,
              tower_windows(TA["cx"], TA["cy"], TA["r"], TA["front"],
                            [(xa(490), za(175)), (xa(430), za(280)), (xa(535), za(440)), (xa(440), za(480)), (xa(515), za(630))], 1.36, 3.4, 5),
              roof="dome", seed=3, props=A.P("BackTowerA", "A", REF_MAIN, cot_note="depth, back half and height above the image are completion (C)"))
TB = dict(cx=-1.3, cy=55.9, r=7.9, front=48.0)
A.build_tower(C_BACK, mats, "COT_BackTower_B", TB["cx"], TB["cy"], -2.0, 47.0, TB["r"], 9.5,
              tower_windows(TB["cx"], TB["cy"], TB["r"], TB["front"],
                            [(xa(710), za(290)), (xa(890), za(325)), (xa(738), za(520)), (xa(895), za(610))], 1.5, 3.85, 6, z_range=(10.0, 40.0)),
              roof="dome", seed=5, props=A.P("BackTowerB", "A", REF_MAIN, cot_note="depth and back half are completion (C)"))
TC = dict(cx=14.6, cy=87.0, r=7.0, front=80.0)
A.build_tower(C_BACK, mats, "COT_FarTower_C", TC["cx"], TC["cy"], -2.0, 72.0, TC["r"], 10.0,
              tower_windows(TC["cx"], TC["cy"], TC["r"], TC["front"],
                            [(xa(1020), za(400)), (xa(1160), za(270)), (xa(1105), za(470)), (xa(1020), za(510)), (xa(1100), za(575)), (xa(1150), za(150))],
                            0.9, 1.6, 7, extra=5, z_range=(12.0, 64.0)),
              roof="dome", seed=7, glass_key="glass_far", fringe_key="tower_far", core_key="tower_core",
              props=A.P("FarTowerC", "A", REF_MAIN, cot_note="blurred pink panes in the reference; depth is completion (C)"))
for name, cx, cy, r, z1, seed in (("COT_FarTower_E", -34.0, 78.0, 9.0, 78.0, 11), ("COT_FarTower_F", 3.0, 92.0, 8.0, 64.0, 13)):
    rand = rng(seed)
    wins = [(rand(-1.2, 1.2), rand(10.0, z1 - 8.0), 3.4, 7.6) for _ in range(9)]
    A.build_tower(C_BACK, mats, name, cx, cy, -2.0, z1, r, 10.0, wins, roof="dome", seed=seed, glass_key="glass_far_blue", fringe_key="tower_far",
                  core_key="tower_core", props=A.P(name[4:], "C", "15_Background/Background_03.jpg", cot_note="far layer completion (C)"))
# free-standing tower on the left of the plaza: only its right flank and two panes show in the reference
FT = dict(cx=-29.9, cy=25.5, r=7.5)
A.build_tower(C_BACK, mats, "COT_FreeTower", FT["cx"], FT["cy"], -2.0, 62.0, FT["r"], 9.0,
              [(0.895, 31.2, 1.9, 5.4), (1.15, 29.4, 1.9, 5.4), (0.2, 42.0, 3.6, 9.0), (1.0, 50.0, 3.6, 9.0), (-0.7, 33.0, 3.6, 9.0),
               (2.4, 38.0, 3.6, 9.0), (3.6, 27.0, 3.6, 9.0), (4.6, 44.0, 3.6, 9.0)],
              roof="umbrella", seed=17, fringe_key="fringe_dim", taper=lambda z: 0.62 + 0.38 * smoothstep((z - 2.0) / 16.0),
              props=A.P("FreeTower", "B", REF_MAIN, cot_note="position corrected from the main reference (stage 1 had X -13.8); most of it is completion (C)"))
# Jointed limb of the free tower (A: top left of the main reference, re-read in round 4). A stout rib comes in from
# the left edge, ends in a claw of stacked blades, a segmented spine climbs from the claw between the two panes,
# and a thin whip sweeps from the top of the spine to the upper right. Rounds 1-3 had one thick diagonal beam here.
g = Geo().use("louvre_frame")
RIB_Y = 16.5                                                     # in front of the tower's fringe, so the limb shows from the image edge
pts = catmull([W(-16.6, 13.2, RIB_Y + 3.0), W(-15.3, 14.2, RIB_Y + 1.2), W(-14.2, 14.94, RIB_Y), W(-13.3, 15.56, RIB_Y), W(-12.4, 15.9, RIB_Y),
               W(-11.6, 16.2, RIB_Y)], per=6)
g.tube(pts, resample([0.3, 0.27, 0.23, 0.2, 0.18, 0.16], len(pts)), segs=10)
for k in range(6):                                               # claw: blades stacked like a rib cage
    cxa, cza = -11.45 + 0.05 * k, 16.25 + 0.2 * k
    ln = 1.7 - 0.16 * k

    def centre(u, cza=cza, ln=ln):
        return (-0.55 * ln + ln * u, 0.22 * math.sin(math.pi * u) - 0.1 * u)

    g.lens(centre, lambda u: 0.34 * math.sin(math.pi * u ** 0.8) ** 0.7, lambda u: 0.12, nu=10, nv=8,
           m=Matrix.Translation(W(cxa, cza, RIB_Y)) @ Matrix.Scale((RIB_Y - CAM["y"]) / -CAM["y"], 4), cup=0.12)
spine = catmull([W(-11.25, 17.3, RIB_Y), W(-11.15, 18.3, RIB_Y), W(-11.0, 19.4, RIB_Y), W(-10.9, 20.4, RIB_Y)], per=5)
for i, p in enumerate(spine):
    f = i / (len(spine) - 1)
    g.ellipsoid(p, (lerp(0.36, 0.2, f), lerp(0.36, 0.2, f), 0.19), segs=10, steps=6)
pts = catmull([W(-10.9, 20.5, RIB_Y), W(-9.75, 21.67, RIB_Y), W(-8.33, 22.17, RIB_Y), W(-7.09, 22.47, RIB_Y)], per=7)
g.tube(pts, resample([0.17, 0.15, 0.13, 0.11], len(pts)), segs=8)
for k in range(3):                                               # ringed tip of the whip
    g.ellipsoid(W(-7.0 + 0.16 * k, 22.48 + 0.02 * k, RIB_Y), (0.2 - 0.03 * k, 0.2 - 0.03 * k, 0.2 - 0.03 * k), segs=8, steps=5)
g.to_object("COT_FreeTower_Ribs", C_BACK, mats, A.P("FreeTowerRibs", "A", REF_MAIN, cot_note="anchoring and the part left of the image edge are completion (C)"))
A.build_tower(C_BACK, mats, "COT_EastTower", 20.9, 9.0, 17.0, 45.0, 4.3, 7.0,
              [(0.27, 21.4, 2.5, 6.2), (0.9, 31.0, 2.5, 6.2), (-0.6, 38.0, 2.5, 6.2), (-1.5, 29.0, 2.5, 6.2),
               (2.6, 25.0, 2.5, 6.2), (3.9, 36.0, 2.5, 6.2)],
              roof="dome", seed=23, props=A.P("EastTower", "B", f"{REF_MAIN}; {REF_UR}", cot_note="stands on the house; only a fringe and one pane show"))

# viewer-side towers of the well (seen when the camera turns round): detailed stand-ins for the stage 1 volumes
for name, cx, cy, r, z1, seed in (("COT_FrontTower_A", -21.6, -92.0, 10.3, 65.0, 31), ("COT_FrontTower_B", 6.6, -108.0, 10.0, 82.0, 33),
                                  ("COT_FrontTower_C", 25.6, -100.0, 7.6, 118.0, 35)):
    rand = rng(seed)
    wins = [(rand(2.1, 4.2), rand(8.0, z1 - 8.0), 3.4, 7.8) for _ in range(9)] + [(rand(-1.0, 1.0), rand(10.0, z1 - 8.0), 3.4, 7.8) for _ in range(4)]
    A.build_tower(C_BACK, mats, name, cx, cy, -2.0, z1, r, 10.0, wins, roof="dome", seed=seed, glass_key="glass_far_blue", fringe_key="tower_far",
                  core_key="tower_core", props=A.P(name[4:], "C", "stage 1 FOREGROUND layer", cot_note="viewer-side completion (C)"))

# --------------------------------------------------------------------------- lights
LP = A.P("Lighting", "A", f"{REF_L1}; {REF_MAIN}")
for i, (lx, ly) in enumerate(LAMPS):
    for j, (gx, gy, gz) in enumerate(A.LAMP_GLOBES):
        L.add_light(C_LIGHTS, f"COT_Light_Lamp{i}{j}", "POINT", (lx + gx, ly + gy, GZ + gz), (0.74, 0.84, 1.0), LK["lamp_power"], radius=0.2, props=LP)
L.add_light(C_LIGHTS, "COT_Light_WellTop", "AREA", (0.0, 12.0, 58.0), (0.20, 0.42, 1.0), LK["well_top"], size=46.0, rotation=(0.0, 0.0, 0.0), props=LP)
L.add_light(C_LIGHTS, "COT_Light_BackGlow", "POINT", (5.8, 38.0, 19.3), (0.25, 0.58, 1.0), LK["back_glow"], radius=6.0, props=LP)
if LK["back_glow_low"] > 0:
    L.add_light(C_LIGHTS, "COT_Light_BackGlowLow", "POINT", (-6.0, 27.0, 14.0), (0.30, 0.52, 1.0), LK["back_glow_low"], radius=4.0, props=LP)
fill = L.add_light(C_LIGHTS, "COT_Light_FrontFill", "AREA", (3.0, -30.0, 15.0), (0.24, 0.38, 0.92), LK["front_fill"], size=26.0, props=LP)
fill.rotation_euler = (Vector((0.0, 0.0, 4.5)) - fill.location).to_track_quat("-Z", "Y").to_euler()
key = L.add_light(C_LIGHTS, "COT_Light_StatueKey", "SPOT", (-9.5, -15.0, 13.5), (0.42, 0.62, 1.0), LK["statue_key"], radius=1.2, props=LP, spot=(math.radians(34), 0.6))
key.rotation_euler = (Vector((0.0, 0.0, 5.2)) - key.location).to_track_quat("-Z", "Y").to_euler()
pfill = L.add_light(C_LIGHTS, "COT_Light_PlazaFill", "SPOT", (2.0, -14.0, 17.0), (0.35, 0.50, 1.0), LK["plaza_fill"], radius=2.5, props=LP, spot=(math.radians(50), 0.8))
pfill.rotation_euler = (Vector((0.0, 1.0, 3.0)) - pfill.location).to_track_quat("-Z", "Y").to_euler()
wash = L.add_light(C_LIGHTS, "COT_Light_ViaductWash", "SPOT", (0.4, 3.6, 15.5), (0.30, 0.55, 1.0), LK["viaduct_wash"], radius=1.5, props=LP,
                   spot=(math.radians(80), 0.8))        # lights the wall behind the fountain so the figures read as silhouettes
wash.rotation_euler = (Vector((0.4, 12.0, 6.6)) - wash.location).to_track_quat("-Z", "Y").to_euler()
rim = L.add_light(C_LIGHTS, "COT_Light_StatueRim", "SPOT", (-3.2, 7.2, 13.5), (0.45, 0.68, 1.0), LK["statue_rim"], radius=0.8, props=LP,
                  spot=(math.radians(30), 0.6))
rim.rotation_euler = (Vector((0.0, 0.0, GZ + 6.9)) - rim.location).to_track_quat("-Z", "Y").to_euler()
L.add_light(C_LIGHTS, "COT_Light_ScreenPane", "POINT", (0.4, 8.6, GZ + 6.4), (0.62, 0.84, 1.0), LK["screen_pane"], radius=0.9, props=LP)
L.add_light(C_LIGHTS, "COT_Light_TerraceBack", "POINT", (11.6, 4.6, 12.0), (0.36, 0.60, 1.0), LK["terrace_back"], radius=0.8, props=LP)
L.add_light(C_LIGHTS, "COT_Light_GlassPillar", "POINT", (8.55, -0.9, 7.6), (0.74, 0.88, 1.0), LK["glass_pillar"], radius=0.5, props=LP)

# --------------------------------------------------------------------------- weather
WP = A.P("Weather", "A", REF_VID)
COVERED = [(ROOF_X0, X_E + 2.0, HOUSE_Y0 - 0.4, PORCH_Y1 + 0.4), (14.2, X_E + 2.0, PORCH_Y1, HOUSE_Y1 + 0.4),   # under the two roofs
           (8.7, 14.2, HOUSE_Y0 - 0.3, HOUSE_Y1),                 # terrace tip and west walkway: streaks would pass through the slab
           (-69.3, -11.7, -4.0, 6.0), (-23.4, HOUSE_X, VIA_Y0 - 0.4, VIA_Y1 + 0.4)]
rain = CFG["rain"]
L.build_rain(C_WEATHER, WP, [
    dict(x0=-22, x1=34, y0=-27, y1=-9, tracks=rain["tracks"]["near"], radius=0.006, len=(8.0, 26.0), fill=0.55),
    dict(x0=-34, x1=40, y0=-9, y1=12, tracks=rain["tracks"]["mid"], radius=0.012, len=rain["streak_length_units"], fill=0.6),
    dict(x0=-50, x1=56, y0=16, y1=58, tracks=rain["tracks"]["far"], radius=0.026, len=(14.0, 44.0), fill=0.6),
], covered=COVERED, seed=CFG["seed"] % 997, speed_per_frame=rain["speed_units_per_frame_24fps"], period=rain["period"], z_top=64.0)
L.build_fog(C_WEATHER, WP, (-120.0, -124.0, -1.5), (130.0, 99.0, 110.0), density=CFG["look"]["fog_density"])
L.build_glow_haze(C_WEATHER, WP, (6.0, 31.0, 17.0), (17.0, 16.0, 19.0), CFG["look"]["glow_haze_density"])
L.setup_world(scene)
L.setup_bloom(scene, **CFG["look"]["bloom"])

# --------------------------------------------------------------------------- cameras
def camera(name, loc, look=None, lens=35.0, ortho=None, shift=(0.0, 0.0), purpose="", rot=None):
    data = bpy.data.cameras.new(name + "_data")
    cam = bpy.data.objects.new(name, data)
    data.clip_start, data.clip_end = 0.1, 600.0
    data.sensor_width = 36.0
    if ortho:
        data.type = "ORTHO"
        data.ortho_scale = ortho
    else:
        data.lens = lens
    data.shift_x, data.shift_y = shift
    cam.location = loc
    if rot is not None:
        cam.rotation_euler = rot
    else:
        cam.rotation_euler = (Vector(look) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    cam["cot_s2"] = True
    cam["cot_asset"] = "Camera"
    cam["cot_purpose"] = purpose
    C_CAMS.objects.link(cam)
    return cam


camera("CAM_REF_Statue", (CAM["x"], CAM["y"], CAM["z"]), lens=CAM["lens"], shift=(0.0, CAM["shift_y"]), rot=(math.pi / 2, 0.0, 0.0),
       purpose="Reference match for 11_Lower_City/Lower_City_statue.jpg (level perspective camera with vertical shift)")
camera("CAM_S2_Oblique", (-18.0, -21.0, 11.5), look=(1.0, 2.0, 5.0), lens=32.0, purpose="Oblique from the front left, above the water")
camera("CAM_S2_SideWest", (-10.4, -2.2, 3.3), look=(0.0, 0.0, 5.0), lens=22.0,
       purpose="Side view from the west end of the plaza, along X (moved 1.1 in round 4: the wing of the new truss stood in the lens)")
camera("CAM_S2_Terrace", (9.3, 0.3, 11.7), look=(-2.0, 1.0, 5.4), lens=24.0, purpose="Side view from the east terrace, looking down on the fountain")
camera("CAM_S2_Back", (-6.6, 10.6, 6.2), look=(0.6, 0.0, 4.8), lens=26.0, purpose="Back view from between the screen and the viaduct")
camera("CAM_S2_Deck", (2.4, 14.4, 13.4), look=(0.2, 0.0, 5.0), lens=24.0, purpose="Back view from the viaduct deck over the fountain screen")
camera("CAM_S2_Top", (0.0, 4.0, 45.0), ortho=64.0, rot=(0.0, 0.0, 0.0), purpose="Plan view of the sample area (weather hidden)")
camera("CAM_S2_StatueClose", (6.6, -13.6, 3.2), look=(0.0, 0.0, 5.0), lens=32.0, purpose="Close three-quarter view of the fountain for 12_Materials/Materials_02.jpg")

camera("CAM_REF_Materials02", (-0.3, -36.0, 2.85), lens=133.0, rot=(math.pi / 2, 0.0, 0.0),
       purpose="Reference match for 12_Materials/Materials_02.jpg (level long-lens view of the fountain base)")
camera("CAM_REF_Closeup", (-0.44, -36.0, 5.27), lens=139.0, rot=(math.pi / 2, 0.0, 0.0),   # re-fitted in round 4 to the corrected fountain widths
       purpose="Reference match for the close-up supplied by the user (docs/reference_review/user_supplied); render at 1068x910")
film = camera("CAM_FILM_S2", (-12.5, -23.0, 2.2), look=(0, 0, 4), lens=CFG["film"]["lens"], purpose="Moving perspective camera, 240 frames at 24 fps")
target = bpy.data.objects.new("CAM_FILM_S2_Target", None)
target["cot_s2"] = True
C_CAMS.objects.link(target)
con = film.constraints.new("TRACK_TO")
con.target = target
con.track_axis = "TRACK_NEGATIVE_Z"
con.up_axis = "UP_Y"
f0, f1 = CFG["film"]["frames"]
keys = [(f0, (-12.5, -23.0, 2.2)), (f0 + (f1 - f0) * 0.34, (-4.5, -21.6, 2.9)), (f0 + (f1 - f0) * 0.68, (4.0, -20.2, 3.6)), (f1, (9.5, -19.0, 4.2))]
for frame, loc in keys:
    film.location = loc
    film.keyframe_insert("location", frame=frame)
for frame, loc in ((f0, (-1.0, 0.0, 4.7)), (f1, (0.6, 0.4, 5.4))):
    target.location = loc
    target.keyframe_insert("location", frame=frame)


def fcurves_of(obj):
    action = obj.animation_data.action
    try:
        return list(action.fcurves)
    except AttributeError:
        out = []
        for layer in action.layers:
            for strip in layer.strips:
                for bag in strip.channelbags:
                    out += list(bag.fcurves)
        return out


for obj in (film, target):
    for fc in fcurves_of(obj):
        for kp in fc.keyframe_points:
            kp.interpolation = "BEZIER"
            kp.handle_left_type = kp.handle_right_type = "AUTO_CLAMPED"
        fc.update()

# --------------------------------------------------------------------------- painted contour (inverted hulls)
OUTLINE = CFG["look"].get("outline", {"enabled": False})
outlined = {}
if OUTLINE.get("enabled"):
    C_OUTLINE = collection("COT_S2_OUTLINE", C_ROOT)
    cam_pos = Vector((CAM["x"], CAM["y"], CAM["z"]))
    for prefix, factor in OUTLINE["targets"].items():
        for obj in sorted((o for o in bpy.data.objects if o.get("cot_s2") and o.type == "MESH" and o.name.startswith(prefix)
                           and not o.name.endswith("_Outline")), key=lambda o: o.name):
            pts = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
            dist = (sum(pts, Vector()) / 8.0 - cam_pos).length
            # same apparent line weight at any depth: thickness grows with the distance from the reference camera
            thick = max(OUTLINE["min"], min(OUTLINE["max"], OUTLINE["thickness"] * dist / OUTLINE["reference_distance"])) * factor
            L.add_outline_hull(C_OUTLINE, [obj], thick / max(1e-6, obj.matrix_world.to_scale().x),
                               A.P("Outline", "A", "painted contour of the references", cot_note="inverted hull; no new form",
                                   cot_outline_thickness=round(thick, 4)))
            outlined[obj.name] = round(thick, 4)

# --------------------------------------------------------------------------- scene state and save
changed = L.redress_greybox()
scene.frame_start, scene.frame_end = f0, f1
scene.render.fps = CFG["film"]["fps"]
scene.frame_set(1)
scene.camera = bpy.data.objects["CAM_REF_Statue"]
scene["cot_stage"] = 2
scene.view_settings.view_transform = CFG["look"]["view_transform"]
scene.view_settings.look = CFG["look"]["look"]
scene.view_settings.exposure = CFG["look"]["exposure"]
scene["cot_s2_superseded"] = ",".join(sorted(superseded))
SAMPLE.parent.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=str(SAMPLE))
report = {
    "source": str(source), "saved": str(SAMPLE),
    "s2_objects": sum(1 for o in bpy.data.objects if o.get("cot_s2")),
    "s2_mesh_vertices": sum(len(o.data.vertices) for o in bpy.data.objects if o.get("cot_s2") and o.type == "MESH"),
    "s2_curve_objects": sum(1 for o in bpy.data.objects if o.get("cot_s2") and o.type == "CURVE"),
    "superseded": len(superseded), "greybox_slots_redressed": changed, "cobbles": n_cobbles,
    "manual_objects_kept": sum(1 for o in bpy.data.objects if not o.get("cot_s2") and not o.get("cot_generated")),
    "outlined": outlined,
}
if "--checkpoint" in argv:
    ckpt = ROOT / PROJECT["checkpoint_dir"]
    existing = sorted(ckpt.glob("plaza_sample_v*.blend"))
    version = (int(existing[-1].stem.split("_v")[-1]) + 1) if existing else 1
    target_file = ckpt / f"plaza_sample_v{version:03d}.blend"
    shutil.copy2(SAMPLE, target_file)
    report["checkpoint"] = str(target_file)
(ROOT / "logs").mkdir(exist_ok=True)
if "--sample" not in argv:
    (ROOT / "logs" / "build_plaza_last.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print("COT_PLAZA", json.dumps(report, ensure_ascii=False))
