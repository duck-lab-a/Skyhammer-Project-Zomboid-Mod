# The AC-130 gunner seat's guns (2026-10-24, the user; design: source/ac130_gunner_design.md).
# Skyhammer_Ops: S.GunnerFire("gun" | "he", x, y) fires the AC-130's own guns by hand from the
# seat: the 40mm as the aimed 40mm (3 rounds 300 ms apart, 1200 ms between bursts), the 105 one
# shell a click, at once, then 2500 ms of reload. A roofed point is refused without spending.
# While the seat is manned (S.SetGunnerManned) the 40mm's own fire pauses. Reload times belong to
# the sortie: re-entering the seat never resets them. The "105 rounds per mark" option is gone
# (a terminal 105 mission, with the seat switched off in the sandbox, fires 2).
# Run: <codex python> -I source/tests/runsim.py source/tests/sim_gunner.py
import io, os, sys
from lupa import lua51

HERE = os.path.dirname(os.path.abspath(__file__))
MOD = os.path.join(HERE, "..", "..", "42", "media")
LUA = os.path.join(MOD, "lua")
SRC = os.path.join(HERE, "..")
sys.path.insert(0, HERE)
import sim_pvp_client as base

STUBS = base.STUBS.replace(
    "getActivatedMods = function() return { contains = function(_, id) return id == 'SkyhammerAirSupportVanilla' end } end",
    "getActivatedMods = function() return { contains = function(_, id) return id == 'SkyhammerAirSupport' end } end"
).replace("ONLINE = true", "ONLINE = false") + r"""
SandboxVars = { Skyhammer = {} }
-- squares: outdoors unless listed in ROOFED; NOLOAD: not loaded (nil)
ROOFED, NOLOAD = {}, {}
local function key(x, y) return math.floor(x) .. "," .. math.floor(y) end
function newSquare(x, y, z)
    local sq = { x = math.floor(x), y = math.floor(y), z = math.floor(z) }
    function sq:getX() return self.x end
    function sq:getY() return self.y end
    function sq:getZ() return self.z end
    function sq:getRoom() if ROOFED[key(self.x, self.y)] then return {} end return nil end
    function sq:haveRoofFull() return ROOFED[key(self.x, self.y)] == true end
    function sq:getMovingObjects() return { size = function() return 0 end } end
    function sq:getStaticMovingObjects() return { size = function() return 0 end } end
    return sq
end
ZOMBIES = {}
CELL = {
    getGridSquare = function(_, x, y, z) if NOLOAD[key(x, y)] then return nil end return newSquare(x, y, z) end,
    getZombieList = function() return { size = function() return #ZOMBIES end, get = function(_, i) return ZOMBIES[i + 1] end } end,
    getVehicles = function() return { size = function() return 0 end } end,
}
getCell = function() return CELL end
DEFINED = { SH_Reload_105 = true, SH_Reload_105_Gunner = true, SH_Incoming_105 = true }
getScriptManager = function() return { getGameSound = function(_, n) if DEFINED[n] then return {} end return nil end } end
PLAYED = {}
E = {}
function E:setPos() end
function E:playSoundImpl(name, flag, parent) PLAYED[#PLAYED + 1] = name; return #PLAYED end
function E:playSound() error("networked playSound") end
function E:setVolume() end
function E:set3D() end
function E:tick() end
function E:isPlaying() return false end
IsoWorld = { instance = { getFreeEmitter = function() return E end } }
"""


