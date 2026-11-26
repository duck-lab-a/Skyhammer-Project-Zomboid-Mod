# Blender (headless): blender -b --factory-startup --python render_preview.py -- out.png view a.obj [b.obj ...]
# view: top | side | three. OBJ files are in game space (+X starboard, +Y up, +Z nose) with vertex
# RGB; they are laid out left to right and rendered with Workbench, flat vertex colours, lit.
import bpy, sys
from mathutils import Vector

args = sys.argv[sys.argv.index('--') + 1:]
out, view, objs = args[0], args[1], args[2:]
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.engine = 'BLENDER_WORKBENCH'
sc.display.shading.light = 'STUDIO'
sc.display.shading.color_type = 'VERTEX'
sc.view_settings.view_transform = 'Standard'
sc.render.resolution_x = 700 * len(objs)
sc.render.resolution_y = 520
x0 = 0.0
items = []
for path in objs:
    # file Y up -> Blender Z up; file +Z (nose) -> Blender +Y; file +X (starboard) -> Blender -X
    bpy.ops.wm.obj_import(filepath=path, forward_axis='Y', up_axis='Z')
    ob = bpy.context.selected_objects[0]
    ob.rotation_euler = (1.5707963, 0, 0)   # file Y-up to Z-up
    ob.scale = (1, 1, -1)                   # (scale runs first) nose to +Y; starboard stays +X (game space is left-handed)
    bpy.context.view_layer.update()
    size = max(ob.dimensions)
    ob.location.x = x0 + size / 2
    items.append(ob)
    x0 += size * 1.2
cx = x0 / 2
cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam'))
sc.collection.objects.link(cam)
cam.data.type = 'ORTHO'
cam.data.ortho_scale = x0 * 1.02
far = x0 * 3
if view == 'top':
    cam.location = Vector((cx, 0, far))
elif view == 'side':
    cam.location = Vector((cx, -far, 0.5))
else:
    cam.location = Vector((cx - far * 0.3, -far * 0.55, far * 0.45))
d = Vector((cx, 0, 0)) - cam.location
cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
sc.camera = cam
sc.render.filepath = out
bpy.ops.render.render(write_still=True)
print('RENDERED', out)
