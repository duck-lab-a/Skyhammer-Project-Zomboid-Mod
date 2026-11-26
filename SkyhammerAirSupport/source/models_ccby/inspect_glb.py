# Blender (headless): blender -b --python inspect_glb.py -- <file.glb>
# Prints each mesh object: name, parent, triangles, materials (with image textures), world bounding box.
import bpy, sys
from mathutils import Vector

path = sys.argv[sys.argv.index('--') + 1]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=path)
dg = bpy.context.evaluated_depsgraph_get()
total = 0
lo = Vector((1e9, 1e9, 1e9)); hi = Vector((-1e9, -1e9, -1e9))
for ob in bpy.context.scene.objects:
    if ob.type != 'MESH':
        continue
    me = ob.evaluated_get(dg).to_mesh()
    me.calc_loop_triangles()
    tris = len(me.loop_triangles)
    total += tris
    pts = [ob.matrix_world @ v.co for v in me.vertices]
    if pts:
        a = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
        b = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
        lo = Vector(map(min, lo, a)); hi = Vector(map(max, hi, b))
    else:
        a = b = Vector()
    mats = []
    for m in ob.data.materials:
        if m is None:
            continue
        imgs = [n.image.name + '%dx%d' % tuple(n.image.size) for n in (m.node_tree.nodes if m.use_nodes else []) if n.type == 'TEX_IMAGE' and n.image]
        col = None
        if m.use_nodes:
            for n in m.node_tree.nodes:
                if n.type == 'BSDF_PRINCIPLED':
                    col = tuple(round(c, 2) for c in n.inputs['Base Color'].default_value[:3])
        mats.append('%s%s%s' % (m.name, ' col=' + str(col) if col else '', ' tex=' + ','.join(imgs) if imgs else ''))
    print('OBJ %-28s parent=%-18s tris=%6d  box=(%.2f,%.2f,%.2f)-(%.2f,%.2f,%.2f)  %s' % (
        ob.name[:28], (ob.parent.name if ob.parent else '-')[:18], tris, a.x, a.y, a.z, b.x, b.y, b.z, ' | '.join(mats)))
    ob.evaluated_get(dg).to_mesh_clear()
print('TOTAL tris=%d  box=(%.2f,%.2f,%.2f)-(%.2f,%.2f,%.2f) size=(%.2f,%.2f,%.2f)' % (total, lo.x, lo.y, lo.z, hi.x, hi.y, hi.z, hi.x - lo.x, hi.y - lo.y, hi.z - lo.z))
