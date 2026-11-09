"""Task 4: populate the Old Town level (world from Task 3 + characters from Task 2) and bring it to life.

blender -b --factory-startup -P build_scene.py [-- --no-render]
Inputs : blender/world_old_town.blend, blender/characters.blend, assets/levels/old_town_layout.json
Outputs: blender/scene_old_town.blend, assets/levels/old_town_population.json, renders/scene/*.png
"""
import json
import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402

import lib_geo as G  # noqa: E402

PI = math.pi
V = Vector
LAYOUT_JSON = os.path.join(G.PROJECT, "assets", "levels", "old_town_layout.json")
POP_JSON = os.path.join(G.PROJECT, "assets", "levels", "old_town_population.json")
RENDER_DIR = os.path.join(G.PROJECT, "renders", "scene")

# day/night frames of the world timeline (see build_world.DN)
F_NIGHT_ON, F_DAY_ON = 170, 330          # night population visible in [170, 330)
FRAME_DAY, FRAME_NIGHT = 0, 250
END = 400

CHARS = {}
POP = []
FX = []
_n = {}


def from_godot(p):
    return V((p[0], -p[2], p[1]))


def yaw_facing(d):
    return math.atan2(d.x, -d.y)


def face_towards(src, dst):
    return yaw_facing((V(dst) - V(src)).normalized())


# ============================================================================= animation helpers (Blender 5 slotted actions)
def fcurves(idblock):
    ad = idblock.animation_data
    if not ad or not ad.action:
        return []
    act = ad.action
    try:
        return list(act.fcurves)
    except AttributeError:
        pass
    out = []
    slot = getattr(ad, "action_slot", None)
    for layer in act.layers:
        for strip in layer.strips:
            cb = strip.channelbag(slot) if slot else None
            if cb:
                out += list(cb.fcurves)
    return out


def set_interp(idblock, path, interp):
    for fc in fcurves(idblock):
        if fc.data_path == path:
            for k in fc.keyframe_points:
                k.interpolation = interp


def add_cycles(idblock, path=None):
    for fc in fcurves(idblock):
        if path is None or fc.data_path == path:
            if not any(m.type == "CYCLES" for m in fc.modifiers):
                fc.modifiers.new("CYCLES")


def asset_col(name):
    """Asset collection from the Task 1 libraries (appended if the world file did not keep it)."""
    c = bpy.data.collections.get(name)
    if c:
        return c
    for fname in ("props.blend", "architecture.blend"):
        with bpy.data.libraries.load(os.path.join(G.BLENDER_DIR, fname), link=False) as (src, dst):
            dst.collections = [n for n in src.collections if n == name]
        if dst.collections:
            return dst.collections[0]
    raise KeyError(name)


# ============================================================================= characters
def load_characters():
    with bpy.data.libraries.load(os.path.join(G.BLENDER_DIR, "characters.blend"), link=False) as (src, dst):
        dst.collections = list(src.collections)
    for c in dst.collections:
        CHARS[c.name] = c
    print("characters", list(CHARS))


def _group(name):
    sc = bpy.context.scene
    c = bpy.data.collections.get(name)
    if not c:
        c = bpy.data.collections.new(name)
        sc.collection.children.link(c)
    return c


