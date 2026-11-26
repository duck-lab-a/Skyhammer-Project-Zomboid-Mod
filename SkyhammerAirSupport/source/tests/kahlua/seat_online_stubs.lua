-- Stubs for the AC-130 gunner seat online (Vanilla Edition client) on the game's Kahlua.
-- Anything not stubbed reads as a do-nothing object, as in the lupa sims.
local dummy
dummy = setmetatable({}, { __index = function() return dummy end, __call = function() return dummy end })
setmetatable(_G, { __index = function(_, k) return dummy end })
Skyhammer, SkyhammerPvP = {}, {} -- (a nil global would read as the do-nothing object)
LOG = {}
require = function() end
Keyboard = setmetatable({}, { __index = function() return 0 end })
HANDLERS = {}
Events = setmetatable({}, { __index = function(t, name)
    local e = { Add = function(fn) HANDLERS[name] = HANDLERS[name] or {}; table.insert(HANDLERS[name], fn) end,
                Remove = function() end }
    rawset(t, name, e)
    return e
end })
getText = function(k) return k end
EDITION = "SkyhammerAirSupportVanilla"
getActivatedMods = function() return { contains = function(_, id) return id == EDITION end } end
ONLINE = true
isClient = function() return ONLINE end
isServer = function() return false end
CLOCK = 1000000
getTimestampMs = function() return CLOCK end
local rolls = 0
ZombRand = function(n) rolls = rolls + 1; return 0 end
WORLD = {}
ModData = { getOrCreate = function() return WORLD end, request = function() end }
SandboxVars = { Skyhammer = {} }
isGamePaused = function() return false end
instanceof = function(o, cls) return type(o) == "table" and o.cls == cls end
SENT = {}
sendClientCommand = function(p, module, command, args) SENT[#SENT + 1] = { m = module, c = command, a = args } end
function sent(command, field, value)
    local n = 0
    for _, s in ipairs(SENT) do
        if s.c == command and (field == nil or s.a[field] == value) then n = n + 1 end
    end
    return n
end
local function newSquare(x, y, z)
    local sq = { x = x, y = y, z = z }
    function sq:getX() return self.x end
    function sq:getY() return self.y end
    function sq:getZ() return self.z end
    function sq:getFloor() return self.z == 0 and {} or nil end
    function sq:HasSlopedRoof() return false end
    function sq:hasRainBlockingTile() return false end
    function sq:getRoom() return nil end
    function sq:haveRoofFull() return false end
    function sq:getMovingObjects() return { size = function() return 0 end } end
    function sq:getChunk() return nil end
    function sq:splatBlood() end
    return sq
end
local cell = {}
function cell:getGridSquare(x, y, z) return newSquare(x, y, z) end
local none = { size = function() return 0 end, get = function() return nil end }
function cell:getZombieList() return none end
function cell:getObjectList() return none end
getCell = function() return cell end
function newPlayer(name)
    local p = { name = name, md = {}, cls = "IsoPlayer" }
    function p:getModData() return self.md end
    function p:isDead() return false end
    function p:getZombieKills() return 0 end
    function p:getX() return 100 end
    function p:getY() return 100 end
    function p:getZ() return 0 end
    function p:getSquare() return newSquare(100, 100, 0) end
    function p:getCurrentSquare() return newSquare(100, 100, 0) end
    function p:getVehicle() return nil end
    function p:isAsleep() return false end
    function p:getUsername() return self.name end
    return p
end
ME = newPlayer("me")
getPlayer = function() return ME end
getSpecificPlayer = function() return ME end
function tick(ms)
    CLOCK = CLOCK + (ms or 20)
    for _, fn in ipairs(HANDLERS.OnTick or {}) do fn() end
end
