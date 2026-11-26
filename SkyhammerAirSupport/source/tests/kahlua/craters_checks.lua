-- Checks for Skyhammer_Craters.lua: blasts fell trees (2026-11-25, Workshop request; the user: "do it").
-- Trees within `core` tiles of a blast fall the game's own way (IsoTree:toppleTree: logs, branches, stump), under
-- their own option; burning stays the craters option. ASCII only.
local fails = 0
local function check(name, ok)
    if ok then say("ok   " .. name) else say("FAIL " .. name); fails = fails + 1 end
end
local C = SkyhammerCraters

-- 1. felling only (craters off, trees on): the trees in the core fall, nothing is burnt
local a = makeSquare(10, 10, 0)
local t1 = addTree(a)
local g1 = addGrass(a)
local b = makeSquare(13, 10, 0)            -- 3 tiles out: in the ragged edge, past the core
local t2 = addTree(b)
C.add(10.5, 10.5, 0, 1.0, 3.5, false, true)
runTicks()
check("felling: the tree in the core fell (the game's toppleTree)", t1.toppled == 1 and not has(a, t1) and a.logs == 2)
check("felling: the tree past the core stands", t2.toppled == 0 and has(b, t2))
check("felling only: the ground is not burnt", a.floor.spr.name ~= "floors_burnt_01_0" and has(a, g1))

-- 2. burning only (the old call, five arguments): burnt as before, the tree stands
C.reset()
local c = makeSquare(20, 20, 0)
local t3 = addTree(c)
addGrass(c)
C.add(20.5, 20.5, 0, 1.0, 2.2)
runTicks()
check("old call: the ground burns as before", c.floor.spr.name == "floors_burnt_01_0")
check("old call: no tree falls", t3.toppled == 0 and has(c, t3))
C.reset()
local c2 = makeSquare(25, 20, 0)
local t3b = addTree(c2)
C.add(25.5, 20.5, 0, 1.0, 2.2, true, false)
runTicks()
check("craters on, trees off: the tree stands", t3b.toppled == 0 and c2.floor.spr.name == "floors_burnt_01_0")

-- 3. both: burnt and felled; a stump left by a big tree is not felled again
C.reset()
local d = makeSquare(30, 30, 0)
local t4 = addTree(d, { stump = true })
C.add(30.5, 30.5, 0, 1.0, 2.2, true, true)
runTicks()
check("both: burnt and felled", d.floor.spr.name == "floors_burnt_01_0" and t4.toppled == 1)

-- 4. the same square from two blasts: one job, the flags merged
C.reset()
local e = makeSquare(40, 40, 0)
local t5 = addTree(e)
C.add(40.5, 40.5, 0, 1.0, 2.2, true, false)
C.add(40.5, 40.5, 0, 1.0, 2.2, false, true)
runTicks()
check("two blasts on one square: burnt and felled once", e.floor.spr.name == "floors_burnt_01_0" and t5.toppled == 1)

-- 5. not outdoors, or not loaded: nothing happens, nothing fails
C.reset()
local f = makeSquare(50, 50, 0, { room = {} })
local t6 = addTree(f)
C.add(50.5, 50.5, 0, 1.0, 2.2, false, true)
C.add(70.5, 70.5, 0, 1.0, 2.2, true, true)   -- no squares loaded there
runTicks()
check("a square in a room: its tree stands", t6.toppled == 0)

-- 6. a tree that fails to fall is logged, the rest of the queue goes on
C.reset()
LOG = {}
local h = makeSquare(60, 60, 0)
addTree(h, { fails = true })
local h2 = makeSquare(61, 60, 0)
local t7 = addTree(h2)
C.add(60.5, 60.5, 0, 1.6, 2.2, false, true)
runTicks()
local logged = false
for _, l in ipairs(LOG) do if string.find(l, "crater failed", 1, true) then logged = true end end
check("a failing tree is logged", logged)
check("the next square is still felled", t7.toppled == 1)

-- 7. neither burning nor felling: nothing queued
C.reset()
local k = makeSquare(80, 80, 0)
local t8 = addTree(k)
addGrass(k)
C.add(80.5, 80.5, 0, 1.0, 2.2, false, false)
runTicks()
check("nothing asked: nothing changes", t8.toppled == 0 and k.floor.spr.name ~= "floors_burnt_01_0")

-- 8. the console line counts the trees
C.reset()
LOG = {}
local m = makeSquare(90, 90, 0)
addTree(m)
C.add(90.5, 90.5, 0, 1.0, 2.2, false, true)
runTicks()
local counted = false
for _, l in ipairs(LOG) do if string.find(l, "1 trees felled", 1, true) then counted = true end end
check("the console line counts the trees felled", counted)

-- 9. a wide core (an add-on's orbital strike, core 20): trees fall within FELL_MAX tiles only, and with burning off
-- only that circle is looked at
C.reset()
local n1 = makeSquare(105, 100, 0)       -- 5 tiles out
local tn1 = addTree(n1)
local n2 = makeSquare(108, 100, 0)       -- 8 tiles out
local tn2 = addTree(n2)
C.add(100.5, 100.5, 0, 20, 30, false, true)
runTicks(2000)
check("wide core: a tree 5 tiles out falls", tn1.toppled == 1)
check("wide core: a tree 8 tiles out stands (FELL_MAX)", tn2.toppled == 0)
check("FELL_MAX is 6", C.FELL_MAX == 6)

say(fails .. " failed")
if fails > 0 then error(fails .. " check(s) failed") end
