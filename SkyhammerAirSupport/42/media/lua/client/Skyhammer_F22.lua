-- Skyhammer Air Support - the F-22 flight strike (a flight of ten, one jet after another)
-- (2026-11-23, the user: "about ten F-22s sweep over fast in formation and bomb", the feel of a
-- carpet of bombs walking along a line behind a fast flight; as many bombs as the B-2's strike,
-- the blasts staggered, the sound a few layers only. Later that day, the user: not all ten at
-- once, one at a time, each bombing as it goes over: the flight comes in trail, F.gapS apart)
--
-- One mark on the terminal (map or eyes-on) and the flight bombs a line through it: F.len tiles
-- long, F.width wide, its direction the flight lead's (the one with the most infected under it,
-- never one that passes within S.F22Safe() of the player, flown away from the player), as the A-10
-- picks its gun run. Each strike spends one of the sortie's ("raid", Mod Option f22Raids). The
-- bombs go into the air the moment the point is marked (guided bombs, released from far out) and
-- each is kept in the save until it lands (Skyhammer_Ops launch / land), so a reload or a recall
-- never loses one. A strike under way takes no new mark. The flight goes home when its strikes
-- are spent, or when its time is up.
--
-- One strike, e seconds after the mark (Raptor.java draws the ten jets on the same clock, and
-- Skyhammer_Shadow their shadows): the flight lead is over the line's start at F.overS, at
-- F.speed tiles a second, and each jet after it F.gapS later. Each drops its share of the bombs
-- on the next stretch of the line: the lead's land at F.impactS, each next jet's F.gapS later,
-- so the carpet walks down the line one jet at a time, each jet with its own roar and sonic boom.
--
-- (2026-11-23, the user: "as wide as the B-2, not a trickle", "literally flatten the area") the
-- strike is a carpet as wide as the B-2's: a strip F.len x F.width, four lanes of bombs (the
-- flight's two GBU-32 JDAMs a jet, 1,000 lb), each bomb a B-2 bomb's blast (B2.bands, size 9).
-- (2026-11-24) The vehicles in it are wrecked farther out than by a B-2 bomb: its own bands
-- (Skyhammer_VehicleDamage BANDS.raid), so the strip's vehicles are wrecked, not just dented.

require "Skyhammer_Core"
require "Skyhammer_Comms"
require "Skyhammer_Ops"
require "Skyhammer_AircraftDiagram"

local S = Skyhammer
local K = S.Kit