def world(opts=None):
    L = lua51.LuaRuntime()
    L.execute(STUBS)
    # (the seat's own sounds and sensor tracers: files of their own since 2026-10-24 evening)
    for f in ("shared/Skyhammer_PvP.lua", "client/Skyhammer_Core.lua", "client/Skyhammer_Killstreak.lua",
              "client/Skyhammer_Comms.lua", "client/Skyhammer_Ops.lua", "client/Skyhammer_SeatShotAudio.lua",
              "client/Skyhammer_25mmAudio.lua", "client/Skyhammer_GunnerTracers.lua"):
        L.execute(io.open(os.path.join(LUA, f), encoding="utf-8").read())
    L.execute(r"""
    S = Skyhammer
    isGamePaused = function() return false end
    -- the AC-130 on station with AMMO rounds; the combat clock is CLOCK
    PHASE = { gun = "ON_STATION", he = "ON_STATION", ac130 = "ON_STATION" }
    AMMO = { gun = 60, he = 8 }
    SORTIE = 1
    SAID, RELEASED = {}, {}
    S.Phase = function(k) return PHASE[k] or "READY" end
    S.Ammo = function(w) return AMMO[w] or 0, 60 end
    S.Spend = function(w, n) if (PHASE[w] ~= "ON_STATION") or (AMMO[w] or 0) < n then return false end; AMMO[w] = AMMO[w] - n; return true end
    S.Sortie = function() return SORTIE end
    S.combatMs = function() return CLOCK end
    S.CombatTick = function() end
    S.Update = function() return nil end
    S.Blocked = function() return false end
    S.CraftDry = function() return (AMMO.gun or 0) <= 0 and (AMMO.he or 0) <= 0 end
    S.Release = function(k) RELEASED[#RELEASED + 1] = k; return true end
    S.Say = function(id) SAID[#SAID + 1] = id end
    STORE = {}
    S.Store = function() return STORE end
    function run_until(ms) for t = CLOCK, ms, 20 do CLOCK = t; for _, fn in ipairs(HANDLERS.OnTick) do fn() end end end
    """)
    for k, v in (opts or {}).items():
        L.execute("OPTVALS[%r] = %s" % (k, v))
    return L


TESTS = []
def test(fn): TESTS.append(fn); return fn
def check(c, what):
    if not c: raise AssertionError(what)
def played(L):
    # (the reloads only: the gunship's engine drone plays through the same emitter stub)
    return [n for n in (L.eval(f"PLAYED[{i}]") for i in range(1, L.eval("#PLAYED") + 1)) if "Reload" in n]
def flights(L): return L.eval("(function() local n = 0; for _ in pairs(S.Store().inflight or {}) do n = n + 1 end; return n end)()")


@test
def he_one_shell_at_once_then_reload():
    L = world()
    ok = L.eval("(S.GunnerFire('he', 120.5, 100.5))")
    check(ok == True, "the 105 fires from the seat")
    check(L.eval("AMMO.he") == 7, f"one shell spent at once, left {L.eval('AMMO.he')}")
    check(flights(L) == 1, "the shell is in the air (kept in the save like a mission's)")
    ok, why = L.eval("(function() return S.GunnerFire('he', 120.5, 100.5) end)()")
    check(ok == False and why == "reload", f"right after: reloading, got {ok} {why}")
    check(L.eval("S.GunnerReload('he')") > 2000, "about 2.5 s of reload left")
    L.execute("run_until(2600)")
    check(L.eval("S.GunnerReload('he')") == 0, "ready after 2.5 s")
    check(L.eval("(S.GunnerFire('he', 121.5, 100.5))") == True and L.eval("AMMO.he") == 6, "the next shell")


@test
def he_lands_like_a_mission_shell():
    L = world()
    L.execute("S.GunnerFire('he', 120.5, 100.5)")
    L.execute("run_until(3500)")
    check(flights(L) == 0, "landed after its 3 s flight")


@test
def roofed_point_refused_without_spending():
    L = world()
    L.execute("ROOFED['120,100'] = true")
    ok, why = L.eval("(function() return S.GunnerFire('he', 120.5, 100.5) end)()")
    check(ok == False and why == "roof" and L.eval("AMMO.he") == 8, f"105 under a roof: {ok} {why}, ammo {L.eval('AMMO.he')}")
    ok, why = L.eval("(function() return S.GunnerFire('gun', 120.5, 100.5) end)()")
    check(ok == False and why == "roof" and L.eval("AMMO.gun") == 60, f"40mm under a roof: {ok} {why}")
    check(L.eval("#SAID") == 0, "no radio line for a refused point")
    L = world({"indoorHits": "true"})
    L.execute("ROOFED['120,100'] = true")
    check(L.eval("(S.GunnerFire('he', 120.5, 100.5))") == True, "with 'indoor hits' on the 105 goes through the roof")


