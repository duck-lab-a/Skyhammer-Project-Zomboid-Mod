# (2026-11-16, the user: "적극 사격 모드를 ... 터미널에서도 선택할수있게", picked "귀환 옆", then
# "빨간색으로") the AC-130 tab's aggressive-fire switch sits beside a half-width recall button, flips the
# Mod Option, revalidates the radio like every command, is locked under PvP, and shows red while on.
# Other tabs keep a full-width recall; ODIN-style beside = "recall" orders still work.
import io, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import sim_loadout as base

TESTS = []
def test(f): TESTS.append(f); return f
def ok(c, what):
    if not c: raise AssertionError(what)
def eq(a, b, what=""):
    if a != b: raise AssertionError(f"{what}: {a!r} != {b!r}")

BTNS = '"callBtn", "recallBtn", "actBtn", "eyeBtn", "act2Btn", "eye2Btn", "holdBtn", "gunAimBtn", "loadoutBtn", "nukeLoadoutBtn", "aggroBtn"'

def world():
    L = base.world(terminal=True)
    for f in ("client/Skyhammer_Apache.lua", "client/Skyhammer_Napalm.lua", "client/Skyhammer_A10.lua",
              "shared/Skyhammer_NukeZones.lua", "client/Skyhammer_Nuke.lua"):
        L.execute(io.open(os.path.join(base.LUA, f), encoding="utf-8").read())
    L.execute("""
        T = SkyhammerTerminal
        function row2(o) return o.A.control.y + o.A.control.h - 16 - 38 * 2 - 8 end
        local function btn()
            local b = { title = "", height = 38, width = 200, x = 516, y = 0, visible = true, enable = false }
            function b:setVisible(v) self.visible = v end
            function b:setY(v) self.y = v end
            function b:setX(v) self.x = v end
            function b:setWidth(v) self.width = v end
            function b:setTitle(v) self.title = v end
            function b:setTooltip(v) self.tip = v end
            return b
        end
        function panel(key)
            local o = setmetatable({ key = key, A = { control = { x = 500, y = 100, w = T.SIDE, h = 428 } },
                btnH = 38, btnX = 516, btnW = T.SIDE - 32, map = {} }, { __index = T })
            for _, n in ipairs({ """ + BTNS + """ }) do o[n] = btn() end
            o.loadoutBtn.internal = "conv"; o.nukeLoadoutBtn.internal = "nuke"
            o.drawRect = function() end; o.drawRectBorder = function() end; o.text = function() end
            o:drawControl(true, false, nil)
            return o
        end
        function col(b, f) local c = b[f or 'textColor']; return string.format('%.2f,%.2f,%.2f', c.r, c.g, c.b) end
        SETS = {}
        S.setOpt = function(id, v) SETS[#SETS + 1] = id .. '=' .. tostring(v); OPTVALS[id] = v end
    """)
    return L

@test
def switch_sits_beside_a_half_width_recall_on_the_ac130_tab():
    L = world()
    L.execute("PA = panel('ac130')")
    eq(L.eval("PA.aggroBtn.visible"), True, "shown on the AC-130 tab")
    eq(L.eval("PA.aggroBtn.y"), L.eval("row2(PA)"), "in the recall row")
    half = L.eval("math.floor((PA.btnW - 8) / 2)")
    eq(L.eval("PA.recallBtn.width"), half, "recall half width")
    eq(L.eval("PA.aggroBtn.x"), L.eval("PA.btnX") + half + 8, "switch on the right half")
    eq(L.eval("PA.aggroBtn.width"), L.eval("PA.btnW") - half - 8, "and the rest of the row")
    eq(L.eval("PA.recallBtn.font == PA.aggroBtn.font"), True, "one font for the row")
    # no extra row: the hold row is still the fourth one, the art keeps its room
    eq(L.eval("PA.holdBtn.y"), L.eval("PA.A.control.y + PA.A.control.h - 16 - 38 * 4 - 8 * 3"), "rows unchanged")

@test
def switch_is_usable_in_any_phase_and_titles_follow_the_option():
    L = world()
    L.execute("PA = panel('ac130')")
    eq(L.eval("PA.aggroBtn.enable"), True, "ready: can be set before the call")
    eq(L.eval("PA.aggroBtn.title"), "IGUI_SH_Btn_AggroOff", "off by default")
    L.execute("OPTVALS.ac130Aggressive = true; PA = panel('ac130')")
    eq(L.eval("PA.aggroBtn.title"), "IGUI_SH_Btn_AggroOn", "on")
    L.execute("S.Call('ac130'); advance(60000); S.Update('ac130'); PA = panel('ac130')")
    eq(L.eval("PA.aggroBtn.enable"), True, "on station too")