def spawn(char, loc, yaw, action, schedule="day", role="", offset=None, group=None, extra=None):
    """Copy a character (shared mesh data, own pose) and give it one looping action."""
    k = _n.get(char, 0)
    _n[char] = k + 1
    pid = f"{char}#{k:02d}"
    col = _group(group or f"Pop_{schedule}")
    src = CHARS[char]
    mp = {}
    for o in src.all_objects:
        c = o.copy()
        c.name = f"{pid}:{o.name}"
        col.objects.link(c)
        mp[o] = c
    for o, c in mp.items():
        if o.parent in mp:
            c.parent = mp[o.parent]
        for m in c.modifiers:
            if m.type == "ARMATURE" and m.object in mp:
                m.object = mp[m.object]
    root = mp[src.objects[char]]
    rig = next(c for c in mp.values() if c.type == "ARMATURE")
    root.location = loc
    root.rotation_euler = (0, 0, yaw)
    # one NLA strip, repeated over the whole timeline with a random phase
    ad = rig.animation_data or rig.animation_data_create()
    for t in list(ad.nla_tracks):
        ad.nla_tracks.remove(t)
    ad.action = None
    act = bpy.data.actions.get(f"{char}_rig_{action}")
    if act is None:
        raise KeyError(f"{char} has no action {action}")
    length = act.frame_range[1] - act.frame_range[0]
    tr = ad.nla_tracks.new()
    tr.name = action
    rnd = random.Random(hash(pid) & 0xffff)
    off = rnd.uniform(0, length) if offset is None else offset
    st = tr.strips.new(action, int(-off), act)
    st.repeat = math.ceil((END + off + 10) / max(length, 1))
    # day / night visibility
    if schedule in ("day", "night"):
        for c in mp.values():
            for f, hidden in ((0, schedule == "night"), (F_NIGHT_ON, schedule == "day"), (F_DAY_ON, schedule == "night")):
                c.hide_render = hidden
                c.hide_viewport = hidden
                c.keyframe_insert("hide_render", frame=f)
                c.keyframe_insert("hide_viewport", frame=f)
            set_interp(c, "hide_render", "CONSTANT")
            set_interp(c, "hide_viewport", "CONSTANT")
    entry = {"id": pid, "character": char, "path": f"res://assets/characters/{char}.gltf", "role": role,
             "schedule": schedule, "animation": action, "pos": [round(loc[0], 3), round(loc[2], 3), round(-loc[1], 3)],
             "yaw_deg": round(math.degrees(yaw) % 360, 1)}
    if extra:
        entry.update(extra)
    POP.append(entry)
    return root, rig


def route_motion(root, pts, speed, start=0, loop=True):
    """Keyframe the root along a closed/open polyline at `speed` m/s, facing the walking direction."""
    pts = [V((p[0], p[1], 0)) for p in pts] + ([V((pts[0][0], pts[0][1], 0))] if loop else [])
    fps = bpy.context.scene.render.fps
    f = start
    for i in range(len(pts) - 1):
        a, b = pts[i], pts[i + 1]
        yaw = yaw_facing((b - a).normalized())
        root.location = a
        root.rotation_euler = (0, 0, yaw)
        root.keyframe_insert("location", frame=f)
        root.keyframe_insert("rotation_euler", frame=f)
        f += max(1, round((b - a).length / speed * fps))
        root.location = b
        root.keyframe_insert("location", frame=f - 1)
        root.keyframe_insert("rotation_euler", frame=f - 1)
    set_interp(root, "location", "LINEAR")
    set_interp(root, "rotation_euler", "CONSTANT")
    if loop:
        add_cycles(root)


# ============================================================================= population
STALL_KEEPER = {"produce": ("market_woman", "talk"), "bread": ("market_woman", "idle"), "pottery": ("merchant", "talk"),
                "cloth": ("merchant", "idle"), "meat": ("butcher", "talk"), "weapons": ("merchant", "talk")}


