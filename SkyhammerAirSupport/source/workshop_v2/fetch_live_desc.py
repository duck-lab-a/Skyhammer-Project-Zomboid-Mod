# Reads the live Workshop titles and descriptions (English and Korean) of the main and Vanilla
# items through the logged-in Steam client (read only: a UGC details query, long descriptions on,
# no cache) and compares them with main_/vanilla_en.txt / _ko.txt and metadata_config.json, so an
# upload never overwrites an edit made on the Steam page. Writes live_<edition>_<lang>.txt.
# usage: python fetch_live_desc.py            (Project Zomboid must not be running)
import ctypes, os, sys, time, json

HERE = os.path.dirname(os.path.abspath(__file__))
DLL = r"C:\Program Files (x86)\Steam\steamapps\common\ProjectZomboid\steam_api64.dll"
APP = 108600
CFG = json.load(open(os.path.join(HERE, "metadata_config.json"), encoding="utf-8"))
ITEMS = {CFG[e]["item_id"]: e for e in ("main", "vanilla")}

os.environ["SteamAppId"] = os.environ["SteamGameId"] = str(APP)
api = ctypes.CDLL(DLL)
P, U64, U32, B, C = ctypes.c_void_p, ctypes.c_uint64, ctypes.c_uint32, ctypes.c_bool, ctypes.c_char_p
api.SteamAPI_InitFlat.restype = ctypes.c_int
api.SteamAPI_SteamUGC_v021.restype = P
api.SteamAPI_SteamUtils_v010.restype = P
api.SteamAPI_ISteamUGC_CreateQueryUGCDetailsRequest.restype = U64
api.SteamAPI_ISteamUGC_CreateQueryUGCDetailsRequest.argtypes = [P, ctypes.POINTER(U64), U32]
for f, extra in (("SetReturnLongDescription", [B]), ("SetLanguage", [C]), ("SetAllowCachedResponse", [U32])):
    getattr(api, "SteamAPI_ISteamUGC_" + f).restype = B
    getattr(api, "SteamAPI_ISteamUGC_" + f).argtypes = [P, U64] + extra
api.SteamAPI_ISteamUGC_SendQueryUGCRequest.restype = U64
api.SteamAPI_ISteamUGC_SendQueryUGCRequest.argtypes = [P, U64]
api.SteamAPI_ISteamUGC_GetQueryUGCResult.restype = B
api.SteamAPI_ISteamUGC_GetQueryUGCResult.argtypes = [P, U64, U32, P]
api.SteamAPI_ISteamUGC_ReleaseQueryUGCRequest.restype = B
api.SteamAPI_ISteamUGC_ReleaseQueryUGCRequest.argtypes = [P, U64]
api.SteamAPI_ISteamUtils_IsAPICallCompleted.restype = B
api.SteamAPI_ISteamUtils_IsAPICallCompleted.argtypes = [P, U64, ctypes.POINTER(B)]
api.SteamAPI_ISteamUtils_GetAPICallResult.restype = B
api.SteamAPI_ISteamUtils_GetAPICallResult.argtypes = [P, U64, P, ctypes.c_int, ctypes.c_int, ctypes.POINTER(B)]

err = ctypes.create_string_buffer(1024)
if api.SteamAPI_InitFlat(err) != 0:
    sys.exit("SteamAPI_InitFlat failed: " + err.value.decode(errors="replace"))
ugc, utils = api.SteamAPI_SteamUGC_v021(), api.SteamAPI_SteamUtils_v010()

# SteamUGCDetails_t: id u64, result i32, file type i32, creator app u32, consumer app u32, then
# title char[129] (offset 24) and description char[8000] (offset 153); the rest is not read
TITLE_AT, TITLE_LEN, DESC_AT, DESC_LEN = 24, 129, 153, 8000


def query(lang):
    ids = (U64 * len(ITEMS))(*ITEMS)
    h = api.SteamAPI_ISteamUGC_CreateQueryUGCDetailsRequest(ugc, ids, len(ITEMS))
    assert api.SteamAPI_ISteamUGC_SetReturnLongDescription(ugc, h, True)
    assert api.SteamAPI_ISteamUGC_SetLanguage(ugc, h, lang.encode())
    api.SteamAPI_ISteamUGC_SetAllowCachedResponse(ugc, h, 0)
    call = api.SteamAPI_ISteamUGC_SendQueryUGCRequest(ugc, h)
    failed = B(False)
    t0 = time.time()
    while not api.SteamAPI_ISteamUtils_IsAPICallCompleted(utils, call, ctypes.byref(failed)):
        api.SteamAPI_RunCallbacks()
        if time.time() - t0 > 60:
            sys.exit("query timed out")
        time.sleep(0.2)
    res = (ctypes.c_ubyte * 512)()
    ok = api.SteamAPI_ISteamUtils_GetAPICallResult(utils, call, res, 280, 3401, ctypes.byref(failed))
    n = int.from_bytes(bytes(res[12:16]), "little")
    out = {}
    for i in range(n):
        buf = ctypes.create_string_buffer(20000)
        assert api.SteamAPI_ISteamUGC_GetQueryUGCResult(ugc, h, i, buf)
        raw = buf.raw
        item = int.from_bytes(raw[0:8], "little")
        title = raw[TITLE_AT:TITLE_AT + TITLE_LEN].split(b"\0", 1)[0].decode("utf-8")
        desc = raw[DESC_AT:DESC_AT + DESC_LEN].split(b"\0", 1)[0].decode("utf-8")
        out[item] = (title, desc)
    api.SteamAPI_ISteamUGC_ReleaseQueryUGCRequest(ugc, h)
    print(f"{lang}: call ok={ok} failed={failed.value} results={n}")
    return out


def norm(s): return s.replace("\r\n", "\n").rstrip("\n")


same = True
for lang, suffix in (("english", "en"), ("koreana", "ko")):
    for item, (title, desc) in query(lang).items():
        e = ITEMS[item]
        open(os.path.join(HERE, f"live_{e}_{suffix}.txt"), "w", encoding="utf-8", newline="\n").write(desc)
        local = norm(open(os.path.join(HERE, f"{e}_{suffix}.txt"), encoding="utf-8").read())
        t_ok = title == CFG[e]["titles"][lang]
        d_ok = norm(desc) == local
        same = same and t_ok and d_ok
        print(f"  {e} {lang}: title {'same' if t_ok else 'DIFFERS: ' + repr(title)}; description "
              f"{'same' if d_ok else 'DIFFERS'} ({len(norm(desc).encode())} live / {len(local.encode())} local bytes)")
api.SteamAPI_Shutdown()
print("ALL SAME" if same else "DIFFERENCES")
