-- (after the mod files) helpers for the F-22 checks: radio lines and sounds collected, the
-- game's start, the clock, a call and a mark; check() / done() report on the game's Kahlua
S = Skyhammer
SAID = {}
S.Say = function(id) SAID[#SAID + 1] = id end
SOUNDS = {}
S.Kit.soundAt = function(sq, name) SOUNDS[#SOUNDS + 1] = name end
S.log = function() end
function gameStart() for _, fn in ipairs(HANDLERS.OnGameStart or {}) do pcall(fn) end end
gameStart()
function run(ms) for _ = 1, math.floor(ms / 100) do CLOCK = CLOCK + 100; fire("OnTick") end end
function onStation() S.Call("f22"); run((S.opt("f22InboundSec") + 1) * 1000) end
function mark(x, y) local ok = S.Aim("raid", true); run(300); S.ConfirmAimAt(x, y); return ok end
function said(id) for _, s in ipairs(SAID) do if s == id then return true end end return false end
function count(list, id) local n = 0; for _, s in ipairs(list) do if s == id then n = n + 1 end end return n end
function inflight() local n = 0; for _ in pairs(S.InFlight()) do n = n + 1 end return n end
function column() for d = -25, 25, 5 do zombie(140.5, 100.5 + d) end end
-- (the runner shows no print: the failed checks go into the error it reports)
FAILS, CHECKS = {}, 0
function check(ok, name)
    CHECKS = CHECKS + 1
    if not ok then FAILS[#FAILS + 1] = name end
end
function done(name)
    if #FAILS > 0 then error(name .. ": " .. #FAILS .. " of " .. CHECKS .. " failed: " .. table.concat(FAILS, " | ")) end
end
function near(a, b, eps) return a ~= nil and b ~= nil and math.abs(a - b) <= (eps or 1e-6) end
function deg(h) local d = math.floor(math.deg(h) + 0.5) % 360; return d end