@test
def unloaded_point_refused():
    L = world()
    L.execute("NOLOAD['150,100'] = true")
    ok, why = L.eval("(function() return S.GunnerFire('he', 150.5, 100.5) end)()")
    check(ok == False and why == "far" and L.eval("AMMO.he") == 8, f"not loaded: {ok} {why}")


@test
def gun_streams_while_held():
    # (2026-10-24, the user: "held, like Call of Duty: du-du-du-du") the seat's 40mm: a round a
    # shot, the next 333 ms on (Codex's retune the same evening), so a held trigger keeps it coming
    L = world()
    check(L.eval("(S.GunnerFire('gun', 110.5, 100.5))") == True, "a 40mm round")
    check(L.eval("AMMO.gun") == 59, f"one round, spent as it leaves the gun: {L.eval('AMMO.gun')}")
    ok, why = L.eval("(function() return S.GunnerFire('gun', 110.5, 100.5) end)()")
    check(ok == False and why == "reload", f"inside 333 ms: {ok} {why}")
    check(L.eval("S.GunnerReloadTotal('gun')") == 333, "333 ms a round")
    L.execute("run_until(340)")
    check(L.eval("(S.GunnerFire('gun', 110.5, 100.5))") == True and L.eval("AMMO.gun") == 58, "the next one")


@test
def gun25_a_sortie_of_its_own():
    # (2026-10-24, the user: "add the 25mm too") the AC-130's 25mm Gatling, the seat's alone: 600
    # rounds a sortie, and like the Apache's flares it never keeps a gunship with empty guns up
    L = lua51.LuaRuntime()
    L.execute(STUBS)
    # (the real Core, its save a plain table: the permissive stubs would hand back one)
    L.execute("MD = {}; ModData = { getOrCreate = function() return MD end }")
    for f in ("shared/Skyhammer_PvP.lua", "client/Skyhammer_Core.lua"):
        L.execute(io.open(os.path.join(LUA, f), encoding="utf-8").read())
    L.execute("S = Skyhammer; S.Call('ac130')")
    check(L.eval("(S.Ammo('gun25'))") == 600 and L.eval("S.CRAFT.gun25") == "ac130", "600 rounds go up with it")
    L.execute("MD.v2.ammo.gun.n = 0; MD.v2.ammo.he.n = 0")
    check(L.eval("S.CraftDry('ac130')") == True, "40mm and 105 empty: dry, the 25mm left or not")


@test
def gun25_streams_fast():
    L = world()
    L.execute("PHASE.gun25 = 'ON_STATION'; AMMO.gun25 = 600")
    check(L.eval("(S.GunnerFire('gun25', 110.5, 100.5))") == True and L.eval("AMMO.gun25") == 599, "a 25mm round, its own ammunition")
    check(L.eval("AMMO.gun") == 60, "the 40mm's untouched")
    check(L.eval("S.GunnerReloadTotal('gun25')") == 70, "about fourteen rounds a second")
    ok, why = L.eval("(function() return S.GunnerFire('gun25', 110.5, 100.5) end)()")
    check(ok == False and why == "reload", f"inside 70 ms: {ok} {why}")
    check(L.eval("S.GunnerReload('gun') == 0"), "the 40mm keeps its own reload")
    L.execute("run_until(120)")
    check(L.eval("(S.GunnerFire('gun25', 110.5, 100.5))") == True and L.eval("AMMO.gun25") == 598, "the next one")
    check(L.eval("(function() local a, b = S.GunnerSpread('gun25'); return a .. ',' .. b end)()") == "1.2,1.3",
          "1.2 tiles of scatter, 1.3 of reach")


