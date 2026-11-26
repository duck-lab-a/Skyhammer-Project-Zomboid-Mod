# AC-130 aggressive fire (2026-11-14, the user): Mod Options "ac130Aggressive", off by default.
# Off: the old fire (the 40mm alone, a burst every gunInterval2 s; the 105 only on a mark; the
# 25mm only from the gunner seat). On ("the Angel of Death": everything around it flattened while
# it circles): all three guns work on their own, spending the rounds the gunner seat shows (40mm
# gunAmmo2, 105 heAmmo, 25mm 600) - quick 40mm bursts, sweeping 25mm bursts, a 105 every few
# seconds at the biggest group in the open well clear of the player. The 25mm then keeps the
# gunship up until it is spent too. The crew talks now and then (a 105 call at most every 30 s),
# not at every shot. Also (same day, the user): the angel flares go out without the crew's call.
# Run: <python with lupa> -I source/tests/runsim.py source/tests/sim_ac130_aggressive.py
import io, json, math, os, sys
from lupa import lua51

HERE = os.path.dirname(os.path.abspath(__file__))
MOD = os.path.join(HERE, "..", "..", "42", "media")
LUA = os.path.join(MOD, "lua")
SRC = os.path.join(HERE, "..")
sys.path.insert(0, HERE)
import sim_gunner as gbase
import sim_radio_ahead as rbase

STUBS = gbase.STUBS + r"""
-- the save's ModData a real table (the base stub's `_G.MD or {}` finds the do-nothing object)
MD = {}
-- zombies stand on squares: getMovingObjects lists them, so splash and blast reach them
ON_SQ = {}
local plainSquare = newSquare
function newSquare(x, y, z)
    local sq = plainSquare(x, y, z)
    function sq:getMovingObjects()
        local l = ON_SQ[sq.x .. "," .. sq.y .. "," .. sq.z] or {}
        return { size = function() return #l end, get = function(_, i) return l[i + 1] end }
    end
    return sq
end
-- mortal ones die when killed; the others come back (an endless supply to shoot at)
function addZombie(x, y, mortal)
    local zb = { cls = "IsoZombie", x = x, y = y, z = 0, dead = false, mortal = mortal == true }
    function zb:getX() return self.x end
    function zb:getY() return self.y end
    function zb:getZ() return self.z end
    function zb:isDead() return self.dead end
    function zb:getHealth() return self.dead and 0 or 1 end
    function zb:getModData() return {} end
    function zb:hasModData() return false end
    function zb:getVariableBoolean() return false end
    function zb:getVariableString() return "" end
    function zb:getCurrentSquare() return newSquare(self.x, self.y, self.z) end
    function zb:getOnlineID() return 1 end
    function zb:Kill() if self.mortal then self.dead = true end end
    ZOMBIES[#ZOMBIES + 1] = zb
    local k = math.floor(x) .. "," .. math.floor(y) .. ",0"
    ON_SQ[k] = ON_SQ[k] or {}
    table.insert(ON_SQ[k], zb)
    return zb
end
-- the Mod Options page as Core builds it: its rows in order
ROWS = {}
local PAGE2 = setmetatable({
    getOption = function(_, id) return { getValue = function() return OPTVALS[id] end, setValue = function() end } end,
    addTitle = function(_, t) ROWS[#ROWS + 1] = "#" .. tostring(t) end,
    addTickBox = function(_, id, label, default) ROWS[#ROWS + 1] = id .. "=" .. tostring(default) end,
    addSlider = function(_, id) ROWS[#ROWS + 1] = id end,
    addKeyBind = function(_, id) ROWS[#ROWS + 1] = id end,
    addComboBox = function(_, id) ROWS[#ROWS + 1] = id; return { addItem = function() end } end,
}, { __index = function() return function() end end })
PZAPI = { ModOptions = { create = function() return PAGE2 end, save = function() end } }
"""


