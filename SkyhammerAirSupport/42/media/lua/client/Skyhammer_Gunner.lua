-- Skyhammer Air Support - the AC-130 gunner seat (2026-10-24, the user; source/ac130_gunner_design.md)
-- Taken from the terminal's AC-130 tab while the gunship is on station: a short entry video (the
-- first time each sortie, any key skips it), then the gunship's thermal sensor full screen, where
-- the player fires its 40mm and 105mm by hand (Skyhammer_Ops S.GunnerFire). Pure Lua, the same in
-- both editions and online (the guns go through the server as the aimed 40mm and a 105 mission do).
-- The body stays exactly where it is and can be attacked: only its movement is held while seated,
-- and the world view behind the full-screen seat is not drawn (as the game's own world map does).
-- What ends the seat: Escape or a right-click, death, a vehicle, the sortie's end; being hit does
-- not (the seat warns instead). Nothing of it is saved: a load starts on the ground.
-- There is no real airborne camera: PZ cannot render a second view from Lua (Skyhammer_Feed).

require "ISUI/ISUIElement"
require "Skyhammer_Core"
require "Skyhammer_Ops"
require "Skyhammer_Feed"
require "Skyhammer_GunnerHUD"

local S = Skyhammer
SkyhammerGunner = SkyhammerGunner or {}
local G = SkyhammerGunner
local F = SkyhammerFeed
local D = F.draw

local SEAT = {
    reach = 40,                          -- tiles from the body the view may look (loaded ground)
    zoom = { gun25 = 21.0, gun = 20.5, he = 19.0 },  -- each weapon's own view: the 105 wide, the 25mm closest
    zoomMin = 17.5, zoomMax = 21.5,
    panPx = 700,                         -- screen px a second, keys or screen edge
    edgePx = 16,
    threatTiles = 4,                     -- infected this close to the body: a warning
    hitMs = 1500,                        -- how long a hit on the body stays on screen
    noteMs = 1200,                       -- how long a refused shot says why
    fadeMs = 500,                        -- the seat fading in from the video's black
}
-- the entry video: media/videos/sh_ac130_entry.bik, encoded at exactly this size (VideoTexture
-- uploads each frame at the size it is given), one for day and night since 2026-10-24 evening (the
-- user's own clip, 4.5 s: source/gunner_video/README.txt); stills as the fallback:
-- media/textures/SH_Gunner/entry_<1..6>.png
local VIDEO = { w = 1280, h = 720, ms = 4500, inputGapMs = 300 }

local function dist(ax, ay, bx, by) return math.sqrt((ax - bx) ^ 2 + (ay - by) ^ 2) end

-- ---------------------------------------------------------------- pure helpers
-- The game opens a video at <game>/media/videos/<name> only. A mod's file is reached from there
-- by climbing to the drive's root (extra ".." stop at the root) and going down the mod's own
-- path; so it works when the game and the mod are on the same drive (else the stills play).
-- (2026-10-24 log) The whole path must stay under Windows' 260 characters: 30 climbs made it 284
-- and the video did not open. The game's own videos folder is 7 deep in a usual Steam install
-- (C:\Program Files (x86)\Steam\steamapps\common\ProjectZomboid\media\videos), so 8 climbs
-- first, 16 for a deeper one.
G.VIDEO_CLIMBS = { 8, 16 }
function G.VideoPath(dir, file, climbs)
    local rest = tostring(dir):gsub("\\", "/"):gsub("^%a:", ""):gsub("^/+", ""):gsub("/+$", "")
    return string.rep("../", climbs or G.VIDEO_CLIMBS[1]) .. rest .. "/media/videos/" .. file
end
-- the view point (x, y) held within r tiles of the body (bx, by)
function G.Clamp(bx, by, x, y, r)
    local d = dist(bx, by, x, y)
    if d <= r or d <= 0 then return x, y end
    return bx + (x - bx) * r / d, by + (y - by) * r / d
end
-- the game's hour: day from 6:00 to 20:00
-- (2026-10-25, the user: the night entry from 22:00 to 6:00)
function G.Scene(hour) return (hour >= 6 and hour < 22) and "day" or "night" end
-- an infected's heat figure, in px tall, for a map scale of pxPerTile: about 0.9 of a tile,
-- never too small to read nor too big
function G.FigureHeight(pxPerTile) return math.max(7, math.min(30, math.floor(pxPerTile * 0.9 + 0.5))) end
-- the sensor's polarity: white-hot (hot is white) or black-hot (hot is black), kept between seats
local blackHot = false
function G.BlackHot() return blackHot end
function G.TogglePolarity() blackHot = not blackHot; return blackHot end
local function gameHour()
    local ok, h = pcall(function() return getGameTime():getTimeOfDay() end)
    return (ok and tonumber(h)) or 12
end

-- ---------------------------------------------------------------- who may take the seat
-- true, or false and why ("off", "dead", "notready", "dry", "vehicle", "asleep")
function G.CanEnter(p)
    if not S.GunnerSeatOn() then return false, "off" end
    if not p or p:isDead() then return false, "dead" end
    if S.Phase("gun") ~= "ON_STATION" then return false, "notready" end
    if S.Ammo("gun") <= 0 and S.Ammo("he") <= 0 then return false, "dry" end
    if p:getVehicle() then return false, "vehicle" end
    if p:isAsleep() then return false, "asleep" end
    return true
end
-- what ends the seat while in it (nil: nothing)
function G.Interrupt(p)
    if not p or p:isDead() then return "dead" end
    if p:getVehicle() then return "vehicle" end
    if S.Phase("gun") ~= "ON_STATION" then return "over" end
    return nil
end

-- ---------------------------------------------------------------- taking and leaving it
local restoreCamera -- assigned after the real-view helpers
local state = { active = false, stage = nil, ui = nil, held = false, introSortie = nil }
function G.Active() return state.active end
function G.Stage() return state.stage end
-- (2026-10-31, the user) the entry video covers the screen and holds the body still, so the body is
-- safe through it; the real view's camera takes over after. A save keeps the flag, so it is dropped
-- for a save and the next frame of the video sets it again.
local introGod = nil
local function videoSafe(p)
    if introGod == nil and p then introGod = p:isGodMod(); p:setGodMod(true) end
end
local function videoSafeEnd()
    if introGod == nil then return end
    local god = introGod
    introGod = nil
    pcall(function() getSpecificPlayer(0):setGodMod(god) end)
end
function G.IntroFrame()
    if state.active and state.stage == "intro" and state.real then videoSafe(getSpecificPlayer(0)) end
end

-- (2026-10-24, the user's screenshot 19: Division Gadgets' panel and the 3D minimap still over the
-- seat) the game's toggle hides the UI once, but some mods show theirs again each tick: the 3D
-- minimap unless ISUIHandler.allUIVisible is false (so the flag is put down too), a gadget panel
-- whatever it says. So while seated, every frame before the UI is drawn, whatever shows that is
-- not the seat's own (skyhammerKeep) is hidden again, and shown again when the seat ends.
local others = {}
local function hideOthers()
    pcall(function()
        local ui = UIManager.getUI()
        for i = 0, ui:size() - 1 do
            local e = ui:get(i)
            if e:isVisible() then
                local t = e.getTable and e:getTable()
                if not (t and t.skyhammerKeep) then
                    e:setVisible(false)
                    others[e] = true
                end
            end
        end
    end)
end
local function othersBack()
    Events.OnPreUIDraw.Remove(hideOthers)
    for e in pairs(others) do pcall(function() e:setVisible(true) end) end
    others = {}
end

local function show(stage, ui)
    local old = state.ui
    state.stage, state.ui = stage, ui
    if old and old ~= ui then pcall(function() old:hide() end) end
    if ui then
        local ok, err = pcall(function() ui:show() end)
        if not ok then
            S.log("gunner screen failed: " .. tostring(err))
            G.Exit("error")
        end
    elseif stage == "intro" then G.IntroDone() end
end

local function createScreen(stage, factory, arg)
    local ok, ui = pcall(factory, arg)
    if not ok then
        S.log("gunner screen creation failed: " .. tostring(ui))
        G.Exit("error")
        return
    end
    show(stage, ui)
end

function G.Enter()
    local p = getSpecificPlayer(0)
    local ok, why = G.CanEnter(p)
    if not ok then
        if p then HaloTextHelper.addBadText(p, getText("IGUI_SH_Gun_No_" .. tostring(why))) end
        return false
    end
    if S.IsAiming() then S.CancelAim(true) end
    if S.CloseTerminal then S.CloseTerminal() end
    -- (2026-10-24, the user's screenshot: the game's bars, hotbar, minimap and clock over the seat)
    -- the game's own UI out of the way through its own toggle (the V key's), back after; left
    -- alone when the player has it hidden already. The seat's screens come after, so they show.
    if ISUIHandler and ISUIHandler.setVisibleAllUI and ISUIHandler.allUIVisible ~= false then
        state.uiHidden = pcall(ISUIHandler.setVisibleAllUI, false)
        if state.uiHidden then ISUIHandler.allUIVisible = false end
    end
    Events.OnPreUIDraw.Add(hideOthers)
    state.active = true
    state.held = p:isBlockMovement()
    p:setBlockMovement(true)
    S.SetGunnerManned(true)
    local scene = G.Scene(gameHour())
    S.GunnerEntrySound(scene)
    -- the real world (Killstreak Air Support's camera) or the thermal map, decided once a seat;
    -- the map hides the world behind it
    state.real = G.RealViewAvailable() == true
    if not state.real then pcall(function() getWorld():setDrawWorld(false) end) end
    local sortie = S.Sortie("ac130")
    if state.introSortie ~= sortie then
        state.introSortie = sortie
        if state.real then videoSafe(p) end
        createScreen("intro", G.makeIntro, scene)
    else
        createScreen("seat", G.makeScreen, state.real)
    end
    if not state.active then return false end
    S.log("gunner seat taken (" .. (state.real and "real view" or "thermal map") .. ")")
    return true
end
S.EnterGunner = G.Enter

-- the video ended or was skipped
function G.IntroDone()
    if not state.active or state.stage ~= "intro" then return end
    videoSafeEnd()
    createScreen("seat", G.makeScreen, state.real)
end

function G.Exit(reason)
    if not state.active then return end
    state.active = false
    videoSafeEnd()
    local ui = state.ui
    state.ui, state.stage = nil, nil
    if ui then pcall(function() ui:hide() end) end
    -- UI/audio cleanup must never be the only route back to the saved body.
    if restoreCamera then restoreCamera() end
    othersBack()
    if state.uiHidden then
        state.uiHidden = false
        ISUIHandler.allUIVisible = true
        pcall(ISUIHandler.setVisibleAllUI, true)
    end
    pcall(S.SetGunnerManned, false)
    local p = getSpecificPlayer(0)
    if p then pcall(function() p:setBlockMovement(state.held == true) end) end
    pcall(function() getWorld():setDrawWorld(true) end)
    S.log("gunner seat left (" .. tostring(reason) .. ")")
end

-- ---------------------------------------------------------------- the entry video
local Intro = ISUIElement:derive("SkyhammerGunnerIntro")

local function modId() return S.VanillaEdition() and "SkyhammerAirSupportVanilla" or "SkyhammerAirSupport" end
-- What the entry plays: { mod, file (in that mod's media/videos), ms, w, h, cues, engine, static }.
-- (2026-10-24, the user: another video for their own game only) a local mod may set
-- G.IntroOverride = { mod, file, ms, sound, w, h }: that video, encoded at w x h (else VIDEO.w x
-- VIDEO.h), for ms, with its own sound (a sound script name) at the start in place of the
-- engines, flares and static.
function G.IntroSpec(scene)
    local o = G.IntroOverride
    if type(o) == "table" and type(o.mod) == "string" and type(o.file) == "string" then
        return { mod = o.mod, file = o.file, ms = tonumber(o.ms) or VIDEO.ms,
                 w = tonumber(o.w) or VIDEO.w, h = tonumber(o.h) or VIDEO.h,
                 cues = o.sound and { { 0, o.sound } } or {}, engine = false, static = false }
    end
    -- (2026-10-25, the user's night clip for the dark hours, the same size and length)
    return { mod = modId(), file = scene == "night" and "sh_ac130_entry_night.bik" or "sh_ac130_entry.bik",
             ms = VIDEO.ms, w = VIDEO.w, h = VIDEO.h, cues = G.INTRO_CUES, engine = false, static = false }
end
local function openVideo(spec)
    local file = spec.file
    local ok, mod = pcall(getModInfoByID, spec.mod)
    if not ok or not mod then return nil end
    -- (the file ships in the mod's 42 folder: its version dir)
    local okD, dir = pcall(function() return mod:getVersionDir() end)
    if not okD or not dir or dir == "" then return nil end
    for _, climbs in ipairs(G.VIDEO_CLIMBS) do
        local okV, v = pcall(function() return VideoTexture.getOrCreate(G.VideoPath(dir, file, climbs), spec.w, spec.h) end)
        if okV and v then return v end
    end
    return nil
end
local function loadStills(scene)
    local list = {}
    for i = 1, 6 do
        local t = getTexture("media/textures/SH_Gunner/entry_" .. i .. ".png")
        if not t then break end
        list[#list + 1] = t
    end
    return list
end

-- (2026-10-24, the user: the entry played silent) its sound: the gunship's engines growing as it
-- closes in, a flare going off each time the video's pairs leave the gunship (1.1-3.3 s), the
-- crew calling the angel flares, and the switch to the sensor picture at the cut. ms -> a sound
-- (SH_*) or a radio line. Played to this player alone, not in 3D.
G.INTRO_CUES = {} -- the entry's sound is one take (SH_Seat_Entry), played on entering the seat

local function playLocal(name, volume)
    local p = getSpecificPlayer(0)
    if not p then return nil end
    local ok, e, id = pcall(function()
        local e = IsoWorld.instance:getFreeEmitter()
        e:setPos(p:getX(), p:getY(), p:getZ())
        local id = e:playSoundImpl(name, false, nil)
        if not id or id == 0 or id == -1 then return nil, nil end
        e:setVolume(id, math.max(0, math.min(1, volume)))
        e:tick(); e:set3D(id, false); e:tick()
        return e, id
    end)
    if ok and e then return { e = e, id = id } end
    return nil
end
local function stopLocal(s)
    if s then pcall(function() s.e:stopSound(s.id); s.e:tick() end) end
end

function Intro:new(scene)
    local o = ISUIElement.new(self, 0, 0, getCore():getScreenWidth(), getCore():getScreenHeight())
    o.scene = scene
    o.skyhammerKeep = true
    return o
end
-- the sounds due by t ms; the engines' volume follows the approach
function Intro:sounds(t)
    local voice = S.opt("voiceVolume") or 0.8
    local cues = self.spec.cues
    while self.cue <= #cues and t >= cues[self.cue][1] do
        local name = cues[self.cue][2]
        self.cue = self.cue + 1
        if not self.spec.static then
            -- (a local video's own sound, at full volume and stopped with it)
            self.playing = self.playing or {}
            self.playing[#self.playing + 1] = playLocal(name, 1)
        elseif name:sub(1, 3) == "SH_" then playLocal(name, voice)
        else S.Say(name, nil, { craft = "ac130", priority = true }) end
    end
    if self.engine then
        local v = (S.opt("engineVolume") or 0.6) * (0.35 + 0.65 * math.min(1, t / 4500))
        pcall(function() self.engine.e:setVolume(self.engine.id, math.max(0, math.min(1, v))) end)
    end
end
function Intro:show()
    self:initialise()
    self:addToUIManager()
    self:setVisible(true)
    pcall(function() self:setAlwaysOnTop(true) end)
    self:setWantKeyEvents(true)
    self:setCapture(true)
    self.startMs = S.now()
    self.spec = G.IntroSpec(self.scene)
    self.video = openVideo(self.spec)
    -- (a local video that does not open: Skyhammer's own)
    if not self.video and self.spec.mod ~= modId() then
        S.log("gunner seat entry: " .. tostring(self.spec.file) .. " did not open")
        G.IntroOverride = nil
        self.spec = G.IntroSpec(self.scene)
        self.video = openVideo(self.spec)
    end
    self.stills = self.video and {} or loadStills(self.scene)
    S.log("gunner seat entry: " .. (self.video and "video" or (#self.stills > 0 and "stills" or "none")) .. " (" .. self.scene .. ")")
    if not self.video and #self.stills == 0 then G.IntroDone(); return end
    self.cue = 1
    self.engine = self.spec.engine and playLocal("SH_AC130_EngineLoop", (S.opt("engineVolume") or 0.6) * 0.35) or nil
end
function Intro:hide()
    pcall(function() self:setCapture(false) end)
    stopLocal(self.engine); self.engine = nil
    -- (skipped before the cut: its switch to the sensor all the same)
    if self.cue and self.spec.static and self.cue <= #self.spec.cues then playLocal("SH_Gunner_Static", S.opt("voiceVolume") or 0.8) end
    for _, s in ipairs(self.playing or {}) do stopLocal(s) end
    self.playing = nil
    self.cue = nil
    if self.video then pcall(function() self.video:closeAndDestroy() end); self.video = nil end
    self:setVisible(false)
    self:removeFromUIManager()
end
-- any key or click skips it (not the one that opened the seat)
function Intro:skip() if S.now() - (self.startMs or 0) >= VIDEO.inputGapMs then G.IntroDone() end end
function Intro:isKeyConsumed() return true end
function Intro:onKeyPress() self:skip() end
function Intro:onMouseDown() return true end
function Intro:onMouseUp() self:skip(); return true end
function Intro:onRightMouseDown() return true end
function Intro:onRightMouseUp() self:skip(); return true end

-- the 16:9 picture, as large as fits, centred
local function frame(w, h)
    local vw, vh = w, math.floor(w * 9 / 16)
    if vh > h then vh, vw = h, math.floor(h * 16 / 9) end
    return math.floor((w - vw) / 2), math.floor((h - vh) / 2), vw, vh
end

function Intro:paint()
    local w, h = self.width, self.height
    local t = S.now() - self.startMs
    local ms = self.spec.ms
    if t >= ms then G.IntroDone(); return end
    if self.cue then self:sounds(t) end
    self:drawRect(0, 0, w, h, 1, 0, 0, 0)
    local x0, y0, vw, vh = frame(w, h)
    if self.video then
        self.video:RenderFrame()
        self:drawTextureScaled(self.video, x0, y0, vw, vh, 1, 1, 1, 1)
    elseif #self.stills > 0 then
        -- each still a share of the time, slowly pushing in, the next one fading over its end
        local per = ms / #self.stills
        local i = math.min(#self.stills, math.floor(t / per) + 1)
        local k = (t - (i - 1) * per) / per
        self:setStencilRect(x0, y0, vw, vh)
        local function still(tex, kk, a)
            local z = 1 + 0.06 * kk
            local sw, sh = vw * z, vh * z
            self:drawTextureScaled(tex, x0 - (sw - vw) / 2, y0 - (sh - vh) / 2, sw, sh, a, 1, 1, 1)
        end
        still(self.stills[i], k, 1)
        local cross = 350 / per
        if i < #self.stills and k > 1 - cross then still(self.stills[i + 1], 0, (k - (1 - cross)) / cross) end
        self:clearStencilRect()
    end
    -- into black at the end, where the seat fades in
    local fade = (t - (ms - 400)) / 400
    if fade > 0 then self:drawRect(0, 0, w, h, math.min(1, fade), 0, 0, 0) end
    local skip = getText("IGUI_SH_Gun_Skip")
    D.hudText(self, skip, w - 24 - D.textW(skip), h - 24 - getTextManager():getFontHeight(UIFont.Small), UIFont.Small, { 0.75, 0.75, 0.75 })
end
function Intro:render()
    G.IntroFrame()
    local ok, err = pcall(self.paint, self)
    if not ok then S.log("gunner seat entry failed: " .. tostring(err)); G.IntroDone() end
end

function G.makeIntro(scene) return Intro:new(scene) end

-- ---------------------------------------------------------------- the seat
-- Two pictures share everything else (the sights, the guns, the HUD, the keys):
--   real  the real world from above through the body cam and the thermal screen shader, single
--         player (G.RealViewAvailable, below)
--   map   the gunship's thermal sensor map (Skyhammer_Feed), the seat's own picture otherwise
-- Each gives toUI / toWorld (world point <-> screen), px (pixels a radius of tiles spans),
-- ring (a ground circle), applyZoom, applyPolarity, centerView and paintWorld.
local AMBER = { 0.96, 0.75, 0.25 }
local GREEN = { 0.58, 0.80, 0.61 }
-- (2026-10-24, the user: "seat 1 25mm, 2 40mm, 3 105mm") the number keys in this order; the
-- switch key goes round them
local WEAPONS = { "gun25", "gun", "he" }
local NAME = { gun25 = "25MM", gun = "40MM", he = "105MM" }
G.WEAPONS = WEAPONS
function G.NextWeapon(w)
    for i, v in ipairs(WEAPONS) do if v == w then return WEAPONS[i % #WEAPONS + 1] end end
    return WEAPONS[1]
end
local Seat = {}

-- where the body is: in the real picture the character is out flying the camera (its body cam
-- keeps where it really is)
local RV = { active = false }
local bodyHome = nil
local function bodyAt(p)
    if bodyHome then
        local x, y, z = bodyHome()
        if x then return x, y, z end
    end
    return p:getX(), p:getY(), math.floor(p:getZ())
end

function Seat:setWeapon(w)
    if self.weapon ~= w then S.StopGunner25Audio(false) end
    self.weapon = w
    self.zoom = self.zooms[w]
    self:applyZoom(self.zoom)
end

function Seat:show()
    local p = getSpecificPlayer(0)
    self.vx, self.vy = p:getX(), p:getY()
    self.trigger, self.note, self.hitAt, self.hp, self.threats = false, nil, nil, nil, 0
    self.shownMs, self.lastMs, self.scanAt, self.kickMs = S.now(), nil, 0, nil
    self.skyhammerKeep = true
    if self.onShow then self:onShow(p) end
    -- the weapon last used (the 40mm the first time), unless it is empty: the next one with rounds
    local w = G.lastWeapon or "gun"
    for _ = 1, #WEAPONS do
        if S.Ammo(w) > 0 then break end
        w = G.NextWeapon(w)
    end
    self:setWeapon(w)
    self:applyPolarity()
    self:addToUIManager()
    self:setVisible(true)
    pcall(function() self:setAlwaysOnTop(true) end)
    self:setWantKeyEvents(true)
    -- (holding the mouse, the seat is a modal window to Viewpoint: its cursor is set free)
    self:setCapture(true)
end
function Seat:hide()
    pcall(S.ClearGunnerTracers)
    pcall(S.StopGunner25Audio, true)
    pcall(S.StopGunnerShotAudio)
    G.lastWeapon = self.weapon
    self.trigger = false
    pcall(function() self:setCapture(false) end)
    pcall(function() self:setVisible(false) end)
    pcall(function() self:removeFromUIManager() end)
    if self.onHide then self:onHide() end
end

-- ---- input
function Seat:aimPoint(mx,my)
    local x,y=self:toWorld(mx,my)
    return x,y,0
end
function Seat:fire()
    local mx, my = self:getMouseX(), self:getMouseY()
    -- (a held trigger waits for the reload quietly; a click during it is not lost: it fires on ready)
    if S.GunnerReload(self.weapon) > 0 then return end
    local wx, wy, wz = self:aimPoint(mx, my, true)
    local ok, why = S.GunnerFire(self.weapon, wx, wy, wz)
    if ok then
        self.kickMs = S.now()
        if self.onShot then self:onShot(self.weapon) end
    elseif why then
        if self.weapon == "gun25" then S.StopGunner25Audio(false) end
        self.note = { why = why, ms = S.now() }
    end
end
function Seat:onMouseDown() self.trigger = true; self:fire(); return true end
function Seat:onMouseUp() self.trigger = false; S.StopGunner25Audio(false); return true end
function Seat:onMouseUpOutside() self.trigger = false; S.StopGunner25Audio(false) end
function Seat:onRightMouseDown() return true end
function Seat:onRightMouseUp() G.Exit("player"); return true end
function Seat:onMouseWheel(del)
    local Z = self.ZOOM
    local z = math.max(Z.min, math.min(Z.max, self.zoom + del * Z.wheel))
    self.zoom, self.zooms[self.weapon] = z, z
    self:applyZoom(z)
    return true
end
local function switchKey() return S.opt("keyGunnerSwitch") end
local function polarityKey() return S.opt("keyGunnerPolarity") end
function Seat:isKeyConsumed(key)
    return key == Keyboard.KEY_ESCAPE or key == Keyboard.KEY_1 or key == Keyboard.KEY_2 or key == Keyboard.KEY_3
        or key == switchKey()
        or key == polarityKey()
end
function Seat:onKeyPress(key)
    if key == Keyboard.KEY_ESCAPE then G.Exit("player")
    elseif key == Keyboard.KEY_1 then self:setWeapon(WEAPONS[1])
    elseif key == Keyboard.KEY_2 then self:setWeapon(WEAPONS[2])
    elseif key == Keyboard.KEY_3 then self:setWeapon(WEAPONS[3])
    elseif key == switchKey() then self:setWeapon(G.NextWeapon(self.weapon))
    elseif key == polarityKey() then G.TogglePolarity(); self:applyPolarity() end
end

-- ---- each frame: what ends the seat, the view's movement, the held trigger, the body
local function down(...)
    for _, k in ipairs({ ... }) do
        local ok, d = pcall(isKeyDown, k)
        if ok and d then return true end
    end
    return false
end
local function threatsNear(px, py, pz)
    local list, n = getCell():getZombieList(), 0
    local r2 = SEAT.threatTiles * SEAT.threatTiles
    for i = 0, list:size() - 1 do
        local z = list:get(i)
        local dx, dy = z:getX() - px, z:getY() - py
        if dx * dx + dy * dy <= r2 and math.floor(z:getZ()) == pz and not z:isDead()
            and not (S.IsFriendlyNPC and S.IsFriendlyNPC(z)) then n = n + 1 end
    end
    return n
end
local function alert(x, y, z)
    pcall(function()
        local e = IsoWorld.instance:getFreeEmitter()
        e:setPos(x, y, z)
        local id = e:playSoundImpl("SH_Gunner_Alert", false, nil)
        if not id or id == 0 or id == -1 then return end
        e:setVolume(id, math.max(0, math.min(1, S.opt("voiceVolume") or 0.8)))
        e:tick(); e:set3D(id, false); e:tick()
    end)
end

function Seat:step()
    local p = getSpecificPlayer(0)
    local why = G.Interrupt(p)
    if why then G.Exit(why); return end
    local now = S.now()
    local dt = math.min(100, now - (self.lastMs or now))
    self.lastMs = now
    if self.everyFrame then self:everyFrame(now) end
    -- the view moves with the keys and at the screen's edges, held within reach of the body
    local w, h = self.width, self.height
    local mx, my = self:getMouseX(), self:getMouseY()
    local sx, sy = 0, 0
    if down(Keyboard.KEY_A, Keyboard.KEY_LEFT) then sx = sx - 1 end
    if down(Keyboard.KEY_D, Keyboard.KEY_RIGHT) then sx = sx + 1 end
    if down(Keyboard.KEY_W, Keyboard.KEY_UP) then sy = sy - 1 end
    if down(Keyboard.KEY_S, Keyboard.KEY_DOWN) then sy = sy + 1 end
    if mx >= 0 and my >= 0 and mx <= w and my <= h then
        if mx < SEAT.edgePx then sx = sx - 1 elseif mx > w - SEAT.edgePx then sx = sx + 1 end
        if my < SEAT.edgePx then sy = sy - 1 elseif my > h - SEAT.edgePx then sy = sy + 1 end
    end
    if (sx ~= 0 or sy ~= 0) and dt > 0 then
        local step = SEAT.panPx * dt / 1000
        local cx, cy = w / 2, h / 2
        local x0, y0 = self:toWorld(cx, cy)
        local x1, y1 = self:toWorld(cx + sx * step, cy + sy * step)
        self.vx, self.vy = self.vx + (x1 - x0), self.vy + (y1 - y0)
    end
    local bx, by, bz = bodyAt(p)
    self.vx, self.vy = G.Clamp(bx, by, self.vx, self.vy, SEAT.reach)
    self:centerView()
    if self.trigger then self:fire() end
    -- Camera health alone cannot identify a body hit. Real-view blast damage reports
    -- explicitly through GunnerBodyHit; the map view keeps normal health polling.
    local okH, hp = false, nil
    if not (bodyHome and bodyHome()) then
        okH, hp = pcall(function() return p:getBodyDamage():getOverallBodyHealth() end)
    end
    if okH and hp then
        if self.hp and hp < self.hp - 0.05 then
            if not self.hitAt or now - self.hitAt > 1000 then alert(bx, by, bz) end
            self.hitAt = now
        end
        self.hp = hp
    end
    if now - self.scanAt >= 250 then
        self.scanAt = now
        local okT, n = pcall(threatsNear, bx, by, bz)
        self.threats = okT and n or 0
    end
end
function Seat:prerender()
    local ok, err = pcall(self.step, self)
    if not ok then S.log("gunner seat failed: " .. tostring(err)); G.Exit("error") end
end

-- ---- drawing
-- the reticle at the pointer: CoD's gunship sights, the 105's wider; it jumps open as a round goes
function Seat:reticle(x,y,c,now)
    SkyhammerGunnerHUD.Reticle(self,x,y,c,now)
end

function Seat:paint()
    local w, h = self.width, self.height
    local p = getSpecificPlayer(0)
    if not p then return end
    local now = S.now()
    local fh = getTextManager():getFontHeight(UIFont.Small)
    -- The shader supplies subtle sensor grain; no full-screen scanline veil.
    local edge=math.max(4,math.floor(h*.012))
    for i=0,7 do
        local n=i*edge;local a=.012*(8-i)
        self:drawRect(n,n,w-n*2,edge,a,0,0,0);self:drawRect(n,h-n-edge,w-n*2,edge,a,0,0,0)
        self:drawRect(n,n,edge,h-n*2,a,0,0,0);self:drawRect(w-n-edge,n,edge,h-n*2,a,0,0,0)
    end
    self:paintWorld(p, now)
    S.DrawGunnerTracers(self, blackHot)
    -- (the real picture keeps to the gunship's TV: the sights and the guns, nothing laid over the
    -- world; the map marks the shells, the body and the danger)
    local clean = self.clean == true
    -- 105 shells still in the air: a ring at the point, closing in as they come down
    local combat = S.combatMs()
    for _, f in pairs((not clean) and S.InFlight and S.InFlight() or {}) do
        local left = (tonumber(f.at) or 0) - combat
        if f.k == "he" and left > 0 then
            local ux, uy = self:toUI(f.x, f.y)
            local r = self:px(f.x, f.y, 1.5 + 6 * math.min(1, left / 3000))
            self:ring(ux, uy, r, AMBER)
            D.hudText(self, string.format("%.1f", left / 1000), ux + r + 4, uy - fh / 2, UIFont.Small, AMBER)
        end
    end
    -- the body: a diamond, red while it is being hit
    local hit = self.hitAt and now - self.hitAt < SEAT.hitMs
    local px0, py0 = bodyAt(p)
    if not clean then
        local bx, by = self:toUI(px0, py0)
        bx, by = math.floor(bx), math.floor(by)
        D.diamond(self, bx, by, 9)
        if hit then D.ring(self, bx, by, 16, D.WARN) end
        D.hudText(self, getText("IGUI_SH_Gun_Body"), bx + 14, by - fh / 2, UIFont.Small, hit and D.WARN or D.WHITE)
    end

    -- the sights at the pointer, with the rounds' scatter and blast; red when the body is in it,
    -- grey over ground out of reach
    local mx, my = self:getMouseX(), self:getMouseY()
    local wx, wy, wz = self:aimPoint(mx, my)
    self.aimZ=wz or 0
    local cell = getCell()
    local loaded = cell and cell:getGridSquare(math.floor(wx), math.floor(wy), self.aimZ) ~= nil
    local spread, danger = S.GunnerSpread(self.weapon)
    local col = not loaded and D.FAR or ((not clean and dist(px0, py0, wx, wy) <= spread + danger) and D.WARN or D.WHITE)
    if not clean then self:ring(mx, my, self:px(wx, wy, spread + danger), { col[1] * 0.6, col[2] * 0.6, col[3] * 0.6 }) end
    self:reticle(mx, my, col, now)
    local note = self.note and now - self.note.ms < SEAT.noteMs and self.note.why or (not loaded and "far" or nil)
    if note and note ~= "reload" then
        D.hudText(self, getText("IGUI_SH_Gun_Why_" .. note), mx + 34, my + 22, UIFont.Small, col == D.WHITE and AMBER or col)
    end

    local keyName,polName="Q","B"
    pcall(function()keyName=Keyboard.getKeyName(switchKey())or keyName end)
    pcall(function()polName=Keyboard.getKeyName(polarityKey())or polName end)
    SkyhammerGunnerHUD.Draw(self,blackHot,wx,wy,loaded,hit,keyName,polName)
    if hit then
        local a=.35*(1-(now-self.hitAt)/SEAT.hitMs)
        self:drawRectBorder(1,1,w-2,h-2,a,D.WARN[1],D.WARN[2],D.WARN[3])
    end

    -- fading in from the video's black
    local t = now - (self.shownMs or now)
    if t < SEAT.fadeMs then self:drawRect(0, 0, w, h, 1 - t / SEAT.fadeMs, 0, 0, 0) end
end
function Seat:render()
    local ok, err = pcall(self.paint, self)
    if not ok then S.log("gunner seat failed: " .. tostring(err)); G.Exit("error") end
end

-- ---------------------------------------------------------------- the map picture
local MapScreen = F:derive("SkyhammerGunnerScreen")
for k, v in pairs(Seat) do MapScreen[k] = v end
MapScreen.ZOOM = { min = SEAT.zoomMin, max = SEAT.zoomMax, wheel = -0.5 }

function MapScreen:new(w, h)
    local o = F.new(self, 0, 0, w, h)
    o.minZoom = SEAT.zoomMin
    o.zooms = { gun25 = SEAT.zoom.gun25, gun = SEAT.zoom.gun, he = SEAT.zoom.he }
    o.weapon = "gun"
    return o
end
function MapScreen:toUI(x, y) return self.mapAPI:worldToUIX(x, y), self.mapAPI:worldToUIY(x, y) end
function MapScreen:toWorld(mx, my) return self.mapAPI:uiToWorldX(mx, my), self.mapAPI:uiToWorldY(mx, my) end
function MapScreen:px(wx, wy, r)
    local ax, ay = self:toUI(wx, wy)
    local bx, by = self:toUI(wx + r, wy)
    return math.sqrt((bx - ax) ^ 2 + (by - ay) ^ 2)
end
function MapScreen:ring(cx, cy, r, c) D.ring(self, cx, cy, r, c) end
function MapScreen:applyZoom(z) self.mapAPI:setZoom(z) end
function MapScreen:applyPolarity() self:thermalStyle(blackHot) end
function MapScreen:centerView() self.mapAPI:centerOn(self.vx, self.vy) end

-- an infected as the gunship's sensor sees it: a small human shape of heat (head, shoulders and
-- arms, body, legs) in a soft halo; hot is white (white-hot) or black (black-hot)
function MapScreen:figure(x, y, hgt, hot, glow)
    local u = hgt / 10
    local function part(dx, dy, pw, ph, a, c)
        self:drawRect(math.floor(x + dx * u), math.floor(y + dy * u), math.max(1, math.floor(pw * u + 0.5)),
            math.max(1, math.floor(ph * u + 0.5)), a, c, c, c)
    end
    part(-3.5, -6, 7, 12, 0.3, glow)          -- halo
    part(-1, -5, 2, 2, 1, hot)                -- head
    part(-2, -3, 4, 4, 1, hot)                -- body
    part(-3, -3, 1, 3, 0.9, hot)              -- arms
    part(2, -3, 1, 3, 0.9, hot)
    part(-2, 1, 1.6, 4, 1, hot)               -- legs
    part(0.4, 1, 1.6, 4, 1, hot)
end
-- what only the map shows: the infected as heat figures, friends (green), the blasts
function MapScreen:paintWorld(p, now)
    local w, h = self.width, self.height
    local inside = function(x, y, m) return x > m and y > m and x < w - m and y < h - m end
    local c = F.Contacts(p, 0)
    local fig = G.FigureHeight(self:px(self.vx, self.vy, 1))
    local hot, glow = (blackHot and 0.04 or 1), (blackHot and 0.3 or 0.8)
    for i = 1, c.n do
        local ux, uy = self:toUI(c[i * 2 - 1], c[i * 2])
        if inside(ux, uy, fig) then self:figure(ux, uy, fig, hot, glow) end
    end
    for _, f in ipairs(c.friends) do
        local ux, uy = self:toUI(f[1], f[2])
        if inside(ux, uy, 5) then
            self:drawRectBorder(ux - 5, uy - 5, 11, 11, 0.6, 0, 0, 0)
            self:drawRectBorder(ux - 4, uy - 4, 9, 9, 1, GREEN[1], GREEN[2], GREEN[3])
        end
    end
    local spark = getTexture("media/ui/SH_FX_Spark.png")
    for _, b in ipairs(S.blasts or {}) do
        local age = now - b.born
        if age < 1500 and spark then
            local k = age / 1500
            local ux, uy = self:toUI(b.x, b.y)
            local r = (3 + b.size * 2.5) * (0.6 + k) * (self.zoom / 18.5)
            if ux > -r and uy > -r and ux < w + r and uy < h + r then
                self:drawTextureScaled(spark, ux - r, uy - r, r * 2, r * 2, 1 - k, 1, 1, 1)
            end
        end
    end
end
-- the world behind the full-screen map is not drawn (as the game's own world map does)
function MapScreen:onShow() pcall(function() getWorld():setDrawWorld(false) end) end
function MapScreen:onHide() pcall(function() getWorld():setDrawWorld(true) end) end

-- ---------------------------------------------------------------- the real picture
-- (2026-10-24, the user: "the minimap looks cheap") The real world from above, made here in pure
-- Lua so both editions have it; single
-- player (online the map stays: a character flying the camera has no place on a server):
--  * camera: the game always draws from the player character, so the character flies the
--    camera: hidden, a ghost to the infected, through walls, unhurt, seeing everything, its model
--    not drawn; set at the view point every frame on the ground floor, and put back exactly where
--    and as it was when the seat ends, and around every save
--  * picture: Skyhammer's media/shaders/screen.frag, the game's own plus a thermal branch, turned
--    on through the forage search-mode values the game hands it (darkness 2001 = white-hot,
--    2002 = black-hot; the game's own stay 0..1, and leaves them alone while on "override")
--  * zoom: the player's own zoom levels, stepped, undone after
--  * the infected: hot figures drawn over them (the picture alone does not know heat)
--  * Viewpoint's 3D view: its isometric view for the seat, back after
local THERMAL = 2000                                   -- + 1 white-hot, + 2 black-hot
function G.RealViewAvailable() return not S.Multiplayer() end

-- the body cam
local Body = { saved = nil }
local cameraPlayer, cameraGuardOn = nil, false
-- Only reject a target that is this seat's hidden camera. No periodic list scan.
local function cameraTargetGuard(z)
    if not cameraPlayer or not z or z:isDead() or z:getTarget() ~= cameraPlayer then return end
    if S.IsFriendlyNPC and S.IsFriendlyNPC(z) then return end
    z:setTarget(nil)
    pcall(function() z:setTargetSeenTime(0) end)
    pcall(function() z:getPathFindBehavior2():cancel() end)
    pcall(function() z:setPath2(nil) end)
    pcall(function() z:setDefaultState() end)
end
local function cameraGuardStart(p)
    cameraPlayer = p
    if not cameraGuardOn then
        Events.OnZombieUpdate.Add(cameraTargetGuard)
        cameraGuardOn = true
    end
    -- Clear targets acquired before entry once; subsequent updates handle reacquisition.
    local cell = getCell()
    local list = cell and cell:getZombieList()
    if list then for i = 0, list:size() - 1 do cameraTargetGuard(list:get(i)) end end
end
local function cameraGuardStop()
    cameraPlayer = nil
    if cameraGuardOn then
        Events.OnZombieUpdate.Remove(cameraTargetGuard)
        cameraGuardOn = false
    end
end
-- Local 360-degree terrain vision only while this camera owns the player.
-- The bridge expires on its own if a Lua error interrupts the camera heartbeat.
local function cameraVision(p)
    if not LocalGunnerVision then return end
    if p then
        LocalGunnerVision.keepAlive(p)
    else LocalGunnerVision.clear() end
end
local function place(p, x, y, z)
    -- (the fractions kept, so the view glides; the square is looked up only when it changes)
    local moved = math.floor(x) ~= math.floor(p:getX()) or math.floor(y) ~= math.floor(p:getY())
    p:setX(x); p:setY(y); p:setZ(z)
    p:setLastX(x); p:setLastY(y); p:setLastZ(z)
    p:setNextX(x); p:setNextY(y)
    if moved then p:ensureOnTile() end
end
function Body.start(p)
    if Body.saved then return end
    Body.saved = { x = p:getX(), y = p:getY(), z = p:getZ(), ghost = p:isGhostMode(), invisible = p:isInvisible(),
        noclip = p:isNoClip(), god = p:isGodMod(), seeAll = p:canSeeAll(), model = getCore():isDisplayPlayerModel() }
    p:setGhostMode(true); p:setInvisible(true); p:setNoClip(true); p:setGodMod(true)
    pcall(function() p:setCanSeeAll(true) end)
    cameraVision(p)
    getCore():setDisplayPlayerModel(false)
    cameraGuardStart(p)
end
function Body.move(p, x, y) if Body.saved then place(p, x, y, 0) end end
function Body.stop(p)
    cameraGuardStop()
    pcall(cameraVision, nil)
    local s = Body.saved
    if not s then return end
    Body.saved = nil
    if p then
        pcall(function() place(p, s.x, s.y, s.z); p:ensureOnTile() end)
        pcall(function()
            p:setGhostMode(s.ghost); p:setInvisible(s.invisible); p:setNoClip(s.noclip); p:setGodMod(s.god)
        end)
        pcall(function() p:setCanSeeAll(s.seeAll == true) end)
    end
    pcall(function() getCore():setDisplayPlayerModel(s.model ~= false) end)
end
bodyHome = function()
    local s = Body.saved
    if s then return s.x, s.y, math.floor(s.z) end
end
-- (2026-10-25, the user: "the body is hit all the time in the seat") while the character is the
-- camera, blasts (Ops hurtPlayer) and fallout (RadiationBody) reach the body where it was left,
-- not the camera over the aim point
function S.GunnerBodyAt() return bodyHome() end
if SkyhammerRadiation and SkyhammerRadiation.body then
    SkyhammerRadiation.body.bodyPlace = function(c)
        if c ~= getSpecificPlayer(0) then return nil end
        local x, y, z = bodyHome()
        if not x then return nil end
        local cell = getCell()
        return x, y, z, cell and cell:getGridSquare(math.floor(x), math.floor(y), z)
    end
end

-- the thermal picture, through the search-mode channel
local Thermal = { saved = nil }
local function thermalOn()
    local sm = getSearchMode and getSearchMode()
    if not sm then return end
    if not Thermal.saved then Thermal.saved = { override = sm:isOverride(0), enabled = sm:isEnabled(0) } end
    sm:setOverride(0, true)
    sm:setEnabled(0, true)
    sm:getDarkness(0):setAll(THERMAL + (blackHot and 2 or 1))
end
local function thermalOff()
    local s = Thermal.saved
    if not s then return end
    Thermal.saved = nil
    pcall(function()
        local sm = getSearchMode()
        sm:getDarkness(0):setAll(0)
        sm:setEnabled(0, s.enabled == true)
        sm:setOverride(0, s.override == true)
    end)
end

-- the player's zoom levels, stepped (the game eases between them); every step undone after
local Zoom = { stepped = 0 }
local function zoomStep(dir)
    local core = getCore()
    if core:getNextZoom(0, dir) == core:getZoom(0) then return end
    core:doZoomScroll(0, dir)
    Zoom.stepped = Zoom.stepped + dir
end
-- The level the game is going to: getZoom is the picture's zoom while it eases, getNextZoom works
-- on the target level (0 steps = the target itself). (2026-10-25, the user: the weapons' views
-- felt jumbled; deciding by the eased picture stopped a weapon switch half way)
local function zoomTarget() return getCore():getNextZoom(0, 0) end
local function zoomTo(target)
    local core = getCore()
    for _ = 1, 12 do
        local z = zoomTarget()
        if math.abs(z - target) < 0.13 then return end
        local dir = target > z and 1 or -1
        local nxt = core:getNextZoom(0, dir)
        -- (stop on the level nearest the weapon's own)
        if nxt == z or math.abs(nxt - target) >= math.abs(z - target) then return end
        zoomStep(dir)
    end
end
local function zoomRestore()
    local core = getCore()
    for _ = 1, math.abs(Zoom.stepped) do
        pcall(function() core:doZoomScroll(0, Zoom.stepped > 0 and -1 or 1) end)
    end
    Zoom.stepped = 0
end

-- Viewpoint's 3D view is put on its isometric one for the seat (the body cam is the game's own
-- camera) and back afterwards. Skyhammer's Java part switches it straight (Viewpoint's own switch,
-- with its camera move in 0.1.7); without it, Viewpoint's cycle is stepped (isometric -> first ->
-- third), which goes through third person and so also turns on Viewpoint's saved third-person choice.
-- A switch asked while Viewpoint's camera is still moving is dropped: asked again a moment later.
local VP_STEP_MS = 200
local VP_SETTLE_MS = 2500   -- (a seat left while the camera still moves out: it lands isometric later)
local VP_BACK_MS = 5000
local function vpView() return Viewpoint and Viewpoint.View and Viewpoint.View.next and Viewpoint.View or nil end
local function vpDirect()
    local b = SkyhammerAircraft
    if not (b and b.viewKnown and b.view3D and b.viewSet) then return nil end
    local ok, known = pcall(b.viewKnown)
    return ok and known == true and b or nil
end
-- Viewpoint's 3D view on (true), its isometric view (false), nil = no Viewpoint
local function vp3D()
    local d = vpDirect()
    if d then local ok, on = pcall(d.view3D); if ok and type(on) == "boolean" then return on end end
    local v = vpView()
    if not v then return nil end
    local ok, n = pcall(v.next)
    if not ok then return nil end
    return n ~= "first"
end
-- one step towards the 3D view (true) or the isometric one (false)
local function vpStep(want3D)
    local d = vpDirect()
    if d then pcall(d.viewSet, want3D); return end
    local v = vpView()
    if v then pcall(v.cycle) end
end
local vpBack = nil       -- { at, settleMs, untilMs }: back to the 3D view
local function vpBackTick()
    local b = vpBack
    local now = S.now()
    local on = b and vp3D()
    -- a 3D view ends it once a switch still under way had time to land (one more step would be the
    -- isometric view again)
    if not b or on == nil or now > b.untilMs or (on and now >= b.settleMs) then
        Events.OnTick.Remove(vpBackTick); vpBack = nil; return
    end
    if on or now - b.at < VP_STEP_MS then return end
    b.at = now
    vpStep(true)
end

local glowOff        -- (below, with the infected's glow)
local function rvStart(screen, p)
    RV.active = true
    RV.t0 = S.now()
    if LocalGunnerViewLock then LocalGunnerViewLock.keepAlive(p) end
    Body.start(p)
    thermalOn()
    local on = vp3D()
    if on ~= nil then
        if vpBack then Events.OnTick.Remove(vpBackTick); vpBack = nil end
        RV.vpWas = on and "3d" or "isometric"
        RV.vpAt = 0
    end
end
local function rvStop()
    local wasActive = RV.active
    RV.active = false
    -- Restore physical state first, even if an optional renderer/bridge fails.
    Body.stop(getSpecificPlayer(0))
    if not wasActive then return end
    if LocalGunnerViewLock then pcall(function() LocalGunnerViewLock.clear() end) end
    pcall(thermalOff)
    pcall(glowOff)
    pcall(zoomRestore)
    if RV.vpWas == "3d" and vp3D() ~= nil then
        local now = S.now()
        vpBack = { at = 0, settleMs = now + VP_SETTLE_MS, untilMs = now + VP_BACK_MS }
        Events.OnTick.Add(vpBackTick)
    end
    RV.vpWas = nil
end
restoreCamera = rvStop

local RealScreen = ISUIElement:derive("SkyhammerGunnerRealView")
for k, v in pairs(Seat) do RealScreen[k] = v end
-- the game's zoom (larger = farther): the 40mm close, the 105 wide; the wheel steps its levels
RealScreen.ZOOM = { min = 0.25, max = 4, wheel = 0.25 }

function RealScreen:new(w, h)
    local o = ISUIElement.new(self, 0, 0, w, h)
    o.zooms = { gun25 = 1.5, gun = 1.75, he = 2.5 }
    o.weapon = "gun"
    o.zoom = 1.75
    return o
end
local function gameZoom()
    local ok, z = pcall(function() return getCore():getZoom(0) end)
    return (ok and tonumber(z)) or 1
end
-- the game's isometric projection on the ground floor
function RealScreen:toUI(x, y, height)
    local sx, sy = ISCoordConversion.ToScreen(x, y, height or 0)
    local z = gameZoom()
    return sx / z, sy / z
end
function RealScreen:toWorld(mx, my)
    local z = gameZoom()
    return ISCoordConversion.ToWorld(mx * z, my * z, 0)
end
-- Pick the highest exposed surface along this screen ray, converting X/Y again
-- at each candidate height. Ground X/Y reused at roof Z would miss by several tiles.
function RealScreen:aimPoint(mx,my,fresh)
    local gx,gy=self:toWorld(mx,my)
    local now=S.now()
    local cached=self.roofAim
    if not fresh and cached and now>=cached.at and now-cached.at<75
        and math.abs(cached.gx-gx)<.01 and math.abs(cached.gy-gy)<.01 then
        return cached.x,cached.y,cached.z
    end
    local x,y,z=gx,gy,0
    local rx,ry,level=self:roofOver(mx,my,0)
    if level then x,y,z=rx,ry,level end
    self.roofAim={x=x,y=y,z=z,gx=gx,gy=gy,at=now}
    return x,y,z
end
-- the highest exposed surface above floor `above` along this screen ray (nil: none). The aim
-- lands there, and the thermal hides the infected drawn under one (2026-10-25, the user: they
-- glowed behind buildings, where only the square right above them was looked at, and the
-- rounds hit the roof drawn over them)
function RealScreen:roofOver(mx,my,above)
    local cell=getCell()
    if not cell then return nil end
    local zoom=gameZoom()
    for level=31,above+1,-1 do
        local rx,ry=ISCoordConversion.ToWorld(mx*zoom,my*zoom,level)
        local sq=cell:getGridSquare(math.floor(rx),math.floor(ry),level)
        if S.GunnerSkySurface(sq) then return rx,ry,level end
    end
    return nil
end
-- along the screen's horizontal (a ground circle shows as a 2:1 ellipse)
function RealScreen:px(wx, wy, r)
    local ax = self:toUI(wx, wy)
    local bx = self:toUI(wx + r / math.sqrt(2), wy - r / math.sqrt(2))
    return math.abs(bx - ax)
end
function RealScreen:ring(cx, cy, r, c)
    local n = math.max(24, math.floor(r * 0.8))
    for k = 0, n - 1 do
        local a = k / n * math.pi * 2
        local x, y = cx + math.cos(a) * r, cy + math.sin(a) * r * 0.5
        self:drawRect(x - 2, y - 2, 4, 4, 0.5, 0, 0, 0)
        self:drawRect(x - 1, y - 1, 2, 2, 1, c[1], c[2], c[3])
    end
end
function RealScreen:applyZoom(z) zoomTo(z) end
function RealScreen:onMouseWheel(del)
    zoomStep(del > 0 and 1 or -1)
    self.zooms[self.weapon] = zoomTarget()
    return true
end
function RealScreen:applyPolarity() if RV.active then thermalOn() end end
-- SENSOR MOTION BEGIN
-- Exact damped-spring integration: equal behaviour at 30/45/60 FPS and no
-- ever-growing shake under rotary fire. Motion lives only in the current seat.
local SensorMotion={}
local function clamp(v,a,b)return math.max(a,math.min(b,v))end
function SensorMotion.new(now,x,y)
    return {at=now,born=now,x=x,y=y,rx=0,ry=0,dx=0,dy=0,shots=0}
end
local function spring(x,v,dt)
    local omega,damping=18,.72
    local decay=damping*omega
    local wd=omega*math.sqrt(1-damping*damping)
    local e=math.exp(-decay*dt)
    local c,si=math.cos(wd*dt),math.sin(wd*dt)
    return e*(x*c+(v+decay*x)*si/wd),e*(v*c-(decay*v+omega*omega*x)*si/wd)
end
function SensorMotion.shot(m,weapon)
    m.shots=m.shots+1
    local gain=weapon=="he" and 460 or weapon=="gun" and 175 or 38
    local side=m.shots%2==0 and 1 or -1
    m.dx=clamp(m.dx+gain*.22*side,-220,220)
    m.dy=clamp(m.dy-gain,-560,200)
end
function SensorMotion.step(m,now,x,y)
    if now<m.at then m.at=now;m.born=now;m.rx=0;m.ry=0;m.dx=0;m.dy=0 end
    local dt=(now-m.at)/1000;m.at=now
    m.rx,m.dx=spring(m.rx,m.dx,dt);m.ry,m.dy=spring(m.ry,m.dy,dt)
    local follow=1-math.exp(-dt/.10)
    m.x=m.x+(x-m.x)*follow;m.y=m.y+(y-m.y)*follow
    local t=(now-m.born)/1000
    -- A slow bank plus a smaller gimbal correction, in DISPLAY pixels. This
    -- stays perceptible at every zoom and drifts even without input or firing.
    -- Smooth entry, no initial one-tile jump, and no high-frequency idle jitter.
    local fade=math.min(1,t/2)
    fade=fade*fade*(3-2*fade)
    local bank=t*(math.pi*2/20)
    local swayX=(math.sin(bank)*36+math.sin(t*.83)*4.4)*fade
    local swayY=(math.cos(bank+.35)*20+math.sin(t*.67+.4)*2.4)*fade
    -- Bound recoil separately: clipping the combined signal would leave the
    -- idle camera parked at its limits during part of the orbit.
    return m.x,m.y,swayX+clamp(m.rx,-10,10),swayY+clamp(m.ry,-16,10)
end
-- SENSOR MOTION END
function RealScreen:onShot(weapon)
    local now=S.combatMs()
    self.sensorMotion=self.sensorMotion or SensorMotion.new(now,self.vx,self.vy)
    SensorMotion.shot(self.sensorMotion,weapon)
end
function RealScreen:centerView()
    local p = getSpecificPlayer(0)
    local now=S.combatMs()
    self.sensorMotion=self.sensorMotion or SensorMotion.new(now,self.vx,self.vy)
    local x,y,px,py=SensorMotion.step(self.sensorMotion,now,self.vx,self.vy)
    -- Convert sensor pixels through the SAME engine projection used for aiming.
    -- No displaced UI/world overlay, so roof selection and tracers stay registered.
    local zoom=gameZoom()
    local ax,ay=ISCoordConversion.ToWorld(0,0,0)
    local bx,by=ISCoordConversion.ToWorld(px*zoom,py*zoom,0)
    Body.move(p,x+(bx-ax),y+(by-ay))
end
RealScreen.clean = true
-- (nothing drawn over the world: the infected glow by themselves, glowInfected below)
function RealScreen:paintWorld() end

-- Body-shaped thermal mask, supplied by the actual animated model, not map icons.
-- Marker colours are decoded ONLY by our aim_outline_blit shader; ordinary aim
-- highlights keep the stock shader path. Cache visible targets at 10 Hz.
local outlined = {}
local heatNext=0
-- Whether a square is open to the sensor: nothing right above it and no roof drawn over it on the
-- screen ray (the aim's own, roofOver). Roofs hardly change, so each square is looked at once
-- every COVER_MS, not up to 62 floors a zombie ten times a second (2026-10-25, the user: the seat
-- got laggy, 29.7 -> 15.8 fps). The ray's world squares do not depend on the camera.
-- (2026-10-25, the user: "the infected inside buildings, not shown at all? it lags") in the seat an
-- infected in a roofed room is not drawn: the game then skips its model and updates it less
-- often (its doRender). Drawn again once out of the building, dead, or the seat left; the game
-- itself turns it back on when it reuses the body.
local hiddenIn={}
local function indoors(sq)
    local ok,r=pcall(function() return sq:getRoom()~=nil and sq:haveRoofFull() end)
    return ok and r==true
end
local function drawAgain(z) pcall(function() z:setDoRender(true) end) end
local COVER_MS,COVER_MAX=2000,4000
local cover,coverN={},0
-- Bound cold/expired roof checks as well as visible masks. Covered candidates do not
-- count toward HEAT_LIMIT, so a dense crowd behind roofs must drain over several passes.
-- Cached results remain free; an unexamined target stays hidden until checked.
local COVER_BUDGET=256
local coverRemaining=0
local function openToSensor(screen,sq,now)
    local x,y,z=sq:getX(),sq:getY(),sq:getZ()
    local k=x..","..y..","..z
    local c=cover[k]
    if c and now>=c.at and now-c.at<COVER_MS then return c.open end
    if coverRemaining<=0 then return false end
    coverRemaining=coverRemaining-1
    local open=S.GunnerOpenSky(sq) and not sq:HasSlopedRoof()
    if open then
        local ux,uy=screen:toUI(x+.5,y+.5,z)
        open=not screen:roofOver(ux,uy,z)
    end
    if not c then
        coverN=coverN+1
        if coverN>COVER_MAX then cover,coverN={},1 end
    end
    -- (each square's renewal staggered over a second, so they do not all fall due in one pass;
    -- world x, y are never negative, so % keeps to 0..999)
    cover[k]={open=open,at=now-(x*7+y*13)%1000}
    return open
end
local HEAT_LIMIT=128 -- animated masks are expensive; prioritize the sensor centre
local function glowInfected(screen)
    local now=S.now()
    if now>=heatNext then
        heatNext=now+100
        local nextSet,candidates,inside={},{},{}
        local cell=getCell()
        local list=cell and cell:getZombieList()
        if not list then return end
        for i=0,list:size()-1 do
            local z=list:get(i)
            if z and not z:isDead() then
                local sq=z:getSquare()
                if sq and indoors(sq) then
                    -- (noted at once: should this pass fail half way, glowOff still draws it again)
                    if not hiddenIn[z] then pcall(function() z:setDoRender(false) end); hiddenIn[z]=true end
                    inside[z]=true
                elseif sq and sq:isCanSee(0) then
                    local x,y=screen:toUI(z:getX(),z:getY(),z:getZ())
                    if x>=-48 and y>=-48 and x<=screen.width+48 and y<=screen.height+96 then
                        candidates[#candidates+1]={z=z,sq=sq,d=(x-screen.width*.5)^2+(y-screen.height*.5)^2}
                    end
                end
            end
        end
        for z in pairs(hiddenIn) do if not inside[z] then drawAgain(z) end end
        hiddenIn=inside
        table.sort(candidates,function(a,b)return a.d<b.d end)
        local count=0
        coverRemaining=COVER_BUDGET
        for _,v in ipairs(candidates) do
            if openToSensor(screen,v.sq,now) then
                nextSet[v.z]=S.IsFriendlyNPC and S.IsFriendlyNPC(v.z) and 2 or 1
                count=count+1
                if count>=HEAT_LIMIT then break end
            end
        end
        for z in pairs(outlined) do
            if not nextSet[z] then pcall(function()z:setOutlineHighlight(0,false)end) end
        end
        outlined=nextSet
    end
    for z,kind in pairs(outlined) do
        if not z:isDead() then
            z:setOutlineHighlight(0,true)
            if kind==2 then z:setOutlineHighlightCol(.45,.95,.55,1)
            else z:setOutlineHighlightCol(32/255,64/255,128/255,1) end
        else z:setOutlineHighlight(0,false);outlined[z]=nil end
    end
end

glowOff = function()
    for z in pairs(outlined) do pcall(function()z:setOutlineHighlight(0,false)end) end
    for z in pairs(hiddenIn) do drawAgain(z) end
    outlined={};hiddenIn={};heatNext=0;cover,coverN={},0
end
function RealScreen:onShow(p)
    self.sensorMotion=nil;self.roofAim=nil;self.heatFailed=false
    rvStart(self,p)
end
function RealScreen:onHide()
    self.sensorMotion=nil;self.roofAim=nil
    rvStop()
end
-- each frame: the thermal kept on, a save's return of the body undone, Viewpoint to isometric
function RealScreen:everyFrame(now)
    local p = getSpecificPlayer(0)
    if RV.active and LocalGunnerViewLock then LocalGunnerViewLock.keepAlive(p) end
    if RV.active and not Body.saved and p then Body.start(p) end
    cameraVision(RV.active and Body.saved and p or nil)
    thermalOn()
    local okHeat,errHeat=pcall(glowInfected,self)
    if not okHeat then
        -- (its error once a seat)
        if not self.heatFailed then self.heatFailed=true; S.log("gunner thermal failed: "..tostring(errHeat)) end
        -- Do not retain stale visible masks if a roof check fails. Retry at 10 Hz.
        glowOff();heatNext=now+100
    end
    self.zoom = gameZoom()
    if not RV.vpWas then return end
    local on = vp3D()
    if on == nil then return end
    if not on then
        -- (Viewpoint's isometric view brings back its own zoom when switched to: the weapon's
        -- level again, once, when the switch is done)
        if not RV.vpZoomed then RV.vpZoomed = true; self:applyZoom(self.zooms[self.weapon]) end
        return
    end
    RV.vpZoomed = false
    if now - (RV.vpAt or 0) >= VP_STEP_MS then RV.vpAt = now; vpStep(false) end
end
-- (a save: the body home and as it was for it; the next frame sends it back up)
function G.SaveBody()
    videoSafeEnd()
    if RV.active then Body.stop(getSpecificPlayer(0)) end
end

-- the seat's picture: kept between uses (the map's data loads once), remade if the screen size
-- changed; real = the borrowed real view (G.Enter decides once per seat)
local screens = {}
local current = nil
function G.makeScreen(real)
    local w, h = getCore():getScreenWidth(), getCore():getScreenHeight()
    local key = real and "real" or "map"
    local s = screens[key]
    if not s or s.width ~= w or s.height ~= h then
        if real then
            s = RealScreen:new(w, h)
            s:initialise()
        else
            s = MapScreen:new(w, h)
            s:initialise(); s:instantiate()
            s:loadMap()
        end
        screens[key] = s
    end
    current = s
    return s
end
function G.Screen() return state.active and current or nil end

-- Called only after Ops applies blast damage at the stored body's coordinates.
function S.GunnerBodyHit(p, damage)
    if p ~= getSpecificPlayer(0) or not damage or damage <= 0 then return end
    local x, y, z = bodyHome()
    local screen = G.Screen()
    if not x or not screen then return end
    local now = S.now()
    if not screen.hitAt or now - screen.hitAt > 1000 then alert(x, y, z) end
    screen.hitAt = now
end

-- ---------------------------------------------------------------- what ends it from outside
table.insert(S.Hooks.released, function(craft) if craft == "ac130" then G.Exit("over") end end)
Events.OnPlayerDeath.Add(function(p) if p == getSpecificPlayer(0) then G.Exit("dead") end end)
-- (the real picture's body cam has the character out flying the camera: every save finds it home
-- and as it was, and the next frame sends it back up; the seat goes on)
Events.OnSave.Add(function() if state.active then G.SaveBody() end end)
local function reset()
    videoSafeEnd()
    cameraGuardStop()
    cameraVision(nil)
    if RV.active then pcall(rvStop) end
    state.uiHidden = false
    state.active, state.stage, state.ui, state.introSortie = false, nil, nil, nil
    for k in pairs(screens) do screens[k] = nil end
    current = nil
    S.SetGunnerManned(false)
end
Events.OnGameStart.Add(function()
    reset()
    -- (the world view is drawn again whatever the last session left)
    pcall(function() getWorld():setDrawWorld(true) end)
end)
if Events.OnMainMenuEnter then Events.OnMainMenuEnter.Add(reset) end
