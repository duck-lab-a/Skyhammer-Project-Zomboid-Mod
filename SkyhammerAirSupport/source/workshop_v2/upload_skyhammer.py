# Uploads a staged Skyhammer edition to its existing Workshop item through the Steam client that is
# already logged in (Steamworks UGC, the calls the game's own uploader makes); no login or password.
# Made from mods/HeliFastTravel/source/upload.py.
#   1. the Korean description (language "koreana") from main_ko.txt / vanilla_ko.txt
#   2. the content folder, the English description (main_en.txt / vanilla_en.txt) and the change note
# Korean/English titles and mandatory ID footers are validated and sent explicitly.
# Tags, visibility and the preview picture are preserved. --metadata-only changes no content.
# (2026-11-26) --preview FILE also replaces the preview (an animated GIF works; Steam wants it under 1 MB);
# the game's own uploader would reset it to preview.png.
# usage:
#   python upload_skyhammer.py main|vanilla changenote.txt            checks only, nothing is sent
#   python upload_skyhammer.py main|vanilla changenote.txt --upload   uploads (Project Zomboid must not be running)
#   ... --preview vp2_480.gif                                         also sets the preview picture
import ctypes, os, sys, time, json
from metadata_rules import validate_metadata

HERE = os.path.dirname(os.path.abspath(__file__))
WORKSHOP = r"C:\Users\user\Zomboid\Workshop"
# (the add-ons: their files and the change note only; their Steam descriptions are left as they are)
EDITIONS = {
    "main": ("SkyhammerAirSupport", "main_ko.txt"),
    "vanilla": ("SkyhammerAirSupportVanilla", "vanilla_ko.txt"),
    "thor": ("SkyhammerThor", None),
    "wraith": ("SkyhammerWraith", None),
}
DLL = r"C:\Program Files (x86)\Steam\steamapps\common\ProjectZomboid\steam_api64.dll"
APP = 108600
LIMIT = 8000          # Steam's description limit, in bytes (CRLF counted)

if len(sys.argv) < 3 or sys.argv[1] not in EDITIONS:
    sys.exit(__doc__ or "usage: upload_skyhammer.py main|vanilla changenote.txt [--upload]")
edition = sys.argv[1]
modid, ko_file = EDITIONS[edition]
stage = os.path.join(WORKSHOP, modid)
txt = open(os.path.join(stage, "workshop.txt"), encoding="utf-8").read().replace("\r\n", "\n").split("\n")
item = int(next(l.split("=", 1)[1] for l in txt if l.startswith("id=")))
title = next(l.split("=", 1)[1] for l in txt if l.startswith("title="))
desc_en = "\n".join(l.split("=", 1)[1] for l in txt if l.startswith("description="))
# (2026-11-16) workshop.txt carries the description without the ID footer (the game's uploader
# shows it as is); Steam gets the full English text, footer included, from main_en.txt / vanilla_en.txt
if ko_file:
    en_path = os.path.join(HERE, ko_file.replace("_ko.txt", "_en.txt"))
    desc_en = open(en_path, encoding="utf-8").read().replace("\r\n", "\n").rstrip("\n")
desc_ko = open(os.path.join(HERE, ko_file), encoding="utf-8").read().replace("\r\n", "\n").rstrip("\n") if ko_file else None
note = open(sys.argv[2], encoding="utf-8").read().replace("\r\n", "\n").strip()
content = os.path.join(stage, "Contents")
preview = os.path.abspath(sys.argv[sys.argv.index("--preview") + 1]) if "--preview" in sys.argv else None

def crlf_bytes(s): return len(s.replace("\n", "\r\n").encode("utf-8"))
problems = []
metadata_only = "--metadata-only" in sys.argv
metadata = None
if ko_file:
    with open(os.path.join(HERE, "metadata_config.json"), encoding="utf-8") as f:
        metadata = json.load(f)[edition]
    problems.extend(validate_metadata(metadata, item, modid, title,
        {"english": desc_en, "koreana": desc_ko}))
elif metadata_only:
    problems.append("metadata-only mode is supported for main and vanilla only")
if not os.path.isfile(os.path.join(content, "mods", modid, "42", "mod.info")): problems.append("no mod.info in the staged content")
if os.path.isdir(os.path.join(content, "mods", modid, "source")): problems.append("a source folder is in the staged content")
for name, d in (("EN", desc_en if ko_file else ""), ("KO", desc_ko or "")):
    if crlf_bytes(d) >= LIMIT: problems.append(f"{name} description {crlf_bytes(d)} bytes >= {LIMIT}")
if not note: problems.append("the change note is empty")
if preview and not os.path.isfile(preview): problems.append(f"no preview file {preview}")
elif preview and os.path.getsize(preview) >= 1000000: problems.append(f"preview {os.path.getsize(preview)} bytes, Steam wants under 1 MB")
print(f"edition {edition}: item {item}, title {title!r}")
print(f"  content {content}")
if ko_file:
    print(f"  EN description {crlf_bytes(desc_en)} bytes, KO description {crlf_bytes(desc_ko)} bytes, change note {len(note)} chars")
else:
    print(f"  descriptions left as they are on Steam; change note {len(note)} chars")
print(f"  preview {preview} ({os.path.getsize(preview)} bytes)" if preview else "  preview kept as it is on Steam")
if problems:
    sys.exit("PROBLEM: " + "; ".join(problems))
