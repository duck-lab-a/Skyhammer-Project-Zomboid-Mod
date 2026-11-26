# The gunner seat's per-weapon zoom (2026-10-25, the user: "the 25/40/105 cameras feel jumbled on
# entry, not lined up"). The game eases its zoom: Core.getZoom is the picture's zoom on its way,
# getNextZoom / doZoomScroll work on the target level (MultiTextureFBO2, decompiled). The seat must
# land on each weapon's own level whatever the picture is doing, keep the wheel's target, and put
# it back once Viewpoint has switched to its isometric view.
# Run: <codex python> -I source/tests/runsim.py source/tests/sim_gunner_zoom.py
import sys
import sim_gunner_realview as rv

EASE = r"""
-- the user's zoom levels (options.ini zoomLevels2x), wider = larger
LEVELS = { 0.25, 0.5, 0.75, 1.25, 1.5, 1.75, 2.0, 2.25, 2.5 }
TARGET, SHOWN = 1.25, 1.25
local function at(v) for i, l in ipairs(LEVELS) do if l == v then return i end end end
local core = getCore()
core.getZoom = function() return SHOWN end
core.getNextZoom = function(_, _, dir)
    local i = at(TARGET)
    if not i or dir == 0 then return TARGET end
    return LEVELS[math.max(1, math.min(#LEVELS, i + (dir > 0 and 1 or -1)))]
end
core.doZoomScroll = function(_, _, dir) TARGET = core.getNextZoom(nil, 0, dir); ZSTEPS = ZSTEPS + dir end
function ease() SHOWN = TARGET end
"""


def world(viewpoint=False):
    L = rv.world(viewpoint=viewpoint)
    L.execute(EASE)
    return L


TESTS = []
def test(fn): TESTS.append(fn); return fn
def check(c, what):
    if not c: raise AssertionError(what)


@test
def each_weapon_lands_on_its_own_level_mid_ease():
    L = world()
    L.execute("G.Enter()")
    check(L.eval("TARGET") == 1.75, f"40mm on entry: {L.eval('TARGET')}")
    # switched while the picture is still on its way (SHOWN not caught up)
    L.execute("G.Screen():setWeapon('he')")
    check(L.eval("TARGET") == 2.5, f"105: {L.eval('TARGET')}")
    L.execute("G.Screen():setWeapon('gun25')")
    check(L.eval("TARGET") == 1.5, f"25mm right after the 105, picture mid-ease: {L.eval('TARGET')}")
    L.execute("G.Screen():setWeapon('gun')")
    check(L.eval("TARGET") == 1.75, f"40mm again: {L.eval('TARGET')}")


@test
def the_wheel_keeps_the_target_level():
    L = world()
    L.execute("G.Enter(); ease(); G.Screen():onMouseWheel(-1)")    # one level in, picture not there yet
    check(L.eval("G.Screen().zooms.gun") == 1.5, f"the 40mm keeps the level it is going to: {L.eval('G.Screen().zooms.gun')}")
    L.execute("G.Screen():setWeapon('he'); G.Screen():setWeapon('gun')")
    check(L.eval("TARGET") == 1.5, f"and comes back to it: {L.eval('TARGET')}")


@test
def viewpoint_switch_does_not_leave_another_zoom():
    L = world(viewpoint=True)
    # Viewpoint's isometric view puts back the zoom it had (here: 0.75) when it is switched to
    L.execute("""
    local cycle = Viewpoint.View.cycle
    Viewpoint.View.cycle = function() cycle(); if VIEW == 'isometric' then TARGET = 0.75; SHOWN = 0.75 end end
    G.Enter(); frames(1500)""")
    check(L.eval("VIEW") == "isometric", f"switched: {L.eval('VIEW')}")
    check(L.eval("TARGET") == 1.75, f"the 40mm's level once the view is isometric: {L.eval('TARGET')}")


if __name__ == "__main__":
    ok = 0
    for t in TESTS:
        try:
            t(); ok += 1; print("PASS", t.__name__)
        except Exception as e:
            print("FAIL", t.__name__, "-", str(e).splitlines()[0][:200])
    print(f"{ok}/{len(TESTS)} passed")
    sys.exit(0 if ok == len(TESTS) else 1)
