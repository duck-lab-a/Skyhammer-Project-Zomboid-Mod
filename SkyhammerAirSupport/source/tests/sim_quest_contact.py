# The unlock quest's first contact (Skyhammer_Quest startContact, 2026-10-25): every aircraft the
# radio can call checks in on the player's channel, the A-10 (VALKYRIE) too, and Aegis closes it.
# Every line it says is voiced (Skyhammer_Lines, a WAV in sound/skyhammer).
# Run: <codex python> -I source/tests/runsim.py source/tests/sim_quest_contact.py
import io, os, sys
from lupa import lua51
HERE = os.path.dirname(os.path.abspath(__file__))
LUA = os.path.join(HERE, "..", "..", "42", "media", "lua")
SOUND = os.path.join(HERE, "..", "..", "42", "media", "sound", "skyhammer")
sys.path.insert(0, HERE)
import sim_shake as base
TESTS = []
def test(f): TESTS.append(f); return f
def check(c, msg):
    if not c: raise AssertionError(msg)


def contact_lines():
    L = lua51.LuaRuntime()
    L.execute(base.STUBS)
    for f in ("client/Skyhammer_Lines.lua", "shared/Skyhammer_PvP.lua", "client/Skyhammer_Core.lua",
              "client/Skyhammer_Killstreak.lua", "client/Skyhammer_Comms.lua", "shared/Skyhammer_Relay.lua",
              "client/Skyhammer_Quest.lua"):
        L.execute(io.open(os.path.join(LUA, f), encoding="utf-8").read())
    return L.eval('''(function()
        local S = Skyhammer
        local said = {}
        S.Say = function(id) said[#said + 1] = id end
        local function up(fn, name)
            for i = 1, 255 do local k, v = debug.getupvalue(fn, i); if not k then return end; if k == name then return v end end
        end
        up(S.LinkBlock, "startContact")()
        return said
    end)()''')


@test
def every_aircraft_checks_in_at_first_contact():
    said = list(contact_lines().values())
    lines = __import__("lupa").lua51.LuaRuntime()
    lines.execute(io.open(os.path.join(LUA, "client/Skyhammer_Lines.lua"), encoding="utf-8").read())
    speakers = [lines.eval(f"Skyhammer_Lines.{i}[1]") for i in said]
    for who in ("HELLHOUND", "BANSHEE", "TITAN", "VALKYRIE"):
        check(who in speakers, f"{who} checks in: {list(zip(said, speakers))}")
    check(speakers[0] == "HAVEN" and speakers[-1] == "HAVEN", f"Aegis opens and closes: {speakers}")


@test
def every_contact_line_is_voiced():
    for i in contact_lines().values():
        check(os.path.isfile(os.path.join(SOUND, "shv_" + i.lower() + ".wav")), f"{i} has its WAV")


if __name__ == "__main__":
    passed = 0
    for f in TESTS:
        try: f(); passed += 1; print("PASS", f.__name__)
        except Exception as e: print("FAIL", f.__name__, repr(e)[:600])
    print(f"{passed}/{len(TESTS)} passed"); sys.exit(0 if passed == len(TESTS) else 1)
