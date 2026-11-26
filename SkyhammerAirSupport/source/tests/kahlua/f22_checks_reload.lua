-- Reloads in the middle of a strike: the bombs in the air land on time. With a strike left the
-- flight stays and its "off target" comes again; with none left Skyhammer_Ops sends an aircraft
-- that has nothing to fire home at the reload (as every aircraft), and the bombs still land.
OPTVALS.f22Raids = 2
column()
onStation()
mark(140, 100)
run(3000)
gameStart()
check(S.Phase("f22") == "ON_STATION", "a strike left: still on station after the reload (" .. tostring(S.Phase("f22")) .. ")")
check(inflight() == 20, "the bombs are still in the save (" .. inflight() .. ")")
run(4500)
check(alive() < 11, "the first bombs land after the reload (" .. alive() .. ")")
-- (the last jet's two at 10.65 s)
run(3500)
check(alive() == 0, "all landed (" .. alive() .. ")")
check(inflight() == 0, "none left in the air")
run(1500)
check(said("F22Off") and S.Phase("f22") == "ON_STATION", "its off-target call comes again, one strike left")
-- the last strike, then a reload while it is under way
for i = 1, 11 do zombie(100.5 + (i - 6) * 5, 150.5) end
run(1000)   -- (the combat clock skips the reload's first tick: the strike's 13.0 s end a little later)
SAID = {}
mark(100, 150)
check(S.Ammo("raid") == 0 and said("F22RollIn"), "the last strike (" .. table.concat(SAID, ",") .. "; ammo "
    .. S.Ammo("raid") .. ", running " .. tostring(S.F22Running()) .. ", aiming " .. tostring(S.IsAiming()) .. ")")
run(2000)
gameStart()
check(S.Phase("f22") == "REARM", "none left: home at the reload (" .. tostring(S.Phase("f22")) .. ")")
check(inflight() == 20, "its bombs still in the save (" .. inflight() .. ")")
run(10000)
check(alive() == 0, "they land all the same (" .. alive() .. ")")
done("reload")
