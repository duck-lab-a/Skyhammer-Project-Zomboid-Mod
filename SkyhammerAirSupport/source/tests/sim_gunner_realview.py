# The gunner seat's real view (2026-10-24, the user: "the minimap looks cheap"; "do it the way
# MW2 Killstreak Air Support does", for the Skyhammer update itself, no other mod). Pure Lua,
# single player (online the thermal map stays):
#  * body cam: the game draws from the player character, so the character flies the camera:
#    hidden, a ghost, no collisions, unhurt, sees everything; set at the view point each frame and
#    put back exactly where and as it was when the seat ends (and around every save)
#  * thermal: Skyhammer's own media/shaders/screen.frag (the game's, plus a thermal branch), on
#    through the forage search-mode channel: darkness 2001 white-hot / 2002 black-hot
#  * zoom: the player's own zoom levels, stepped, undone after
#  * Viewpoint's 3D view: its isometric view for the seat, back after
# Run: <codex python> -I source/tests/runsim.py source/tests/sim_gunner_realview.py
import io, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
MEDIA = os.path.join(HERE, "..", "..", "42", "media")
LUA = os.path.join(MEDIA, "lua")
GAME_SHADER = r"C:\Program Files (x86)\Steam\steamapps\common\ProjectZomboid\media\shaders\screen.frag"
sys.path.insert(0, HERE)
import sim_gunner as guns

UI = r"""
local E = {}
for _, n in ipairs({ "initialise", "instantiate", "addToUIManager", "removeFromUIManager", "setVisible",
    "setAlwaysOnTop", "setWantKeyEvents", "setCapture", "drawRect", "drawRectBorder", "drawText",
    "drawTextureScaled", "setStencilRect", "clearStencilRect", "drawTextCentre", "createChildren" }) do E[n] = function() end end
ISUIElement = E
ISUIElement.__index = ISUIElement
function ISUIElement:derive(name) local o = {}; setmetatable(o, self); self.__index = self; o.Type = name; return o end
function ISUIElement:new(x, y, w, h) local o = { x = x, y = y, width = w, height = h }; setmetatable(o, self); self.__index = self; return o end
MX, MY = 960, 540
function ISUIElement:getMouseX() return MX end
function ISUIElement:getMouseY() return MY end
DRAW_WORLD = true
getWorld = function() return { setDrawWorld = function(_, on) DRAW_WORLD = on end } end
-- the game's zoom levels 0.5 .. 2.5 by 0.25
ZOOM, ZSTEPS = 1.0, 0
MODEL = true
local core = { getScreenWidth = function() return 1920 end, getScreenHeight = function() return 1080 end,
    getZoom = function() return ZOOM end, getMinZoom = function() return 0.5 end, getMaxZoom = function() return 2.5 end,
    getNextZoom = function(_, _, dir) return math.max(0.5, math.min(2.5, ZOOM + dir * 0.25)) end,
    doZoomScroll = function(_, _, dir) ZOOM = math.max(0.5, math.min(2.5, ZOOM + dir * 0.25)); ZSTEPS = ZSTEPS + dir end,
    isDisplayPlayerModel = function() return MODEL end, setDisplayPlayerModel = function(_, on) MODEL = on end }
getCore = function() return core end
getTextManager = function() return { getFontHeight = function() return 16 end, MeasureStringX = function() return 10 end } end
HaloTextHelper = { addBadText = function() end, addText = function() end }
isKeyDown = function() return false end
-- the game's isometric projection: 64 x 32 px a tile, the camera's corner at world 100,100 (zoom 1)
ISCoordConversion = {
    ToWorld = function(sx, sy, z) return 100 + sy / 32 + sx / 64, 100 + sy / 32 - sx / 64 end,
    ToScreen = function(x, y, z) return (x - y) * 32, (x + y - 200) * 16 end,
}
-- the forage search mode, as the screen shader is fed from it
SM = { override = false, enabled = false, darkness = 0 }
getSearchMode = function() return {
    isOverride = function() return SM.override end, setOverride = function(_, _, v) SM.override = v end,
    isEnabled = function() return SM.enabled end, setEnabled = function(_, _, v) SM.enabled = v end,
    getDarkness = function() return { setAll = function(_, v) SM.darkness = v end } end } end
"""