@test
def gun25_is_one_stream_with_a_wind_down():
    # (2026-10-31, the user: "brrrr") a burst is one recorded stream, not a report a round, at full level
    # at once, the wind-down on release; nothing delays a round
    L = world()
    L.execute(r"""
    PHASE.gun25 = 'ON_STATION'; AMMO.gun25 = 600; S.SetGunnerManned(true); PLAYED = {}
    S.now = function() return CLOCK end
    VOL, STOPPED = {}, {}
    function E:setVolume(id, v) VOL[id] = v end
    function E:isPlaying(id) return not STOPPED[id] end
    function E:stopSound(id) STOPPED[id] = true end
    function round(t) CLOCK = t; return (S.GunnerFire('gun25', 110.5, 100.5)) end
    function count(name) local n = 0; for _, p in ipairs(PLAYED) do if p == name then n = n + 1 end end; return n end
    function idOf(name, k) local n = 0; for i, p in ipairs(PLAYED) do if p == name then n = n + 1; if n == k then return i end end end end
    function ticks() for _, fn in ipairs(HANDLERS.OnTickEvenPaused) do fn() end end
    """)
    check(L.eval("round(1000)") == True, "the first round leaves at once")
    check(L.eval("count('SH_Seat_Fire25')") == 1 and L.eval("count('SH_Seat_Spin25')") == 0, "the stream alone: the spin sounded like an explosion")
    fire = L.eval("idOf('SH_Seat_Fire25', 1)")
    first = L.eval(f"VOL[{fire}]")
    for t in range(1, 15):
        check(L.eval(f"round({1000 + t * 80})") == True, "the stream goes on")
        L.execute("ticks()")
    check(L.eval("count('SH_Seat_Fire25')") == 1, "one stream a burst, not one a round")
    check(not L.eval(f"STOPPED[{fire}]"), "a held trigger keeps the stream")
    last = L.eval(f"VOL[{fire}]")
    check(abs(first - 1) < 1e-9, f"full level from the first round (2026-10-31, the user): {first}")
    check(abs(last - 1) < 1e-9, f"and stays there: {last}")
    # the trigger let go: stream and spin go by a short fade, the wind-down plays once
    level = last
    L.execute("CLOCK = 2130; S.StopGunner25Audio(false); ticks(); S.StopGunner25Audio(false); CLOCK = 2170; ticks()")
    check(L.eval("count('SH_Seat_Tail25')") == 1, "one wind-down a release")
    check(L.eval(f"VOL[{fire}]") < level, "fading")
    L.execute("CLOCK = 2230; ticks()")
    check(L.eval(f"STOPPED[{fire}]") == True, "the stream is gone 80 ms after the release")
    # a real pause is a new burst, a round soon after is the same one
    check(L.eval("round(2600)") == True and L.eval("count('SH_Seat_Fire25')") == 2, "a new burst starts again")
    check(L.eval("round(2680)") == True and L.eval("count('SH_Seat_Fire25')") == 2, "same burst")
    # rounds stop with no release: a loop must not run on by itself
    fire = L.eval("idOf('SH_Seat_Fire25', 2)")
    L.execute("CLOCK = 3100; ticks()")
    check(L.eval(f"STOPPED[{fire}]") == True, "the stream ends without rounds")
    # leaving the seat: no wind-down
    L.execute("round(4000); S.StopGunner25Audio(true); S.StopGunnerShotAudio()")
    check(L.eval("count('SH_Seat_Tail25')") == 1, "no wind-down on leaving")
    check(L.eval("STOPPED[idOf('SH_Seat_Fire25', 3)]") == True, "stopped with the seat")