def populate(layout):
    M = layout["markers"]
    by_name = {m["name"]: m for m in M}
    inst = {i["id"]: i for i in layout["instances"]}
    rnd = random.Random(7)
    # --- hero ------------------------------------------------------------------------------
    ps = by_name["MARK_player_start"]
    spawn("vaclav", from_godot(ps["pos"]), math.radians(ps["yaw_deg"]), "idle", "always", "player")
    # --- traders at their stalls, customers in front ------------------------------------------
    for m in M:
        if m["kind"] == "merchant":
            stall = inst[m["owner"]]["asset"].replace("market_stall_", "")
            ch, an = STALL_KEEPER.get(stall, ("merchant", "idle"))
            spawn(ch, from_godot(m["pos"]), math.radians(m["yaw_deg"]), an, "day", f"trader_{stall}",
                  extra={"stall": m["owner"]})
        if m["kind"] == "customer" and rnd.random() < 0.6:
            ch = rnd.choice(["market_woman", "merchant", "child_boy", "beggar"])
            spawn(ch, from_godot(m["pos"]), math.radians(m["yaw_deg"]), rnd.choice(["idle", "talk"]), "day", "customer",
                  extra={"stall": m["owner"]})
        if m["kind"] == "cook":
            spawn("butcher", from_godot(m["pos"]), math.radians(m["yaw_deg"]), "work", "day", "cook")
        if m["kind"] == "smith" and inst[m["owner"]]["asset"] == "anvil":
            spawn("butcher", from_godot(m["pos"]), math.radians(m["yaw_deg"]), "work", "day", "blacksmith",
                  extra={"note": "uses the butcher model (apron) until a blacksmith model exists"})
    # --- NPC markers ------------------------------------------------------------------------
    for m in M:
        if m["kind"] != "npc":
            continue
        t = m["npc"]
        an = {"guard": "idle", "beggar": "beg", "child_boy": "talk", "child_girl": "idle", "market_woman": "talk",
              "merchant": "talk"}[t]
        sched = "always" if t in ("guard", "beggar") else "day"
        loc = from_godot(m["pos"])
        yaw = face_towards(loc, (2, 14, 0)) if t.startswith("child") else math.radians(m["yaw_deg"])
        spawn(t, loc, yaw, an, sched, "npc_" + t)
    # --- guard patrol around the square (always) ----------------------------------------------
    route = [from_godot(by_name[f"MARK_patrol_square_{i}"]["pos"]) for i in range(7)]
    r, _ = spawn("guard", route[0], 0, "walk", "always", "patrol", offset=0,
                 extra={"route": [f"MARK_patrol_square_{i}" for i in range(7)], "speed_mps": 1.1})
    route_motion(r, route, 1.1)
    # --- wandering townsfolk (day) ----------------------------------------------------------
    W = [from_godot(by_name[f"MARK_wander_{i:02d}"]["pos"]) for i in range(10)]
    for i, (ch, idx) in enumerate((("market_woman", [0, 1, 2, 9]), ("merchant", [3, 7, 4, 8]), ("beggar", [6, 5, 8]),
                                   ("child_boy", [8, 4, 9]))):
        r, _ = spawn(ch, W[idx[0]], 0, "walk" if ch != "child_boy" else "run", "day", "wanderer", offset=0,
                     extra={"route": [f"MARK_wander_{j:02d}" for j in idx]})
        route_motion(r, [W[j] for j in idx], 1.0 if ch != "child_boy" else 1.9, start=i * 13)
    # --- horses: one at the parked cart, one pulling a cart along Celetna --------------------
    for m in M:
        if m["kind"] == "horse":
            spawn("horse", from_godot(m["pos"]), math.radians(m["yaw_deg"]), "idle", "always", "cart_horse",
                  extra={"cart": m["owner"]})
    cart_col = asset_col("cart")
    path = [V((98, -8.6, 0)), V((84, -7.0, 0)), V((62, -12.0, 0)), V((44, -11.6, 0))]
    cart = bpy.data.objects.new("cart_moving", None)
    cart.instance_type = "COLLECTION"
    cart.instance_collection = cart_col
    _group("Pop_day").objects.link(cart)
    h, _ = spawn("horse", path[0], 0, "pull", "day", "cart_driver",
                 extra={"route_points": [[round(p.x, 2), 0.0, round(-p.y, 2)] for p in path], "speed_mps": 1.0,
                        "pulls": "res://assets/props/cart.gltf", "cart_offset_m": 3.0})
    route_motion(h, path, 1.0, loop=False)
    # the cart follows 3 m behind the horse: same keys, shifted in time
    fps = bpy.context.scene.render.fps
    route_motion(cart, path, 1.0, start=round(3.0 / 1.0 * fps), loop=False)
    for f, hidden in ((0, False), (F_NIGHT_ON, True), (F_DAY_ON, False)):
        cart.hide_render = hidden
        cart.keyframe_insert("hide_render", frame=f)
    set_interp(cart, "hide_render", "CONSTANT")
    side = V((0, 1.0, 0))
    r2, _ = spawn("merchant", path[0] + side, 0, "walk", "day", "carter", offset=0)
    route_motion(r2, [p + side for p in path], 1.0, start=round(1.0 * fps), loop=False)
    # --- enemies ----------------------------------------------------------------------------
    anims = {"alchemist": ["idle", "cast"], "skeleton": ["idle", "walk"], "golem": ["idle"]}
    for m in M:
        if m["kind"] != "spawn":
            continue
        t = m["enemy"]
        loc = from_godot(m["pos"])
        an = rnd.choice(anims[t])
        yaw = rnd.uniform(0, 2 * PI)
        spawn(t, loc, yaw, an, "night", "enemy_" + t, extra={"spawn_marker": m["name"]})
    # a lone alchemist lurking in the Celetna alley by day
    spawn("alchemist", V((57.0, 33.0, 0)), face_towards((57, 33), (60, 8)), "idle", "day", "enemy_alchemist",
          extra={"note": "daytime lurker"})
    # skeleton patrol in the Tyn court at night
    r, _ = spawn("skeleton", V((-6, 52, 0)), 0, "walk", "night", "enemy_skeleton_patrol", offset=0,
                 extra={"route_points": [[-6, 0, -52], [8, 0, -52], [8, 0, -64], [-6, 0, -64]], "speed_mps": 1.0})
    route_motion(r, [(-6, 52), (8, 52), (8, 64), (-6, 64)], 1.0)
    # night on the square: skeleton band crossing it, alchemists at the column (more enemies at night)
    band = [(-20, 20), (18, 20), (18, -8), (-18, -8)]
    for i in range(3):
        r, _ = spawn("skeleton", V((band[0][0] + i * 1.6, band[0][1] - i * 1.2, 0)), 0, "walk", "night", "enemy_skeleton_band",
                     offset=i * 5, extra={"route_points": [[x, 0, -y] for x, y in band], "speed_mps": 1.0})
        route_motion(r, [(x + i * 1.6, y - i * 1.2) for x, y in band], 1.0, start=i * 6)
    for x, y in ((-1.5, 10.5), (5.5, 11.0)):
        spawn("alchemist", V((x, y, 0)), face_towards((x, y), (2, 14)) + PI, "cast", "night", "enemy_alchemist_ritual")
    crowd(layout, rnd)
    print("population", len(POP))


