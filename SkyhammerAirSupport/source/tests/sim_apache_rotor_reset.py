# The Apache's rotor loop is stopped, and its fly-off tail forgotten, when a game starts or the
# main menu opens, as the AC-130's engines are (2026-10-25, Codex's MP audio audit: only its tick
# was kept, so the last world's loop handle and tail carried over).
# Run: <codex python> -I source/tests/runsim.py source/tests/sim_apache_rotor_reset.py
import sys
import sim_pvp_client as base

TESTS = []
def test(fn): TESTS.append(fn); return fn


def world():
    L = base.world()
    L.execute("""
    ROTOR = { plays = 0, stops = 0 }
    local E = {}
    function E:setPos() end
    function E:playSoundImpl(name) if name == 'SH_Rotor_Loop' then ROTOR.plays = ROTOR.plays + 1 end; return ROTOR.plays end
    function E:playSound() error('networked playSound') end
    function E:stopSound() ROTOR.stops = ROTOR.stops + 1 end
    function E:setVolume() end; function E:set3D() end; function E:tick() end
    function E:isPlaying() return true end
    IsoWorld = { instance = { getFreeEmitter = function() return E end } }
    OPTVALS = OPTVALS or {}; OPTVALS.rotorVolume = 0.6
    APH = 'ON_STATION'
    local phase = S.Phase
    S.Phase = function(k) if k == 'apache' then return APH end return phase(k) end
    function hookTick(n) for i = 1, n do for _, f in ipairs(S.Hooks.tick) do pcall(f, 0, 250) end end end
    function hookStart() for _, f in ipairs(S.Hooks.gameStart) do pcall(f) end end
    """)
    return L


@test
def a_new_game_stops_the_rotor_and_its_tail():
    L = world()
    L.execute("hookTick(4)")
    assert L.eval("ROTOR.plays") == 1, "the rotor is heard on station"
    L.execute("APH = 'READY'; hookStart()")
    assert L.eval("ROTOR.stops") == 1, "stopped at the game's start"
    L.execute("hookTick(4)")
    assert L.eval("ROTOR.plays") == 1, "no fly-off tail carried into the new game"


@test
def the_main_menu_stops_it():
    L = world()
    L.execute("hookTick(4); APH = 'READY'; fire('OnMainMenuEnter'); hookTick(4)")
    assert L.eval("ROTOR.stops") >= 1 and L.eval("ROTOR.plays") == 1, (L.eval("ROTOR.stops"), L.eval("ROTOR.plays"))


if __name__ == "__main__":
    passed = 0
    for t in TESTS:
        try: t(); passed += 1; print("ok  ", t.__name__)
        except Exception as e: print("FAIL", t.__name__, "-", repr(e)[:300])
    print(f"{passed}/{len(TESTS)} passed")
    sys.exit(0 if passed == len(TESTS) else 1)