@test
def seat_sounds_are_skyhammers_own_slots():
    # (2026-10-24, the user) the seat's and the gunship's sounds are Skyhammer's own, one file a
    # slot in media/sound/skyhammer_seat (Skyhammer_SeatSounds.txt): a shot a round, each gun its own
    def fired(w, n):
        L = world()
        L.execute(f"PHASE.gun25 = 'ON_STATION'; AMMO.gun25 = 600; S.SetGunnerManned(true); PLAYED = {{}}")
        for k in range(n):
            L.execute(f"run_until({k * 400}); S.GunnerFire('{w}', 110.5, 100.5)")
        return [L.eval(f"PLAYED[{i}]") for i in range(1, L.eval("#PLAYED") + 1)]
    check(fired("gun25", 3).count("SH_Seat_Fire25") == 3, "25mm")
    check(fired("gun", 2).count("SH_Seat_Shot40") == 2, "40mm")
    check(fired("he", 1).count("SH_Seat_Shot105") == 1, "105mm")
    script = io.open(os.path.join(MOD, "scripts", "Skyhammer_SeatSounds.txt"), encoding="utf-8").read()
    for slot in ("SH_Seat_Fire25", "SH_Seat_Tail25", "SH_Seat_Shot40", "SH_Seat_Shot105", "SH_Seat_Impact40",
                 "SH_Seat_Impact105", "SH_Seat_Reload40", "SH_Seat_Reload105", "SH_Seat_Hitmarker", "SH_Seat_Entry",
                 "SH_AC130_EngineLoop", "SH_AC130_EngineDepart"):
        check(("sound " + slot + "\n") in script.replace("\r\n", "\n"), f"{slot} defined")
    for f in __import__("re").findall(r"file = (media/sound/[^,]+),", script):
        check(os.path.isfile(os.path.join(MOD, "..", f)), f"{f} is there")


@test
def nothing_tied_to_another_games_audio():
    # (2026-10-24, the user: "don't tie it to MW2, nothing") no file, sound or name of it left
    for d, _, fs in os.walk(MOD):
        for f in fs:
            p = os.path.join(d, f)
            check("mw2" not in p.lower(), f"no such file: {p}")
            if f.endswith((".lua", ".txt")):
                check("mw2" not in open(p, encoding="utf-8", errors="replace").read().lower(), f"no MW2 in {f}")


def zombie_at(L, x, y):
    L.execute(f"""
    local z = {{ cls = 'IsoZombie', x = {x}, y = {y}, z = 0 }}
    function z:getX() return self.x end; function z:getY() return self.y end; function z:getZ() return self.z end
    function z:isDead() return false end; function z:getHealth() return 1 end
    function z:getModData() return {{}} end; function z:getVariableBoolean() return false end
    function z:getCurrentSquare() return newSquare(self.x, self.y, 0) end
    function z:getOnlineID() return 1 end
    ON_SQUARE = ON_SQUARE or {{}}
    ON_SQUARE[math.floor(z.x) .. ',' .. math.floor(z.y)] = z""")


@test
def seat_40mm_kill_reach():
    # (the user: "check the hit area") a round kills for sure within 1.25 tiles of where it lands
    # and 6 in 10 out to 2.5 tiles (2026-10-25, the user: "a little wider"; was 1 / 2). The aimed
    # 40mm from the ground keeps its own 1.6 tiles at 35%
    # (ZombRand n-1: the scatter puts the round 0.5 tiles toward +x, so a zombie d tiles toward -x
    # is d + 0.5 from it)
    for d, want in ((0.7, True), (1.0, False)):
        L = world()
        zombie_at(L, 120.5 - d, 100.5)
        L.execute("""
        local base = newSquare
        newSquare = function(x, y, z)
            local sq = base(x, y, z)
            local o = ON_SQUARE[math.floor(x) .. ',' .. math.floor(y)]
            function sq:getMovingObjects() return { size = function() return o and 1 or 0 end, get = function() return o end } end
            return sq
        end
        ZombRand = function(n) return n - 1 end      -- every chance below 100 % fails, the scatter is ~0
        BEFORE = S.Kit.killCount()
        S.GunnerFire('gun', 120.5, 100.5)""")
        L.execute("run_until(1000)")
        got = L.eval("S.Kit.killCount() - BEFORE") > 0
        check(got == want, f"{d} tiles off: killed {got}, want {want}")
    L = world()
    check(L.eval("(function() local a, b = S.GunnerSpread('gun'); return a .. ',' .. b end)()") == "0.5,2.5",
          "the map's rings: 0.5 tiles of scatter, 2.5 tiles of reach")