def crowd(layout, rnd, n=22):
    """Market crowd by day: townsfolk standing, haggling and strolling between the stalls."""
    blockers = [from_godot(i["pos"]) for i in layout["instances"] if i["group"] == "square_props"]
    blockers += [from_godot(p["pos"]) for p in POP]
    folk = ["market_woman", "merchant", "beggar", "child_boy", "child_girl", "market_woman", "merchant", "guard"]
    placed = 0
    tries = 0
    while placed < n and tries < 2000:
        tries += 1
        p = V((rnd.uniform(-26, 26), rnd.uniform(-24, 24), 0))
        if any((p - b).length < (2.4 if b.z == 0 else 2.4) for b in blockers):
            continue
        ch = rnd.choice(folk)
        if placed % 4 == 3:
            q = p + V((rnd.uniform(-8, 8), rnd.uniform(-8, 8), 0))
            r, _ = spawn(ch, p, 0, "walk", "day", "crowd", offset=0)
            route_motion(r, [p, q], 1.0, start=rnd.randint(0, 40))
        else:
            near = min(blockers, key=lambda b: (p - b).length)
            spawn(ch, p, face_towards(p, near), rnd.choice(["idle", "talk", "talk"]), "day", "crowd")
        blockers.append(p)
        placed += 1


# ============================================================================= effects
def smoke_material():
    m = bpy.data.materials.get("FX_Smoke")
    if m:
        return m
    m = bpy.data.materials.new("FX_Smoke")
    try:
        m.use_nodes = True
    except Exception:
        pass
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Base Color"].default_value = (0.32, 0.3, 0.29, 1)
    b.inputs["Roughness"].default_value = 1.0
    oi = nt.nodes.new("ShaderNodeObjectInfo")
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = 3.0
    lw = nt.nodes.new("ShaderNodeLayerWeight")
    mul = nt.nodes.new("ShaderNodeMath")
    mul.operation = "MULTIPLY"
    mul2 = nt.nodes.new("ShaderNodeMath")
    mul2.operation = "MULTIPLY"
    inv = nt.nodes.new("ShaderNodeMath")
    inv.operation = "SUBTRACT"
    inv.inputs[0].default_value = 1.0
    nt.links.new(lw.outputs["Facing"], inv.inputs[1])            # soft edges
    nt.links.new(nz.outputs["Fac"], mul.inputs[0])
    nt.links.new(inv.outputs[0], mul.inputs[1])
    nt.links.new(mul.outputs[0], mul2.inputs[0])
    nt.links.new(oi.outputs["Alpha"], mul2.inputs[1])
    nt.links.new(mul2.outputs[0], b.inputs["Alpha"])
    try:
        m.surface_render_method = "BLENDED"
    except Exception:
        m.blend_method = "BLEND"
    return m


