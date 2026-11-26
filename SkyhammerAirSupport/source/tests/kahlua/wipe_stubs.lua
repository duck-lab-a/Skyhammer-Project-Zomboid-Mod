-- Stubs for Skyhammer_Core / Killstreak / Quest on the game's Kahlua (mod data wipe test).
-- Anything not stubbed reads as a do-nothing object, as in the lupa sims.
local dummy
dummy = setmetatable({}, { __index = function() return dummy end, __call = function() return dummy end })
setmetatable(_G, { __index = function(_, k) return dummy end })
Skyhammer, SkyhammerPvP = {}, {}
LOG = {}
require = function() end
Keyboard = setmetatable({}, { __index = function() return 0 end })
Events = setmetatable({}, { __index = function() return { Add = function() end, Remove = function() end } end })
getText = function(k) return k end
getActivatedMods = function() return { contains = function() return false end } end
ONLINE = true
isClient = function() return ONLINE end
isServer = function() return false end
getTimestampMs = function() return 0 end
local rolls = 0
ZombRand = function() rolls = rolls + 1; return rolls end
WORLD = {}
ModData = { getOrCreate = function() return WORLD end }
SandboxVars = { Skyhammer = {} }
isGamePaused = function() return false end
instanceof = function() return false end
function newPlayer(name)
    local p = { name = name, md = {} }
    function p:getModData() return self.md end
    function p:isDead() return false end
    function p:getZombieKills() return 0 end
    return p
end
ME = newPlayer("me")
getPlayer = function() return ME end
getSpecificPlayer = function() return ME end
-- the game's ObjectModDataPacket on the client (42.22): the same table, wiped, then the server's copy
function serverSends(copy)
    local md = ME:getModData()
    local keys = {}
    for k in pairs(md) do keys[#keys + 1] = k end
    for _, k in ipairs(keys) do md[k] = nil end
    for k, v in pairs(copy or {}) do md[k] = v end
end