def friend_on_point(L):
    # a friendly NPC (a Bandits friend; A-Life's friends go through the same friendly()) on the aim
    # point, every chance passing and no scatter
    zombie_at(L, 120.5, 100.5)
    L.execute("""
    local f = ON_SQUARE['120,100']
    function f:getOutfitName() return nil end; function f:getModData() return { brain = { hostile = false } } end
    local base = newSquare
    newSquare = function(x, y, z)
        local sq = base(x, y, z)
        local o = ON_SQUARE[math.floor(x) .. ',' .. math.floor(y)]
        function sq:getMovingObjects() return { size = function() return o and 1 or 0 end, get = function() return o end } end
        return sq
    end
    ZombRand = function() return 0 end
    PHASE.gun25 = 'ON_STATION'; AMMO.gun25 = 600
    BEFORE = S.Kit.killCount()""")
    check(L.eval("S.IsFriendlyNPC(ON_SQUARE['120,100'])") == True, "the NPC counts as friendly")


@test
def seat_hits_friendly_npcs():
    # (2026-10-25, the user: "from the seat, friendly NPCs are hit too") the seat's 25mm, 40mm and
    # 105 kill a friendly NPC; air support called any other way still spares it
    for w in ("gun25", "gun", "he"):
        L = world()
        friend_on_point(L)
        L.execute(f"S.GunnerFire('{w}', 120.5, 100.5)")
        L.execute("run_until(3000)")
        check(L.eval("S.Kit.killCount() - BEFORE") == 1, f"{w}: the friendly NPC is hit from the seat")
    L = world()
    friend_on_point(L)
    L.execute("S.Kit.blast(120.5, 100.5, 0, { { 2, 100 } }, 2, 'he')")
    check(L.eval("S.Kit.killCount() - BEFORE") == 0, "a mission's blast still spares it")
    L = world()
    friend_on_point(L)
    L.execute("S.Kit.launch('he', 120.5, 100.5, 0, 100); run_until(500)")
    check(L.eval("S.Kit.killCount() - BEFORE") == 0, "a 105 mission's shell still spares it")


@test
def seat_kills_go_online_marked():
    # online the server decides: the seat's kills go in their own command, marked seat, so the
    # server lets them through; a mission's kills go unmarked as before
    L = world()
    friend_on_point(L)
    L.execute("""
    ONLINE = true; KILLS = {}
    local send = sendClientCommand
    sendClientCommand = function(p, m, c, a) if c == 'kill' then KILLS[#KILLS + 1] = a.seat == true and 'seat' or 'plain' end; send(p, m, c, a) end
    S.GunnerFire('gun', 120.5, 100.5)""")
    L.execute("run_until(1000)")
    check([L.eval(f"KILLS[{i}]") for i in range(1, L.eval("#KILLS") + 1)] == ["seat"], "the seat's kill is sent marked")
    srv = io.open(os.path.join(LUA, "server", "Skyhammer_Server.lua"), encoding="utf-8").read()
    check("elseif not args.seat and friendly(z, player) then" in srv, "the server spares friends unless the seat fired")


@test
def seat_blasts_hurt_the_body_where_it_stands():
    # (2026-10-25, the user: "the body is hit all the time in the seat") in the real view the
    # character is the camera over the aim point; a blast there must not count as hitting the
    # body, which stays home (S.GunnerBodyAt); one at home still does
    L = world()
    L.execute("OPTVALS.protectPlayer = false; LOST = {}; ME.x, ME.y = 100, 100")
    L.execute("S.GunnerBodyAt = function() return 300, 300, 0 end")
    L.execute("S.Kit.hurtPlayer(100, 100, 0, { { 2, 100 } })")
    check(L.eval("#LOST") == 0, f"a blast under the camera, the body far off: {L.eval('#LOST')}")
    L.execute("S.Kit.hurtPlayer(300.5, 300.5, 0, { { 2, 100 } })")
    check(L.eval("#LOST") == 1, f"a blast at the body: {L.eval('#LOST')}")
    L.execute("S.GunnerBodyAt = nil; LOST = {}; S.Kit.hurtPlayer(100, 100, 0, { { 2, 100 } })")
    check(L.eval("#LOST") == 1, "out of the seat: where the character stands, as before")


