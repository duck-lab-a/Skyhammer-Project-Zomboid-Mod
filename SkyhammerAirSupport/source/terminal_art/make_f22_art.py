"""The terminal's F-22 picture (SH_Art_F22): the CC-BY F-22 model (models_ccby/f22, manilov.ap, "F22")
rendered with its own textures from the A-10 picture's angle (make_a10_art.py: front-right, above), on
a clear background. package_f22_art.py then crops it to the 512 px picture and makes the tab icon.
Run: blender -b --factory-startup --python make_f22_art.py"""
from pathlib import Path
import math, re
import bpy
from mathutils import Vector, Matrix

HERE = Path(__file__).resolve().parent
MOD = HERE.parents[1]
GLB = MOD / 'source/models_ccby/f22/f22.glb'
# left out: landing gear (it flies), and the parts glb_to_mesh.py leaves out as hidden inside the
# airframe; the cockpit stays (it shows through the canopy here)
DROP = re.compile(r'(Nose_Gear|Nose_Wheel|Left_Main_Gear|Right_Main_Gear|Left_MGear|Right_MGear|Left_Nose_Gear|'
                  r'Right_Nose_Gear|Left_Front_Turbina|Right_Front_Turbina|Left_Back_Turbina|Right_Back_Turbina|'
                  r'OilTank|ILS|Box\d|Left_Rocket_Bay-|Right_Rocket_Bay-)')

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(GLB))
scene = bpy.context.scene
for ob in list(scene.objects):
    if ob.type == 'MESH' and DROP.match(ob.name):
        bpy.data.objects.remove(ob, do_unlink=True)

# the fuselage is 51.5 deg off Blender X with the nose toward -x/-y (glb_to_mesh.py): turn the whole
# model about Z so the nose is -X and the right wing +Y, centred on its bounding box
pivot = bpy.data.objects.new('pivot', None)
scene.collection.objects.link(pivot)
for ob in scene.objects:
    if ob is not pivot and ob.parent is None:
        ob.parent = pivot
pivot.rotation_euler = (0, 0, math.radians(-51.5))
bpy.context.view_layer.update()
pts = [ob.matrix_world @ Vector(c) for ob in scene.objects if ob.type == 'MESH' for c in ob.bound_box]
lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
pivot.location = -(lo + hi) / 2
bpy.context.view_layer.update()
print('F22 box', tuple(round(v, 2) for v in hi - lo))

# the A-10 picture's camera, from game space (+X right wing, +Y up, +Z nose) to this one
# (nose -X, right wing +Y, up +Z): game (27, 11, 21) looking at (0, 0.5, 0)
cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam'))
scene.collection.objects.link(cam)
scene.camera = cam
cam.data.type = 'ORTHO'
cam.data.ortho_scale = 24
cam.location = Vector((-21, -27, 11))
target = Vector((0, 0, 0.5))
forward = (target - cam.location).normalized()
right = forward.cross(Vector((0, 0, 1))).normalized()
up = right.cross(forward).normalized()
cam.rotation_euler = Matrix((right, up, -forward)).transposed().to_quaternion().to_euler()

# light: a key from above and in front, a cool fill from the other side, a dim grey sky
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
scene.cycles.samples = 64
scene.cycles.use_denoising = True
scene.render.resolution_x, scene.render.resolution_y, scene.render.resolution_percentage = 2560, 1280, 100
scene.render.film_transparent = True
scene.render.image_settings.color_mode = 'RGBA'
scene.view_settings.exposure = -0.25
scene.render.filepath = str(HERE / 'SH_Art_F22_native.png')
bpy.ops.render.render(write_still=True)
print('RENDERED', scene.render.filepath)
