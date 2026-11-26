-- The tables the terminal, killstreak, PvP and the server read; the pick; the bomb pattern
local P = SkyhammerPvP
local order = table.concat(S.ORDER, ",")
check(order == "apache,a10,ac130,f22,b2", "tab order by price (" .. order .. ")")
check(S.PointCost("f22") == 200, "killstreak price (" .. tostring(S.PointCost("f22")) .. ")")
check(S.CRAFT.raid == "f22" and S.CRAFT.f22 == "f22", "weapon to craft")
check(P.KIND_CRAFT and P.KIND_CRAFT.raid == "f22", "PvP kind to craft")
check(P.SORTIES and P.SORTIES.f22 and P.SORTIES.f22.rounds.raid == 20, "PvP rounds of one strike at the default")
check(P.FIRE and P.FIRE.raid and P.FIRE.raid.burst >= 20, "the server takes a whole strike at once")
check(P.Locked("f22Raids") and P.Locked("f22Bombs") and P.Locked("f22InboundSec") and P.Locked("f22RearmMin"),
    "PvP holds the F-22 at its defaults")
check(P.Reach("raid") == 14, "PvP reach: a B-2 bomb's (" .. tostring(P.Reach("raid")) .. ")")
check(S.F22.safeFar > S.F22.width / 2 + S.F22.bands[#S.F22.bands][1], "protection off: a line kept clear of the player is clear of the blasts")
check(S.F22.safe == 10 and S.F22Safe() == 10, "protection on: 10 tiles (" .. tostring(S.F22Safe()) .. ")")
check(S.F22.bands[#S.F22.bands][1] == 14 and S.F22.size == 9 and S.F22.width == 40 and S.F22.len == 70, "a B-2 sized carpet of B-2 bombs")
-- the pick
local function pick(tx, ty, pts) return S.F22PickLine(tx, ty, 100, 100, pts or {}) end
for _, t in ipairs({ { 145, 100 }, { 100, 146 }, { 134, 132 }, { 66, 66 } }) do
    local sx, sy, h = pick(t[1], t[2])
    check(sx ~= nil, "a line through " .. t[1] .. "," .. t[2])
    if sx then
        local ex, ey = sx + math.cos(h) * 70, sy + math.sin(h) * 70
        check(S.A10SegDist(100, 100, sx, sy, ex, ey) >= 10 - 1e-6, "  keeps 10 tiles from the player")
        check(near((sx + ex) / 2, t[1]) and near((sy + ey) / 2, t[2]), "  centred on the mark")
        check((t[1] - 100) * math.cos(h) + (t[2] - 100) * math.sin(h) >= -1e-6, "  flown away from the player")
    end
end
check(pick(105, 100) == nil, "5 tiles out: no line")
check(pick(112, 100) ~= nil, "12 tiles out: a line (protection on)")
OPTVALS.protectPlayer = false
check(S.F22Safe() == 36, "protection off: 36 tiles (" .. tostring(S.F22Safe()) .. ")")
check(pick(130, 100) == nil, "protection off, 30 tiles out: no safe line (the carpet would reach the player)")
do
    local sx, sy, h = pick(145, 100)
    check(sx ~= nil and S.A10SegDist(100, 100, sx, sy, sx + math.cos(h) * 70, sy + math.sin(h) * 70) >= 36 - 1e-6,
        "protection off, 45 tiles out: a line 36 tiles clear")
end
OPTVALS.protectPlayer = nil
-- a diagonal column: the line follows it
local pts = {}
for d = -24, 24, 4 do pts[#pts + 1] = 160 + d * 0.7071; pts[#pts + 1] = 100 + d * 0.7071 end
local _, _, h, score = S.F22PickLine(160, 100, 100, 100, pts)
check(deg(h) == 45, "along the diagonal column (" .. deg(h) .. ")")
check(score == 13, "all 13 counted (" .. tostring(score) .. ")")
-- the bombs
ROLL = function(n) return math.floor(n / 2) end
local l = { x = 200, y = 200, z = 0, h = 0 }
local bombs = S.F22Bombs(l, 20)
check(#bombs == 20, "twenty bombs")
local left, right, sorted, onStrip, inTime = 0, 0, true, true, true
for i, b in ipairs(bombs) do
    if not (b.x >= 200 - 1e-6 and b.x <= 270 + 1e-6 and math.abs(b.y - 200) <= 20 + 1e-6) then onStrip = false end
    if not (b.ms >= 6900 - 1e-6 and b.ms <= 10650 + 1e-6) then inTime = false end
    if i > 1 and b.ms < bombs[i - 1].ms then sorted = false end
    if b.y < 200 then left = left + 1 else right = right + 1 end
end
check(onStrip, "every bomb on the strip")
check(inTime, "every bomb lands between 6.9 and 10.65 s")
check(sorted, "in the order they land")
check(left == 10 and right == 10, "both sides of the line (" .. left .. "/" .. right .. ")")
-- one jet after another (2026-11-23, the user: one at a time, each bombing as it passes): two a
-- jet, the jet's own two F.rippleS apart, each jet's F.gapS after the one before, each jet's two
-- under it (its place across the line) and the next stretch of the line after the last jet's
local F = S.F22
local perJet, timed, under, walks, lastAlong = {}, true, true, true, -1
for j = 1, #F.jets do perJet[j] = {} end
for _, b in ipairs(bombs) do local t = perJet[b.jet]; if t then t[#t + 1] = b end end
for j, t in ipairs(perJet) do
    if #t ~= 2 then timed = false else
        local at = (F.impactS + (j - 1) * F.gapS) * 1000
        if not (near(t[1].ms, at, 1e-3) and near(t[2].ms, at + F.rippleS * 1000, 1e-3)) then timed = false end
        if not near((t[1].y + t[2].y) / 2 - 200, F.jets[j][2], 1e-6) then under = false end
        local mid = (t[1].x + t[2].x) / 2
        if mid <= lastAlong then walks = false end
        lastAlong = mid
    end
end
check(#F.jets == 10, "a flight of ten (the radio says ten)")
check(timed, "two bombs a jet, a jet every 0.4 s, a jet's own two 0.15 s apart")
check(under, "each jet flies over its own two (its place across the line)")
check(walks, "the carpet walks down the line jet by jet")
local trail = true
for j, p in ipairs(F.jets) do if not near(p[1], (j - 1) * F.gapS * F.speed) then trail = false end end
check(trail, "the jets in trail 0.4 s apart (tiles behind the lead: gapS x speed)")
check(near(F.gapS, 0.4) and F.offS == 12.0 and F.endS == 13.0, "0.4 s apart, off target at 12 s, over at 13 s")
check(near(bombs[#bombs].ms, 10650, 1e-3) and bombs[#bombs].ms < F.offS * 1000, "the last down at 10.65 s, before off target")
-- other bomb counts from the option (6 to 40): all ten jets still pass, the last bombs before off target
for _, m in ipairs({ 6, 40 }) do
    local bs, ok = S.F22Bombs(l, m), true
    for _, b in ipairs(bs) do if b.jet < 1 or b.jet > 10 or b.ms >= F.offS * 1000 or b.ms < F.impactS * 1000 - 1e-6 then ok = false end end
    check(#bs == m and ok, m .. " bombs: from jets 1 to 10, all down before off target")
end
local gap = 0
for i = 2, #bombs do gap = math.max(gap, bombs[i].x - bombs[i - 1].x) end
check(gap / 2 < S.F22.bands[1][1], "no gap along the line wider than the sure kill (" .. gap .. ")")
-- the whole strip flattened: every point of it within the 70% band of a bomb, and nearly all
-- within the 95% band (a B-2 bomb's)
local far, in95, pts = 0, 0, 0
for ax = 0, 70, 2 do
    for sy = -20, 20, 2 do
        local best = 1e9
        for _, b in ipairs(bombs) do best = math.min(best, math.sqrt((b.x - 200 - ax) ^ 2 + (b.y - 200 - sy) ^ 2)) end
        pts = pts + 1
        if best <= S.F22.bands[2][1] then in95 = in95 + 1 end
        if best > S.F22.bands[3][1] then far = far + 1 end
    end
end
check(far == 0, "every point of the strip within a blast's reach (" .. far .. " not)")
check(in95 / pts >= 0.95, "95% of the strip in the 95% band (" .. in95 .. "/" .. pts .. ")")
-- sandbox off
SandboxVars.Skyhammer.EnableF22 = false
local tabs = table.concat(S.Tabs(), ",")
check(tabs == "apache,a10,ac130,b2", "sandbox off: no tab (" .. tabs .. ")")
check(S.Call("f22") == false, "sandbox off: cannot be called")
done("tables")
