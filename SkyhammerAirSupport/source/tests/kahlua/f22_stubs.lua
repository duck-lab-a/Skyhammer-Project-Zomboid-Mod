-- Stubs for the F-22 flight strike checks on the game's Kahlua (run_f22_test.cmd): the same
-- permissive single-player world as the lupa sims (sim_a10.py), with stub infected, a stub
-- player at (PX, PY) and a clock driven by run(ms). Loaded before the REAL Skyhammer_PvP, Core,
-- Killstreak, Comms, Ops, Apache, A10 and F22; f22_after.lua then sets up the helpers.
local dummy
dummy = setmetatable({}, { __index = function() return dummy end, __call = function() return dummy end })
setmetatable(_G, { __index = function(_, k) return dummy end })
OUT = print
print = function() end
Skyhammer, SkyhammerPvP = {}, {}
require = function() end
Keyboard = setmetatable({}, { __index = function() return 0 end })
HANDLERS = {}
Events = setmetatable({}, { __index = function(_, name)
    return { Add = function(fn) HANDLERS[name] = HANDLERS[name] or {}; table.insert(HANDLERS[name], fn) end,
             Remove = function() end } end })
function fire(name, a, b, c) for _, fn in ipairs(HANDLERS[name] or {}) do fn(a, b, c) end end
getText = function(k) return k end
getActivatedMods = function() return { contains = function() return false end } end
isClient = function() return false end
isServer = function() return false end
CLOCK = 0
getTimestampMs = function() return CLOCK end
getGameTime = function() return { getWorldAgeHours = function() return CLOCK / 3600000 end, getMinutesPerDay = function() return 60 end } end
MD = {}
ModData = { getOrCreate = function() return MD end }
ROLL = function(n) return 0 end
ZombRand = function(n) return ROLL(n) end
SandboxVars = { Skyhammer = {} }

-- the infected: tables with the methods the mod calls
ZOMBIES = {}
local Z = {}
Z.__index = Z
function Z:getX() return self.x end
function Z:getY() return self.y end
function Z:getZ() return 0 end
function Z:isDead() return self.dead end
function Z:getHealth() return self.dead and 0 or 1 end
function Z:getModData() return {} end
function Z:Kill() self.dead = true end
function Z:getCurrentSquare() return square(math.floor(self.x), math.floor(self.y), 0) end
function zombie(x, y) local z = setmetatable({ isZombie = true, x = x, y = y, dead = false }, Z); ZOMBIES[#ZOMBIES + 1] = z; return z end
function alive() local n = 0; for _, z in ipairs(ZOMBIES) do if not z.dead then n = n + 1 end end; return n end
instanceof = function(o, cls) return type(o) == "table" and o.isZombie == true and cls == "IsoZombie" end

GRID = 0
function square(x, y, z)
    GRID = GRID + 1
    return { getX = function() return x end, getY = function() return y end, getZ = function() return z end,
             getRoom = function() return nil end,
             getMovingObjects = function()
                 local here = {}
                 for _, zb in ipairs(ZOMBIES) do
                     if math.floor(zb.x) == x and math.floor(zb.y) == y then here[#here + 1] = zb end
                 end
                 return { size = function() return #here end, get = function(_, i) return here[i + 1] end }
             end }
end
CELL = {
    getGridSquare = function(_, x, y, z) return square(x, y, z) end,
    addLamppost = function() return {} end,
    removeLamppost = function() end,
    getZombieList = function() return { size = function() return #ZOMBIES end, get = function(_, i) return ZOMBIES[i + 1] end } end,
}
getCell = function() return CELL end
PX, PY = 100, 100
ME = setmetatable({ getX = function() return PX end, getY = function() return PY end, getZ = function() return 0 end,
       getCurrentSquare = function() return square(PX, PY, 0) end, isDead = function() return false end,
       getModData = function() return {} end, getZombieKills = function() return 0 end,
       getHealth = function() return 1 end, getPlayerNum = function() return 0 end },
       { __index = function() return function() return dummy end end })
getSpecificPlayer = function() return ME end
getPlayer = getSpecificPlayer
OPTVALS = {}
local PAGE = setmetatable({
    getOption = function(_, id) return { getValue = function() return OPTVALS[id] end } end,
}, { __index = function() return function() return dummy end end })
PZAPI = { ModOptions = { create = function() return PAGE end } }
