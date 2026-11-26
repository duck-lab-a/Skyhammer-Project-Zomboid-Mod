-- Refusals, a strike under way, and a sortie of two strikes
SAID = {}
check(S.Aim("raid", true) == false and SAID[1] == "NotReady", "not called yet: NotReady (" .. tostring(SAID[1]) .. ")")
OPTVALS.f22Raids = 2
onStation()
check(S.Ammo("raid") == 2, "two strikes from the option (" .. S.Ammo("raid") .. ")")
check(S.Supports.f22.hint("ON_STATION") == "IGUI_SH_Hint_F22Mark", "terminal hint: mark a point")
SAID = {}
mark(105, 100)
check(SAID[2] == "F22DangerClose", "a mark 5 tiles out: no safe line (" .. tostring(SAID[2]) .. ")")
check(S.IsAiming("raid") == true, "still aiming: pick another point")
check(S.Ammo("raid") == 2, "nothing spent")
S.ConfirmAimAt(160, 100)
check(S.Ammo("raid") == 1, "a safe point is taken")
local l = S.Store().f22.line
local ex, ey = l.x + math.cos(l.h) * 70, l.y + math.sin(l.h) * 70
check(S.A10SegDist(PX, PY, l.x, l.y, ex, ey) >= 10 - 1e-6, "the line keeps 10 tiles from the player")
check(near((l.x + ex) / 2, 160.5) and near((l.y + ey) / 2, 100.5), "centred on the mark")
check(S.Supports.f22.hint("ON_STATION") == "IGUI_SH_Hint_F22Next", "terminal hint: one more after this")
run(2000)
SAID = {}
check(S.Aim("raid", true) == false and SAID[1] == "Busy", "a strike under way takes no new mark (" .. tostring(SAID[1]) .. ")")
check(S.Ammo("raid") == 1, "nothing spent")
-- (off target at 12.0 s, the strike over at 13.0: ten jets 0.4 s apart)
run(11600)
check(said("F22Off") and not said("F22Winchester"), "off target, one strike left")
check(S.Phase("f22") == "ON_STATION", "still on station")
SAID = {}
mark(100, 150)
check(said("F22RollIn") and S.Ammo("raid") == 0, "the second strike")
check(S.Store().f22VisualRun.raid == 2, "second visual run")
run(13000)
check(said("F22Winchester") and S.Phase("f22") == "REARM", "home after the second")
done("marks")
