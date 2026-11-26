# The AC-130 gunner seat's states (2026-10-24, the user; design: source/ac130_gunner_design.md).
# Skyhammer_Gunner (SkyhammerGunner = G): who may take the seat, what taking and leaving it does
# to the body and the game (the body stays where it is, only its movement is held; the world view
# behind the full-screen seat is not drawn), the entry video once a sortie, what ends the seat, and
# the small pure helpers (the video path, the view's reach, day or night).
# The seat's screens are made through G.makeIntro / G.makeScreen, replaced here by recorders.
# Run: <codex python> -I source/tests/runsim.py source/tests/sim_gunner_seat.py
import io, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
LUA = os.path.join(HERE, "..", "..", "42", "media", "lua")
sys.path.insert(0, HERE)
import sim_gunner as guns

UI = r"""
ISUIElement = {}
ISUIElement.__index = ISUIElement
function ISUIElement:derive(name) local o = {}; setmetatable(o, self); self.__index = self; o.Type = name; return o end
function ISUIElement:new(x, y, w, h) local o = { x = x, y = y, width = w, height = h }; setmetatable(o, self); self.__index = self; return o end
DRAW_WORLD = true
getWorld = function() return { setDrawWorld = function(_, on) DRAW_WORLD = on end } end
TERMINAL_CLOSED = 0
HALO = {}
HaloTextHelper = { addBadText = function(_, t) HALO[#HALO + 1] = t end, addText = function(_, t) HALO[#HALO + 1] = t end }
"""

PLAYER = r"""
ME.blocked = false
function ME:isBlockMovement() return self.blocked end
function ME:setBlockMovement(b) self.blocked = b end
function ME:isGodMod() return self.god == true end
function ME:setGodMod(v) self.god = v end
function ME:getVehicle() return self.vehicle end
function ME:isAsleep() return self.asleep == true end
S.CloseTerminal = function() TERMINAL_CLOSED = TERMINAL_CLOSED + 1 end
-- the screens: recorders
SHOWN = {}
G = SkyhammerGunner
G.makeIntro = function(scene) local o = { kind = 'intro', scene = scene }
    function o:show() SHOWN[#SHOWN + 1] = 'intro ' .. scene end
    function o:hide() SHOWN[#SHOWN + 1] = 'hide intro' end
    return o end
G.makeScreen = function() local o = { kind = 'seat' }
    function o:show() SHOWN[#SHOWN + 1] = 'seat' end
    function o:hide() SHOWN[#SHOWN + 1] = 'hide seat' end
    return o end
"""


def world(sandbox_off=False):
    L = guns.world()
    L.execute(UI)
    for f in ("client/Skyhammer_Feed.lua", "client/Skyhammer_GunnerHUD.lua", "client/Skyhammer_Gunner.lua"):
        L.execute(io.open(os.path.join(LUA, f), encoding="utf-8").read())
    L.execute(PLAYER)
    if sandbox_off:
        L.execute("SandboxVars.Skyhammer.GunnerSeat = false")
    return L


TESTS = []
def test(fn): TESTS.append(fn); return fn
def check(c, what):
    if not c: raise AssertionError(what)
def shown(L): return [L.eval(f"SHOWN[{i}]") for i in range(1, L.eval("#SHOWN") + 1)]
def can(L):
    return L.eval("(function() local ok, why = G.CanEnter(ME); return tostring(ok) .. ' ' .. tostring(why) end)()")


@test
def who_may_take_the_seat():
    L = world()
    check(can(L) == "true nil", f"on station, alive, on foot: {can(L)}")
    L.execute("PHASE.gun = 'INBOUND'; PHASE.he = 'INBOUND'")
    check(can(L) == "false notready", can(L))
    L = world(); L.execute("AMMO.gun = 0; AMMO.he = 0")
    check(can(L) == "false dry", can(L))
    L = world(); L.execute("ME.vehicle = {}")
    check(can(L) == "false vehicle", can(L))
    L = world(); L.execute("ME.asleep = true")
    check(can(L) == "false asleep", can(L))
    L = world(); L.execute("ME.dead = true")
    check(can(L) == "false dead", can(L))
    L = world(sandbox_off=True)
    check(can(L) == "false off", f"the server switched the seat off: {can(L)}")
    check(L.eval("S.GunnerSeatOn()") == False, "S.GunnerSeatOn() reads the sandbox")
    # (2026-10-24, the user: the seat ships single player only; online after more testing) online
    # the seat is off whatever the sandbox says: the terminal offers the 105's eyes-on mark instead
    L = world(); L.execute("ONLINE = true")
    check(can(L) == "false off" and L.eval("S.GunnerSeatOn()") == False, f"online: off for now: {can(L)}")