@test
def seat_noise_has_no_player_source():
    # (2026-10-25, the user: infected came and bit the air over the aim point, "the body is hit")
    # while the character is the seat's camera, a blast's noise names no source: the infected
    # still go to it, but no mod (Blackout Predators' volatiles) takes the camera as its target
    L = world()
    # (the stub world answers a missing global with a table: record "none" for nil)
    L.execute("SRC = 'unset'; addSound = function(src, x, y, z, r, v) SRC = (src == nil) and 'none' or src end")
    L.execute("S.GunnerBodyAt = function() return 300, 300, 0 end; S.Kit.attract(100, 100, 0, 50)")
    check(L.eval("SRC") == "none", f"seated: no source ({L.eval('SRC')})")
    L.execute("S.GunnerBodyAt = nil; S.Kit.attract(100, 100, 0, 50)")
    check(L.eval("SRC == ME"), "out of the seat: the player, as before")


@test
def not_on_station_or_empty():
    L = world()
    L.execute("PHASE.he = 'INBOUND'")
    ok, why = L.eval("(function() return S.GunnerFire('he', 120.5, 100.5) end)()")
    check(ok == False and why == "notready", f"not on station: {ok} {why}")
    L = world()
    L.execute("AMMO.he = 0")
    ok, why = L.eval("(function() return S.GunnerFire('he', 120.5, 100.5) end)()")
    check(ok == False and why == "empty", f"no shells: {ok} {why}")


@test
def last_shell_sends_the_gunship_home_when_dry():
    L = world()
    L.execute("AMMO.he = 1; AMMO.gun = 0; S.GunnerFire('he', 120.5, 100.5)")
    L.execute("run_until(5000)")
    check("HeDry" in [L.eval(f"SAID[{i}]") for i in range(1, L.eval("#SAID") + 1)], "the crew says the 105 is dry")
    check(L.eval("#RELEASED") == 1, "nothing left: the gunship goes home")


@test
def reload_kept_across_reentry_but_not_sorties():
    L = world()
    L.execute("S.SetGunnerManned(true); S.GunnerFire('he', 120.5, 100.5); S.SetGunnerManned(false); S.SetGunnerManned(true)")
    check(L.eval("S.GunnerReload('he')") > 2000, "leaving and re-entering the seat keeps the reload")
    L.execute("SORTIE = 2")
    check(L.eval("S.GunnerReload('he')") == 0, "a new sortie starts loaded")


@test
def seat_reload_sound_is_the_loud_one():
    L = world()
    L.execute("S.GunnerFire('he', 120.5, 100.5)")
    L.execute("run_until(600)")
    check(played(L) == ["SH_Reload_105_Gunner"], f"the seat's own (louder) reload: {played(L)}")
    L = world()
    L.execute("DEFINED.SH_Reload_105_Gunner = nil; S.GunnerFire('he', 120.5, 100.5)")
    L.execute("run_until(600)")
    check(played(L) == ["SH_Reload_105"], f"without it, the usual one: {played(L)}")


@test
def auto_40mm_pauses_while_manned():
    L = world()
    L.execute("""
    local z = { x = 110, y = 100, z = 0 }
    function z:getX() return self.x end; function z:getY() return self.y end; function z:getZ() return self.z end
    function z:isDead() return false end; function z:getHealth() return 1 end
    function z:getCurrentSquare() return newSquare(self.x, self.y, 0) end
    function z:getModData() return {} end; function z:getVariableBoolean() return false end
    ZOMBIES[1] = z
    S.SetGunnerManned(true)""")
    L.execute("run_until(8000)")
    check(L.eval("AMMO.gun") == 60, f"manned: the 40mm's own fire waits, spent {60 - L.eval('AMMO.gun')}")
    L.execute("S.SetGunnerManned(false)")
    L.execute("run_until(20000)")
    check(L.eval("AMMO.gun") < 60, "the seat left: it fires on its own again")


