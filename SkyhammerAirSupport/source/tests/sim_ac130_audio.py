# The AC-130's engines (2026-10-24 evening): SH_AC130_EngineLoop while the gunship is on station,
# local and 2D, at the engine volume; when it leaves, the loop stops and SH_AC130_EngineDepart
# plays once (Skyhammer_SeatShotAudio GunshipDepartSound). Before that day the loop itself faded
# with the departing aircraft; that went with the seat's sound rework.
# Run: <codex python> -I source/tests/runsim.py source/tests/sim_ac130_audio.py
import io, os, sys
import sim_b2_polish as base

LUA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "42", "media", "lua")
TESTS = []
def test(f): TESTS.append(f); return f


def world():
    L = base.world()
    L.execute(io.open(os.path.join(LUA, "client", "Skyhammer_SeatShotAudio.lua"), encoding="utf-8").read())
    L.execute('''
    PH = 'ON_STATION'; S.Phase = function() return PH end
    for _, fn in ipairs(HANDLERS.OnTick) do local f = up(fn, 'gunshipEngine'); if f then GT = f end end
    assert(type(GT) == 'function')
    NAMES = {}
    E.playSoundImpl = function(_, name, flag) assert(flag == false); NAMES[#NAMES + 1] = name; CALLS.plays = CALLS.plays + 1; return CALLS.plays end
    OPTVALS.engineVolume = .6
    S.Multiplayer = function() return false end
    isGamePaused = function() return false end
    function sampleAC(ms) CLOCK = ms; GT(ms, 250); return CALLS.volume end
    for i = 0, 4000, 250 do sampleAC(i) end
    ''')
    return L


def names(L): return [L.eval(f"NAMES[{i}]") for i in range(1, L.eval("#NAMES") + 1)]


@test
def loop_on_station_at_the_engine_volume():
    L = world()
    assert names(L) == ["SH_AC130_EngineLoop"], names(L)
    assert abs(L.eval("CALLS.volume") - .6) < 1e-8, L.eval("CALLS.volume")


@test
def leaving_stops_the_loop_and_plays_the_departure_once():
    L = world()
    L.execute('PH = "REARM"; sampleAC(4250)')
    assert L.eval("CALLS.stops") == 1, "the loop stopped"
    assert names(L) == ["SH_AC130_EngineLoop", "SH_AC130_EngineDepart"], names(L)
    L.execute('for i = 4500, 9000, 250 do sampleAC(i) end')
    assert names(L).count("SH_AC130_EngineDepart") == 1, "once, not every tick"


@test
def engine_slider_at_zero_silences_it():
    L = world()
    L.execute('OPTVALS.engineVolume = 0; for i = 4250, 8000, 250 do sampleAC(i) end')
    assert L.eval("CALLS.stops") == 1, "faded out and stopped"


@test
def back_on_station_starts_again():
    L = world()
    L.execute('PH = "REARM"; sampleAC(4250); PH = "ON_STATION"; for i = 4500, 6000, 250 do sampleAC(i) end')
    assert names(L).count("SH_AC130_EngineLoop") == 2, names(L)


if __name__ == '__main__':
    passed = 0
    for f in TESTS:
        try: f(); passed += 1
        except Exception as e: print('FAIL', f.__name__, repr(e))
    print(f'{passed}/{len(TESTS)} passed'); sys.exit(0 if passed == len(TESTS) else 1)