@test
def taking_the_seat():
    L = world()
    check(L.eval("G.Enter()") == True, "the seat is taken")
    check(L.eval("S.GunnerManned()") == True, "manned: the 40mm's own fire waits")
    check(L.eval("ME.blocked") == True, "the body's movement is held (it stays where it is)")
    # (single player: the real picture IS the world, drawn; online the map hides it, below)
    check(L.eval("DRAW_WORLD") == True, "single player: the world stays drawn (the real view)")
    check(L.eval("TERMINAL_CLOSED") == 1, "the terminal closes")
    check(shown(L) == ["intro day"] or shown(L) == ["intro night"], f"the entry video first: {shown(L)}")
    L.execute("G.IntroDone()")
    check(shown(L)[-1] == "seat" and L.eval("G.Stage()") == "seat", f"then the seat: {shown(L)}")
    L = world()
    check(L.eval("(function() ONLINE = true; return G.Enter() end)()") == False and L.eval("S.GunnerManned()") == False,
          "online: not taken (single player only for now)")


@test
def leaving_restores_everything():
    L = world()
    L.execute("G.Enter(); G.IntroDone(); G.Exit('player')")
    check(L.eval("S.GunnerManned()") == False, "not manned")
    check(L.eval("ME.blocked") == False, "movement back")
    check(L.eval("DRAW_WORLD") == True, "the world drawn again")
    check(L.eval("G.Active()") == False and shown(L)[-1] == "hide seat", f"the seat closed: {shown(L)}")
    # (a body held before, by something else, stays held)
    L = world()
    L.execute("ME.blocked = true; G.Enter(); G.Exit('player')")
    check(L.eval("ME.blocked") == True, "a hold that was there before is left as it was")


@test
def video_once_a_sortie():
    L = world()
    L.execute("G.Enter(); G.IntroDone(); G.Exit('player'); G.Enter()")
    check(shown(L)[-1] == "seat", f"the second time this sortie: straight to the seat: {shown(L)}")
    L.execute("G.Exit('player'); SORTIE = 2; G.Enter()")
    check(shown(L)[-1].startswith("intro"), f"a new sortie: the video again: {shown(L)}")


@test
def leaving_during_the_video():
    L = world()
    L.execute("G.Enter(); G.Exit('player')")
    check(shown(L) == [shown(L)[0], "hide intro"] and L.eval("S.GunnerManned()") == False, f"{shown(L)}")


@test
def what_ends_the_seat():
    for setup, why in (("ME.dead = true", "dead"), ("ME.vehicle = {}", "vehicle"),
                       ("PHASE.gun = 'REARM'", "over")):
        L = world()
        L.execute("G.Enter(); G.IntroDone()")
        L.execute(setup)
        check(L.eval("G.Interrupt(ME)") == why, f"{setup}: {L.eval('G.Interrupt(ME)')}")
    L = world()
    L.execute("G.Enter(); G.IntroDone()")
    check(L.eval("G.Interrupt(ME)") is None, "nothing wrong: stays")
    # the sortie's end (recall, time up, dry) through the release hook
    L.execute("for _, f in ipairs(S.Hooks.released) do f('ac130') end")
    check(L.eval("G.Active()") == False, "the gunship released: the seat closes")
    # death
    L = world()
    L.execute("G.Enter(); G.IntroDone(); fire('OnPlayerDeath', ME)")
    check(L.eval("G.Active()") == False, "the player died: the seat closes")


@test
def refused_entry_says_why():
    L = world()
    L.execute("ME.vehicle = {}")
    check(L.eval("G.Enter()") == False and L.eval("G.Active()") == False, "refused")
    check(L.eval("HALO[1]") == "IGUI_SH_Gun_No_vehicle", f"said: {L.eval('HALO[1]')}")


@test
def aiming_cancelled_on_entry():
    L = world()
    L.execute("S.Aim('gunaim', false)")
    check(L.eval("S.IsAiming()") == True, "aiming the 40mm by eye")
    L.execute("G.Enter()")
    check(L.eval("S.IsAiming()") == False, "taking the seat ends the eyes-on aiming")