PLAYER = r"""
G = SkyhammerGunner
ME.blocked = false
ME.flags = { ghost = false, invisible = false, noclip = false, god = false }
function ME:isBlockMovement() return self.blocked end
function ME:setBlockMovement(b) self.blocked = b end
function ME:getVehicle() return nil end
function ME:isAsleep() return false end
function ME:isGhostMode() return self.flags.ghost end;        function ME:setGhostMode(v) self.flags.ghost = v end
function ME:isInvisible() return self.flags.invisible end;    function ME:setInvisible(v) self.flags.invisible = v end
function ME:isNoClip() return self.flags.noclip end;          function ME:setNoClip(v) self.flags.noclip = v end
function ME:isGodMod() return self.flags.god end;             function ME:setGodMod(v) self.flags.god = v end
function ME:setCanSeeAll(v) self.seeAll = v end
function ME:canSeeAll() return self.seeAll == true end
function ME:setX(v) self.x = v end; function ME:setY(v) self.y = v end; function ME:setZ(v) self.z = v end
function ME:setLastX() end; function ME:setLastY() end; function ME:setLastZ() end
function ME:setNextX() end; function ME:setNextY() end; function ME:ensureOnTile() end
ME.z = 0
ME.offsetY=192
function ME:getOffsetY() return self.offsetY end
function ME:setOffsetY(y) self.offsetY=y end
IsoCamera={update=function()end}
S.CloseTerminal = function() end
G.makeIntro = function() return nil end      -- (straight to the seat)
function frames(ms) for t = CLOCK, CLOCK + ms, 50 do CLOCK = t; for _, f in ipairs(HANDLERS.OnTick or {}) do pcall(f) end; for _,f in ipairs(HANDLERS.OnPostRender or {}) do f() end; local s = G.Screen and G.Screen(); if s and s.prerender then s:prerender() end end end
"""

VP = r"""
-- Viewpoint's views (FP.nextView / cycleView / toggle, ThirdPerson.poll; 0.1.6 and 0.1.7 decompiled):
-- first -> third flips the SAVED "third person on foot" choice (camera.thirdPersonOnFoot); third ->
-- isometric; isometric -> the 3D view that choice says (poll() reads it back every frame), so a
-- cycle through third person leaves the player in third person afterwards.
-- 0.1.7 moves the camera between the isometric view and 3D (view.switchSeconds 0.45 + fade 0.3):
-- a switch asked while one is moving is dropped (ViewSwitch.toggle: step != NONE). MOVE_MS = 0 is 0.1.6.
VIEW, SAVED_THIRD, CYCLES, MOVE_MS, MOVING_UNTIL = "third", true, 0, 0, -1
local function busy() return CLOCK < MOVING_UNTIL end
local function moved() MOVING_UNTIL = CLOCK + MOVE_MS end
Viewpoint = { View = {
    next = function() return VIEW == "isometric" and "first" or (VIEW == "third" and "isometric" or "third") end,
    cycle = function()
        CYCLES = CYCLES + 1
        if VIEW == "first" then SAVED_THIRD = true; VIEW = "third"
        elseif busy() then return
        elseif VIEW == "third" then VIEW = "isometric"; moved()
        else VIEW = SAVED_THIRD and "third" or "first"; moved() end
    end } }
"""

# Skyhammer's Java part (SkyhammerAircraft.view*, AircraftBridge -> ViewSwitchBridge): Viewpoint's own
# isometric <-> 3D switch, straight, no step through third person
DIRECT = r"""
SkyhammerAircraft = SkyhammerAircraft or {}
SkyhammerAircraft.viewKnown = function() return true end
SkyhammerAircraft.view3D = function() return VIEW ~= "isometric" end
SkyhammerAircraft.viewSet = function(want3D)
    if CLOCK < MOVING_UNTIL then return true end
    if want3D and VIEW == "isometric" then VIEW = SAVED_THIRD and "third" or "first"; MOVING_UNTIL = CLOCK + MOVE_MS
    elseif not want3D and VIEW ~= "isometric" then VIEW = "isometric"; MOVING_UNTIL = CLOCK + MOVE_MS end
    return true
end
"""


