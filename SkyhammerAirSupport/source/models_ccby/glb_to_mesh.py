# Blender (headless): blender -b --factory-startup --python glb_to_mesh.py -- <model key>
# Turns a downloaded CC-BY glb (see CREDITS.md) into Skyhammer's SHA1 mesh:
#   big-endian 'SHA1', vertex count, then 10 floats per vertex: position, normal, colour, part.
# Model space: +X starboard, +Y up, +Z nose, metres. Colours are the textures sampled at every
# triangle corner (as stored, sRGB) times the material's base colour, so no texture is needed in game.
# Also writes <key>_preview.obj (vertex RGB) and <key>_report.json (triangles, bounds, part boxes).
import bpy, bmesh, sys, re, json, struct, math
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
LINEARISE = False
JAVA = HERE.parent / 'java' / 'skyhammer' / 'aircraft'


def inside(box, lo, hi):
    """box = (min xyz, max xyz) in Blender space; True when the whole box is within lo..hi."""
    return all(lo[i] <= box[0][i] and box[1][i] <= hi[i] for i in range(3))


def cut_faces(ob, rule):
    """Delete the faces of ob that rule(object name, corners in Blender world space) calls
    landing gear: gear modelled inside objects that hold the airframe too. Returns how many.
    (The caller gives ob a mesh of its own first: an imported mesh may be shared.)"""
    if rule is None:
        return 0
    mw = ob.matrix_world
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    dead = [f for f in bm.faces if rule(ob.name, [mw @ v.co for v in f.verts])]
    if dead:
        bmesh.ops.delete(bm, geom=dead, context='FACES')
        bm.to_mesh(ob.data)
        ob.data.update()
    bm.free()
    return len(dead)


def patch_object(cfg, name='patch'):
    """cfg patch's faces as a Blender object, world space (for the pictures: make_turntables.py,
    make_steam_shots.py), in the grey render_grey; the game mesh gets them in a colour sampled
    from the model instead."""
    p = cfg.get('patch')
    if not p:
        return None
    verts, faces = [], []
    for tri in p['tris']:
        faces.append(tuple(range(len(verts), len(verts) + 3)))
        verts += [tuple(v) for v in tri]
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.update()
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bs = next(n for n in mat.node_tree.nodes if n.bl_idname == 'ShaderNodeBsdfPrincipled')
    g = p.get('render_grey', 0.5)
    bs.inputs['Base Color'].default_value = (g, g, g, 1.0)
    bs.inputs['Roughness'].default_value = 0.6
    me.materials.append(mat)
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def ac130_gear(name, ps):
    """The AC-130's landing gear (Blender space: z up, the belly at z 0, nose -X), in the nose-gear
    bay and the two main-gear wells only: elsewhere the belly skin dips under z 0 too.
    2026-11-23, the user: the wheels showed on the flying gunship."""
    xs = [p[0] for p in ps]
    ays = [abs(p[1]) for p in ps]
    zs = [p[2] for p in ps]
    nose = min(xs) > -10.3 and max(xs) < -8.7 and max(ays) < 0.9
    main = min(xs) > -1.6 and max(xs) < 1.6 and min(ays) > 1.3 and max(ays) < 2.9
    if not (nose or main):
        return False
    if max(zs) < -0.02:                          # wholly under the belly: wheels, axles, links
        return True
    if name == 'Object_59' and main and max(zs) < 0.1:   # the tops of the front main wheels
        return True
    if name == 'Object_56' and max(ays) < 2.3:   # a main-gear brace (the rest of it: the sponsons' sides)
        return True
    if main and min(ays) > 2.50 and max(zs) < 0.45:   # the open gear doors standing out of the sponsons
        return True
    # the legs: thin upright pieces reaching down under the belly
    return min(zs) < -0.08 and max(xs) - min(xs) < 0.3 and max(ays) - min(ays) < 0.3


# the main-gear wells' outer side and floor, open in the model (the gear was down): closed with
# the sponson's own section (the wells' end walls at x +-1.39: y, z from the top of the opening
# round to the inner wall), one strip after another, facing out
AC130_WELL = [(2.46, 0.50), (2.43, 0.40), (2.35, 0.22), (2.26, 0.07), (2.14, -0.03), (2.03, -0.10), (1.90, -0.12),
              (1.69, -0.12)]


