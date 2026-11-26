-- Stubs for Skyhammer_Craters.lua on the game's Kahlua (tree felling test, 2026-11-25). Run: run_craters_test.cmd
say = print
LOG = {}
print = function(s) LOG[#LOG + 1] = tostring(s) end
IsoFlagType = { canBeRemoved = "canBeRemoved", vegitation = "vegitation", water = "water" }
IsoObjectType = { tree = "tree", other = "other" }
luautils = { stringStarts = function(s, p) return string.sub(s, 1, #p) == p end }
NOW = 0
getTimestampMs = function() return NOW end
ZombRand = function() return 0 end   -- every ragged edge square is taken
getSprite = function(name) return { name = name } end
instanceof = function(o, cls) return o ~= nil and o.cls == cls end

local function sprite(name, flags)
    local spr = { name = name, flags = flags or {} }
    function spr:getName() return self.name end
    function spr:getProperties()
        local f = self.flags
        return { has = function(_, k) return f[k] == true end }
    end
    return spr
end

local function list(t)
    return { size = function() return #t end, get = function(_, i) return t[i + 1] end }
end

SQUARES = {}
function makeSquare(x, y, z, opts)
    opts = opts or {}
    local sq = { x = x, y = y, z = z, objs = {}, room = opts.room, recalc = 0 }
    local floor = { cls = "IsoObject", spr = sprite(opts.floor or "blends_natural_01_16", opts.water and { water = true } or {}) }
    function floor:getSprite() return self.spr end
    function floor:setSprite(s) self.spr = sprite(s.name) end
    function floor:RemoveAttachedAnims() end
    function floor:transmitUpdatedSpriteToClients() end
    function floor:getType() return IsoObjectType.other end
    sq.floor = floor
    sq.objs[1] = floor
    function sq:getRoom() return self.room end
    function sq:getFloor() return self.floor end
    function sq:getObjects() return list(self.objs) end
    function sq:transmitRemoveItemFromSquare(o)
        for i = #self.objs, 1, -1 do if self.objs[i] == o then table.remove(self.objs, i) end end
    end
    function sq:RecalcProperties() self.recalc = self.recalc + 1 end
    SQUARES[x .. ":" .. y .. ":" .. z] = sq
    return sq
end

-- the game's IsoTree: toppleTree takes it off its square and leaves logs (dropWood) and, for a big one, a stump
function addTree(sq, opts)
    opts = opts or {}
    local tree = { cls = "IsoTree", spr = sprite("e_americanholly_1_3", { vegitation = true }), sq = sq, toppled = 0 }
    function tree:getSprite() return self.spr end
    function tree:getType() return IsoObjectType.tree end
    function tree:toppleTree()
        if opts.fails then error("topple failed") end
        self.toppled = self.toppled + 1
        self.sq:transmitRemoveItemFromSquare(self)
        self.sq.logs = (self.sq.logs or 0) + 2
        if opts.stump then
            local stump = { cls = "IsoObject", spr = sprite("vegetation_trees_stump") }
            function stump:getSprite() return self.spr end
            function stump:getType() return IsoObjectType.other end
            self.sq.objs[#self.sq.objs + 1] = stump
        end
    end
    sq.objs[#sq.objs + 1] = tree
    return tree
end

function addGrass(sq)
    local g = { cls = "IsoObject", spr = sprite("blends_grassoverlays_01_1") }
    function g:getSprite() return self.spr end
    function g:getType() return IsoObjectType.other end
    sq.objs[#sq.objs + 1] = g
    return g
end

function has(sq, o)
    for i = 1, #sq.objs do if sq.objs[i] == o then return true end end
    return false
end

getCell = function()
    return { getGridSquare = function(_, x, y, z) return SQUARES[x .. ":" .. y .. ":" .. z] end }
end

function runTicks(n)
    for _ = 1, n or 400 do
        NOW = NOW + 20
        SkyhammerCraters.tick()
    end
end
