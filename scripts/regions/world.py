"""Stage 3 structure: _World - the cavern shell and the rock the districts are built into.

Everything here is level-C completion unless the layout element says otherwise: the master map shows black where
these masses stand. Each mass is an exact core (so that rooms built against it stay closed) with a rough rock skin
on the faces that can be seen; the skin never reaches beyond the layout box.
"""
import cot_kit as K
import cot_parts as P
import cot_shell as SH
from cot_geo import Geo
from cot_s3 import X, Z

R = "_World"
LAYER = {"HOSTROCK": "ROCK", "CEILING": "CEILING", "CAVESHELL": "CAVESHELL"}
A_SKIN = 0.9
# visible faces per element (default: front for host rock, front + bottom for ceilings)
FACES = {
    "GroundBase": (), "BackWall": ("front",), "FrontWall": ("back",), "Roof": ("bottom",), "FrontFloor": ("top",), "BackFloor": ("top",),
    "HostEastEnd": ("west",), "HostWestEnd": ("east",),
    "HostMidA": ("front", "west", "east", "top"), "HostMidB": ("front", "west"),
    "HostEastA": ("front", "east"), "HostEastB": ("front", "east"),
    "HostWestC": ("front", "east", "top"), "HostWestD": ("front", "east", "top"),
    "HostWestBehind": (), "HostSanctumBack": ("front", "east"),
}
# layout corrections made in stage 3 (see docs/decisions.md): world z of the underside, or an x limit
Z0 = {"HostBridgeRoofW": Z(1983) + 7.6, "HostBridgeRoofE": Z(1983) + 10.2}     # upper bridge roof re-measured 6.3 .. 9.4 above the deck
X1 = {"HostSanctumBack": -50.6}                                               # keeps clear of the sanctum's west bar and rear podium
Z1 = {"HostBridgeRoofE": Z(1802) - 0.5 - 0.3}                                 # under the floor slab of the sanctum's left wing (lowest floor, map 1802)


def world(S):
    ta, hall = S.el("WestStation", "TunnelArch"), S.el("WestStation", "Hall")
    hyc = (hall["y"][0] + hall["y"][1]) / 2                       # the station tunnel runs east from the hall's end wall (D-363)
    holes = {"HostBridgeRoofW": (X(hall["map"][2]) - 0.8, X(hall["map"][2]) + 14.0, hyc - 4.2, hyc + 4.2, Z(hall["floors"][0]) - 0.6, Z(ta["map"][1]) + 2.4)}
    holes["HostWestC"] = (X(1173) - 0.7, X(1300) + 0.7, -6.8, 8.8, Z(2230) - 1.0, Z(2203) + 0.5)       # sunken middle room of the low corridor
    for n, e in enumerate(S.layout[R]["elements"]):
        if "map" not in e:
            continue
        eid = e["id"]
        layer = LAYER.get(e.get("layer", "HOSTROCK"), "ROCK")
        x0, x1, z0, z1 = X(e["map"][0]), X(e["map"][2]), Z(e["map"][3]), Z(e["map"][1])
        y0, y1 = e["y"]
        z0 = max(z0, Z0.get(eid, z0))
        x1 = min(x1, X1.get(eid, x1))
        z1 = min(z1, Z1.get(eid, z1))
        if z1 - z0 < 0.5 or x1 - x0 < 0.5:
            continue
        faces = FACES.get(eid, ("front", "bottom") if layer == "CEILING" else ("front",))
        a = A_SKIN if min(x1 - x0, y1 - y0, z1 - z0) > 6.0 else 0.4
        box = (x0, x1, y0, y1, z0, z1)
        size = 96.0 if layer == "CAVESHELL" else 44.0
        note = "rock mass / cavern shell: completion; rough faces: " + (", ".join(faces) if faces else "none (hidden)")
        if eid in Z0 or eid in X1 or eid in Z1:
            note += "; extent adjusted in stage 3"
        P.host(S, R, eid, box, faces, e.get("ev", "C"), e.get("ref", ""), note=note, layer=layer, a=a, size=size, seed=n * 3, hole=holes.get(eid))
        if layer == "CEILING" and "bottom" in faces and eid == "HostEastTopB":
            g = Geo()
            xs = X(7060) + 1.0                                     # east of the dome hall's own cave roof
            K.stalactite_field(g, xs, x1 - 2.0, y0 + 2.0, min(y1 - 2.0, 44.0), lambda x, y, z0=z0: z0 + 0.6, max(20, int((x1 - xs) * 0.9)), seed=n, lmin=1.0, lmax=4.5)
            SH.hanging_fringe(g, xs, x1 - 0.5, y0 + 0.5, z0 + 0.4, 2.2, seed=n + 2)
            S.add(g, eid + "_Stalactites", R, "Stalactites", "C", e.get("ref", ""), layer="CEILING", smooth=50,
                  note="stalactites under the cavern roof over the east end: completion")
    # ---- overview cameras
    S.cam_front("CityElevation", R, (0, 60, 7600, 3740), y=-62.0, hide=("FRONT", "CAVESHELL", "BACKDROP"), ref="docs/reference_review/master_map_overview.jpg",
                purpose="whole city in section with the far layers hidden (the master draws them blurred), comparable with the master map", width=3840)
    S.cam_front("CityClosed", R, (0, 60, 7600, 3740), y=-62.0, hide=("CAVESHELL", "BACKDROP"), ref="docs/reference_review/master_map_overview.jpg",
                purpose="whole city with the viewer-side facades", width=3840)
    S.cam_front("CityFar", R, (0, 60, 7600, 3740), y=-62.0, hide=("FRONT", "CAVESHELL"), ref="docs/reference_review/master_map_overview.jpg",
                purpose="whole city in section including the far towers (without fog they read much stronger than on the master)", width=3840)
    for name, loc, look, lens in (("Overview_West", (-330.0, -330.0, 210.0), (-110.0, 20.0, 70.0), 30.0),
                                  ("Overview_Centre", (-20.0, -360.0, 200.0), (0.0, 20.0, 80.0), 26.0),
                                  ("Overview_East", (360.0, -330.0, 190.0), (170.0, 20.0, 50.0), 30.0),
                                  ("Overview_Back", (60.0, 400.0, 230.0), (0.0, 20.0, 80.0), 24.0),
                                  ("Overview_Top", (0.0, -40.0, 620.0), (0.0, 10.0, 0.0), 44.0)):
        S.camera(name, R, loc, look=look, lens=lens, kind="view", hide=("CAVESHELL", "CEILING", "ROCK") if "Top" in name or "Back" in name else ("CAVESHELL", "CEILING"),
                 purpose="overview of the whole structure")


REGIONS = {"_World": world}