@test
def gun_hold_kept():
    L = world()
    L.execute("S.SetGunHold(true); S.SetGunnerManned(true); S.SetGunnerManned(false)")
    check(L.eval("S.GunHold()") == True, "a hold order stays a hold after the seat")


@test
def he_rounds_option_gone():
    core = io.open(os.path.join(LUA, "client", "Skyhammer_Core.lua"), encoding="utf-8").read()
    pvp = io.open(os.path.join(LUA, "shared", "Skyhammer_PvP.lua"), encoding="utf-8").read()
    feed = io.open(os.path.join(LUA, "client", "Skyhammer_Feed.lua"), encoding="utf-8").read()
    ops = io.open(os.path.join(LUA, "client", "Skyhammer_Ops.lua"), encoding="utf-8").read()
    for name, txt in (("Core", core), ("PvP", pvp), ("Feed", feed), ("Ops", ops)):
        check('"heRounds"' not in txt, f"{name} no longer uses the heRounds option")
    L = world()
    check(L.eval("S.HeRounds()") == 2, "a terminal 105 mission fires 2 (the old default)")


@test
def online_shell_warns_players():
    L = world()
    L.execute("ONLINE = true; SandboxVars.Skyhammer.PvP = true; SENT = {}")
    L.execute("S.GunnerFire('he', 120.5, 100.5)")
    sent = [L.eval(f"SENT[{i}]") for i in range(1, L.eval("#SENT") + 1)]
    check(any(s.startswith("warn") for s in sent), f"PvP: other players are warned of the shell: {sent}")


@test
def loud_reload_defined_in_both_places():
    txt = io.open(os.path.join(MOD, "scripts", "Skyhammer_Sounds.txt"), encoding="utf-8").read()
    check("sound SH_Reload_105_Gunner\n" in txt and "sh_reload_105.wav, distanceMin = 40, distanceMax = 80, reverbFactor = 0, volume = 2.0," in txt,
          "SH_Reload_105_Gunner: the same file at volume 2.0")
    js = io.open(os.path.join(SRC, "build.js"), encoding="utf-8").read()
    check("fixedEffect('SH_Reload_105_Gunner'" in js, "build.js writes it too (else a rebuild drops it)")


@test
def gun25_has_no_impact_sound():
    # (2026-10-31, the user) the impact buried the gun, so the 25mm lands silently.
    L = world()
    L.execute("""
    HEARD, WORLD = {}, {}
    S.GunnerImpactAudio = function(w) HEARD[w] = (HEARD[w] or 0) + 1; return true end
    S.SetGunnerManned(true)
    PHASE.gun25 = 'ON_STATION'; AMMO.gun25 = 600
    for k = 1, 8 do run_until(k * 100); S.GunnerFire('gun25', 110.5, 100.5) end
    run_until(2000)
    """)
    check(L.eval("HEARD.gun25") is None, "no 25mm impact in the seat")
    ops = io.open(os.path.join(LUA, "client", "Skyhammer_Ops.lua"), encoding="utf-8").read()
    check('"SH_30mm_Impact", impactEvery' not in ops, "nor from the world sound")
    L.execute("PHASE.gun = 'ON_STATION'; AMMO.gun = 60; run_until(3000); S.GunnerFire('gun', 110.5, 100.5); run_until(5000)")
    check(L.eval("HEARD.gun") == 1, "the 40mm keeps its impact")


if __name__ == "__main__":
    passed = 0
    for t in TESTS:
        try:
            t(); passed += 1; print("PASS", t.__name__)
        except Exception as e:
            print("FAIL", t.__name__, repr(e)[:400])
    print(f"{passed}/{len(TESTS)} passed")
    sys.exit(0 if passed == len(TESTS) else 1)
