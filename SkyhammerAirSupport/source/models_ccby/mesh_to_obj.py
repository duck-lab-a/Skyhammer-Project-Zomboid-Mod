# python mesh_to_obj.py in.mesh out.obj [--parts]  : SHA1 mesh -> OBJ with vertex RGB (or part colours)
import struct, sys
src, dst = sys.argv[1], sys.argv[2]
by_part = '--parts' in sys.argv
pal = [(.55, .55, .55), (1, .2, .2), (.2, .5, 1), (1, .8, .1), (.2, 1, .3), (1, .3, 1)]
d = open(src, 'rb').read()
n = struct.unpack('>I', d[4:8])[0]
f = struct.unpack('>%df' % (n * 10), d[8:8 + n * 40])
out = []
for i in range(n):
    v = f[i * 10:i * 10 + 10]
    c = pal[int(v[9] + .1) % len(pal)] if by_part else v[6:9]
    out.append('v %.4f %.4f %.4f %.3f %.3f %.3f' % (*v[:3], *c))
for i in range(n // 3):
    out.append('f %d %d %d' % (i * 3 + 1, i * 3 + 2, i * 3 + 3))
open(dst, 'w').write('\n'.join(out) + '\n')