def world(aggressive=True, opts=None):
    L = lua51.LuaRuntime()
    L.execute(STUBS)
    L.execute("OPTVALS.ac130Aggressive = %s" % ("true" if aggressive else "false"))
    for k, v in (opts or {}).items():
        L.execute("OPTVALS[%r] = %s" % (k, v))
    for f in ("shared/Skyhammer_PvP.lua", "client/Skyhammer_Core.lua", "client/Skyhammer_Killstreak.lua",
              "client/Skyhammer_Comms.lua", "client/Skyhammer_Ops.lua", "client/Skyhammer_SeatShotAudio.lua",
              "client/Skyhammer_25mmAudio.lua", "client/Skyhammer_GunnerTracers.lua"):
        L.execute(io.open(os.path.join(LUA, f), encoding="utf-8").read())
    L.execute(r"""
    S = Skyhammer
    isGamePaused = function() return false end
    -- the AC-130 on station; its rounds are kept in the save's own table, so Core's real
    -- S.CraftDry sees what is spent here
    PHASE = { gun = "ON_STATION", he = "ON_STATION", gun25 = "ON_STATION", ac130 = "ON_STATION" }
    D = S.Store()
    D.ammo.gun, D.ammo.he, D.ammo.gun25 = { n = 60, cap = 60 }, { n = 8, cap = 8 }, { n = 600, cap = 600 }
    AMMO = setmetatable({}, {
        __index = function(_, w) return D.ammo[w] and D.ammo[w].n or 0 end,
        __newindex = function(_, w, v) D.ammo[w] = D.ammo[w] or { n = 0, cap = v }; D.ammo[w].n = v end })
    SORTIE = 1
    SAID, RELEASED = {}, {}
    S.Phase = function(k) return PHASE[k] or "READY" end
    S.Ammo = function(w) return AMMO[w], 60 end
    S.Spend = function(w, n) if PHASE[w] ~= "ON_STATION" or AMMO[w] < n then return false end; AMMO[w] = AMMO[w] - n; return true end
    S.Sortie = function() return SORTIE end
    -- on station STATION_S seconds (the default 3 minutes) from STATION_FROM
    STATION_S, STATION_FROM = 180, 0
    S.SecondsLeft = function() return math.max(0, STATION_S - (CLOCK - STATION_FROM) / 1000) end
    S.combatMs = function() return CLOCK end
    S.CombatTick = function() end
    S.Update = function() return nil end
    S.Blocked = function() return false end
    S.Release = function(k)
        if PHASE.ac130 ~= "ON_STATION" then return false end   -- (as Core's: once off station, no more)
        RELEASED[#RELEASED + 1] = k
        PHASE.gun, PHASE.he, PHASE.gun25, PHASE.ac130 = "REARM", "REARM", "REARM", "REARM"
        return true
    end
    S.Say = function(id) SAID[#SAID + 1] = { id = id, at = CLOCK } end
    -- the 105 shells' aim points as they leave the gun (the save's rounds in the air)
    HEPTS, HEN = {}, 0
    function run_until(ms)
        for t = CLOCK, ms, 20 do
            CLOCK = t
            for _, fn in ipairs(HANDLERS.OnTick) do fn() end
            for id, f in pairs(D.inflight or {}) do
                if f.k == "he" and not HEPTS[id] then HEPTS[id] = { x = f.x, y = f.y, at = t }; HEN = HEN + 1 end
            end
        end
    end
    function said(id) local n = 0; for _, s in ipairs(SAID) do if s.id == id then n = n + 1 end end; return n end
    """)
    return L


TESTS = []
def test(fn): TESTS.append(fn); return fn
def check(c, what):
    if not c: raise AssertionError(what)
def ammo(L, w): return L.eval(f"AMMO[{w!r}]")
def he_points(L):
    return [(L.eval(f"(function() local i = 0; for _, p in pairs(HEPTS) do i = i + 1; if i == {k} then return p.x end end end)()"),
             L.eval(f"(function() local i = 0; for _, p in pairs(HEPTS) do i = i + 1; if i == {k} then return p.y end end end)()"))
            for k in range(1, L.eval("HEN") + 1)]
