"""The terminal's 3D look-around (Skyhammer_Viewer.lua): each aircraft's CC-BY model (models_ccby, the
same glb files the game meshes come from) rendered with its own textures from 36 directions, 10 deg
apart, at the terminal pictures' angle (18 deg above, as make_f22_art.py). Frame 0 is the picture's
view; frame i has the model turned i * 10 deg about its vertical axis. The landing gear and the
other parts glb_to_mesh.py leaves out stay out (its MODELS table is read from that file).
Writes turntable/<key>/f00.png .. f35.png; package_turntables.py makes the sheets.
Run: blender -b --factory-startup --python make_turntables.py -- [keys...]   (default: all five)"""
from pathlib import Path
import math, re, sys
import bpy
from mathutils import Vector, Matrix

HERE = Path(__file__).resolve().parent
MOD = HERE.parents[1]
CCBY = MOD / 'source/models_ccby'
FRAMES, STEP = 36, 10.0

# glb_to_mesh.py's MODELS (its drop rules, yaw, tint, material colours), without running it
src = (CCBY / 'glb_to_mesh.py').read_text(encoding='utf-8')
src = src[:src.rindex('main()')]
ns = {'__file__': str(CCBY / 'glb_to_mesh.py'), '__name__': 'glb_to_mesh'}
exec(compile(src, 'glb_to_mesh.py', 'exec'), ns)
MODELS = ns['MODELS']
cut_faces = ns['cut_faces']
patch_object = ns['patch_object']
KEYS = {'ac130': 'ac130', 'apache': 'ah64', 'a10': 'a10', 'b2': 'b2', 'f22': 'f22'}
# the F-22 picture keeps its cockpit (it shows through the canopy): the same here
KEEP = {'f22': re.compile(r'(Pilot_|Cabin_Carcas|Cabin_Inner|Control_Panel|Right_Display|Left_Display)')}
# per aircraft (2026-11-23, the user: the A-10 and the AC-130 grey, the B-2 black): grey = the
# texture's colour taken out (its markings and panel lines kept); the B-2 darkened to near black,
# seen from 35 deg (a flying wing seen from 18 deg is a thin line most of the turn); the Apache
# lifted to read on the terminal's dark panel. (No light from behind: the B-2's flat top mirrors it
# into the camera and turns it light grey.)
LOOK = {'apache': dict(exposure=0.55), 'a10': dict(grey=True, exposure=0.25), 'ac130': dict(grey=True),
        'b2': dict(grey=True, tint=0.3, elevation=35, exposure=0.1)}


def gpu(scene):
    prefs = bpy.context.preferences.addons['cycles'].preferences
    for kind in ('OPTIX', 'CUDA'):
        try:
            prefs.compute_device_type = kind
            prefs.get_devices()
        except Exception:
            continue
        if any(d.type == kind for d in prefs.devices):
            for d in prefs.devices:
                d.use = d.type == kind
            scene.cycles.device = 'GPU'
            return kind
    return 'CPU'


def tint_materials(objs, k):
    """Every material's base colour times k (glb_to_mesh's 'tint': the B-2's texture is too light)."""
    done = set()
    for ob in objs:
        for slot in ob.material_slots:
            m = slot.material
            if not m or m.name in done or not m.use_nodes:
                continue
            done.add(m.name)
            nt = m.node_tree
            for bs in [n for n in nt.nodes if n.bl_idname == 'ShaderNodeBsdfPrincipled']:
                sock = bs.inputs['Base Color']
                if sock.is_linked:
                    link = sock.links[0]
                    mul = nt.nodes.new('ShaderNodeMixRGB')
                    mul.blend_type, mul.inputs[0].default_value = 'MULTIPLY', 1.0
                    mul.inputs[2].default_value = (k, k, k, 1)
                    nt.links.new(link.from_socket, mul.inputs[1])
                    nt.links.new(mul.outputs[0], sock)
                else:
                    c = sock.default_value
                    sock.default_value = (c[0] * k, c[1] * k, c[2] * k, c[3])


def grey_materials(objs):
    """Every material's base colour without its hue: a Hue/Saturation node at saturation 0."""
    done = set()
    for ob in objs:
        for slot in ob.material_slots:
            m = slot.material
            if not m or m.name in done or not m.use_nodes:
                continue
            done.add(m.name)
            nt = m.node_tree
            for bs in [n for n in nt.nodes if n.bl_idname == 'ShaderNodeBsdfPrincipled']:
                sock = bs.inputs['Base Color']
                if sock.is_linked:
                    src = sock.links[0].from_socket
                    hs = nt.nodes.new('ShaderNodeHueSaturation')
                    hs.inputs['Saturation'].default_value = 0.0
                    nt.links.new(src, hs.inputs['Color'])
                    nt.links.new(hs.outputs['Color'], sock)
                else:
                    c = sock.default_value
                    y = 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]
                    sock.default_value = (y, y, y, c[3])


