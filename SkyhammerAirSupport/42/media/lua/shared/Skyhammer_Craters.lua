-- Skyhammer Air Support - craters (the "craters" option)
-- The ground where a heavy round or bomb lands is left burnt black and stripped of grass and
-- bushes, the way the game's own fire and shovel leave it. Solid out to `core` tiles, ragged out
-- to `edge`; outdoor squares on the impact floor only, never water, never trees, walls or
-- anything built. It is a real change to the map and is saved with it.
-- Shared: single player burns them on this machine (Skyhammer_Ops), a server burns them for
-- everyone (Skyhammer_Server), each with its own queue.
-- (2026-11-25, a Workshop request; the user: "do it") Trees within `core` tiles of a blast fall, the game's own
-- way (IsoTree:toppleTree: the tree goes and leaves logs, branches and, for a big one, a stump, as an axe
-- does). Their own option ("fellTrees"); the burning stays the "craters" option. The same queue does both.

SkyhammerCraters = SkyhammerCraters or {}
local C = SkyhammerCraters

local BURNT_FLOOR = "floors_burnt_01_0"
-- The squares to burn wait in a queue and are done a few per tick (BUDGET), so a B-2 strike's
-- few hundred squares never land in one frame. The cost is measured: each strike's total and
-- its slowest tick go to the console ("[Skyhammer] craters: ...").
-- The queue is a table with its own head and tail indices: the front is cleared as it is
-- worked, so #queue would not be its end (Lua's length of a table with holes is not).
local BUDGET = 4
local TIME_BUDGET_MS = 2
local queue, head, tail = {}, 1, 0
local pending = {}
local stats = { squares = 0, trees = 0, ms = 0, worstMs = 0, lastWorkMs = 0 }

local function log(msg) print("[Skyhammer] " .. tostring(msg)) end

local function stripVegetation(sq)
    local changed = false
    local objs = sq:getObjects()
    for i = objs:size(), 1, -1 do
        local o = objs:get(i - 1)
        local spr = o and o:getSprite()
        if spr and o ~= sq:getFloor() then
            local props = spr:getProperties()
            local name = spr:getName() or ""
            if props:has(IsoFlagType.canBeRemoved)
                or (props:has(IsoFlagType.vegitation) and o:getType() ~= IsoObjectType.tree)
                or luautils.stringStarts(name, "blends_grassoverlays") then
                sq:transmitRemoveItemFromSquare(o)
                changed = true
            end
        end
    end
    return changed
end

local function burnSquare(sx, sy, z, burnt)
    local cell = getCell()
    local sq = cell and cell:getGridSquare(sx, sy, z)
    if not (sq and sq:getRoom() == nil) then return false end
    local floor = sq:getFloor()
    if not floor or not floor:getSprite() then return false end
    if floor:getSprite():getProperties():has(IsoFlagType.water) then return false end
    local changed = false
    if floor:getSprite():getName() ~= BURNT_FLOOR then
        changed = true
        floor:setSprite(burnt)
        floor:RemoveAttachedAnims()   -- the grass / dirt blend tiles on top
        floor:transmitUpdatedSpriteToClients()
    end
    changed = stripVegetation(sq) or changed
    if changed then sq:RecalcProperties() end
    return changed
end

-- the trees standing on an outdoor square, felled; how many fell
local function fellTrees(sq)
    if sq:getRoom() ~= nil then return 0 end
    local n = 0
    local objs = sq:getObjects()
    for i = objs:size(), 1, -1 do
        local o = objs:get(i - 1)
        if o and instanceof(o, "IsoTree") then
            o:toppleTree()
            n = n + 1
        end
    end
    if n > 0 then sq:RecalcProperties() end
    return n
end

-- a queued square: { x, y, z, key, burn, fell }
local function workSquare(job, burnt)
    local felled = 0
    if job[6] then
        local cell = getCell()
        local sq = cell and cell:getGridSquare(job[1], job[2], job[3])
        if sq then felled = fellTrees(sq) end
    end
    local done = false
    if job[5] and burnt then done = burnSquare(job[1], job[2], job[3], burnt) end
    return done, felled
end

-- trees fall within core, but never farther out than this (an add-on's orbital strike has a 20-tile core:
-- hundreds of trees and thousands of logs at once)
C.FELL_MAX = 6

-- queue the squares of one crater around (cx, cy) on floor z. burn: the crater (default on, as the
-- callers before 2026-11-25 meant); fell: the trees within core (at most FELL_MAX) fall.
function C.add(cx, cy, z, core, edge, burn, fell)
    burn, fell = burn ~= false, fell == true
    if not (burn or fell) then return end
    z = math.floor(z)
    local fellR = math.min(core, C.FELL_MAX)
    local reach = burn and edge or fellR
    for sx = math.floor(cx - reach), math.floor(cx + reach) do
        for sy = math.floor(cy - reach), math.floor(cy + reach) do
            local d = math.sqrt((sx + 0.5 - cx) ^ 2 + (sy + 0.5 - cy) ^ 2)
            local inCore = d <= core and (burn or d <= fellR)
            if inCore or (burn and d <= edge and ZombRand(1000000) / 1000000 < (edge - d) / (edge - core)) then
                local key = sx .. ":" .. sy .. ":" .. z
                local fellHere = fell and d <= fellR
                local job = pending[key]
                if job then
                    job[5] = job[5] or burn
                    job[6] = job[6] or fellHere
                else
                    tail = tail + 1
                    job = { sx, sy, z, key, burn, fellHere }
                    queue[tail] = job
                    pending[key] = job
                end
            end
        end
    end
end

-- burns a few queued squares; called once per tick
function C.tick()
    if head > tail then
        if (stats.squares > 0 or stats.trees > 0) and getTimestampMs() - stats.lastWorkMs > 1500 then
            log(string.format("craters: %d squares burnt, %d trees felled, %.1f ms in total, slowest tick %.1f ms",
                stats.squares, stats.trees, stats.ms, stats.worstMs))
            stats.squares, stats.trees, stats.ms, stats.worstMs = 0, 0, 0, 0
        end
        return
    end
    local burnt = getSprite(BURNT_FLOOR)
    local t0 = getTimestampMs()
    for _ = 1, BUDGET do
        if head > tail or getTimestampMs() - t0 >= TIME_BUDGET_MS then break end
        local job = queue[head]
        queue[head] = nil
        head = head + 1
        pending[job[4]] = nil
        local ok, done, felled = pcall(workSquare, job, burnt)
        if not ok then log("crater failed at " .. job[1] .. "," .. job[2] .. ": " .. tostring(done))
        else
            if done then stats.squares = stats.squares + 1 end
            stats.trees = stats.trees + (felled or 0)
        end
    end
    if head > tail then queue, head, tail = {}, 1, 0 end
    local ms = getTimestampMs() - t0
    stats.ms = stats.ms + ms
    stats.worstMs = math.max(stats.worstMs, ms)
    stats.lastWorkMs = getTimestampMs()
end

function C.reset()
    queue, head, tail, pending = {}, 1, 0, {}
    stats = { squares = 0, trees = 0, ms = 0, worstMs = 0, lastWorkMs = 0 }
end