def crowd(L, n=10, mortal=False):
    # n infected in the open 13-28 tiles east of the player (at 100,100), all inside the guns'
    # 30 tiles: rows of 8, two tiles apart, three between rows
    for i in range(n):
        x, y = 113 + (i % 8) * 2, 94 + (i // 8) * 3
        L.execute(f"addZombie({x}.5, {y}.5, {'true' if mortal else 'false'})")


@test
def option_row_off_by_default_in_the_ac130_section():
    L = world(aggressive=False)
    rows = [L.eval(f"ROWS[{i}]") for i in range(1, L.eval("#ROWS") + 1)]
    check("ac130Aggressive=false" in rows, f"a tick box, off by default: {rows}")
    i = rows.index("ac130Aggressive=false")
    a, b = rows.index("#IGUI_SH_OptAc130"), rows.index("#IGUI_SH_OptB2")
    check(a < i < b, f"under the AC-130's title (rows {a} < {i} < {b})")
    check(L.eval("SkyhammerPvP.Locked('ac130Aggressive')") == True, "PvP holds it at its default (off)")
    for lang in ("en", "ko", "cn"):
        ui = json.load(io.open(os.path.join(SRC, f"ui_{lang}.json"), encoding="utf-8"))
        for k in ("IGUI_SH_OptAc130Aggressive", "IGUI_SH_OptAc130Aggressive_tt"):
            check(ui.get(k, "").strip(), f"{k} in ui_{lang}.json")
        built = json.load(io.open(os.path.join(LUA, "shared", "Translate", lang.upper(), "IG_UI.json"), encoding="utf-8"))
        check(built.get("IGUI_SH_OptAc130Aggressive") == ui["IGUI_SH_OptAc130Aggressive"], f"built into Translate/{lang.upper()}")


@test
def off_is_the_old_fire():
    L = world(aggressive=False)
    crowd(L)
    L.execute("run_until(60000)")
    check(ammo(L, "he") == 8, f"off: no 105 without a mark, left {ammo(L, 'he')}")
    check(ammo(L, "gun25") == 600, f"off: the 25mm only from the seat, left {ammo(L, 'gun25')}")
    spent = 60 - ammo(L, "gun")
    # (a burst of 3-5, then gunInterval2 10 s x 0.75-1.25: at most 8 bursts in a minute)
    check(3 <= spent <= 40, f"off: the 40mm now and then, spent {spent} in 60 s")


@test
def on_all_three_guns_fire():
    L = world()
    crowd(L, n=40)      # (enough bodies for three guns: the ones hit stay down a few seconds here)
    # (waves since the same day: the first wave gets a wave's share of 3 minutes, 1 of 9, spread
    # over its 15 s from 2.5 s after arrival)
    L.execute("run_until(17500)")
    g, h, q = 60 - ammo(L, "gun"), 8 - ammo(L, "he"), 600 - ammo(L, "gun25")
    check(g >= 4, f"the 40mm in quick bursts: {g} in the first wave")
    check(q >= 40, f"the 25mm sweeping on its own: {q} in the first wave")
    check(h >= 1, f"the 105 on its own: {h} in the first wave")


@test
def on_spends_every_round_then_goes_home():
    L = world()
    crowd(L, n=40)
    L.execute("run_until(200000)")
    left = (ammo(L, "gun"), ammo(L, "he"), ammo(L, "gun25"))
    check(left == (0, 0, 0), f"every round the seat shows is fired: left {left}")
    rel = [L.eval(f"RELEASED[{i}]") for i in range(1, L.eval("#RELEASED") + 1)]
    check(rel == ["ac130"], f"then home once: {rel}")
    check(L.eval("said('GunRtbAck')") == 1, "the crew says it is going home, once")


@test
def gun25_is_a_real_weapon_only_when_aggressive():
    for aggr, want in ((True, False), (False, True)):
        L = world(aggressive=aggr)
        L.execute("AMMO.gun = 0; AMMO.he = 0; AMMO.gun25 = 100")
        check(L.eval("S.CraftDry('ac130')") == want, f"aggressive {aggr}: 40mm and 105 empty, 25mm left -> dry {want}")


@test
def the_105_keeps_clear_of_the_player():
    L = world()
    for i in range(8):
        L.execute(f"addZombie({103 + i}.5, 100.5)")      # 3-10 tiles off
    L.execute("run_until(30000)")
    check(ammo(L, "he") == 8, f"no 105 with the infected inside its blast of the player: left {ammo(L, 'he')}")
    check(ammo(L, "gun") < 60 and ammo(L, "gun25") < 600, "the 40mm and 25mm still work them")
    for dx in (0, 1, -1):
        L.execute(f"addZombie({100 + dx}.5, 115.5)")     # a group of 3, 15 tiles off (2026-11-15: 3+ only)
    L.execute("run_until(70000)")                        # (a shell in most waves, 20 s apart)
    pts = he_points(L)
    check(len(pts) >= 1, "the 105 fires once there is one far enough out")
    for x, y in pts:
        d = math.hypot(x - 100, y - 100)
        check(d >= 12, f"every 105 lands 12+ tiles from the player (its blast reaches 9.5): {d:.1f}")


@test
def the_105_goes_for_the_crowd():
    L = world()
    L.execute("addZombie(114.5, 100.5)")                 # a lone one, 14 tiles off
    for dx, dy in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1), (1, 1)):
        L.execute(f"addZombie({100 + dx}.5, {121 + dy}.5)")  # a group 21 tiles off
    L.execute("run_until(2000)")
    pts = he_points(L)
    check(len(pts) >= 1, "a 105 out")
    x, y = pts[0]
    check(math.hypot(x - 100.5, y - 121.5) <= 2, f"the first one at the group, not the lone one: {x:.1f},{y:.1f}")