@test
def video_path_climbs_to_the_drive_root():
    L = world()
    p = L.eval(r"G.VideoPath('C:\\Program Files (x86)\\Steam\\steamapps\\workshop\\content\\108600\\1\\mods\\SkyhammerAirSupport\\42', 'sh_ac130_entry_day.bik', 8)")
    check(p == "../" * 8 + "Program Files (x86)/Steam/steamapps/workshop/content/108600/1/mods/SkyhammerAirSupport/42/media/videos/sh_ac130_entry_day.bik",
          f"relative to the game's media/videos, up to the root, then down: {p}")
    check("\\" not in p and "C:" not in p, "forward slashes, no drive")
    # (2026-10-24 log: 30 climbs made a 284-character path, past Windows' 260, and the video did
    # not open) few climbs first, more only for a deeper install: the game's own path
    # C:\Program Files (x86)\Steam\steamapps\common\ProjectZomboid\media\videos is 7 deep
    climbs = L.eval("(function() local t = {}; for i, n in ipairs(G.VIDEO_CLIMBS) do t[i] = n end; return table.concat(t, ',') end)()")
    check(climbs == "8,16", f"tries 8 then 16 climbs: {climbs}")
    game = "C:\\Program Files (x86)\\Steam\\steamapps\\common\\ProjectZomboid\\media\\videos\\"
    full = game + p.replace("/", "\\")
    check(len(full) < 260, f"the whole path stays under 260 characters: {len(full)}")


@test
def view_reach():
    L = world()
    x, y = L.eval("(function() return G.Clamp(100, 100, 100 + 80, 100, 40) end)()")
    check(abs(x - 140) < 1e-9 and abs(y - 100) < 1e-9, f"held to the reach: {x},{y}")
    x, y = L.eval("(function() return G.Clamp(100, 100, 110, 95, 40) end)()")
    check((x, y) == (110, 95), "inside: unchanged")


@test
def day_or_night():
    L = world()
    # (2026-10-25, the user: night 22:00-6:00)
    check([L.eval(f"G.Scene({h})") for h in (3, 6, 12, 20, 21.9, 22, 23)] == ["night", "day", "day", "day", "day", "night", "night"],
          "day from 6:00 to 22:00 game time")


@test
def terminal_offers_the_seat():
    term = io.open(os.path.join(LUA, "client", "Skyhammer_Terminal.lua"), encoding="utf-8").read()
    check("S.EnterGunner" in term or "SkyhammerGunner.Enter" in term, "the AC-130's top row enters the seat")
    # (2026-10-24, the user) the seat takes the eyes-on half of the 105 row; the map mark stays
    body = lambda name: term.split(f"function T:{name}()")[1].split("\nfunction ")[0]
    check("EnterGunner" not in body("onAction") and "mapMark" in body("onAction"),
          "the map mark button (onAction) still marks the 105 on the map")
    check("EnterGunner" in body("onEyes"), "the eyes-on button (onEyes) enters the seat")
    check("IGUI_SH_Btn_Gunner" in term and "S.GunnerSeatOn" in term, "the button's name, and the sandbox switch")
    check("function S.CloseTerminal" in term, "the seat can close the terminal")


@test
def black_hot_toggle_kept():
    # (2026-10-24, the user) white-hot / black-hot: a key flips it, and it is kept between seats
    L = world()
    check(L.eval("G.BlackHot()") == False, "white-hot to start")
    L.execute("G.TogglePolarity()")
    check(L.eval("G.BlackHot()") == True, "flipped to black-hot")
    L.execute("G.Enter(); G.IntroDone(); G.Exit('player'); G.Enter()")
    check(L.eval("G.BlackHot()") == True, "still black-hot the next time")
    check(L.eval("SkyhammerFeed.ThermalGrey(76, false)") == 76 and L.eval("SkyhammerFeed.ThermalGrey(76, true)") == 179,
          "the map's greys turn over for black-hot")


@test
def heat_figures_scale_with_zoom():
    # infected drawn as small human-shaped heat, sized from the map's scale, within limits
    L = world()
    check(L.eval("G.FigureHeight(4)") == 7, "far out: a small figure (never under 7 px)")
    check(L.eval("G.FigureHeight(20)") == 18, "about 0.9 of a tile")
    check(L.eval("G.FigureHeight(80)") == 30, "close in: capped at 30 px")


@test
def lua_is_ascii():
    for f in ("Skyhammer_Gunner.lua", "Skyhammer_Ops.lua", "Skyhammer_Feed.lua", "Skyhammer_Terminal.lua"):
        b = open(os.path.join(LUA, "client", f), "rb").read()
        check(all(c < 128 for c in b), f"{f} is ASCII only")


if __name__ == "__main__":
    passed = 0
    for t in TESTS:
        try:
            t(); passed += 1; print("PASS", t.__name__)
        except Exception as e:
            print("FAIL", t.__name__, repr(e)[:400])
    print(f"{passed}/{len(TESTS)} passed")
    sys.exit(0 if passed == len(TESTS) else 1)
