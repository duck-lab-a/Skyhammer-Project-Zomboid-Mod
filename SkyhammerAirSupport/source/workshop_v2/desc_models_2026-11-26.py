# 2026-11-26 (user): the new 3D models picture into both descriptions, the killstreak picture out, and
# in the Vanilla edition a short note that the terminal shows the aircraft in 3D (Skyhammer_Viewer.lua:
# a click on a tab's aircraft picture turns its model, pre-rendered from the same CC BY models).
# Exact replacements, each must match once; CRLF kept. Edits main_/vanilla_ en/ko and both staged workshop.txt.
from pathlib import Path

HERE = Path(__file__).resolve().parent
WS = Path(r"C:\Users\user\Zomboid\Workshop")
MODELS = "[img]https://i.ibb.co/cmQSwQK/3d.jpg[/img]"
STRIP = "[img]https://i.ibb.co/xK1k7X0k/SUPPORT-STRIP.png[/img]"
KILL = "[img]https://i.ibb.co/n8jjJ5Z4/vanilla-05-killstreak-420.jpg[/img]"
NOTE = {
    "en": ("Aircraft appear as [b]ground shadows[/b].",
           "Aircraft appear as [b]ground shadows[/b], and in 3D in the terminal."),
    "ko": ("기체는 [b]지면 그림자[/b]로 보입니다.",
           "기체는 [b]지면 그림자[/b]로, 단말기에서는 3D로 보입니다."),
}


def edit(path, prefix, lang, vanilla):
    s = path.read_bytes().decode("utf-8")
    def rep(a, b):
        nonlocal s
        assert s.count(a) == 1, (path.name, s.count(a), a[:60])
        s = s.replace(a, b)
    rep(prefix + KILL + "\r\n", "")
    rep(prefix + STRIP + "\r\n", prefix + STRIP + "\r\n" + prefix + MODELS + "\r\n")
    if vanilla:
        rep(*NOTE[lang])
    path.write_bytes(s.encode("utf-8"))
    print(path, len(s.encode("utf-8")), "bytes")


for ed, vanilla in (("main", False), ("vanilla", True)):
    for lang in ("en", "ko"):
        edit(HERE / f"{ed}_{lang}.txt", "", lang, vanilla)
edit(WS / "SkyhammerAirSupport" / "workshop.txt", "description=", "en", False)
edit(WS / "SkyhammerAirSupportVanilla" / "workshop.txt", "description=", "en", True)