@test
def the_105_only_at_three_or_more_together():
    # (2026-11-15, the user: "105mm는 조건을 정해야 하지 않나 뭐 3마리 이상 모여있을때") the 105 waits
    # for at least 3 infected together; lone ones and pairs are left to the 40mm and 25mm
    L = world()
    L.execute("addZombie(114.5, 100.5)")                 # a lone one, 14 tiles off
    L.execute("addZombie(100.5, 121.5); addZombie(101.5, 121.5)")   # a pair, 21 tiles off
    L.execute("addZombie(85.5, 100.5); addZombie(85.5, 101.5)")     # another pair, 15 tiles off
    L.execute("run_until(45000)")
    check(ammo(L, "he") == 8, f"no 105 at lone infected or pairs: left {ammo(L, 'he')}")
    check(ammo(L, "gun") < 60 or ammo(L, "gun25") < 600, "the 40mm and 25mm still work them")
    L.execute("addZombie(100.5, 122.5)")                 # the pair at 21 tiles becomes three
    L.execute("run_until(70000)")
    pts = he_points(L)
    check(len(pts) >= 1, "three together: the 105 fires")
    for x, y in pts:
        check(math.hypot(x - 100.8, y - 121.8) <= 2, f"at the three: {x:.1f},{y:.1f}")


@test
def waits_while_manned_or_on_hold():
    L = world()
    crowd(L)
    L.execute("S.SetGunnerManned(true)")
    L.execute("run_until(15000)")
    check((ammo(L, "gun"), ammo(L, "he"), ammo(L, "gun25")) == (60, 8, 600), "the seat manned: its own fire waits")
    L.execute("S.SetGunnerManned(false); S.SetGunHold(true)")
    L.execute("run_until(30000)")
    check((ammo(L, "gun"), ammo(L, "he"), ammo(L, "gun25")) == (60, 8, 600), "a hold order holds every gun")
    L.execute("S.SetGunHold(false)")
    L.execute("run_until(45000)")
    check(ammo(L, "gun") < 60 and ammo(L, "he") < 8 and ammo(L, "gun25") < 600, "cleared hot: all three again")


