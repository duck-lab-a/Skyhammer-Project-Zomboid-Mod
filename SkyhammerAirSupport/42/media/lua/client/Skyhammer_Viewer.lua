-- Skyhammer Air Support - the terminal's 3D look-around. A click on a tab's aircraft picture
-- opens its model over the sensor map, on an inspection-display background (SH_Viewer_Bg.png),
-- turned through 36 pre-rendered views 10 degrees apart
-- (media/ui/SH_Spin_<NAME>.png, 4 columns x 9 rows, frame i at column i % 4, row i // 4; made by
-- source/terminal_art/make_turntables.py and package_turntables.py from the same CC-BY models as
-- the game meshes). It turns by itself until dragged; drag or the wheel turns it. The X, a second
-- click on the picture, aiming a mark or folding the terminal closes it; a tab change shows the
-- new tab's aircraft, or closes it when that tab has none. The sheet loads on the first look.
-- Add-ons may add their own sheet (same layout) with SkyhammerViewer.Register(key, path).
require "ISUI/ISPanel"
require "ISUI/ISButton"

SkyhammerViewer = SkyhammerViewer or {}
local V = SkyhammerViewer
local COLS, ROWS, FRAMES, STEP = 4, 9, 36, 10
local SPIN = 60          -- degrees a second while it turns by itself
local DRAG = 0.5         -- degrees per pixel dragged (a full turn in 720 px)
local sheets = {
    ac130 = "media/ui/SH_Spin_AC130.png",
    apache = "media/ui/SH_Spin_Apache.png",
    a10 = "media/ui/SH_Spin_A10.png",
    b2 = "media/ui/SH_Spin_B2.png",
    f22 = "media/ui/SH_Spin_F22.png",
}
local cached = {}
-- (2026-11-23, the user's pick of four mock-ups: the inspection display) the background, stretched
-- over the panel: slate blue-grey, lighter in the middle, a floor grid and the turntable's ring
-- (source/terminal_art/make_viewer_bg.py); the corner brackets are drawn here, crisp at any size
local BG_PATH = "media/ui/SH_Viewer_Bg.png"
local bgTex = nil

function V.Register(key, path)
    if type(key) ~= "string" or key == "" or type(path) ~= "string" then return end
    sheets[key] = path
    cached[key] = nil
end
function V.Has(key) return key ~= nil and sheets[key] ~= nil end
local function sheet(key)
    if not V.Has(key) then return nil end
    if cached[key] == nil then
        local ok, t = pcall(getTexture, sheets[key])
        cached[key] = (ok and t) or false
    end
    return cached[key] or nil
end
-- whether a texture has finished loading (the game loads them in the background: the size is
-- known at once, but drawn before it is ready it shows the error texture for a frame or two)
local function ready(t)
    if not t then return false end
    local ok, r = pcall(function() return t:isReady() end)
    return not ok or r == true
end
V.ready = ready

-- the terminal's colours (its add-on themes included), or its base ones
local BASE = {
    bg = { 16 / 255, 20 / 255, 22 / 255 }, panel = { 23 / 255, 28 / 255, 30 / 255 },
    line = { 75 / 255, 83 / 255, 85 / 255 }, text = { 226 / 255, 229 / 255, 226 / 255 },
    dim = { 162 / 255, 170 / 255, 171 / 255 }, accent = { 220 / 255, 182 / 255, 94 / 255 },
}
local function colours()
    local C = SkyhammerTerminal and SkyhammerTerminal.C
    return C and C.accent and C or BASE
end
local function fontH(font) return getTextManager():getFontHeight(font or UIFont.Small) end
local function textW(s, font) return getTextManager():MeasureStringX(font or UIFont.Small, s) end
-- the view nearest an angle: 0 .. FRAMES - 1 for any angle, negative ones included (no %: the
-- game's Lua keeps the dividend's sign)
local function frameOf(angle)
    local f = math.floor(angle / STEP + 0.5)
    return f - math.floor(f / FRAMES) * FRAMES
end
V.frameOf = frameOf

-- ---------------------------------------------------------------- the panel over the map
local P = ISPanel:derive("SkyhammerViewerPanel")
V.Panel = P

function P:new(x, y, w, h, key)
    local o = ISPanel:new(x, y, w, h)
    setmetatable(o, self); self.__index = self
    o.key = key
    o.angle = 0
    o.spin = true
    o.background = false; o.border = false
    o.moveWithMouse = false
    return o
end

function P:createChildren()
    local s = math.max(24, fontH() + 8)
    local C = colours()
    local b = ISButton:new(self.width - s - 8, 8, s, s, "X", self, P.onCloseButton)
    b:initialise(); b:instantiate()
    b.backgroundColor = { r = C.panel[1], g = C.panel[2], b = C.panel[3], a = 1 }
    b.backgroundColorMouseOver = { r = 0.13, g = 0.15, b = 0.16, a = 1 }
    b.borderColor = { r = C.line[1], g = C.line[2], b = C.line[3], a = 1 }
    b.textColor = { r = C.text[1], g = C.text[2], b = C.text[3], a = 1 }
    self:addChild(b)
    self.closeBtn = b
end
function P:onCloseButton() if self.term then V.Close(self.term) end end

-- the map's place, kept after the terminal is resized
function P:fit(m)
    if self.x == m.x and self.y == m.y and self.width == m.w and self.height == m.h then return end
    self:setX(m.x); self:setY(m.y); self:setWidth(m.w); self:setHeight(m.h)
    if self.closeBtn then self.closeBtn:setX(m.w - self.closeBtn.width - 8) end
end

function P:prerender()
    local C = colours()
    self:drawRect(0, 0, self.width, self.height, 1, C.panel[1], C.panel[2], C.panel[3])
    if bgTex == nil then
        local ok, t = pcall(getTexture, BG_PATH)
        bgTex = (ok and t) or false
    end
    if ready(bgTex) then self:drawTextureScaled(bgTex, 0, 0, self.width, self.height, 1, 1, 1, 1) end
end

-- the four corner brackets in the accent colour, inside the border
local function brackets(self, col)
    local w, h, i, arm, t = self.width, self.height, 4, 16, 2
    local r, g, b = col[1], col[2], col[3]
    self:drawRect(i, i, arm, t, 0.9, r, g, b); self:drawRect(i, i, t, arm, 0.9, r, g, b)
    self:drawRect(w - i - arm, i, arm, t, 0.9, r, g, b); self:drawRect(w - i - t, i, t, arm, 0.9, r, g, b)
    self:drawRect(i, h - i - t, arm, t, 0.9, r, g, b); self:drawRect(i, h - i - arm, t, arm, 0.9, r, g, b)
    self:drawRect(w - i - arm, h - i - t, arm, t, 0.9, r, g, b); self:drawRect(w - i - t, h - i - arm, t, arm, 0.9, r, g, b)
end

function P:render()
    local C = colours()
    local now = getTimestampMs()
    local dt = self.last and math.max(0, math.min(0.1, (now - self.last) / 1000)) or 0
    self.last = now
    if self.spin and not self.drag then self.angle = self.angle + dt * SPIN end
    local pad, fh, mh = 12, fontH(), fontH(UIFont.Medium)
    local top, bottom = pad + mh + 8, pad + fh + 8
    local bw, bh = self.width - pad * 2, self.height - top - bottom
    local tex = sheet(self.key)
    if not ready(tex) then tex = nil end
    local iw, ih = tex and tex:getWidth() or 0, tex and tex:getHeight() or 0
    if bw > 0 and bh > 0 and iw > 0 and ih > 0 then
        local cw, ch = math.floor(iw / COLS), math.floor(ih / ROWS)
        local scale = math.min(bw / cw, bh / ch, 2)
        local dw, dh = math.floor(cw * scale), math.floor(ch * scale)
        local f = frameOf(self.angle)
        local col = f - math.floor(f / COLS) * COLS
        self:drawSubTexture(tex, col * cw, math.floor(f / COLS) * ch, cw, ch,
            pad + math.floor((bw - dw) / 2), top + math.floor((bh - dh) / 2), dw, dh, 1, 1, 1, 1)
    elseif bw > 0 and bh > 0 and SkyhammerAircraftDiagram then
        -- (the sheet still loading, or it did not load: the tab's still picture, larger)
        SkyhammerAircraftDiagram.draw(self, self.key, pad, top, bw, bh, C.dim, 0.92)
    end
    local title = getText("IGUI_SH_Craft_" .. self.key) .. " / " .. getText("IGUI_SH_Big_" .. self.key)
    self:drawText(title, pad, pad, C.text[1], C.text[2], C.text[3], 1, UIFont.Medium)
    local hint = getText("IGUI_SH_ViewerHint")
    if hint ~= "IGUI_SH_ViewerHint" then
        self:drawText(hint, pad, self.height - pad - fh, C.dim[1], C.dim[2], C.dim[3], 1, UIFont.Small)
    end
    self:drawRectBorder(0, 0, self.width, self.height, 1, C.line[1], C.line[2], C.line[3])
    brackets(self, C.accent)
end

function P:onMouseDown(x, y)
    self.drag = true
    self.spin = false
    self:setCapture(true)
    return true
end
function P:onMouseMove(dx, dy)
    if self.drag then self.angle = self.angle + dx * DRAG end
end
P.onMouseMoveOutside = P.onMouseMove
function P:stopDrag()
    if not self.drag then return end
    self.drag = nil
    self:setCapture(false)
end
function P:onMouseUp(x, y) self:stopDrag(); return true end
function P:onMouseUpOutside(x, y) self:stopDrag() end
function P:onMouseWheel(del)
    self.spin = false
    self.angle = frameOf(self.angle) * STEP + (del > 0 and STEP or -STEP)
    return true
end

-- ---------------------------------------------------------------- the terminal's side
local function showMap(term, on)
    if term.map then pcall(function() term.map:setVisible(on) end) end
end

-- (folded: the terminal hid the map with everything else and shows it again as it unfolds; shown
-- here, it stayed live beside the folded icon, where a click marked the map's ground)
function V.Close(term)
    local v = term and term.viewer
    if not v then return end
    v:stopDrag()
    term.viewer = nil
    term:removeChild(v)
    if not term.folded then showMap(term, true) end
end

local function open(term, key)
    local m = term.A and term.A.map
    if not m or not V.Has(key) then return end
    local v = P:new(m.x, m.y, m.w, m.h, key)
    v.term = term
    v:initialise(); v:instantiate()
    term:addChild(v)
    term.viewer = v
    showMap(term, false)
end

-- a click on the picture: open it, or close it when it is already open
function V.Toggle(term)
    if term.viewer then V.Close(term); return end
    if Skyhammer and Skyhammer.IsAiming and Skyhammer.IsAiming() then return end
    open(term, term.key)
end

-- every frame, from the terminal's prerender (folded included)
function V.Sync(term)
    local v = term.viewer
    if not v then return end
    local aiming = Skyhammer and Skyhammer.IsAiming and Skyhammer.IsAiming()
    if term.folded or aiming or not V.Has(term.key) then V.Close(term); return end
    if v.key ~= term.key then v.key = term.key end
    if term.A and term.A.map then v:fit(term.A.map) end
    -- (a resize builds the sensor map again, shown)
    if term.map and term.map:isVisible() then showMap(term, false) end
end

-- the picture's box, from drawControl after it drew the picture: it can be clicked when the tab
-- has views, and shows so (a "3D" tag in its corner; an outline under the pointer and while open)
function V.ArtDrawn(term, key, x, y, w, h)
    if not V.Has(key) then term.viewerArt = nil; return end
    term.viewerArt = { x = x, y = y, w = w, h = h }
    local C = colours()
    local over = V.ArtHit(term, term:getMouseX(), term:getMouseY())
    local shown = term.viewer ~= nil
    if over or shown then
        term:drawRectBorder(x - 3, y - 3, w + 6, h + 6, over and 0.95 or 0.55, C.accent[1], C.accent[2], C.accent[3])
    end
    local fh = fontH()
    local tw = textW("3D")
    local tagW, tagH = tw + 10, fh + 2
    local tx, ty = x + w - tagW, y + h - tagH
    local edge = (over or shown) and C.accent or C.line
    local ink = (over or shown) and C.accent or C.dim
    term:drawRect(tx, ty, tagW, tagH, 0.85, C.bg[1], C.bg[2], C.bg[3])
    term:drawRectBorder(tx, ty, tagW, tagH, 1, edge[1], edge[2], edge[3])
    term:drawText("3D", tx + 5, ty + 1, ink[1], ink[2], ink[3], 1, UIFont.Small)
end

-- whether (x, y) (the terminal's own coordinates) is on the clickable picture
function V.ArtHit(term, x, y)
    local a = term.viewerArt
    if not a or term.folded or not V.Has(term.key) then return false end
    return x >= a.x and y >= a.y and x <= a.x + a.w and y <= a.y + a.h
end