@test
def switch_is_red_while_on():
    L = world()
    L.execute("PA = panel('ac130'); OFF = col(PA.aggroBtn)")
    L.execute("OPTVALS.ac130Aggressive = true; PA = panel('ac130')")
    red = "%.2f,%.2f,%.2f" % (214 / 255, 104 / 255, 88 / 255)
    eq(L.eval("col(PA.aggroBtn)"), red, "red text while on")
    eq(L.eval("col(PA.aggroBtn, 'borderColor')"), red, "red edge while on")
    ok(L.eval("OFF") != red, "not red while off")
    # (mod-verifier: hovering the red switch turned its background grey) hovered it stays red
    L.execute("hv = PA.aggroBtn.backgroundColorMouseOver")
    ok(L.eval("hv.r > hv.g * 1.5 and hv.r > hv.b * 1.5"), "hover background red while on")
    L.execute("OPTVALS.ac130Aggressive = false; PA:drawControl(true, false, nil); hv = PA.aggroBtn.backgroundColorMouseOver")
    eq(L.eval("string.format('%.2f,%.2f,%.2f', hv.r, hv.g, hv.b)"), "0.13,0.15,0.16", "usual grey hover while off")

@test
def pressing_flips_the_mod_option():
    L = world()
    L.execute("PA = panel('ac130'); PA.signal = function() return true end; PA:onAggro()")
    eq(L.eval("SETS[1]"), "ac130Aggressive=true", "turned on")
    L.execute("PA:onAggro()")
    eq(L.eval("SETS[2]"), "ac130Aggressive=false", "and off again")

@test
def pvp_lock_disables_and_refuses():
    L = world()
    L.execute("S.PvP = function() return true end; PA = panel('ac130'); PA.signal = function() return true end")
    eq(L.eval("PA.aggroBtn.enable"), False, "greyed under the PvP lock")
    L.execute("PA:onAggro()")
    eq(L.eval("#SETS"), 0, "nothing set")

@test
def other_tabs_keep_a_full_width_recall():
    L = world()
    for key in ("b2", "a10", "apache"):
        L.execute(f"P = panel('{key}')")
        eq(L.eval("P.aggroBtn.visible"), False, f"{key}: no switch")
        eq(L.eval("P.recallBtn.width"), L.eval("P.btnW"), f"{key}: full recall")
    # the same panel going from the AC-130 tab to the B-2's
    L.execute("PA = panel('ac130'); PA.key = 'b2'; PA:drawControl(true, false, nil)")
    eq((L.eval("PA.aggroBtn.visible"), L.eval("PA.recallBtn.width")), (False, L.eval("PA.btnW")), "switch goes with the tab")

@test
def odin_style_beside_recall_order_still_works():
    L = world()
    L.execute("""S.RegisterSupport({ key = 'odin', inbound = 1000, station = 60000, rearm = 1000,
        orders = { { title = 'A', press = function() end }, { title = 'B', beside = 'recall', press = function() end } } })""")
    eq(L.eval("S.Supports.odin ~= nil"), True, "registered")
    L.execute("P = panel('odin')")
    eq(L.eval("P.aggroBtn.visible"), False, "no switch on an add-on tab")
    eq(L.eval("P.gunAimBtn.y"), L.eval("row2(P)"), "its order beside recall")

@test
def switch_revalidates_the_radio():
    import sim_terminal_perf as perf
    L = perf.world()
    L.execute("SETS = {}; S.setOpt = function(id, v) SETS[#SETS + 1] = id end")
    L.execute("P:signal(true);PRESENT=false;P.key='ac130';P:onAggro()")
    eq(L.eval("#SETS"), 0, "no radio: nothing set")
    eq(L.eval("SCANS"), 2, "looked again")

@test
def texts_exist_in_every_language():
    import json
    want = {"ko": ("초토화 켜짐", "초토화 꺼짐")}
    for lang in ("en", "ko", "cn"):
        src = json.load(open(os.path.join(HERE, "..", "ui_%s.json" % lang), encoding="utf-8"))
        built = json.load(open(os.path.join(base.LUA, "shared", "Translate", lang.upper(), "IG_UI.json"), encoding="utf-8"))
        for k in ("IGUI_SH_Btn_AggroOn", "IGUI_SH_Btn_AggroOff"):
            ok(src.get(k) and built.get(k) == src.get(k), f"{lang}: {k}")
        if lang in want:
            eq((src["IGUI_SH_Btn_AggroOn"], src["IGUI_SH_Btn_AggroOff"]), want[lang], lang)

if __name__ == '__main__':
    passed = 0
    for t in TESTS:
        try: t(); passed += 1; print('PASS', t.__name__)
        except Exception as e: print('FAIL', t.__name__, str(e)[:600])
    print(f'{passed}/{len(TESTS)} passed'); sys.exit(0 if passed == len(TESTS) else 1)
