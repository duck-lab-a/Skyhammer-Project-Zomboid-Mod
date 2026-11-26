-- The AC-130 gunner seat's own sounds (2026-10-24): one slot each in Skyhammer_SeatSounds.txt
-- (media/sound/skyhammer_seat). A shot a round, the reload 600 ms after the last one, impacts at
-- their point, a tick for a kill, the entry, and the gunship's engines going away. Played to this
-- player alone, stopped with the seat. Online (the seat there since 2026-11-18) only the cues
-- marked online play: the entry and the kill tick, which nobody else would hear anyway. The shots,
-- reloads and impacts stay single player: online Skyhammer_Ops plays them as world sounds the
-- server passes on, so the players nearby hear them too.
require "Skyhammer_Core"
local S = Skyhammer
local active, pending = {}, {}
local cues = {
    gun25 = {name="SH_Seat_Fire25",gain=1,life=300},
    tail25 = {name="SH_Seat_Tail25",gain=1,life=1950},
    gun = {name="SH_Seat_Shot40",gain=1,life=1356},
    he = {name="SH_Seat_Shot105",gain=0.8,life=4055},
    hit40 = {name="SH_Seat_Impact40",gain=0.9,life=5137},
    hit105 = {name="SH_Seat_Impact105",gain=0.8,life=3096},
    reload40 = {name="SH_Seat_Reload40",gain=1,life=2681},
    reload105 = {name="SH_Seat_Reload105",gain=1,life=4648},
    hitmarker = {name="SH_Seat_Hitmarker",gain=0.6,life=317,online=true},
    entry = {name="SH_Seat_Entry",gain=1,life=6799,online=true},
    entryNight = {name="SH_Seat_EntryNight",gain=1,life=6799,online=true},
    departure = {name="SH_AC130_EngineDepart",gain=1,life=6267},
}
-- online: true for a cue that also plays online (the tick below passes true: what is playing may go on)
local function eligible(seat, online)
    local p = getSpecificPlayer(0)
    return p and not p:isDead() and (online or not S.Multiplayer())
        and not (isGamePaused and isGamePaused()) and (not seat or S.GunnerManned())
end
local function stop(q)
    -- Check the individual handle before touching a pooled emitter.
    pcall(function()
        if q.sound then if q.sound:isPlaying() then q.sound:stop() end
        elseif q.e:isPlaying(q.id) then q.e:stopSound(q.id); q.e:tick() end
    end)
end
function S.StopGunnerShotAudio()
    pending = {}
    for i = #active, 1, -1 do
        if active[i].seat then stop(active[i]); table.remove(active, i) end
    end
end
local function clear()
    pending = {}
    for _, q in ipairs(active) do stop(q) end
    active = {}
end
-- Retire the previous 105mm cabin cycle on a successful new shot. An isolated
-- shot keeps its full original tail; repeated shots cannot accumulate old reloads.
-- This affects only the seat reports/reloads, never paid world impacts or other guns.
local HE_RETRIGGER_FADE_MS = 80
local function retire105(now)
    for i = #active, 1, -1 do
        local q = active[i]
        if q.kind == "he" or q.kind == "reload105" then
            if q.fadeAt then stop(q); table.remove(active, i)
            else q.fadeAt = now end
        end
    end