def world(viewpoint=False, online=False):
    L = guns.world()
    L.execute(UI)
    if viewpoint: L.execute(VP)
    if online: L.execute("ONLINE = true")
    for f in ("client/Skyhammer_Feed.lua", "client/Skyhammer_GunnerHUD.lua", "client/Skyhammer_Gunner.lua"):
        L.execute(io.open(os.path.join(LUA, f), encoding="utf-8").read())
    L.execute(PLAYER)
    return L


TESTS = []
def test(fn): TESTS.append(fn); return fn
def check(c, what):
    if not c: raise AssertionError(what)


@test
def single_player_only():
    check(world().eval("G.RealViewAvailable()") == True, "single player: the real view")
    check(world(online=True).eval("G.RealViewAvailable()") == False, "online: the thermal map (no body cam there)")
    check(io.open(os.path.join(LUA, "client", "Skyhammer_Gunner.lua"), encoding="utf-8").read().find("KSCam_") < 0,
          "nothing of the Killstreak mod is used")


@test
def the_body_flies_the_camera():
    L = world()
    check(L.eval("G.Enter()") == True, "entered")
    f = L.eval("ME.flags")
    check(f.ghost and f.invisible and f.noclip and f.god, "hidden, a ghost, no collisions, unhurt")
    check(L.eval("ME.seeAll") == True and L.eval("MODEL") == False, "sees everything; its model not drawn")
    check(L.eval("DRAW_WORLD") == True, "the world is drawn: it IS the picture")
    L.execute("MX, MY = 64 * 10, 32 * 2; frames(200)")
    # (1 tile of the gunship's slow circle, and since 2026-10-24 evening a little sensor sway)
    check(abs(L.eval("ME.x") - 100) <= 1.5 and abs(L.eval("ME.y") - 100) <= 1.5 and L.eval("ME.z") == 0,
          f"at the view point (the body's spot, with the slow drift), ground floor: {L.eval('ME.x')},{L.eval('ME.y')}")


@test
def thermal_through_the_search_mode():
    L = world()
    L.execute("G.Enter(); frames(100)")
    check(L.eval("SM.override") == True and L.eval("SM.enabled") == True and L.eval("SM.darkness") == 2001,
          "white-hot: darkness 2001, the mode on override")
    L.execute("G.TogglePolarity(); G.Screen():applyPolarity(); frames(100)")
    check(L.eval("SM.darkness") == 2002, "black-hot: 2002")


@test
def leaving_puts_everything_back():
    L = world()
    L.execute("ME.x, ME.y = 123.4, 87.6; G.Enter(); MX, MY = 64 * 10, 32 * 2; frames(300); G.Exit('player')")
    check(L.eval("ME.x") == 123.4 and L.eval("ME.y") == 87.6 and L.eval("ME.z") == 0, "the body back exactly where it was")
    f = L.eval("ME.flags")
    check(not (f.ghost or f.invisible or f.noclip or f.god), "its flags as they were")
    check(L.eval("ME.seeAll") == False and L.eval("MODEL") == True, "sees as usual; its model drawn again")
    check(L.eval("SM.override") == False and L.eval("SM.enabled") == False and L.eval("SM.darkness") == 0,
          "the search mode as it was")
    check(L.eval("ZSTEPS") == 0, f"the zoom levels stepped are undone ({L.eval('ZSTEPS')})")


@test
def a_save_finds_the_body_home():
    L = world()
    L.execute("ME.x, ME.y = 123.4, 87.6; G.Enter(); MX, MY = 64 * 10, 32 * 2; frames(300); fire('OnSave')")
    check(L.eval("ME.x") == 123.4 and L.eval("ME.y") == 87.6, "saved with the body at home")
    check(L.eval("ME.flags.god") == False, "and as it was")
    L.execute("frames(100)")
    check(L.eval("G.Active()") == True and L.eval("ME.flags.ghost") == True, "the seat goes on after the save")


