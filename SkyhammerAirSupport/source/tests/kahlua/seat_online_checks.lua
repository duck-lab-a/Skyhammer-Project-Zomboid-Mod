-- (2026-11-18, the user asked to try it) The AC-130 gunner seat online, in the Vanilla Edition. The
-- seat was held back to single player on 10-24; its guns already went through the server like the
-- aimed 40mm and the 105 mission. Online it shows the thermal map (no real view). Under PvP the
-- server only knows the 40mm's aimed rounds ("gunaim", 60 a sortie) and the 105 ("he"), so the
-- 25mm (600 rounds, 14 a second) must not report hits on players: it would use up the 40mm's
-- allowance and run past its pace.
local S = Skyhammer
S.log = function(s) LOG[#LOG + 1] = s end
local G = SkyhammerGunner
local fails, names = 0, {}
local function check(ok, name) if not ok then fails = fails + 1; names[#names + 1] = name end end

local function onStation()
    ME = newPlayer("p" .. tostring(CLOCK))
    S.Call("ac130")
    local st = S.Store().craft.ac130
    st.phase, st.stationFromH, st.leaveAtH = "ON_STATION", 0, 1e9
end

-- (2026-11-23, the user: leave it out of this update) held back: online the seat is off until
-- S.GUNNER_SEAT_ONLINE is set, and the terminal offers the 105 marks instead
check(S.GUNNER_SEAT_ONLINE == false, "held back: GUNNER_SEAT_ONLINE is false")
check(S.GunnerSeatOn() == false, "held back: online the gunner seat is off")
onStation()
check(G.CanEnter(ME) ~= true, "held back: online nobody can take the seat")
S.GUNNER_SEAT_ONLINE = true

-- with it on: the seat is offered online in the Vanilla Edition
check(S.GunnerSeatOn() == true, "online: the gunner seat is on")
onStation()
check(G.CanEnter(ME) == true, "online: a player can take the seat with the AC-130 on station")
check(G.RealViewAvailable() == false, "online: the thermal map, not the real view")

-- the seat's own cues heard by this player alone play online too (entry, kill tick); its impacts
-- stay world sounds sent through the server, so the other players hear them
S.SetGunnerManned(true) -- (as G.Enter does before the entry sound)
check(S.GunnerEntrySound("day") == true, "online: the entry sound plays")
check(S.GunnerHitmarker() == true, "online: the kill tick plays")
check(S.GunnerImpactAudio("gun", 110.5, 110.5, 0) == false, "online: impacts left to the shared world sound")
S.SetGunnerManned(false)

-- the server's sandbox can still switch it off
SandboxVars.Skyhammer.GunnerSeat = false
local ok, why = G.CanEnter(ME)
check(S.GunnerSeatOn() == false and ok == false and why == "off", "the server's sandbox switches it off")
SandboxVars.Skyhammer.GunnerSeat = nil

-- the seat's rounds go to the server as hits and effects
onStation()
SENT = {}
check(S.GunnerFire("gun", 110.5, 110.5, 0) == true, "the 40mm fires from the seat online")
for _ = 1, 30 do tick(20) end
check(sent("fx") > 0, "its blast goes to the server for everyone")

-- PvP: the 40mm reports hits on players, the 25mm does not
SandboxVars.Skyhammer.PvP = true
SandboxVars.Skyhammer.PvPCallMode = 2 -- (calls without killstreak points, so the test needs none)
S.PvPServerLive = true
onStation()
SENT = {}
check(S.GunnerFire("gun", 110.5, 110.5, 0) == true, "PvP: the 40mm fires")
for _ = 1, 30 do tick(20) end
check(sent("pvp", "k", "gunaim") == 1, "PvP: one 40mm round, one report (" .. sent("pvp", "k", "gunaim") .. ")")
SENT = {}
local fired = 0
for _ = 1, 10 do
    if S.GunnerFire("gun25", 112.5, 112.5, 0) == true then fired = fired + 1 end
    tick(80)
end
for _ = 1, 30 do tick(20) end
check(fired >= 5, "PvP: the 25mm fires (" .. fired .. ")")
check(sent("pvp") == 0, "PvP: the 25mm reports no hits on players (" .. sent("pvp") .. ")")
check(sent("fx") > 0, "PvP: the 25mm's effects still go to the server")
SandboxVars.Skyhammer.PvP = nil

-- no timed job (an impact) failed along the way: a hidden error would skip the hits
local failed = 0
for _, l in ipairs(LOG) do if string.find(tostring(l), "failed", 1, true) then failed = failed + 1 end end
check(failed == 0, "no timed job failed (" .. failed .. ")")

if fails > 0 then error("gunner seat online checks failed: " .. table.concat(names, " | ")) end
print("skyhammer gunner seat online checks: all passed")
