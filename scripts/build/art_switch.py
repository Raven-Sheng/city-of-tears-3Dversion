"""One switch for every rain / fog element of the stage 4 city.

Scene property cot_weather (1 = on, 0 = off). Drivers on every object of the weather collections (COT_S2_WEATHER,
COT_S4_WEATHER, COT_S4_FOG) set their render and viewport visibility from it, and a driver on the compositor's
depth-haze mix sets its strength, so changing the one property in the UI (Scene properties > Custom Properties) shows
the bare structure with materials and lights. (Blender 5.2 does not allow drivers on a collection's visibility, so
the drivers sit on the objects.) set_weather() sets the same values directly for background renders.
"""
import bpy

WEATHER_COLLECTIONS = ("COT_S2_WEATHER", "COT_S4_WEATHER", "COT_S4_FOG")
MIST_NODE = "COT_S4_MistMix"


def weather_objects():
    seen = []
    for name in WEATHER_COLLECTIONS:
        coll = bpy.data.collections.get(name)
        if coll is not None:
            for o in coll.all_objects:
                if o not in seen:
                    seen.append(o)
    # Imported local beam volumes may live outside the standard collections.
    for o in bpy.data.objects:
        if o.get('cot_weather') and o not in seen:seen.append(o)
    return seen


def _add_driver(id_block, path, scene, expr):
    try:
        id_block.driver_remove(path)
    except (TypeError, RuntimeError):
        pass
    try:
        fc = id_block.driver_add(path)
    except (TypeError, RuntimeError) as exc:
        return f"no driver for {id_block.name}.{path}: {exc}"
    d = fc.driver
    d.type = "SCRIPTED"
    var = d.variables.new()
    var.name = "w"
    var.type = "SINGLE_PROP"
    var.targets[0].id_type = "SCENE"
    var.targets[0].id = scene
    var.targets[0].data_path = '["cot_weather"]'
    d.expression = expr
    return None


def install(scene, mist_strength):
    """Create the switch property and its drivers. Returns a list of problems (empty when every driver was added)."""
    scene["cot_weather"] = 1
    try:
        scene.id_properties_ui("cot_weather").update(min=0, max=1, description="Stage 4: 1 shows rain, drips, ripples, volumes and depth haze; 0 hides them")
    except Exception:
        pass
    problems = []
    for o in weather_objects():
        for path in ("hide_render", "hide_viewport"):
            err = _add_driver(o, path, scene, "w < 0.5")
            if err:
                problems.append(err)
    tree = scene.compositing_node_group
    node = tree.nodes.get(MIST_NODE) if tree else None
    if node is not None:
        node["cot_strength"] = mist_strength
        err = _add_driver(tree, f'nodes["{MIST_NODE}"].inputs[0].default_value', scene, f"{mist_strength} * w")
        if err:
            problems.append(err)
    return problems


def set_weather(scene, on):
    scene["cot_weather"] = 1 if on else 0
    for o in weather_objects():
        o.hide_render = not on
        o.hide_viewport = not on
    for name in WEATHER_COLLECTIONS:                         # collections stay visible; the objects carry the switch
        coll = bpy.data.collections.get(name)
        if coll is not None:
            coll.hide_render = False
    tree = scene.compositing_node_group
    node = tree.nodes.get(MIST_NODE) if tree else None
    if node is not None:
        node.inputs[0].default_value = float(node.get("cot_strength", 0.5)) if on else 0.0
    bpy.context.view_layer.update()
