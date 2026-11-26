-- The seat's 25mm (2026-10-31, the user: "brrrr"): one recorded stream a burst, not a report a round.
-- Each round keeps the loop alive (Skyhammer_SeatShotAudio); without rounds it ends by itself.
-- Release plays the wind-down.
require "Skyhammer_Core"
local S = Skyhammer
local NEW_BURST_MS = 300
local lastRound, firing = -1e9, false
function S.Gunner25AudioPulse()
    local now = S.now()
    local gap = now - lastRound
    lastRound = now
    if firing and gap <= NEW_BURST_MS and S.HoldGunner25(1) then return true end
    firing = S.GunnerShotAudio("gun25")
    return firing
end
-- Called on release, weapon change and seat exit, more than once for one burst. Seat exit (immediate)
-- is stopped outright by SeatShotAudio, with no wind-down.
function S.StopGunner25Audio(immediate)
    if not firing then return end
    firing = false
    S.FadeGunner25()
    if not immediate and S.now() - lastRound <= NEW_BURST_MS then S.GunnerShotAudio("tail25") end
end