def ac130_well_doors():
    x0, x1 = -1.39, 1.39
    tris = []
    for s in (1, -1):
        for (ya, za), (yb, zb) in zip(AC130_WELL, AC130_WELL[1:]):
            a, b, c, d = (x0, s * ya, za), (x1, s * ya, za), (x1, s * yb, zb), (x0, s * yb, zb)
            tris += [[a, b, c], [a, c, d]] if s > 0 else [[a, c, b], [a, d, c]]
    return tris


# the nose-gear bay's opening (x -10.03..-8.83, |y| < 0.59), closed at the belly skin's height
# (rows: x, z at the bay's sides, z on the centre line), facing down
AC130_NOSE_BAY = [(-10.03, 0.02, 0.0), (-9.36, -0.05, -0.08), (-8.83, -0.07, -0.10)]


def ac130_nose_door():
    tris = []
    for (xa, ea, ca), (xb, eb, cb) in zip(AC130_NOSE_BAY, AC130_NOSE_BAY[1:]):
        for ya, yb in ((-0.59, 0.0), (0.0, 0.59)):
            za, zb = (ca if ya == 0 else ea), (ca if yb == 0 else ea)
            wa, wb = (cb if ya == 0 else eb), (cb if yb == 0 else eb)
            a, b, c, d = (xa, ya, za), (xb, ya, wa), (xb, yb, wb), (xa, yb, zb)
            tris += [[a, c, b], [a, d, c]]
    return tris