end
local function play(kind, seat, gain)
    local c = cues[kind]
    if not c or not eligible(seat, c.online) then return false end
    local p, e, id = getSpecificPlayer(0)
    local ok, err = pcall(function()
        e = IsoWorld.instance:getFreeEmitter()
        e:setPos(p:getX(), p:getY(), p:getZ())
        id = e:playSoundImpl(c.name, false, nil)
        if not id or id == 0 or id == -1 then error("sound event could not start") end
        e:setVolume(id, 0.001); e:tick(); e:set3D(id, false)
        e:setVolume(id, (c.gain or 1) * (gain or 1))
    end)
    if not ok then
        if e and id then stop({e=e,id=id}) end
        S.log("seat audio failed: " .. kind .. " " .. tostring(err))
        return false
    end
    if kind == "he" then retire105(S.now()) end
    if #active >= 64 then stop(table.remove(active, 1)) end
    active[#active+1] = {e=e,id=id,seat=seat,kind=kind,baseGain=(c.gain or 1)*(gain or 1),untilMs=S.now()+c.life}
    return true
end
-- The 25mm's stream leaves with the trigger, by the same short fade.
function S.FadeGunner25()
    local now = S.now()
    for _, q in ipairs(active) do
        if q.kind == "gun25" and not q.fadeAt then q.fadeAt = now end
    end
end
-- A round keeps the looping stream alive for another moment, at this level; false if it is gone.
function S.HoldGunner25(gain)
    for _, q in ipairs(active) do
        if q.kind == "gun25" and not q.fadeAt then
            q.untilMs = S.now() + cues.gun25.life
            q.baseGain = cues.gun25.gain * gain
            return (pcall(function() q.e:setVolume(q.id, q.baseGain) end))
        end
    end
    return false
end
function S.GunnerShotAudio(kind, gain)
    local ok = play(kind, true, gain)
    if ok and (kind == "gun" or kind == "he") then
        -- the crew reloads 600 ms after the last round of the burst
        pending[kind] = S.now()+600
    end
    return ok
end
function S.GunnerImpactAudio(kind, x, y, z)
    local key = kind == "he" and "hit105" or "hit40"
    if not eligible(true) then return false end
    local c = cues[key]
    local sq = x and getCell():getGridSquare(math.floor(x), math.floor(y), z)
    if not sq then return false end
    -- impacts at their own landing point, each gun its own reach and level
    local radius = kind == "he" and 200 or 100
    local ok, sound = pcall(function()
        return getSoundManager():PlayWorldSound(c.name, sq, 0.1, radius, c.gain, false)
    end)
    if not ok or not sound then S.log("seat impact audio failed: " .. key); return false end
    if #active >= 64 then stop(table.remove(active, 1)) end
    active[#active+1] = {sound=sound,seat=true,untilMs=S.now()+c.life}
    return true
end
function S.GunnerHitmarker() return play("hitmarker", true) end
-- (scene "night": the night clip's own sound, 2026-10-25)
function S.GunnerEntrySound(scene) return play(scene == "night" and "entryNight" or "entry", true) end
function S.GunshipDepartSound() return play("departure", false, S.opt("engineVolume") or 0.6) end
local function tick()
    if not eligible(false, true) then clear(); return end
    if not S.GunnerManned() then S.StopGunnerShotAudio() end
    local now = S.now()
    for kind, at in pairs(pending) do
        if now >= at then pending[kind]=nil; play(kind == "he" and "reload105" or "reload40", true) end
    end
    for i = #active, 1, -1 do
        local q = active[i]
        local ok, playing = pcall(function() return q.sound and q.sound:isPlaying() or (q.e and q.e:isPlaying(q.id)) end)
        if not ok or not playing then table.remove(active, i)
        elseif now >= q.untilMs then stop(q); table.remove(active, i)
        elseif q.fadeAt then
            local t = math.max(0, math.min(1, (now - q.fadeAt) / HE_RETRIGGER_FADE_MS))
            if t >= 1 then stop(q); table.remove(active, i)
            else
                local ok = pcall(function()
                    q.e:setVolume(q.id, math.max(0.001, q.baseGain * (1 - t*t*(3-2*t))))
                    q.e:tick()
                end)
                if not ok then stop(q); table.remove(active, i) end
            end
        elseif q.e then pcall(function() q.e:tick() end) end
    end
end
Events.OnTickEvenPaused.Add(tick)
Events.OnGameStart.Add(clear)
if Events.OnMainMenuEnter then Events.OnMainMenuEnter.Add(clear) end
Events.OnPlayerDeath.Add(function(p) if p == getSpecificPlayer(0) then clear() end end)