@test
def weapon_zoom_and_wheel():
    L = world()
    L.execute("G.Enter()")
    check(L.eval("ZOOM") == 1.75, f"the 40mm's view: {L.eval('ZOOM')}")
    L.execute("G.Screen():setWeapon('he')")     # (the stub Keyboard has every key as 0)
    check(L.eval("ZOOM") == 2.5, f"the 105's, wider: {L.eval('ZOOM')}")
    L.execute("G.Screen():onMouseWheel(-1)")
    check(L.eval("ZOOM") == 2.25, f"the wheel steps the game's levels: {L.eval('ZOOM')}")


@test
def aim_through_the_iso_projection():
    L = world()
    L.execute("FIRED = nil; S.GunnerFire = function(w, x, y) FIRED = { w, x, y }; return true end")
    L.execute("G.Enter(); MX, MY = 64 * 3, 32 * 2; local s = G.Screen(); s:onMouseDown(); s:onMouseUp()")
    w, x, y = L.eval("FIRED[1]"), L.eval("FIRED[2]"), L.eval("FIRED[3]")
    # (192, 64) px at zoom 1.75 -> (336, 112) game px -> 100 + 3.5 + 5.25, 100 + 3.5 - 5.25
    check(w == "gun" and abs(x - 108.75) < 1e-6 and abs(y - 98.25) < 1e-6, f"the ground under the pointer (zoom 1.75): {w} {x},{y}")


@test
def viewpoint_3d_to_isometric_and_back():
    L = world(viewpoint=True)
    L.execute("G.Enter(); frames(1500)")
    check(L.eval("VIEW") == "isometric", f"Viewpoint switched to its isometric view: {L.eval('VIEW')}")
    L.execute("G.Exit('player'); frames(2000)")
    check(L.eval("VIEW") == "third", f"and back to the third-person view after: {L.eval('VIEW')}")


def from_first(L, move_ms):
    L.execute(f"VIEW, SAVED_THIRD, MOVE_MS = 'first', false, {move_ms}")


@test
def cycle_only_never_bounces_back_to_isometric():
    # 2026-11-04 log: seat left 20:16:19 -> third person -> isometric again 20:16:21 -> the player
    # switched by hand. Without the Java switch the way back may only end in a 3D view, never isometric.
    for move in (0, 750):
        L = world(viewpoint=True)
        from_first(L, move)
        L.execute("G.Enter(); frames(2000)")
        check(L.eval("VIEW") == "isometric", f"move {move}: isometric in the seat: {L.eval('VIEW')}")
        L.execute("G.Exit('player'); frames(4000)")
        check(L.eval("VIEW") != "isometric", f"move {move}: a 3D view after the seat, not isometric again: {L.eval('VIEW')}")


@test
def direct_switch_keeps_first_person_and_the_saved_choice():
    for move in (0, 750):
        L = world(viewpoint=True)
        L.execute(DIRECT)
        from_first(L, move)
        L.execute("G.Enter(); frames(2000)")
        check(L.eval("VIEW") == "isometric", f"move {move}: isometric in the seat: {L.eval('VIEW')}")
        L.execute("G.Exit('player'); frames(4000)")
        check(L.eval("VIEW") == "first", f"move {move}: first person again, as before the seat: {L.eval('VIEW')}")
        check(L.eval("SAVED_THIRD") is False, f"move {move}: Viewpoint's saved third-person choice untouched")
        check(L.eval("CYCLES") == 0, f"move {move}: no step through Viewpoint's view cycle: {L.eval('CYCLES')}")


@test
def direct_switch_from_isometric_stays_isometric():
    L = world(viewpoint=True)
    L.execute(DIRECT)
    L.execute("VIEW = 'isometric'; G.Enter(); frames(1000); G.Exit('player'); frames(3000)")
    check(L.eval("VIEW") == "isometric", f"entered from the isometric view, left in it: {L.eval('VIEW')}")


@test
def map_mode_online():
    L = world(online=True)
    L.execute("G.makeScreen = function(real) MADE = real; local o = {}; function o:show() end; function o:hide() end; return o end")
    # (2026-10-24, the user: the seat ships single player only; online after more testing) online
    # the seat is not taken at all: no screen, the world drawn, the body left alone
    check(L.eval("G.Enter()") == False, "online: not taken")
    check(L.eval("rawget(_G, 'MADE')") is None and L.eval("DRAW_WORLD") == True and L.eval("ME.flags.ghost") == False,
          "online: nothing changed")


