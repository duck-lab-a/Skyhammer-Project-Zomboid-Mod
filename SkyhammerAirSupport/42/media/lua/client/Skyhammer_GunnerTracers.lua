-- Sensor projectiles: continuous flight, with impact confirmed by the real damage/audio job.
require "Skyhammer_Core"
local S=Skyhammer
local rounds,flashes={},{}
local serial=0
local LIMIT,FLASH_LIMIT=48,24
local glow
local profiles={
    gun25={dx=.38,dy=.53,head=2.3,tail=60,life=80,bloom=8},
    gun={dx=.55,dy=.49,head=3.7,tail=92,life=170,bloom=21},
    he={dx=.28,dy=.72,head=2.6,tail=24,life=210,bloom=35,visibleMs=420},
}
function S.ClearGunnerTracers() rounds={};flashes={} end
local function prune(now)
    for i=#rounds,1,-1 do
        local f=rounds[i]
        -- A cancelled sortie must never create a phantom explosion. Retain a short grace
        -- period for the OnTick impact job, but never draw a projectile parked on the ground.
        if now<f.born or now>f.at+1000 then table.remove(rounds,i) end
    end
    for i=#flashes,1,-1 do
        if now<flashes[i].at or now>=flashes[i].at+flashes[i].life then table.remove(flashes,i) end
    end
end
function S.AddGunnerTracer(kind,x,y,z,flightMs,key)
    if not profiles[kind] or flightMs<=0 or not S.GunnerManned() then return end
    local p=getSpecificPlayer(0);if not p or p:isDead()then return end
    local now=S.combatMs();prune(now)
    serial=serial+1;key=key or ("seat-v7-"..serial)
    if #rounds>=LIMIT then table.remove(rounds,1)end
    rounds[#rounds+1]={key=key,kind=kind,x=x,y=y,z=z,born=now,at=now+flightMs}
    return key
end
function S.GunnerTracerImpact(key)
    if not key then return end
    local now=S.combatMs()
    for i=#rounds,1,-1 do
        local f=rounds[i]
        if f.key==key then
            table.remove(rounds,i)
            if S.GunnerManned() and now>=f.born then
                if #flashes>=FLASH_LIMIT then table.remove(flashes,1) end
                flashes[#flashes+1]={x=f.x,y=f.y,z=f.z,kind=f.kind,at=now,life=profiles[f.kind].life}
            end
            return
        end
    end
end
local function dot(s,x,y,d,a,c)
    if d<=1.5 then s:drawRect(x-d/2,y-d/2,d,d,a,c,c,c);return end
    if glow==nil then glow=getTexture("media/ui/circle.png") or false end
    if glow then
        -- Neutral white alpha texture: thermal polarity stays monochrome. Concentric
        -- low-opacity layers soften the edge without a new texture or shader dependency.
        for i=1,3 do
            local size=d*(1-(i-1)*.27)
            s:drawTextureScaled(glow,x-size/2,y-size/2,size,size,a*(i==3 and .78 or .20),c,c,c)
        end
    else
        for i=-3,3 do
            local v=i/3.5;local width=d*math.sqrt(1-v*v)
            s:drawRect(x-width/2,y+d*v/2-d/14,width,math.max(.65,d/7),a,c,c,c)
        end
    end
end
local function streak(s,tx,ty,hx,hy,width,alpha,c)
    local dx,dy=hx-tx,hy-ty
    s:drawLine(nil,tx,ty,hx,hy,width+2,alpha*.10,c,c,c)
    for i=1,5 do
        local a,b=(i-1)/5,i/5
        s:drawLine(nil,tx+dx*a,ty+dy*a,tx+dx*b,ty+dy*b,
            math.max(.65,width*(.2+.8*b)),alpha*(.12+.88*b*b),c,c,c)
    end
end
local function project(s,x,y,z)
    local a,b=s:toUI(x,y,z)
    if a~=a or b~=b or math.abs(a)>1e6 or math.abs(b)>1e6 then return end
    return a,b
end
-- Perspective acceleration instead of exponential ease-out. The last part of the flight
-- covers MORE distance per millisecond, so a shell cannot hover at its landing point.
local function progress(t) return t/(1+.65*(1-t)) end
function S.DrawGunnerTracers(s,blackHot)
    local now=S.combatMs();prune(now)
    local u=math.max(.65,math.min(2,s.height/1080))
    local c=blackHot and .025 or .985
    for _,f in ipairs(rounds)do
        local q=profiles[f.kind]
        -- Ballistic travel still takes 2.2 s. Only its final, fast descent is visible
        -- in the sensor field, rather than dragging a glowing ball across it for 2.2 s.
        local duration=math.min(f.at-f.born,q.visibleMs or (f.at-f.born))
        local t=(now-(f.at-duration))/duration
        if t>=0 and t<1 then
            local ex,ey=project(s,f.x,f.y,f.z)
            if ex then
                local q=profiles[f.kind]
                local dx,dy=s.width*q.dx,-s.height*q.dy
                local p=f.kind=="he" and t or progress(t)
                local hx,hy=ex-dx*(1-p),ey-dy*(1-p)
                local distance=math.sqrt(dx*dx+dy*dy)
                local length=q.tail*u*(.45+.55*(1-t))
                local head=q.head*u*(f.kind=="he" and 1 or (1-.55*t))
                streak(s,hx-dx*length/distance,hy-dy*length/distance,hx,hy,math.max(.8,head*.48),.9,c)
                dot(s,hx,hy,head*3.0,.16,c)
                dot(s,hx,hy,head*1.5,.98,c)
            end
        end
    end
    -- Only the actual impact callback creates this brief thermal glare. Existing world
    -- explosion sprites supply the dirt/smoke and the seat's impact sound (SH_Seat_Impact*) the sound.
    for _,f in ipairs(flashes)do
        local x,y=project(s,f.x,f.y,f.z)
        if x then
            local t=(now-f.at)/f.life
            local size=profiles[f.kind].bloom*u
            local fade=(1-t)^2
            dot(s,x,y,size*(1+1.8*t),fade*.30,c)
            dot(s,x,y,size*.42*(1-t),fade*.95,c)
            if f.kind=="gun" then
                for i=1,4 do
                    local angle=i*2.39996
                    local radius=size*(.18+.65*t)
                    local dx,dy=math.cos(angle)*radius,math.sin(angle)*radius*.62
                    s:drawLine(nil,x+dx*.65,y+dy*.65,x+dx,y+dy,.8*u,fade*.38,c,c,c)
                end
            end
        end
    end
end
Events.OnGameStart.Add(S.ClearGunnerTracers)
if Events.OnMainMenuEnter then Events.OnMainMenuEnter.Add(S.ClearGunnerTracers)end
Events.OnPlayerDeath.Add(function(p)if p==getSpecificPlayer(0)then S.ClearGunnerTracers()end end)
