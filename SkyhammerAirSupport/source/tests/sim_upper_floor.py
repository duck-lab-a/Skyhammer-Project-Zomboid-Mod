# Sim (2026-10-22, Workshop comment): marks and guns from an upper floor or a helicopter reach the
# ground. Runs the real lookedAtSquare / hasFloor (Ops), canShoot and rocketTarget (Apache) bodies,
# cut out of the files, on stub squares and zombies.   python sim_upper_floor.py (lupa)
import os, re, sys
from lupa import lua51
HERE = os.path.dirname(os.path.abspath(__file__))
C = os.path.join(HERE, "..", "..", "42", "media", "lua", "client")
ops = open(os.path.join(C, "Skyhammer_Ops.lua"), encoding="utf-8").read()
ah = open(os.path.join(C, "Skyhammer_Apache.lua"), encoding="utf-8").read()
def cut(src, start, end_marker="\nend\n"):
    i = src.index(start); j = src.index(end_marker, i) + len(end_marker); return src[i:j]
fails = 0
def check(c, m):
    global fails
    print(("PASS " if c else "FAIL ") + m); fails += 0 if c else 1
L = lua51.LuaRuntime()
L.execute('''
FLOORS = {}   -- "x,y,z" -> true when that square has a floor
function square(x, y, z)
    x, y, z = math.floor(x), math.floor(y), math.floor(z)
    local sq = { x = x, y = y, z = z }
    function sq:getX() return self.x end; function sq:getY() return self.y end; function sq:getZ() return self.z end
    function sq:getFloor() return FLOORS[self.x .. "," .. self.y .. "," .. self.z] and {} or nil end
    return sq
end
VIEW3D = true; MX, MY = 10, 20
S = { Viewpoint3D = function() return VIEW3D end }
Viewpoint = { Mouse = { worldX = function() return MX end, worldY = function() return MY end } }
getMouseX = function() return 0 end; getMouseY = function() return 0 end
screenToIsoX = function(_, mx, my, z) return MX - 3 * z end
screenToIsoY = function(_, mx, my, z) return MY - 3 * z end
function P(z) return { getZ = function() return z end, getX = function() return 0 end, getY = function() return 0 end } end
''')
L.execute(cut(ops, "local function hasFloor(sq)") + cut(ops, "local function lookedAtSquare(p)") + "LAS = lookedAtSquare")
L.execute('FLOORS = { ["10,20,0"] = true }')
check(L.eval("LAS(P(0)):getZ()") == 0, "on the ground: the ground")
check(L.eval("LAS(P(2)):getZ()") == 0, "from the 2nd floor over open ground: the ground (was the air at z 2)")
check(L.eval("LAS(P(5.4)):getZ()") == 0, "from a helicopter: the ground")
L.execute('FLOORS["10,20,1"] = true')
check(L.eval("LAS(P(3)):getZ()") == 1, "over a roof at z 1: the roof")
check(L.eval("LAS(P(-1)):getZ()") == -1, "in a basement: its own floor")
L.execute('VIEW3D = false; FLOORS = { ["4,14,2"] = true, ["10,20,0"] = true }')
check(L.eval("LAS(P(2)):getZ()") == 2, "isometric, pointer on the 2nd-floor floor: that floor")
L.execute('FLOORS = { ["10,20,0"] = true }')
s = L.eval("LAS(P(2))")
check(s.getZ(s) == 0 and s.getX(s) == 10, "isometric, open air: the ground square under the pointer (iso shift per floor)")
# guns
canShoot = cut(ah, "local function canShoot(z, p)")
L.execute('''
K = { alive = function() return true end, dist = function(a, b, c, d) return math.sqrt((a - c) ^ 2 + (b - d) ^ 2) end,
      outdoors = function() return true end }
ah = { doomed = {} }
S.IsFriendlyNPC = function() return false end
S.opt = function(k) return ({ apacheRange = 40, apacheRocketMin = 3 })[k] or 30 end
AH = { clusterRadius = 4, safeDistance = 8 }
function Z(x, y, z) return { getX = function() return x end, getY = function() return y end, getZ = function() return z end,
    getCurrentSquare = function() return {} end } end
''')
L.execute(canShoot + "CS = canShoot")
check(L.eval("CS(Z(5, 0, 0), P(3)) ~= false"), "Apache gun: an infected on the ground below a player on floor 3")
check(L.eval("CS(Z(5, 0, 4), P(3)) == false"), "Apache gun: never one above the player")
check(L.eval("CS(Z(5, 0, 3), P(3)) ~= false"), "Apache gun: same floor as before")
L.execute(cut(ah, "local function rocketTarget(p)") + "RT = rocketTarget")
L.execute('''
LIST = { Z(20, 0, 0), Z(21, 0, 0), Z(20, 1, 0), Z(22, 1, 0), Z(20, 0, 2), Z(21, 0, 2) }
getCell = function() return { getZombieList = function() return { size = function() return #LIST end, get = function(_, i) return LIST[i + 1] end } end } end
''')
r = L.execute("local x, y, z, n = RT(P(3)); return z, n")
check(r[0] == 0 and r[1] == 4, f"rockets from floor 3: the ground group of 4 at z 0 (got z {r[0]}, n {r[1]})")
r = L.execute("LIST = { Z(20, 0, 2), Z(21, 0, 2), Z(20, 1, 2), Z(20, 0, 0), Z(21, 0, 0) }; local x, y, z, n = RT(P(2)); return z, n")
check(r[0] == 2 and r[1] == 3, "groups are counted per floor (3 on floor 2, not 5 across floors)")
sys.exit(1 if fails else 0)