@test
def the_games_ui_hidden_while_seated():
    # (2026-10-24, the user's screenshot: the game's bars, hotbar, minimap and clock over the seat)
    L = world()
    L.execute("""UICALLS = {}
    ISUIHandler = { allUIVisible = true, setVisibleAllUI = function(v) UICALLS[#UICALLS + 1] = tostring(v) end }""")
    L.execute("G.Enter()")
    check(L.eval("UICALLS[1]") == "false", "the game's UI hidden as the seat is taken (its own toggle)")
    L.execute("G.Exit('player')")
    check(L.eval("UICALLS[2]") == "true" and L.eval("#UICALLS") == 2, "and shown again after")
    L = world()
    L.execute("UICALLS = {}; ISUIHandler = { allUIVisible = false, setVisibleAllUI = function(v) UICALLS[#UICALLS + 1] = tostring(v) end }")
    L.execute("G.Enter(); G.Exit('player')")
    check(L.eval("#UICALLS") == 0, "already hidden by the player: left alone")


@test
def mod_panels_that_show_themselves_stay_hidden():
    # (2026-10-24, the user's screenshot 19: Division Gadgets' panel and the 3D minimap over the
    # seat) the game's own toggle hides them once, but they show themselves again each tick: the
    # minimap unless ISUIHandler.allUIVisible is false, the gadget panel always. While seated the
    # flag is down and every frame, before the UI is drawn, whatever is not the seat's goes again;
    # all of it back after
    L = world()
    L.execute("""
    local function el(name, keep)
        local o = { name = name, vis = true, tbl = keep and { skyhammerKeep = true } or {} }
        function o:isVisible() return self.vis end
        function o:setVisible(v) self.vis = v end
        function o:getTable() return self.tbl end
        function o:toString() return self.name end
        return o
    end
    PANEL, MINE = el('gadgets'), el('seat', true)
    local list = { PANEL, MINE }
    UIManager = { getUI = function() return { size = function() return #list end, get = function(_, i) return list[i + 1] end } end,
                  setVisibleAllUI = function() end }
    ISUIHandler = { allUIVisible = true, setVisibleAllUI = function(v) for _, e in ipairs(list) do if not e.tbl.skyhammerKeep then e.vis = v end end end }
    -- (the stub's Remove does nothing: a real one for the draw hook)
    local pre = HANDLERS.OnPreUIDraw or {}; HANDLERS.OnPreUIDraw = pre
    local ev = Events
    Events = setmetatable({ OnPreUIDraw = { Add = function(fn) table.insert(pre, fn) end,
        Remove = function(fn) for i = #pre, 1, -1 do if pre[i] == fn then table.remove(pre, i) end end end } },
        { __index = function(_, k) return ev[k] end })
    G.Enter()""")
    check(L.eval("ISUIHandler.allUIVisible") == False, "the flag the minimap reads is down while seated")
    L.execute("PANEL.vis = true; fire('OnPreUIDraw')")
    check(L.eval("PANEL.vis") == False, "a panel that showed itself again is hidden before the UI draws")
    check(L.eval("MINE.vis") == True, "the seat's own screens are left alone")
    L.execute("G.Exit('player')")
    check(L.eval("ISUIHandler.allUIVisible") == True and L.eval("PANEL.vis") == True, "all back after")
    n = L.eval("#(HANDLERS.OnPreUIDraw or {})")
    L.execute("PANEL.vis = true; fire('OnPreUIDraw')")
    check(L.eval("PANEL.vis") == True, f"the hook is gone after the seat ({n} handlers)")


@test
def the_seats_screens_are_marked_keep():
    L = world()
    L.execute("G.Enter()")
    check(L.eval("G.Screen() ~= nil and G.Screen().skyhammerKeep == true or (G.ActiveUI and G.ActiveUI().skyhammerKeep == true)") == True,
          "the screen showing is marked to keep")