@test
def crew_talks_now_and_then():
    L = world()
    crowd(L, n=30)
    L.execute("run_until(90000)")
    shells = 8 - ammo(L, "he")
    calls = [L.eval(f"SAID[{i}].at") for i in range(1, L.eval("#SAID") + 1) if L.eval(f"SAID[{i}].id") == "HeShot"]
    check(1 <= len(calls) < shells, f"a 105 call now and then, not every shell: {len(calls)} calls, {shells} shells")
    for a, b in zip(calls, calls[1:]):
        check(b - a >= 30000, f"30 s or more between the 105 calls: {a} -> {b}")
    fired = (60 - ammo(L, "gun")) + shells + (600 - ammo(L, "gun25"))
    check(L.eval("#SAID") <= 20, f"a handful of lines for {fired} rounds: {L.eval('#SAID')}")


@test
def seat_25mm_last_round_sends_it_home_when_aggressive():
    L = world()
    L.execute("AMMO.gun = 0; AMMO.he = 0; AMMO.gun25 = 3; S.SetGunnerManned(true)")
    for k in range(3):
        L.execute(f"run_until({k * 100 + 100}); S.GunnerFire('gun25', 120.5, 100.5)")
    check(ammo(L, "gun25") == 0, "the seat fired the last 25mm rounds")
    L.execute("run_until(4000)")
    check(L.eval("#RELEASED") == 1, "aggressive: nothing left, the gunship goes home")


def emptied_and_home(L):
    left = (ammo(L, "gun"), ammo(L, "he"), ammo(L, "gun25"))
    rel = [L.eval(f"RELEASED[{i}]") for i in range(1, L.eval("#RELEASED") + 1)]
    return left, rel


def next_sortie_same_number(L, how):
    # a new sortie that happens to carry the old number (each save counts its sorties from 1;
    # so does a new character online): the combat clock starts over (the wall clock does not), the
    # guns are full again
    L.execute("""
    COMBAT0 = CLOCK; S.combatMs = function() return CLOCK - COMBAT0 end
    STATION_FROM = CLOCK
    SAID, RELEASED = {}, {}
    PHASE.gun, PHASE.he, PHASE.gun25, PHASE.ac130 = "ON_STATION", "ON_STATION", "ON_STATION", "ON_STATION"
    D.ammo.gun.n, D.ammo.he.n, D.ammo.gun25.n = 60, 8, 600
    """)
    if how == "game":
        L.execute("for _, fn in ipairs(HANDLERS.OnGameStart or {}) do pcall(fn) end")
    else:
        # the last one's release as Core reports it (this world's S.Release is a stand-in), then it
        # flies in: Core reports the arrival once
        L.execute("""
        S.OnReleased('ac130')
        local upd, done = S.Update, false
        S.Update = function(k) if k == 'ac130' and not done then done = true; return 'arrived' end; return nil end
        """)


@test
def next_game_starts_fresh():
    # (verifier 2026-11-14) the aggressive state was kept by sortie number alone, so a second game
    # in the same run with the same number found the first one's: the 25mm silent, no first 105
    # call, and no trip home once all was spent
    for how in ("game", "arrival"):
        L = world()
        crowd(L, n=40)
        L.execute("run_until(200000)")
        check(emptied_and_home(L) == ((0, 0, 0), ["ac130"]), f"first sortie spent and home: {emptied_and_home(L)}")
        next_sortie_same_number(L, how)
        L.execute("run_until(400000)")
        left, rel = emptied_and_home(L)
        check(left == (0, 0, 0), f"{how}: the next one spends it all again, left {left}")
        check(rel == ["ac130"], f"{how}: and goes home: {rel}")
        check(L.eval("said('HeShot')") >= 1, f"{how}: the crew calls the first 105 again")