def smoke(name, base, n=6, height=7.0, period=120, size=0.5):
    mat = smoke_material()
    col = _group("FX")
    me = bpy.data.meshes.new("FX_puff")
    import bmesh
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=2, radius=1.0)
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = True
    me.materials.append(mat)
    base = V(base)
    for i in range(n):
        o = bpy.data.objects.new(f"FX_{name}_puff{i}", me)
        col.objects.link(o)
        o.visible_shadow = False
        ph = int(i * period / n)
        drift = V((0.6, 0.4, 0))
        for f, t in ((0, 0.0), (period, 1.0)):
            o.location = base + V((0, 0, height * t)) + drift * (height * 0.4 * t * t)
            o.scale = V((1, 1, 1)) * (size * (0.4 + 2.6 * t))
            o.color = (1, 1, 1, 0.55 * (1 - t) * min(1.0, t * 6))
            o.keyframe_insert("location", frame=f - ph)
            o.keyframe_insert("scale", frame=f - ph)
            o.keyframe_insert("color", frame=f - ph)
        for fc in fcurves(o):
            for k in fc.keyframe_points:
                k.interpolation = "LINEAR"
            fc.modifiers.new("CYCLES")
        o.color = (1, 1, 1, 0.3)
    FX.append({"type": "smoke", "name": name, "pos": [round(base.x, 2), round(base.z, 2), round(-base.y, 2)],
               "height_m": height, "period_s": period / 24})


def animate_environment(layout):
    # spit roast turning (ANIM_spit inside the instanced spit_roast collection)
    for o in bpy.data.objects:
        if o.name.startswith("ANIM_spit"):
            o.rotation_mode = "XYZ"
            for f, a in ((0, 0.0), (96, 2 * PI)):
                o.rotation_euler = (a, 0, 0)
                o.keyframe_insert("rotation_euler", frame=f)
            set_interp(o, "rotation_euler", "LINEAR")
            add_cycles(o)
            FX.append({"type": "rotate", "node": "ANIM_spit", "asset": "spit_roast", "axis": "x", "period_s": 4.0})
    # banners swaying (ANIM_banner inside banner_lion; placed on square facades below)
    for o in bpy.data.objects:
        if o.name.startswith("ANIM_banner"):
            o.rotation_mode = "XYZ"
            for f in range(0, 121, 10):
                o.rotation_euler = (math.radians(4.0 * math.sin(2 * PI * f / 120) + 1.5 * math.sin(2 * PI * f / 40)), 0,
                                    math.radians(1.5 * math.sin(2 * PI * f / 60)))
                o.keyframe_insert("rotation_euler", frame=f)
            add_cycles(o)
            FX.append({"type": "sway", "node": "ANIM_banner", "asset": "banner_lion", "amplitude_deg": 5.0, "period_s": 5.0})
    # fire light flicker: noise on the energy curves (multiplies, so lights stay off by day)
    for l in bpy.data.lights:
        nm = l.name.lower()
        if l.type == "POINT" and any(k in nm for k in ("fire", "forge", "torch")):
            for fc in fcurves(l):
                if fc.data_path == "energy":
                    mod = fc.modifiers.new("NOISE")
                    mod.blend_type = "MULTIPLY"
                    mod.scale = 3.0
                    mod.strength = 2.0
                    mod.phase = random.uniform(0, 100)
    FX.append({"type": "flicker", "lights": "LIGHT_fire*, LIGHT_forge*, LIGHT_*torch*", "amount": 0.35, "speed_hz": 8})
    # smoke over the hearths
    inst = layout["instances"]
    for i in inst:
        p = from_godot(i["pos"])
        if i["asset"] == "spit_roast":
            smoke("spit", p + V((0, 0, 1.6)), height=8.0)
        if i["asset"] == "forge":
            smoke("forge", p + V((0, 0, 3.6)), height=7.0, size=0.4)
        if i["asset"] == "cooking_pot":
            smoke("pot", p + V((0, 0, 1.0)), n=4, height=5.0, size=0.3)


def banners(layout):
    """Lion banners on some square facades (as on the concept art)."""
    col = asset_col("banner_lion")
    k = 0
    for i in layout["instances"]:
        if not i["group"].startswith("square_") or not i["asset"].startswith("house_burgher"):
            continue
        k += 1
        if k % 3:
            continue
        yaw = math.radians(i["yaw_deg"])
        c = from_godot(i["pos"])
        fwd = V((math.sin(yaw), -math.cos(yaw), 0))
        right = V((math.cos(yaw), math.sin(yaw), 0))
        p = c + fwd * 6.0 + right * 1.2
        e = bpy.data.objects.new(f"banner_lion@{i['id']}", None)
        e.instance_type = "COLLECTION"
        e.instance_collection = col
        e.location = p + V((0, 0, 4.2))
        e.rotation_euler = (0, 0, yaw)
        _group("FX").objects.link(e)
        FX.append({"type": "prop", "asset": "banner_lion", "path": "res://assets/props/banner_lion.gltf",
                   "pos": [round(e.location.x, 3), round(e.location.z, 3), round(-e.location.y, 3)],
                   "yaw_deg": round(i["yaw_deg"], 1), "note": "origin at wall base: mount height already added"})