@test
def the_entry_video_can_be_replaced_locally():
    # (2026-10-24, the user: another entry video for their own game only) a local mod may set
    # SkyhammerGunner.IntroOverride; the seat then plays that mod's video for its length, with its
    # own sound at the start in place of Skyhammer's engine and flare cues
    L = world()
    d = L.eval("G.IntroSpec('night')")
    # (2026-10-24 evening, the user's own clip, 4.5 s; 2026-10-25 the user's night clip for the
    # dark hours: sh_ac130_entry_night.bik)
    check(d.mod == "SkyhammerAirSupport" and d.file == "sh_ac130_entry_night.bik" and d.ms == 4500
          and L.eval("G.IntroSpec('day').file") == "sh_ac130_entry.bik"
          and os.path.isfile(os.path.join(MEDIA, "videos", "sh_ac130_entry.bik"))
          and os.path.isfile(os.path.join(MEDIA, "videos", "sh_ac130_entry_night.bik"))
          and d.engine == False and L.eval("G.IntroSpec('night').cues == G.INTRO_CUES"),
          "Skyhammer's own by default, a night one for the dark hours")
    L.execute("G.IntroOverride = { mod = 'LocalPatches', file = 'other.bik', ms = 5900, sound = 'LP_Other' }")
    o = L.eval("G.IntroSpec('day')")
    check(o.mod == "LocalPatches" and o.file == "other.bik" and o.ms == 5900 and o.engine == False,
          "the override's video and length, no engine drone")
    check(L.eval("#G.IntroSpec('day').cues") == 1 and L.eval("G.IntroSpec('day').cues[1][1]") == 0
          and L.eval("G.IntroSpec('day').cues[1][2]") == "LP_Other", "its own sound at the start, nothing else")
    check(L.eval("G.IntroSpec('day').static") == False, "no switch static over its own sound")
    check(L.eval("G.IntroSpec('day').w") == 1280 and L.eval("G.IntroSpec('day').h") == 720, "1280x720 unless it says")
    L.execute("G.IntroOverride.w = 1920; G.IntroOverride.h = 1080")
    check(L.eval("G.IntroSpec('day').w") == 1920 and L.eval("G.IntroSpec('day').h") == 1080, "its own size")
    L.execute("G.IntroOverride = nil")
    check(L.eval("G.IntroSpec('day').w") == 1280, "Skyhammer's own: 1280x720")


@test
def real_view_camera_hits_are_not_body_hits():
    # (2026-10-25, the user: "the body is hit" while infected bit the air) in the real view the
    # character is the god-mode camera; its health dipping is never the body being hit
    L = world()
    L.execute("HP = 100; function ME:getBodyDamage() return { getOverallBodyHealth = function() return HP end } end")
    L.execute("PLAYED = {}; G.Enter(); frames(600); HP = 80; frames(300)")
    got = [L.eval(f"PLAYED[{i}]") for i in range(1, L.eval("#PLAYED") + 1)]
    check(L.eval("G.Screen().hitAt") is None and "SH_Gunner_Alert" not in got, f"no hit alert: {got}")


@test
def three_guns_keys_one_two_three():
    # (2026-10-24, the user: "seat 1 25mm, 2 40mm, 3 105mm") the switch key goes round them in turn
    L = world()
    check([L.eval(f"G.WEAPONS[{i}]") for i in (1, 2, 3)] == ["gun25", "gun", "he"], "1 25mm, 2 40mm, 3 105mm")
    check([L.eval(f"G.NextWeapon('{w}')") for w in ("gun25", "gun", "he")] == ["gun", "he", "gun25"], "Q goes round")
    L.execute("G.Enter(); G.Screen():setWeapon('gun25'); frames(100)")
    check(L.eval("G.Screen().weapon") == "gun25" and L.eval("G.Screen().zooms.gun25") is not None, "the 25mm has its own view")