local F = {
    len = 70, width = 40,          -- the bombed strip, in tiles (a B-2 carpet is a 30-tile radius)
    lanes = 4,                     -- rows of bombs across it (F22Bombs)
    -- no line passes closer than this to the player (2026-11-23, the user: no need to keep it so
    -- far from the survivor, the player decides; was 36). safe: with "protect the player" on (the
    -- blasts spare the player; the A-10's), 10 my pick; safeFar: with it off, clear of the blasts
    -- (width / 2 + reach). S.F22Safe() gives the one in force.
    safe = 10, safeFar = 36,
    stepDeg = 15,                  -- directions tried through the marked point
    count = 20,                    -- infected within this of the line count for its direction
    overS = 6.0,                   -- the flight lead over the line's start
    -- tiles a second (Raptor.java, Skyhammer_Shadow): Mach 1 at a tile a metre (2026-11-23, the
    -- user: fighters at Mach going over "like CoD"; was 120)
    speed = 340,
    -- one jet after another (2026-11-23, the user: one at a time, each bombing as it passes; then:
    -- less wait between them, 1.0 -> 0.4, my pick): each over the line's start gapS after the one
    -- before
    gapS = 0.4,
    releaseS = 5.2,                -- "bombs away" on the radio
    impactS = 6.9,                 -- the lead's first bomb lands; each next jet's gapS later
    rippleS = 0.15,                -- one jet's own bombs, one after another
    -- each jet going over: its roar (the three recordings in turn, one recording at three speeds:
    -- not one roar ten times), loudest flybyPeakS into the sound (build.js F22_FLYBY_PEAK)
    flybyPeakS = 2.0,
    flybySounds = { "SH_F22_Flyby", "SH_F22_Flyby2", "SH_F22_Flyby3" },
    -- each jet's sonic boom: as it passes nearest the player (the lead kept within boomS seconds,
    -- each next jet gapS later), the view shaking boomShake at the track, nothing boomFar tiles
    -- from it, for boomShakeS (about until the next jet's: the shakes add up, so ten 1.1 s ones
    -- 0.4 s apart would pile up three deep)
    boomS = { 4.5, 7.5 }, boomShake = 0.5, boomFar = 160, boomShakeS = 0.5,
    -- (the last jet's last bomb: impactS + 9 gapS + a ripple or three, 10.65 to 10.95 s)
    offS = 12.0,                   -- "off target" on the radio
    endS = 13.0,                   -- the strike is over (the 3D flight and the shadows are gone)
    bands = { { 4.5, 100 }, { 9.0, 95 }, { 14.0, 70 } },   -- a B-2 bomb's (Skyhammer_Ops B2.bands)
    size = 9,                      -- the blasts as drawn (a B-2 bomb's)
    noiseBeyond = 50,
    -- the flight in trail: tiles behind the lead (gapS x speed each: 0.4 s apart), to its right,
    -- and up. Each jet over its own bombs: at the default twenty, the 1st, 3rd, ... jet's two
    -- fall on the line's one side (lanes 1 and 2, 10 tiles out on average), the 2nd, 4th, ...
    -- jet's on the other (F22Bombs)
    jets = {
        { 0, -10, 0 }, { 136, 10, 2 }, { 272, -10, 4 }, { 408, 10, 0 }, { 544, -10, 2 },
        { 680, 10, 4 }, { 816, -10, 0 }, { 952, 10, 2 }, { 1088, -10, 4 }, { 1224, 10, 0 },
    },
}
S.F22 = F                          -- (Skyhammer_Shadow and the tests read the numbers)
function S.F22Safe()
    if S.opt("protectPlayer") == false then return F.safeFar end
    return F.safe
end

-- ---------------------------------------------------------------- the line
local segDist = S.A10SegDist
if not segDist then
    segDist = function(px, py, ax, ay, bx, by)
        local vx, vy = bx - ax, by - ay
        local l2 = vx * vx + vy * vy
        local t = l2 > 0 and ((px - ax) * vx + (py - ay) * vy) / l2 or 0
        t = math.max(0, math.min(1, t))
        local dx, dy = ax + vx * t - px, ay + vy * t - py
        return math.sqrt(dx * dx + dy * dy)
    end
end

-- The strike through (tx, ty): of the lines through it (F.len long, centred on it) every
-- F.stepDeg, the one with the most infected within F.count of it, leaving out every line that
-- passes within S.F22Safe() of the player at (px, py). Of lines with as many, the one running closest
-- through them (the least distance summed: F.count is wide, so several directions often take in
-- a whole group), then the one farther from the player. It is flown away from the player.
-- pts: a flat list x1, y1, x2, y2, ... Returns the line's start x, y, its heading and its score,
-- or nil.
function S.F22PickLine(tx, ty, px, py, pts)
    local half = F.len / 2
    local best, bestScore, bestSum, bestClear = nil, -1, 0, -1
    local safe = S.F22Safe()
    for i = 0, math.floor(180 / F.stepDeg) - 1 do
        local h = i * F.stepDeg * math.pi / 180
        local dx, dy = math.cos(h), math.sin(h)
        local ax, ay, bx, by = tx - dx * half, ty - dy * half, tx + dx * half, ty + dy * half
        local clear = segDist(px, py, ax, ay, bx, by)
        if clear >= safe then
            local score, sum = 0, 0
            for j = 1, #pts - 1, 2 do
                local d = segDist(pts[j], pts[j + 1], ax, ay, bx, by)
                if d <= F.count then score, sum = score + 1, sum + d end
            end
            local better = score > bestScore
            if score == bestScore then
                better = sum < bestSum - 1e-6 or (math.abs(sum - bestSum) <= 1e-6 and clear > bestClear)
            end
            if better then
                best, bestScore, bestSum, bestClear = h, score, sum, clear
            end
        end
    end
    if not best then return nil end
    if (tx - px) * math.cos(best) + (ty - py) * math.sin(best) < 0 then best = best + math.pi end
    return tx - math.cos(best) * half, ty - math.sin(best) * half, best, bestScore
end

-- the infected the bombs could reach around (tx, ty) on floor z, as a flat list of positions
local function targets(tx, ty, z)
    local pts = {}
    local cell = getCell(); if not cell then return pts end
    local list = cell:getZombieList()
    local r = F.len / 2 + F.count
    local r2 = r * r
    for i = 0, list:size() - 1 do
        local zb = list:get(i)
        local x, y = zb:getX(), zb:getY()
        local dx, dy = x - tx, y - ty
        if dx * dx + dy * dy <= r2 and math.floor(zb:getZ()) == z and K.alive(zb) and not K.friendly(zb) then
            pts[#pts + 1] = x; pts[#pts + 1] = y
        end
    end
    return pts
end

-- a line: { x, y, z, h } (start, floor, heading); its end
local function lineEnd(l) return l.x + math.cos(l.h) * F.len, l.y + math.sin(l.h) * F.len end
local function pickAt(x, y, z, p)
    local sx, sy, h = S.F22PickLine(x, y, p:getX(), p:getY(), targets(x, y, z))
    if not sx then return nil end
    return { x = sx, y = sy, z = z, h = h }
end

-- Where the n bombs of a strike along l land, when (ms after the mark) and from which jet, in the
-- order they land: F.lanes lanes across the strip (F.width wide), the bombs of each lane evenly
-- along it, each lane a part of a step on from the one before so they fill each other's gaps (a
-- little jitter keeps them from lining up). The jets drop them in the order laid out here, from
-- the line's start on, an even share each (two at the default; at fewer than ten bombs some jets
-- drop none): jet j's land F.gapS after jet j - 1's, its own F.rippleS apart, so the carpet walks
-- down the strip one jet at a time. With twenty: every point of the strip within a B-2 bomb's 95%
-- band of one, its corners within the 70% one.
-- Each: { x, y, ms, jet (1..10) }.
function S.F22Bombs(l, n)
    local out = {}
    local hx, hy = math.cos(l.h), math.sin(l.h)
    local rx, ry = -hy, hx
    local lanes, jets = F.lanes, #F.jets
    local step = F.len / math.ceil(n / lanes)
    local jetOf, nth = -1, 0
    for k = 0, n - 1 do
        local lane, row = k % lanes, math.floor(k / lanes)
        local along = step * (row + (lane + 0.5) / lanes) + (S.frac() - 0.5) * step * 0.3
        along = math.max(0, math.min(F.len, along))
        local side = ((lane + 0.5) / lanes - 0.5) * F.width + (S.frac() - 0.5) * F.width / lanes * 0.3
        local jet = math.floor(k * jets / n)
        if jet == jetOf then nth = nth + 1 else jetOf, nth = jet, 0 end
        out[k + 1] = { x = l.x + hx * along + rx * side, y = l.y + hy * along + ry * side,
            ms = (F.impactS + jet * F.gapS + nth * F.rippleS) * 1000, jet = jet + 1 }
    end
    table.sort(out, function(a, b) return a.ms < b.ms end)
    return out
end

-- ---------------------------------------------------------------- the sortie's record
-- In the save, for this sortie only (a new call or a release starts a fresh one):
--   line      the last strike's line       startMs   when it was marked (combat clock)
--   raids     strikes flown                lastMs    its last bomb down, ms after startMs
local function rec()
    local d = S.Store()
    local sortie = S.Sortie("f22")
    if type(d.f22) ~= "table" or d.f22.sortie ~= sortie then d.f22 = { sortie = sortie, raids = 0 } end
    return d.f22
end
local function running(r, now)
    return tonumber(r.startMs) ~= nil and now < r.startMs + F.endS * 1000
end
function S.F22Running() return running(rec(), S.combatMs()) end
-- the line of the strike under way, until its last bomb is down, for the sensor map:
-- { ax, ay, bx, by, width, edge } (the line, the strip bombed round it and a blast's reach past
-- that, in tiles) or nil
function S.F22Track()
    if S.Phase("f22") ~= "ON_STATION" then return nil end
    local r = rec()
    local l = r.line
    if type(l) ~= "table" or not tonumber(r.startMs) then return nil end
    -- (a record saved before lastMs: the last jet's pair at the default)
    local last = tonumber(r.lastMs) or (F.impactS + (#F.jets - 1) * F.gapS + F.rippleS) * 1000
    if S.combatMs() >= r.startMs + last then return nil end
    local ex, ey = lineEnd(l)
    return { l.x, l.y, ex, ey, F.width, F.bands[#F.bands][1] }
end

-- ---------------------------------------------------------------- one bomb
-- (Skyhammer_Ops lands it from the save: a reload in between still brings it down on time)
-- loud / light: whether this one carries the blast sound / a real light (every one of them)
S.RegisterImpact("raid", function(f)
    if f.loud then K.soundAt(K.square(f.x, f.y, f.z), "SH_Bomb_Impact", 550) end
    K.boom(f.x, f.y, f.z, F.size, not f.light, S.FX_VIS and S.FX_VIS.bomb, not f.loud, true)
    K.shake(f.x, f.y, "bomb")
    -- (through the roofs in single player, as the B-2's: on a server its "indoor hits" decides)
    K.blast(f.x, f.y, f.z, F.bands, 4, "raid", not K.online())
    K.scorch(f.x, f.y, f.z, 2.5, 4.5)   -- (the B-2's)
    K.wreck(f.x, f.y, f.z, "raid")
end)

-- ---------------------------------------------------------------- one strike
-- the radio after the strike, and home after the last one (a job of this sortie only)
local function offTarget(delayMs, last)
    K.after(delayMs, function()
        if last then
            S.Say("F22Winchester", nil, { craft = "f22" })
            S.Release("f22")
        else
            S.Say("F22Off", nil, { craft = "f22" })
        end
    end, "f22")
end

local function startStrike(l)
    if not S.Spend("raid", 1) then return false end
    local r = rec()
    local now = S.combatMs()
    r.line, r.startMs = l, now
    r.raids = (r.raids or 0) + 1
    local last = S.Ammo("raid") <= 0
    -- (a mark sent late in the time on station still gets the strike it paid for)
    S.KeepOnStation("f22", F.endS + 5)
    -- the 3D flight and the shadows fly it (Skyhammer_AircraftVisual, Skyhammer_Shadow)
    S.Store().f22VisualRun = { x = l.x, y = l.y, z = l.z, heading = l.h, len = F.len, startedMs = now,
        sortie = S.Sortie("f22"), raid = r.raids }
    local ex, ey = lineEnd(l)
    local n = math.floor(S.opt("f22Bombs"))
    S.log(string.format("flight strike %d: %d,%d -> %d,%d, %d bombs", r.raids, math.floor(l.x), math.floor(l.y),
        math.floor(ex), math.floor(ey), n))
    local reach = F.width / 2 + F.bands[#F.bands][1]
    K.pvpWarn((l.x + ex) / 2, (l.y + ey) / 2, l.z, F.len / 2 + reach)
    -- the line on the ground, each part of it until the bombs walking down the line reach it (the
    -- jet bombing that stretch: one every F.gapS), on the combat clock as the bombs
    for k = 0, 12 do
        local t = k / 12
        local jet = math.min(#F.jets - 1, math.floor(t * #F.jets))
        K.fx(l.x + (ex - l.x) * t, l.y + (ey - l.y) * t, l.z,
            { tex = "SH_Mark", tiles = k == 12 and 0.9 or 0.5, h = 0.15, life = (F.impactS + jet * F.gapS) * 1000,
              alpha = 0.85, combat = true })
    end
    -- the bombs: into the air now, each in the save until it lands. Each carries the blast sound,
    -- a light and the full smoke (2026-11-23, the user: each jet's two bombs; the second of each
    -- jet's went off quiet, dark and thin before, so a jet looked to drop one); the first, the
    -- middle and the last are heard falling.
    local bombs = S.F22Bombs(l, n)
    r.lastMs = bombs[#bombs] and bombs[#bombs].ms or nil
    for i, b in ipairs(bombs) do
        if i == 1 or i == math.floor(n / 2) + 1 or i == n then
            K.after(math.max(0, b.ms - K.WHISTLE_LEAD_MS), function()
                K.soundAt(K.square(b.x, b.y, l.z), "SH_Incoming", 260)
            end)
        end
        K.launch("raid", b.x, b.y, l.z, b.ms, true, true)
    end
    K.after(F.impactS * 1000, function() K.attract((l.x + ex) / 2, (l.y + ey) / 2, l.z, F.len / 2 + F.noiseBeyond) end)
    -- each jet going over (2026-11-23, the user: fighters at Mach going over "like CoD"; then one
    -- at a time): its roar and its sonic boom from the point of its track nearest this player, as
    -- it passes there (the line is flown away from the player, so the jets come in over them; the
    -- lead kept within F.boomS, each next jet F.gapS later). The view shakes with each boom, less
    -- the farther the track (Mod Options "impact shake" scales it, 0 turns it off).
    local co, si = math.cos(l.h), math.sin(l.h)
    local me = getSpecificPlayer(0)
    local along, side = F.len / 2, F.boomFar          -- (no player: the line's middle, no shake)
    if me then
        local dx, dy = me:getX() - l.x, me:getY() - l.y
        along, side = dx * co + dy * si, math.abs(dy * co - dx * si)
    end
    along = math.max((F.boomS[1] - F.overS) * F.speed, math.min((F.boomS[2] - F.overS) * F.speed, along))
    local passS = F.overS + along / F.speed
    local nx, ny = l.x + co * along, l.y + si * along
    local amp = F.boomShake * (tonumber(S.opt("impactShake")) or 1) * math.max(0, 1 - side / F.boomFar)
    for j = 1, #F.jets do
        local at = passS + (j - 1) * F.gapS
        local roar = F.flybySounds[(j - 1) % #F.flybySounds + 1]
        K.after(math.max(0, at - F.flybyPeakS) * 1000, function()
            local p = getSpecificPlayer(0)
            K.soundAt(K.square(nx, ny, l.z) or (p and p:getCurrentSquare()), roar, 600)
        end)
        K.after(at * 1000, function()
            local p = getSpecificPlayer(0)
            K.soundAt(K.square(nx, ny, l.z) or (p and p:getCurrentSquare()), "SH_F22_Boom", 600)
            local b = SkyhammerAircraft
            if b and b.rumble and amp >= 0.03 then pcall(b.rumble, 0, amp, F.boomShakeS) end
        end)
    end
    S.Say("F22RollIn", nil, { craft = "f22", priority = true })
    K.after(F.releaseS * 1000, function() S.Say("F22Release", nil, { craft = "f22", priority = true }) end, "f22")
    offTarget(F.offS * 1000, last)
    return true
end

-- ---------------------------------------------------------------- the mark
-- the line under the pointer, worked out again at most every PREVIEW_MS or when the point moves
local PREVIEW_MS = 250
local cache = { at = -PREVIEW_MS }
local function preview(x, y, z)
    local p = getSpecificPlayer(0); if not p then return nil end
    local fx, fy, fz = math.floor(x), math.floor(y), math.floor(z or 0)
    local now = S.now()
    if cache.x ~= fx or cache.y ~= fy or cache.z ~= fz or now - cache.at >= PREVIEW_MS then
        cache.x, cache.y, cache.z, cache.at = fx, fy, fz, now
        cache.line = pickAt(fx + 0.5, fy + 0.5, fz, p)
    end
    local l = cache.line
    if not l then return nil end
    local ex, ey = lineEnd(l)
    return l.x, l.y, ex, ey
end

S.RegisterAim("raid", {
    craft = "f22",
    ready = function()
        if S.Phase("f22") ~= "ON_STATION" then return false, "NotReady" end
        -- (none left, or a strike under way: the flight takes the next mark once it is over)
        if S.Ammo("raid") <= 0 or S.F22Running() then return false, "Busy" end
        return true
    end,
    prompt = "F22Mark",
    commit = function(sq)
        local p = getSpecificPlayer(0); if not p then return false end
        if S.Phase("f22") ~= "ON_STATION" or S.Ammo("raid") <= 0 then S.Say("NotReady"); return true end
        if S.F22Running() then S.Say("Busy"); return true end
        local l = pickAt(sq:getX() + 0.5, sq:getY() + 0.5, sq:getZ(), p)
        if not l then S.Say("F22DangerClose", nil, { priority = true }); return false end
        cache.at = -PREVIEW_MS
        startStrike(l)
        return true
    end,
    preview = preview,
    -- (2026-11-23, the user: show the area on the map, not the line alone) the strip round the
    -- line and a blast's reach past it
    width = F.width, edge = F.bands[#F.bands][1],
    spread = F.len / 2,
    -- (the map's outer ring: out to the strip's far corners and a blast's reach past them)
    danger = math.sqrt((F.len / 2 + F.bands[#F.bands][1]) ^ 2 + (F.width / 2 + F.bands[#F.bands][1]) ^ 2) - F.len / 2,
    fitMap = true,
    tint = { 255 / 255, 125 / 255, 200 / 255 },
    icon = "SH_Wpn_b2",
    label = "IGUI_SH_MapMarkF22",
    prefix = "IGUI_SH_Pre_F22",
})

-- ---------------------------------------------------------------- the terminal
-- (an aircraft of the main mod, its tab drawn from these as the A-10's: Skyhammer_Terminal,
-- Skyhammer_Ops, Skyhammer_Feed)
S.Supports.f22 = {
    key = "f22",
    icon = "SH_Icon_F22",
    callLines = { "F22Call", "F22CallAck" },
    recallLines = { "F22Rtb", "F22RtbAck" },
    arriveLines = { "F22OnStation" },
    timeoutLines = { "F22Bingo" },
    ammoRows = { { "raid", "IGUI_SH_Ammo_raid" } },
    markKind = function() return "raid" end,
    -- (the terminal calls these every frame without a pcall: a failure here must never stop it)
    phaseText = function(phase)
        local ok, text = pcall(function()
            if phase == "ON_STATION" and S.F22Running() then return getText("IGUI_SH_Phase_F22Run") end
            return nil
        end)
        return ok and text or nil
    end,
    hint = function(phase)
        local ok, text = pcall(function()
            if phase ~= "ON_STATION" or S.IsAiming("raid") then return nil end
            if S.F22Running() then
                return getText(S.Ammo("raid") > 0 and "IGUI_SH_Hint_F22Next" or "IGUI_SH_Hint_F22Last")
            end
            return getText("IGUI_SH_Hint_F22Mark")
        end)
        return ok and text or nil
    end,
    mapTitle = "IGUI_SH_MapTitleF22",
    sensor = function() return true end,
}
-- the terminal's picture (source/terminal_art/make_f22_art.py: the CC-BY model rendered as the
-- others are), and the line schematic in case it does not load: an F-22 seen from its left side
SkyhammerTerminalArt.Register("f22", "media/ui/SH_Art_F22.png")
SkyhammerAircraftDiagram.Register("f22", {
    { 2,22, 10,19, 22,17, 30,15, 38,15, 46,16, 74,17, 82,15, 90,15, 96,19, 92,21, 70,23, 40,24, 18,24, 2,22 },
    { 22,17, 28,13, 36,12, 42,15 },
    { 74,17, 80,6, 86,6, 86,16 },
    { 50,21, 78,21, 84,24, 56,24, 50,21 },
    { 30,23, 48,23, 50,26, 32,26, 30,23 },
})

-- ---------------------------------------------------------------- hooks into Skyhammer_Ops
table.insert(S.Hooks.released, function(craft)
    if craft == "f22" then cache.at = -PREVIEW_MS end
end)
-- A reload loses the strike's scheduled radio (the bombs themselves are in the save): its "off
-- target" is due again at its time, and a flight with nothing left to drop goes home.
table.insert(S.Hooks.gameStart, function()
    cache = { at = -PREVIEW_MS }
    if S.Phase("f22") ~= "ON_STATION" then return end
    local r, now = rec(), S.combatMs()
    local last = S.Ammo("raid") <= 0
    local start = tonumber(r.startMs)
    if start and now < start + F.offS * 1000 then
        offTarget(start + F.offS * 1000 - now, last)
    elseif last then
        S.Release("f22")
    end
end)
