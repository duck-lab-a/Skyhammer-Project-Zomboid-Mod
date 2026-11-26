# blender -b -P decode.py -- <src.mp4> <outdir> <mode> [start end step w h]
#   mode probe: prints fps/frames/size and renders every step-th frame small
#   mode frames: renders frames start..end (source frame numbers) every step at w x h
#   mode audio: mixes the audio of start..end down to <outdir>/audio.wav
import bpy, sys, os

a = sys.argv[sys.argv.index("--") + 1:]
src, out, mode = a[0], a[1], a[2]
os.makedirs(out, exist_ok=True)
sc = bpy.context.scene
se = sc.sequence_editor_create()
coll = se.strips if hasattr(se, "strips") else se.sequences
v = coll.new_movie("v", src, channel=1, frame_start=1)
fps = v.fps
sc.render.fps = int(round(fps))
sc.render.fps_base = sc.render.fps / fps
n = v.frame_final_duration
w0, h0 = v.elements[0].orig_width, v.elements[0].orig_height
print("PROBE fps=%.3f frames=%d size=%dx%d" % (fps, n, w0, h0))
# (Blender's default view transform would wash the colours out: the frames as they are)
sc.view_settings.view_transform = "Standard"
sc.view_settings.look = "None"
sc.render.image_settings.file_format = "PNG"
sc.render.image_settings.color_mode = "RGB"
sc.render.resolution_percentage = 100
if mode == "probe":
    step = int(a[3]) if len(a) > 3 else 15
    sc.render.resolution_x, sc.render.resolution_y = 480, 270
    for f in range(1, n + 1, step):
        sc.frame_set(f)
        sc.render.filepath = os.path.join(out, "p%04d.png" % f)
        bpy.ops.render.render(write_still=True)
elif mode == "frames":
    s, e, step, w, h = (int(x) for x in a[3:8])
    sc.render.resolution_x, sc.render.resolution_y = w, h
    k = 0
    for f in range(s, e + 1, step):
        k += 1
        sc.frame_set(f)
        sc.render.filepath = os.path.join(out, "f%03d.png" % k)
        bpy.ops.render.render(write_still=True)
    print("FRAMES", k)
elif mode == "audio":
    s, e = int(a[3]), int(a[4])
    coll.new_sound("a", src, channel=2, frame_start=1)
    sc.frame_start, sc.frame_end = s, e
    bpy.ops.sound.mixdown(filepath=os.path.join(out, "audio.wav"), container="WAV", codec="PCM",
                          format="S16", mixrate=44100, channels="STEREO")
    print("AUDIO done")