@test
def switched_off_while_out_still_goes_home():
    # (verifier 2026-11-14) off again, the 25mm is a spare once more: with the 40mm and 105 already
    # empty, the gunship goes home instead of circling with 25mm rounds it no longer fires
    L = world()
    L.execute("AMMO.gun = 0; AMMO.he = 0")
    crowd(L, n=10)
    L.execute("run_until(3000)")
    check(ammo(L, "gun25") < 600 and L.eval("#RELEASED") == 0, "on: still up, the 25mm working")
    L.execute("OPTVALS.ac130Aggressive = false")
    L.execute("run_until(6000)")
    check(L.eval("#RELEASED") == 1, "switched off: nothing it fires is left, home")
    check(L.eval("said('GunRtbAck')") == 1, "with the crew's call")
    # (verifier re-check) the same while the crew holds fire the whole time (a save loaded on hold)
    L = world()
    L.execute("AMMO.gun = 0; AMMO.he = 0; S.SetGunHold(true)")
    L.execute("run_until(3000); OPTVALS.ac130Aggressive = false; run_until(6000)")
    check(L.eval("#RELEASED") == 1, "on hold, switched off: home too")


def fire_times(L, until_ms):
    # the times (ms) at which any of the three guns spent a round, run until until_ms
    L.execute(f"""
    FIRED = FIRED or {{}}
    local function total() return AMMO.gun + AMMO.he + AMMO.gun25 end
    local last = total()
    for t = CLOCK, {until_ms}, 20 do
        CLOCK = t
        for _, fn in ipairs(HANDLERS.OnTick) do fn() end
        local now = total()
        if now ~= last then FIRED[#FIRED + 1] = t; last = now end
    end""")
    return [L.eval(f"FIRED[{i}]") for i in range(1, L.eval("#FIRED") + 1)]


@test
def fires_in_waves_with_a_breath_between():
    # (2026-11-14, the user: it fired without a breath -> "응, 리듬으로"; 2026-11-15: "15초 발사 5초
    # 휴식으로") about 15 s of everything, then about 5 s of quiet while it circles, and again
    L = world()
    crowd(L, n=40)
    times = fire_times(L, 70000)
    check(len(times) >= 40, f"it fires: {len(times)} moments")
    gaps = [(a, b) for a, b in zip(times, times[1:]) if b - a >= 4000]
    check(len(gaps) >= 2, f"quiet spells of 4 s or more between the waves: {gaps}")
    for a, b in gaps:
        check(b - a <= 7000, f"a quiet spell of about 5 s: {a} -> {b}")
    waves, start = [], times[0]
    for (a, b) in gaps:
        waves.append((start, a)); start = b
    for s, e in waves:
        check(13000 <= e - s <= 15500, f"a wave lasts about 15 s: {s} -> {e}")


@test
def each_gun_keeps_firing_through_the_wave():
    # (2026-11-15, mod-verifier) the 40mm spent its wave share by about 11.7 s and left the last
    # 3.5 s to the 25mm alone. Each of the 40mm and the 25mm now fires to near the wave's end and
    # is never quiet for long inside it. Waves start 2.5 s after arrival, every 20 s, for 15 s.
    L = world()
    crowd(L, n=40)
    L.execute("""
    FT = {gun = {}, gun25 = {}}
    local last = {gun = AMMO.gun, gun25 = AMMO.gun25}
    for t = CLOCK, 58000, 20 do
        CLOCK = t
        for _, fn in ipairs(HANDLERS.OnTick) do fn() end
        for _, k in ipairs({"gun", "gun25"}) do
            if AMMO[k] ~= last[k] then table.insert(FT[k], t); last[k] = AMMO[k] end
        end
    end""")
    for k in ("gun", "gun25"):
        ts = [L.eval(f"FT.{k}[{i}]") for i in range(1, L.eval(f"#FT.{k}") + 1)]
        for w in range(3):
            s = 260 + 20000 * w; e = s + 15000
            inw = [t for t in ts if s - 100 <= t <= e + 100]
            check(len(inw) >= 3, f"{k}, wave {w + 1}: fires {inw}")
            if not inw: continue
            worst = max(b - a for a, b in zip(inw, inw[1:])) if len(inw) > 1 else 0
            # (the 40mm has only 5-7 rounds a wave at the default 60, so one every ~3 s at best)
            limit = 3200 if k == "gun" else 3000
            check(worst <= limit, f"{k}, wave {w + 1}: quiet at most {limit} ms inside it: {worst} ms in {inw}")
            check(e - inw[-1] <= 3000, f"{k}, wave {w + 1}: still firing in its last 3 s: last {inw[-1]}, ends {e}")