def material_colours(objs, table):
    for ob in objs:
        for slot in ob.material_slots:
            m = slot.material
            if m and m.name in table and m.use_nodes:
                for bs in [n for n in m.node_tree.nodes if n.bl_idname == 'ShaderNodeBsdfPrincipled']:
                    for name, value in (('Base Color', table[m.name] + (1,)), ('Alpha', 1.0)):
                        s = bs.inputs[name]
                        for l in list(s.links):
                            m.node_tree.links.remove(l)
                        s.default_value = value


def render(key):
    cfg = MODELS[KEYS[key]]
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    bpy.ops.import_scene.gltf(filepath=str(CCBY / cfg['glb']))
    keep = KEEP.get(key)
    for ob in list(scene.objects):
        if ob.type != 'MESH':
            continue
        pts = [ob.matrix_world @ v.co for v in ob.data.vertices]
        if not pts:
            continue
        box = (tuple(min(p[i] for p in pts) for i in range(3)), tuple(max(p[i] for p in pts) for i in range(3)))
        if cfg['drop'](ob.name, box) and not (keep and keep.match(ob.name)):
            bpy.data.objects.remove(ob, do_unlink=True)
    # the landing gear left inside airframe objects, face by face, as in the game mesh (cfg cut)
    if cfg.get('cut'):
        for ob in list(scene.objects):
            if ob.type == 'MESH':
                ob.data = ob.data.copy()
                cut_faces(ob, cfg['cut'])
    # the wells and bays the cut opens, closed as in the game mesh (cfg patch)
    patch_object(cfg)
    meshes = [ob for ob in scene.objects if ob.type == 'MESH']
    look = LOOK.get(key, {})
    if look.get('grey'):
        grey_materials(meshes)
    tint = look.get('tint', cfg.get('tint', 1.0))
    if tint != 1.0:
        tint_materials(meshes, tint)
    material_colours(meshes, cfg.get('mat_colour', {}))

    # inner: the model turned nose to -X (right wing +Y) and centred; spin: the turntable
    inner = bpy.data.objects.new('inner', None)
    spin = bpy.data.objects.new('spin', None)
    scene.collection.objects.link(inner)
    scene.collection.objects.link(spin)
    for ob in list(scene.objects):
        if ob not in (inner, spin) and ob.parent is None:
            ob.parent = inner
    inner.rotation_euler = (0, 0, math.radians(cfg.get('yaw', 0.0)))
    bpy.context.view_layer.update()
    pts = [ob.matrix_world @ Vector(c) for ob in meshes for c in ob.bound_box]
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    inner.location = -(lo + hi) / 2
    inner.parent = spin
    size = hi - lo
    r = math.hypot(size.x, size.y) / 2

    cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam'))
    scene.collection.objects.link(cam)
    scene.camera = cam
    cam.data.type = 'ORTHO'
    cam.data.ortho_scale = 2 * r * 1.08
    d = Vector((-21, -27, math.hypot(21, 27) * math.tan(math.radians(look.get('elevation', 17.8))))).normalized()
    cam.location = d * (r * 4 + 20)
    forward = -d
    right = forward.cross(Vector((0, 0, 1))).normalized()
    up = right.cross(forward).normalized()
    cam.rotation_euler = Matrix((right, up, -forward)).transposed().to_quaternion().to_euler()
    cam.data.clip_end = r * 10 + 100

    def sun(name, energy, rot, colour):
        l = bpy.data.objects.new(name, bpy.data.lights.new(name, 'SUN'))
        l.data.energy, l.data.color, l.data.angle = energy, colour, math.radians(8)
        l.rotation_euler = tuple(math.radians(a) for a in rot)
        scene.collection.objects.link(l)
    sun('key', 3.2, (38, 0, 205), (1.0, 0.97, 0.92))
    sun('fill', 0.9, (70, 0, 20), (0.85, 0.9, 1.0))
    world = bpy.data.worlds.new('w')
    scene.world = world
    world.use_nodes = True
    world.node_tree.nodes['Background'].inputs['Color'].default_value = (0.32, 0.34, 0.36, 1)
    world.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.4

    scene.render.engine = 'CYCLES'
    device = gpu(scene)
    scene.cycles.samples = 32
    scene.cycles.use_denoising = True
    scene.render.resolution_x, scene.render.resolution_y, scene.render.resolution_percentage = 1024, 640, 100
    scene.render.film_transparent = True
    scene.render.image_settings.color_mode = 'RGBA'
    scene.view_settings.exposure = look.get('exposure', -0.25)
    out = HERE / 'turntable' / key
    out.mkdir(parents=True, exist_ok=True)
    print('TURNTABLE', key, 'size', tuple(round(v, 2) for v in size), 'device', device)
    for i in range(FRAMES):
        spin.rotation_euler = (0, 0, math.radians(i * STEP))
        scene.render.filepath = str(out / ('f%02d.png' % i))
        bpy.ops.render.render(write_still=True)
    print('TURNTABLE DONE', key)


args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
for key in args or list(KEYS):
    render(key)
