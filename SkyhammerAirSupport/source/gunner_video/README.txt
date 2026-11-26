AC-130 gunner seat entry video (42/media/videos/sh_ac130_entry.bik), since 2026-10-24 evening.

Source: the user's own clip, AI-generated with Google Gemini (credited in common/CREDITS.txt):
  C:\Users\user\Downloads\AC-130_gunship_cinematic_generation_1080p_20261024210812.mp4
  1920x1080, 24 fps, 108 frames (4.5 s), 48 kHz stereo sound. One video for day and night.

1. Frames with Blender 5.2, view transform Standard (source/gunner_video/decode.py):
     blender -b --factory-startup -P decode.py -- src.mp4 <full> frames 1 108 1 1920 1080
2. prep_entry.py <full> <out>: each frame cropped to 1690x951 from the top left, which leaves out
   the generator's sparkle mark in the bottom right corner, and scaled to 1280x720 (the size the
   seat opens it at: Skyhammer_Gunner VIDEO.w x VIDEO.h, VIDEO.ms 4500); the five fallback stills
   <out>/stills/entry_1..5.png (960x540) go to 42/media/textures/SH_Gunner.
3. Bink 1 with RAD Video Tools (radgametools.com/bnkdown.htm, RADTools.7z, password RAD, unpacked
   with 7-Zip):
     radvideo64.exe Binkc "f???.png*1-108" sh_ac130_entry.bik /V100 /F24 /D2000000 /O /#
   -> 8.4 MB. Check a frame: radvideo64.exe BinkConv in.bik out.png /S60 /E60 /O /#
4. Its sound (the game does not play a video's own sound): Blender's aud module, 0-4.5 s, mixed to
   mono 44.1 kHz 16-bit, peaked at -1 dBFS with a 60 ms fade out: sh_seat_entry_master.wav here,
   copied to 42/media/sound/skyhammer_seat/sh_seat_entry.wav (SH_Seat_Entry, played as the seat
   is taken; source/make_seat_placeholders.py copies it too).

Night (2026-10-25): the user's night clip C:\Users\user\Downloads\ac-130 night.mp4 (Gemini, the
same 1920x1080 24 fps 4.5 s with the same mark), the same steps 1-3 -> sh_ac130_entry_night.bik
(8.8 MB; Skyhammer_Gunner plays it when G.Scene says "night", 22:00-6:00). Its sound: ffmpeg 0-4.5 s
mono 44.1 kHz, peaked at -1 dBFS with a 60 ms fade out -> sh_seat_entry_night_master.wav here,
42/media/sound/skyhammer_seat/sh_seat_entry_night.wav (SH_Seat_EntryNight).
(Run radvideo64.exe from PowerShell/cmd: Git Bash turns /V100 and the like into paths.)

Before: two FlightGear-model renders (day / night, 6.5 s); replaced by this clip.
