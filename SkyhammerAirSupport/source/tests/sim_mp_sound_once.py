# Online, a Skyhammer sound at a point is heard once by each player (2026-10-25; Codex's MP audio
# audit). The game's SoundManager.PlayWorldSound sends the sound to the server as well when it runs
# on a client (GameClient.PlayWorldSound, then PlayWorldSoundImpl), and Skyhammer relays it itself
# ("fx", to the players near enough): both together gave the others two copies, and a receiver's
# own playback sent a third. So the sound plays here through PlayWorldSoundImpl (this player
# only) and reaches the others through the relay alone.
# Run: <codex python> -I source/tests/runsim.py source/tests/sim_mp_sound_once.py
import sys
import sim_pvp_client as base

TESTS = []
def test(fn): TESTS.append(fn); return fn


def world():
    L = base.world()
    L.execute("""
    PLAYS = {}
    getSoundManager = function() return {
        PlayWorldSound = function(_, name) PLAYS[#PLAYS + 1] = 'sent ' .. name end,
        PlayWorldSoundImpl = function(_, name) PLAYS[#PLAYS + 1] = 'here ' .. name end,
    } end
    function sq(x, y, z) return { getX = function() return x end, getY = function() return y end, getZ = function() return z end } end
    local cell = getCell and getCell() or {}
    getCell = function() return setmetatable({ getGridSquare = function(_, x, y, z) return sq(x, y, z) end }, { __index = cell }) end
    """)
    return L


def plays(L): return [L.eval(f"PLAYS[{i}]") for i in range(1, L.eval("#PLAYS") + 1)]


@test
def own_sound_here_once_and_relayed():
    L = world()
    L.execute("SENT = {}; S.Kit.soundAt(sq(103, 100, 0), 'SH_40mm_Impact', 200)")
    assert plays(L) == ["here SH_40mm_Impact"], plays(L)
    assert any(s.startswith("fx") for s in base.vals(L, "SENT")), base.vals(L, "SENT")


@test
def relayed_sound_plays_here_and_goes_no_further():
    L = world()
    L.execute("server('fx', { x = 110, y = 100, z = 0, s = 'SH_105_Impact', r = 380 })")
    assert plays(L) == ["here SH_105_Impact"], plays(L)


@test
def without_the_local_call_the_old_one_still_plays():
    L = world()
    L.execute("""getSoundManager = function() return {
        PlayWorldSound = function(_, name) PLAYS[#PLAYS + 1] = 'sent ' .. name end } end
        S.Kit.soundAt(sq(103, 100, 0), 'SH_40mm_Impact', 200)""")
    assert plays(L) == ["sent SH_40mm_Impact"], plays(L)


@test
def radio_voice_for_this_player_only():
    # the crew's voice comes from the radio in this player's hand: played with the local
    # playSoundImpl, never the emitter's playSound, which online is sent to the players around
    # (whose copies this player's volume and stop then never reach)
    import io, os, re
    src = io.open(os.path.join(base.LUA, "client", "Skyhammer_Comms.lua"), encoding="utf-8").read()
    body = re.search(r"local function playVoice\(sound\)(.*?)\nend\n", src, re.S).group(1)
    assert "playSoundImpl(sound, false, nil)" in body, "the voice plays locally"
    assert re.search(r":playSound\(", src) is None, "no networked playSound left in Comms"


if __name__ == "__main__":
    passed = 0
    for t in TESTS:
        try: t(); passed += 1; print("ok  ", t.__name__)
        except Exception as e: print("FAIL", t.__name__, "-", repr(e)[:300])
    print(f"{passed}/{len(TESTS)} passed")
    sys.exit(0 if passed == len(TESTS) else 1)