@test
def the_infected_glow_not_icons():
    # (the user: "why icons on the zombies") the infected glow through the game's own character
    # outline, white-hot white (black-hot black), friends green; cleared after
    L = world()
    L.execute("""
    local function zed(x, friend)
        local z = { x = x, y = 100, z = 0, friend = friend, outline = false }
        function z:getX() return self.x end; function z:getY() return self.y end; function z:getZ() return self.z end
        function z:isDead() return false end; function z:getHealth() return 1 end
        function z:getTarget() return nil end
        function z:setOutlineHighlight(i, on) self.outline = on end
        function z:setOutlineHighlightCol(r, g, b, a) self.col = { r, g, b, a } end
        function z:getSquare() local sq=newSquare(self.x,self.y,self.z); sq.isCanSee=function()return true end; sq.HasSlopedRoof=function()return false end; return sq end
        return z
    end
    ZOMBIES[1] = zed(105); ZOMBIES[2] = zed(110, true)
    S.IsFriendlyNPC = function(z) return z.friend == true end
    G.Enter(); frames(100)""")
    # (2026-10-24 evening, Codex: the outline carries one marker colour that only Skyhammer's
    # aim_outline_blit.frag turns into the hot body; the screen shader does black-hot after)
    check(L.eval("ZOMBIES[1].outline") == True and abs(L.eval("ZOMBIES[1].col[1]") - 32 / 255) < 1e-6, "an infected: the marker outline")
    check(L.eval("ZOMBIES[2].outline") == True and L.eval("ZOMBIES[2].col[1]") < L.eval("ZOMBIES[2].col[2]"), "a friend: green")
    L.execute("G.TogglePolarity(); G.Screen():applyPolarity(); frames(100)")
    check(abs(L.eval("ZOMBIES[1].col[1]") - 32 / 255) < 1e-6, "black-hot: the same marker (inverted once, by the screen)")
    L.execute("G.Exit('player')")
    check(L.eval("ZOMBIES[1].outline") == False and L.eval("ZOMBIES[2].outline") == False, "outlines cleared after")


@test
def entry_has_sound():
    # (the user: the entry played silent) since 2026-10-24 evening the entry's sound is one take,
    # SH_Seat_Entry (media/sound/skyhammer_seat/sh_seat_entry.wav), played as the seat is taken
    L = world()
    L.execute("PLAYED = {}; G.Enter()")
    got = [L.eval(f"PLAYED[{i}]") for i in range(1, L.eval("#PLAYED") + 1)]
    check("SH_Seat_Entry" in got, f"the entry's sound: {got}")
    snd = open(os.path.join(MEDIA, "scripts", "Skyhammer_SeatSounds.txt"), encoding="utf-8").read().replace("\r\n", "\n")
    check("sound SH_Seat_Entry\n" in snd and os.path.isfile(os.path.join(MEDIA, "sound", "skyhammer_seat", "sh_seat_entry.wav")),
          "defined, its file there")
    # (2026-10-25) at night the night clip plays, with its own sound
    L = world()
    L.execute("getGameTime = function() return { getTimeOfDay = function() return 23 end, getWorldAgeHours = function() return 0 end, getMinutesPerDay = function() return 60 end } end")
    L.execute("PLAYED = {}; G.Enter()")
    got = [L.eval(f"PLAYED[{i}]") for i in range(1, L.eval("#PLAYED") + 1)]
    check("SH_Seat_EntryNight" in got and "SH_Seat_Entry" not in got, f"the night entry's sound: {got}")
    check("sound SH_Seat_EntryNight\n" in snd and os.path.isfile(os.path.join(MEDIA, "sound", "skyhammer_seat", "sh_seat_entry_night.wav")),
          "the night one defined, its file there")


@test
def shader_is_the_games_plus_thermal():
    mine = open(os.path.join(MEDIA, "shaders", "screen.frag"), encoding="utf-8").read().replace("\r\n", "\n")
    game = open(GAME_SHADER, encoding="utf-8").read().replace("\r\n", "\n")
    check("skyhammerThermal" in mine and "2000.5" in mine, "the thermal branch, on the 2000+ darkness signal")
    # take Skyhammer's marked blocks out: the rest is the game's own file
    stripped = re.sub(r"// SKYHAMMER BEGIN.*?// SKYHAMMER END\n", "", mine, flags=re.S)
    check(stripped == game, "everything else is exactly the game's screen.frag")


if __name__ == "__main__":
    passed = 0
    for t in TESTS:
        try:
            t(); passed += 1; print("PASS", t.__name__)
        except Exception as e:
            print("FAIL", t.__name__, repr(e)[:400])
    print(f"{passed}/{len(TESTS)} passed")
    sys.exit(0 if passed == len(TESTS) else 1)