# ============================================================================= renders
SHOTS = {
    "square": ((-23.5, -28.0, 3.4), (-5.0, 30.0, 7.5), 78, ("day", "night")),
    "square_wide": ((1.5, -27.0, 6.5), (1.0, 40.0, 16.0), 72, ("day", "night")),
    "market": ((-14.0, -24.0, 3.2), (-8.0, 2.0, 2.0), 62, ("day", "night")),
    "spit": ((-17.0, -26.0, 2.4), (-22.5, -19.5, 1.2), 55, ("day", "night")),
    "tyn_court": ((1.5, 45.0, 2.4), (1.5, 74.0, 9.0), 75, ("day", "night")),
    "celetna": ((44.0, -12.5, 2.8), (80.0, -8.0, 4.0), 66, ("day",)),
    "vaclav": ((2.4, -24.8, 1.9), (0.0, -19.6, 1.3), 42, ("day", "night")),
}


def render_all():
    import build_world as BW
    os.makedirs(RENDER_DIR, exist_ok=True)
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_EEVEE"
    sc.render.resolution_x, sc.render.resolution_y = 1600, 900
    try:
        sc.eevee.taa_render_samples = 32
        sc.view_settings.view_transform = "Standard"
    except Exception:
        pass
    for name, (loc, look, fov, tags) in SHOTS.items():
        sc.camera = BW.camera("s_" + name, loc, look, fov)
        for tag in tags:
            sc.frame_set(FRAME_DAY if tag == "day" else FRAME_NIGHT)
            sc.render.filepath = os.path.join(RENDER_DIR, f"{name}_{tag}.png")
            bpy.ops.render.render(write_still=True)
            print("RENDERED", sc.render.filepath)
    # concept comparison
    import numpy as np
    for tag in ("day", "night"):
        imgs = []
        for p in (os.path.join(G.PROJECT, "concept", "locations", f"old_town_square_{tag}.png"),
                  os.path.join(RENDER_DIR, f"square_{tag}.png")):
            im = bpy.data.images.load(p)
            w, h = im.size
            px = np.array(im.pixels[:], np.float32).reshape(h, w, 4)
            imgs.append(px[(np.arange(450) * h / 450).astype(int)][:, (np.arange(800) * w / 800).astype(int)])
            bpy.data.images.remove(im)
        sheet = np.concatenate(imgs, axis=1)
        o = bpy.data.images.new("cmp", sheet.shape[1], sheet.shape[0], alpha=True)
        o.pixels.foreach_set(sheet.ravel())
        o.filepath_raw = os.path.join(RENDER_DIR, f"compare_{tag}.png")
        o.file_format = "PNG"
        o.save()


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    bpy.ops.wm.open_mainfile(filepath=os.path.join(G.BLENDER_DIR, "world_old_town.blend"))
    with open(LAYOUT_JSON, encoding="utf-8") as f:
        layout = json.load(f)
    load_characters()
    banners(layout)
    populate(layout)
    animate_environment(layout)
    counts = {}
    for p in POP:
        key = f"{p['schedule']}:{p['character']}"
        counts[key] = counts.get(key, 0) + 1
    data = {"level": "old_town_square", "version": 1,
            "coordinate_system": "Godot coordinates (same as old_town_layout.json). Characters face local +Z.",
            "schedule": {"day": "visible/active by day (merchants close at dusk)", "night": "spawned at dusk (enemies)",
                         "always": "day and night"},
            "population": POP, "fx": FX, "counts": counts}
    with open(POP_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    print("COUNTS", json.dumps(counts, ensure_ascii=False))
    bpy.context.scene.frame_set(0)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(G.BLENDER_DIR, "scene_old_town.blend"))
    if "--no-render" not in argv:
        render_all()
        bpy.context.scene.frame_set(0)
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join(G.BLENDER_DIR, "scene_old_town.blend"))
    print("DONE scene")


if __name__ == "__main__":
    main()