# Blender space after the glTF import: Z up. Each model: file, axis map to game space, triangle
# budget, objects to drop (landing gear, pilot), parts (name regex or box -> part id), and the
# game-space point the model is moved to (bounding-box centre x/z, and y centre).
MODELS = {
    'a10': dict(
        glb='a10/a10.glb', out='a10.mesh',
        # nose is -X, starboard +Y
        axes=lambda x, y, z: (y, z, -x),
        tris=28000,
        drop=lambda name, b: (
            name.startswith('cmj')                                              # pilot legs
            or inside(b, (-1.1, -3.3, 0.0), (0.05, -1.85, 2.1))                 # left main gear
            or inside(b, (-1.1, 1.85, 0.0), (0.05, 3.3, 2.1))                   # right main gear
            or inside(b, (-6.6, -0.6, 0.0), (-5.2, 0.6, 2.45)) and b[0][2] < 1.65  # nose gear, doors
        ),
        parts=[(1, lambda name, b: inside(b, (-9.2, -0.6, 1.8), (-7.6, -0.2, 2.3)))],  # GAU-8 barrels
        keep_parts={1},
        # 2026-11-23, the user: the A-10 is grey (the texture is a little green)
        grey=True,
        # gun barrels land where the hand-made model had them (axis y -0.46, muzzle z 8.15), so
        # Strafer.GUN_Y/Z and the muzzle flash stay right; only GUN_X moves (-0.18 -> -0.105)
        centre=(0.0, 0.31, 0.09),
    ),
    'ah64': dict(
        glb='ah64/ah64.glb', out='apache.mesh',
        # nose is -X, starboard +Y (same author as the A-10); fixed gear stays (the real one has no retract)
        axes=lambda x, y, z: (y, z, -x),
        tris=28000,
        drop=lambda name, b: False,
        # apache.vert: 1 main rotor, 2 tail rotor, 3 turret, 4 gun barrel
        parts=[
            (1, lambda name, b: re.match(r'ah(62\d|63|64|73\d|79\d)-', name) is not None),
            (2, lambda name, b: re.match(r'ah(59a|59b|76)-', name) is not None),
            (4, lambda name, b: re.match(r'ah65-', name) is not None),
            (3, lambda name, b: re.match(r'ah(66|67|68|69)-', name) is not None),
        ],
        # main rotor hub lands where the hand-made model had it, so Hover's heights stay right
        anchor=((-0.02, 0.015, 4.43), (0.0, 2.65, -0.45)),
        pivots=dict(main=(-0.02, 0.015, 4.43), tail=(8.84, -1.0, 4.165), turret=(-2.5, -0.03, 0.85)),
    ),
    'f22': dict(
        glb='f22/f22.glb', out='f22.mesh',
        # fuselage axis is 51.5 deg off Blender X with the nose toward -x/-y: turn it so the nose is -X,
        # then the same axis map as the other manilov.ap models (right wing ends up at +Y)
        yaw=-51.5,
        axes=lambda x, y, z: (y, z, -x),
        tris=10000,
        drop=lambda name, b: re.match(
            r'(Nose_Gear|Nose_Wheel|Left_Main_Gear|Right_Main_Gear|Left_MGear|Right_MGear|Left_Nose_Gear|'
            r'Right_Nose_Gear|Pilot_|Cabin_Carcas|Cabin_Inner|Control_Panel|Left_Front_Turbina|Right_Front_Turbina|'
            r'Left_Back_Turbina|Right_Back_Turbina|OilTank|ILS|Box\d|Right_Display|Left_Display|Left_Rocket_Bay-|Right_Rocket_Bay-)',
            name) is not None,
        parts=[],
        centre=(0.0, 0.0, 0.0),
    ),
    'b2': dict(
        glb='b2/b2.glb', out='b2.mesh',
        # nose gear (-4.7,-1.15) is 163.5 deg from the main-gear midpoint: turn the nose to -X, then the
        # usual axis map; the model is small, so scale it to the real 52.4 m span
        yaw=16.5,
        axes=lambda x, y, z: (y, z, -x),
        span=52.4,
        tris=28000,
        # landing gear: wheels, struts and the small parts hanging below the belly
        drop=lambda name, b: b[0][2] < -0.3 and b[1][2] < 0.75 and (b[1][0] - b[0][0]) < 1.5 and (b[1][1] - b[0][1]) < 1.5
                             or name in ('Object_10', 'Object_158'),
        # gear doors and struts that are part of the belly object: anything reaching under the belly
        keep_tri=lambda ps: min(p[2] for p in ps) > -0.05,   # belly skin is at z >= 0.03
        parts=[],
        # the texture is a light grey; the real one is near black (2026-11-23, the user: "b-2는 검은색")
        grey=True,
        tint=0.3,
        centre=(0.0, 0.66, 0.0),
    ),
    'ac130': dict(
        glb='ac130/ac130.glb', out='ac130.mesh',
        # nose (cockpit panels at x -11) is -X, starboard +Y; the Bofors pokes out of the port side (-Y)
        axes=lambda x, y, z: (y, z, -x),
        tris=28000,
        # keep the outside only: airframe pieces, propellers, the Bofors and the outer window glass.
        # No landing gear (2026-11-23, the user: the wheels showed): Object_58 and 59 are the wheels,
        # the legs and braces inside the airframe objects go face by face (ac130_gear)
        drop=lambda name, b: name not in ('Object_14', 'Object_44', 'Object_45', 'Object_46', 'Object_47',
                                          'Object_48', 'Object_52', 'Object_53', 'Object_54', 'Object_55',
                                          'Object_56', 'Object_57', 'Object_59', 'Object_64'),
        cut=ac130_gear,
        # the wells closed, in the sponson's colour (sampled from its skin just fore and aft of them;
        # render_grey: the same grey for the Blender pictures, which do not sample)
        patch=dict(tris=ac130_well_doors() + ac130_nose_door(),
                   colour_from=lambda p: 1.45 < abs(p[0]) < 2.6 and 2.0 < abs(p[1]) < 2.6 and -0.15 < p[2] < 0.5,
                   render_grey=0.55),
        mat_colour={'transparentExt': (0.10, 0.12, 0.14)},
        # 2026-11-23, the user: the AC-130 is grey (the texture is a little olive)
        grey=True,
        # every propeller object holds blades of all four engines: split them per triangle by the nearest hub
        parts=[(9, lambda name, b: name in ('Object_44', 'Object_45', 'Object_46', 'Object_47', 'Object_48'))],
        tri_part=lambda part, c: part if part != 9 else 1 + min(range(4), key=lambda k: abs(c[1] - (-9.825, -4.925, 4.925, 9.825)[k])),
        # bounding-box middle (x 1.6) at the old z centre, fuselage bottom at the old bottom
        anchor=((1.6, 0.0, -0.9), (0.0, -2.0, -0.5)),
        pivots={'prop%d' % (k + 1): (-4.06, y, 3.62) for k, y in enumerate((-9.825, -4.925, 4.925, 9.825))}
               | {'muzzle': (3.62, -6.15, 1.0)},
        # aircraft.frag: part 5 is the muzzle flash, shown only while firing; reuse the hand-made one,
        # moved from the old muzzle (-4.3,-0.4,-5.0) to the Bofors muzzle
        graft=[('old_meshes/ac130.mesh', 5, (-1.85, 0.3, 2.48))],
    ),
}