@test
def few_40mm_rounds_still_shared_over_the_waves():
    # (2026-11-15, mod-verifier) with 12 rounds of 40mm left, the gun went on past its wave share
    # and spent all 12 in the first wave
    L = world()
    L.execute("AMMO.gun = 12")
    crowd(L, n=40)
    L.execute("""
    GT = {}
    local last = AMMO.gun
    for t = CLOCK, 40000, 20 do
        CLOCK = t
        for _, fn in ipairs(HANDLERS.OnTick) do fn() end
        if AMMO.gun ~= last then for _ = 1, last - AMMO.gun do table.insert(GT, t) end; last = AMMO.gun end
    end""")
    ts = [L.eval(f"GT[{i}]") for i in range(1, L.eval("#GT") + 1)]
    first = [t for t in ts if t < 17000]
    second = [t for t in ts if 20000 <= t < 37000]
    check(1 <= len(first) <= 3, f"the first wave fires its share only: {first}")
    check(len(second) >= 1, f"the second wave still has 40mm: {second}")


@test
def rounds_last_the_time_on_station():
    # the rounds the seat shows are shared out over the time on station: still firing late in it,
    # every round gone by its end, then home
    L = world()
    crowd(L, n=40)
    L.execute("run_until(110000)")
    left = (ammo(L, "gun"), ammo(L, "he"), ammo(L, "gun25"))
    check(all(n > 0 for n in left), f"after 110 s of 180 every gun still has rounds: {left}")
    check(L.eval("#RELEASED") == 0, "still up")
    L.execute("run_until(185000)")
    left = (ammo(L, "gun"), ammo(L, "he"), ammo(L, "gun25"))
    check(left == (0, 0, 0), f"all fired by the end of its time: left {left}")
    check([L.eval(f"RELEASED[{i}]") for i in range(1, L.eval("#RELEASED") + 1)] == ["ac130"], "then home")


@test
def many_105s_in_a_wave_all_inside_it():
    # (verifier) with a big 105 load a wave holds several shells: spaced over the wave from its
    # share at the start, not from what is left of it (the last one fell outside the wave)
    L = world()
    L.execute("AMMO.he = 40")
    crowd(L, n=40)
    L.execute("run_until(17000)")      # (the first wave: 2.5 s after arrival, 15 s long)
    want = int(0.5 + 40 / 9)           # (the first wave's share of 9: 180 s in 20 s cycles)
    check(40 - ammo(L, "he") == want, f"the wave's {want} shells all fired in it: {40 - ammo(L, 'he')}")


@test
def angel_flares_go_out_without_the_call():
    L = rbase.world()
    L.execute('S.Say("GunAngelFlares", nil, { craft = "ac130", ahead = true, stale = 3000 })')
    check(rbase.cur(L) == "" and rbase.ids(L) == "", f"no flares call on the radio: on air '{rbase.cur(L)}', waiting '{rbase.ids(L)}'")
    L.execute('S.Say("GunOrbitWatch")')
    check(rbase.cur(L) == "GunOrbitWatch", "other lines still go on the air")


@test
def lua_ascii():
    for f in ("client/Skyhammer_Core.lua", "client/Skyhammer_Ops.lua", "client/Skyhammer_Comms.lua", "shared/Skyhammer_PvP.lua"):
        raw = open(os.path.join(LUA, f), "rb").read()
        check(all(b < 128 for b in raw), f"{f} is ASCII")
        check(b" next(" not in raw and b"(next(" not in raw, f"{f}: no global next (Kahlua)")


if __name__ == "__main__":
    passed = 0
    for t in TESTS:
        try:
            t(); passed += 1; print("PASS", t.__name__)
        except Exception as e:
            print("FAIL", t.__name__, repr(e)[:400])
    print(f"{passed}/{len(TESTS)} passed")
    sys.exit(0 if passed == len(TESTS) else 1)