if "--upload" not in sys.argv:
    print("checks passed; nothing sent (add --upload to send)")
    sys.exit(0)

os.environ["SteamAppId"] = os.environ["SteamGameId"] = str(APP)
api = ctypes.CDLL(DLL)
P, U64, B, C = ctypes.c_void_p, ctypes.c_uint64, ctypes.c_bool, ctypes.c_char_p
api.SteamAPI_InitFlat.restype = ctypes.c_int
api.SteamAPI_SteamUGC_v021.restype = P
api.SteamAPI_SteamUtils_v010.restype = P
api.SteamAPI_ISteamUGC_StartItemUpdate.restype = U64
api.SteamAPI_ISteamUGC_StartItemUpdate.argtypes = [P, ctypes.c_uint32, U64]
for f in ("SetItemContent", "SetItemDescription", "SetItemUpdateLanguage", "SetItemTitle", "SetItemPreview"):
    getattr(api, "SteamAPI_ISteamUGC_" + f).restype = B
    getattr(api, "SteamAPI_ISteamUGC_" + f).argtypes = [P, U64, C]
api.SteamAPI_ISteamUGC_SubmitItemUpdate.restype = U64
api.SteamAPI_ISteamUGC_SubmitItemUpdate.argtypes = [P, U64, C]
api.SteamAPI_ISteamUGC_GetItemUpdateProgress.restype = ctypes.c_int
api.SteamAPI_ISteamUGC_GetItemUpdateProgress.argtypes = [P, U64, ctypes.POINTER(U64), ctypes.POINTER(U64)]
api.SteamAPI_ISteamUtils_IsAPICallCompleted.restype = B
api.SteamAPI_ISteamUtils_IsAPICallCompleted.argtypes = [P, U64, ctypes.POINTER(B)]
api.SteamAPI_ISteamUtils_GetAPICallResult.restype = B
api.SteamAPI_ISteamUtils_GetAPICallResult.argtypes = [P, U64, P, ctypes.c_int, ctypes.c_int, ctypes.POINTER(B)]


class SubmitResult(ctypes.Structure):          # SubmitItemUpdateResult_t (callback 3404)
    _pack_ = 8
    _fields_ = [("result", ctypes.c_int32), ("legal", ctypes.c_bool), ("file", ctypes.c_uint64)]


err = ctypes.create_string_buffer(1024)
rc = api.SteamAPI_InitFlat(err)
if rc != 0:
    sys.exit(f"SteamAPI_InitFlat failed ({rc}): {err.value.decode(errors='replace')}")
ugc, utils = api.SteamAPI_SteamUGC_v021(), api.SteamAPI_SteamUtils_v010()


def submit(label, setup, change_note):
    h = api.SteamAPI_ISteamUGC_StartItemUpdate(ugc, APP, item)
    setup(h)
    call = api.SteamAPI_ISteamUGC_SubmitItemUpdate(ugc, h, change_note.encode("utf-8") if change_note is not None else None)
    failed = B(False)
    last = None
    while not api.SteamAPI_ISteamUtils_IsAPICallCompleted(utils, call, ctypes.byref(failed)):
        api.SteamAPI_RunCallbacks()
        done, total = U64(0), U64(0)
        st = api.SteamAPI_ISteamUGC_GetItemUpdateProgress(ugc, h, ctypes.byref(done), ctypes.byref(total))
        if (st, done.value) != last:
            print(f"  {label}: status {st} {done.value}/{total.value}", flush=True)
            last = (st, done.value)
        time.sleep(0.5)
    res = SubmitResult()
    ok = api.SteamAPI_ISteamUtils_GetAPICallResult(utils, call, ctypes.byref(res), ctypes.sizeof(res), 3404, ctypes.byref(failed))
    print(f"{label}: call ok={ok} failed={failed.value} EResult={res.result} needs legal={res.legal} file={res.file}", flush=True)
    return ok and not failed.value and res.result == 1


def ko(h):
    assert api.SteamAPI_ISteamUGC_SetItemUpdateLanguage(ugc, h, b"koreana")
    assert api.SteamAPI_ISteamUGC_SetItemTitle(ugc, h, metadata["titles"]["koreana"].encode("utf-8"))
    assert api.SteamAPI_ISteamUGC_SetItemDescription(ugc, h, desc_ko.encode("utf-8"))


def main(h):
    if not metadata_only:
        assert api.SteamAPI_ISteamUGC_SetItemContent(ugc, h, content.encode("utf-8"))
    if preview:
        assert api.SteamAPI_ISteamUGC_SetItemPreview(ugc, h, preview.encode("utf-8"))
    if ko_file:
        assert api.SteamAPI_ISteamUGC_SetItemUpdateLanguage(ugc, h, b"english")
        assert api.SteamAPI_ISteamUGC_SetItemTitle(ugc, h, metadata["titles"]["english"].encode("utf-8"))
        assert api.SteamAPI_ISteamUGC_SetItemDescription(ugc, h, desc_en.encode("utf-8"))


ok1 = submit("korean description", ko, None) if ko_file else True
ok2 = submit("metadata" if metadata_only else "update", main, None if metadata_only else note)
api.SteamAPI_Shutdown()
print("DONE" if ok1 and ok2 else "PROBLEM")
sys.exit(0 if ok1 and ok2 else 1)