def make_transform(cfg):
    """Blender point -> game point before scale/offset: optional yaw about Blender Z, then the axis map."""
    yaw = math.radians(cfg.get('yaw', 0.0))
    c, s = math.cos(yaw), math.sin(yaw)
    axes = cfg['axes']
    def t(x, y, z):
        return axes(c * x - s * y, s * x + c * y, z)
    return t


def srgb_to_linear(c):
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def material_source(mat):
    """(image or None, base colour rgb) for a glTF-imported material."""
    if mat is None or not mat.use_nodes:
        return None, (0.6, 0.6, 0.6)
    bsdf = next((n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
    if bsdf is None:
        return None, (0.6, 0.6, 0.6)
    sock = bsdf.inputs['Base Color']
    factor = [1.0, 1.0, 1.0]
    img = None
    stack = [l.from_node for l in sock.links]
    seen = set()
    while stack:
        n = stack.pop()
        if n in seen:
            continue
        seen.add(n)
        if n.type == 'TEX_IMAGE' and n.image is not None:
            img = n.image
        elif n.type in ('MIX', 'MIX_RGB', 'MATH', 'VECT_MATH', 'SEPARATE_COLOR', 'COMBINE_COLOR', 'GAMMA'):
            for i in n.inputs:
                if not i.is_linked and i.type == 'RGBA':
                    v = list(i.default_value)[:3]
                    if any(abs(a - 1.0) > 1e-3 for a in v) and any(a > 0 for a in v):
                        factor = [factor[k] * v[k] for k in range(3)]
            stack += [l.from_node for i in n.inputs for l in i.links]
    if not sock.is_linked:
        return None, tuple(sock.default_value[:3])
    return img, tuple(factor)


_cache = {}


def image_array(img):
    if img.name not in _cache:
        w, h = img.size
        a = np.array(img.pixels[:], dtype=np.float32).reshape(h, w, 4)[:, :, :3]
        # Kept as stored (sRGB): the hand-made meshes' colours are sRGB-like values too
        # (old A-10 mean 0.33); linearising made the converted A-10 half as bright (0.09).
        if LINEARISE and img.colorspace_settings.name.lower().startswith('srgb'):
            a = srgb_to_linear(a)
        _cache[img.name] = a
    return _cache[img.name]


def sample(img, u, v):
    a = image_array(img)
    h, w = a.shape[:2]
    x = int((u % 1.0) * w) % w
    y = int((v % 1.0) * h) % h
    return a[y, x]


def main():
    key = sys.argv[sys.argv.index('--') + 1]
    cfg = MODELS[key]
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(HERE / cfg['glb']))
    dg = bpy.context.evaluated_depsgraph_get()

    groups = {}   # part id -> list of objects
    dropped = []
    for ob in list(bpy.context.scene.objects):
        if ob.type != 'MESH':
            continue
        pts = [ob.matrix_world @ v.co for v in ob.data.vertices]
        if not pts:
            continue
        box = (tuple(min(p[i] for p in pts) for i in range(3)), tuple(max(p[i] for p in pts) for i in range(3)))
        if cfg['drop'](ob.name, box):
            dropped.append(ob.name)
            continue
        part = 0
        for pid, rule in cfg['parts']:
            if rule(ob.name, box):
                part = pid
                break
        groups.setdefault(part, []).append(ob)

    # bake transforms, cut the gear left in (cfg cut), join each part, decimate the airframe
    # (part 0) to the budget
    joined = {}
    cut = {}
    for part, obs in groups.items():
        for ob in obs:
            ob.data = ob.data.copy()
            ob.data.transform(ob.matrix_world)
            ob.parent = None
            ob.matrix_world.identity()
            n = cut_faces(ob, cfg.get('cut'))
            if n:
                cut[ob.name] = n
        bpy.ops.object.select_all(action='DESELECT')
        for ob in obs:
            ob.select_set(True)
        bpy.context.view_layer.objects.active = obs[0]
        if len(obs) > 1:
            bpy.ops.object.join()
        joined[part] = bpy.context.view_layer.objects.active
    for ob in bpy.context.scene.objects:
        if ob.type == 'MESH' and ob not in joined.values():
            ob.hide_set(True)

    def tri_count(ob):
        me = ob.evaluated_get(bpy.context.evaluated_depsgraph_get()).to_mesh()
        me.calc_loop_triangles()
        n = len(me.loop_triangles)
        ob.evaluated_get(bpy.context.evaluated_depsgraph_get()).to_mesh_clear()
        return n

    kept = sum(tri_count(o) for p, o in joined.items() if p in cfg.get('keep_parts', set()))
    base = sum(tri_count(o) for p, o in joined.items() if p not in cfg.get('keep_parts', set()))
    budget = max(1000, cfg['tris'] - kept)
    if base > budget:
        ratio = budget / base
        for p, o in joined.items():
            if p in cfg.get('keep_parts', set()):
                continue
            m = o.modifiers.new('dec', 'DECIMATE')
            m.decimate_type = 'COLLAPSE'
            m.ratio = ratio
            m.use_collapse_triangulate = True

    # gather triangles in game space
    axes = make_transform(cfg)
    tris = []   # (part, [(pos, rgb)]*3)
    patch_cols = []   # (cfg patch: the colours it is given)
    dg = bpy.context.evaluated_depsgraph_get()
    for part, ob in joined.items():
        ev = ob.evaluated_get(dg)
        me = ev.to_mesh()
        me.calc_loop_triangles()
        uv = me.uv_layers.active.data if me.uv_layers.active else None
        col = me.color_attributes.active_color if me.color_attributes else None
        sources = [material_source(m) for m in me.materials] or [(None, (0.6, 0.6, 0.6))]
        for i, m in enumerate(me.materials):
            if m is not None and m.name in cfg.get('mat_colour', {}):
                sources[i] = (None, cfg['mat_colour'][m.name])
        keep_tri = cfg.get('keep_tri')
        patch = cfg.get('patch')
        tint = cfg.get('tint', 1.0)
        grey = cfg.get('grey', False)
        for lt in me.loop_triangles:
            if keep_tri is not None and not keep_tri([me.vertices[vi].co for vi in lt.vertices]):
                continue
            img, fac = sources[min(lt.material_index, len(sources) - 1)]
            corners = []
            for li, vi in zip(lt.loops, lt.vertices):
                p = axes(*me.vertices[vi].co)
                if img is not None and uv is not None:
                    u, v = uv[li].uv
                    c = sample(img, u, v)
                    c = [c[k] * fac[k] for k in range(3)]
                else:
                    c = list(fac)
                if col is not None and col.domain == 'CORNER':
                    vc = col.data[li].color
                    c = [c[k] * vc[k] for k in range(3)]
                if grey:   # the same brightness, no colour (Rec. 709 weights)
                    l = 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]
                    c = [l, l, l]
                corners.append((p, [min(1.0, max(0.0, float(x) * tint)) for x in c]))
                if patch is not None and patch['colour_from'](me.vertices[vi].co):
                    patch_cols.append(corners[-1][1])
            tp = part
            if 'tri_part' in cfg:
                cen = [sum(me.vertices[vi].co[k] for vi in lt.vertices) / 3 for k in range(3)]
                tp = cfg['tri_part'](part, cen)
            tris.append((tp, corners))
        ev.to_mesh_clear()

    # (cfg patch: faces the model lacks, part 0, in the mean colour sampled from its colour_from box)
    patch_rgb = None
    if cfg.get('patch'):
        n = max(1, len(patch_cols))
        patch_rgb = [round(sum(c[k] for c in patch_cols) / n, 4) for k in range(3)] if patch_cols else [0.5] * 3
        for tri in cfg['patch']['tris']:
            tris.append((0, [(axes(*p), list(patch_rgb)) for p in tri]))

    # scale (fixed, or to a wingspan along game X), then move: an anchor point (Blender space) to a
    # game point, or else the bounding-box centre to cfg centre
    allp = [p for _, cs in tris for p, _ in cs]
    lo = [min(p[i] for p in allp) for i in range(3)]
    hi = [max(p[i] for p in allp) for i in range(3)]
    k = cfg.get('scale', 1.0)
    if 'span' in cfg:
        k = cfg['span'] / (hi[0] - lo[0])
    tris = [(part, [(tuple(v * k for v in p), rgb) for p, rgb in cs]) for part, cs in tris]
    lo = [v * k for v in lo]; hi = [v * k for v in hi]
    if 'anchor' in cfg:
        src, dst = cfg['anchor']
        a = [v * k for v in axes(*src)]
        off = [dst[i] - a[i] for i in range(3)]
    else:
        off = [cfg['centre'][i] - (lo[i] + hi[i]) / 2 for i in range(3)]
    pivots = {name: [round(v * k + off[i], 3) for i, v in enumerate(axes(*pt))] for name, pt in cfg.get('pivots', {}).items()}

    grafts = []   # (part, [(pos, rgb)]*3) already in final game space
    for path, gpart, move in cfg.get('graft', []):
        d = (HERE / path).read_bytes()
        gn = struct.unpack('>I', d[4:8])[0]
        gf = struct.unpack('>%df' % (gn * 10), d[8:8 + gn * 40])
        for t in range(gn // 3):
            vs = [gf[(t * 3 + j) * 10:(t * 3 + j) * 10 + 10] for j in range(3)]
            if int(vs[0][9] + .1) == gpart:
                grafts.append((gpart, [(tuple(v[k] + move[k] for k in range(3)), list(v[6:9])) for v in vs]))

    floats = []
    parts_box = {}
    obj_lines = ['# Converted from a CC-BY model (see CREDITS.md). +X starboard +Y up +Z nose. Vertex RGB.']
    moved = [(part, [(tuple(p[i] + off[i] for i in range(3)), rgb) for p, rgb in cs]) for part, cs in tris] + grafts
    for part, cs in moved:
        ps = [p for p, _ in cs]
        a, b, c = [np.array(p) for p in ps]
        n = np.cross(b - a, c - a)
        ln = float(np.linalg.norm(n))
        if ln < 1e-12:
            continue
        n = n / ln
        for p, (_, rgb) in zip(ps, cs):
            floats += [*p, *n.tolist(), *rgb, float(part)]
            obj_lines.append('v %.5f %.5f %.5f %.4f %.4f %.4f' % (*p, *rgb))
            pb = parts_box.setdefault(part, [list(p), list(p)])
            for i in range(3):
                pb[0][i] = min(pb[0][i], p[i]); pb[1][i] = max(pb[1][i], p[i])
    nverts = len(floats) // 10
    for i in range(nverts // 3):
        obj_lines.append('f %d %d %d' % (i * 3 + 1, i * 3 + 2, i * 3 + 3))
    assert nverts % 3 == 0 and 0 < nverts <= 100000, nverts
    raw = struct.pack('>II', 0x53484131, nverts) + struct.pack('>%df' % len(floats), *floats)
    out_dir = HERE / key
    (out_dir / cfg['out']).write_bytes(raw)
    (out_dir / (key + '_preview.obj')).write_text('\n'.join(obj_lines) + '\n', encoding='utf-8')
    rep = dict(triangles=nverts // 3, vertices=nverts, bytes=len(raw), dropped=len(dropped), cut=cut, patch_rgb=patch_rgb,
               bounds=[[round(v + off[i], 3) for i, v in enumerate(lo)], [round(v + off[i], 3) for i, v in enumerate(hi)]],
               parts={str(k): [[round(x, 3) for x in v[0]], [round(x, 3) for x in v[1]]] for k, v in parts_box.items()},
               scale=round(k, 4), pivots=pivots,
               mean_colour=[round(float(np.mean(floats[6 + k::10])), 3) for k in range(3)])
    (out_dir / (key + '_report.json')).write_text(json.dumps(rep, indent=1), encoding='utf-8')
    print('REPORT ' + json.dumps(rep))


main()
