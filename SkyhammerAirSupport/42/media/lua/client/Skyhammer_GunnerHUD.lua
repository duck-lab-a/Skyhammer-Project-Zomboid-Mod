-- Local MW4-reference HUD: amber sensor rails, open centre and a compact weapon strip.
require "Skyhammer_Core"
require "Skyhammer_Feed"
local S, D = Skyhammer, SkyhammerFeed.draw
SkyhammerGunnerHUD = {}
local H = SkyhammerGunnerHUD
local GOLD, DIM, WHITE = {0.86,0.70,0.40}, {0.53,0.46,0.32}, {0.98,0.91,0.73}
local RED, GREEN = {0.98,0.43,0.30}, {0.66,0.83,0.55}
local weapons, names = {"gun25","gun","he"}, {he="105MM",gun="40MM",gun25="25MM"}
local keys = {he="3",gun="2",gun25="1"}
local function line(s,x,y,x2,y2,a,c)
    c=c or GOLD
    if x~=x2 and y~=y2 then s:drawLine(nil,x,y,x2,y2,1,a,c[1],c[2],c[3])
    else D.hudLine(s,x,y,x2,y2,a,c) end
end
local function label(s,t,x,y,c,font) D.hudText(s,t,math.floor(x),math.floor(y),font or UIFont.Small,c or GOLD) end
local function centre(s,t,x,y,c,font) label(s,t,x-D.textW(t,font)/2,y,c,font) end
function H.Reticle(s,x,y,col,now)
    local u=math.max(.75,math.min(1.5,s.height/900))
    local kick=s.kickMs and math.max(0,1-(now-s.kickMs)/180) or 0
    local size=(s.weapon=="he" and 100 or s.weapon=="gun" and 84 or 72)*u*(1+.10*kick)
    local c=col==D.WHITE and GOLD or col
    -- Open brackets and a diamond sensor spot, matching the supplied gunship reference.
    for _,side in ipairs({-1,1})do
        local bx=x+side*size
        line(s,bx,y-size*.66,bx,y+size*.66,.88,c)
        line(s,bx,y-size*.66,bx-side*5*u,y-size*.66,.88,c)
        line(s,bx,y+size*.66,bx-side*5*u,y+size*.66,.88,c)
    end
    local d=5*u
    line(s,x,y-d,x+d,y,.98,c);line(s,x+d,y,x,y+d,.98,c)
    line(s,x,y+d,x-d,y,.98,c);line(s,x-d,y,x,y-d,.98,c)
    line(s,x,y-size-13*u,x,y-size-3*u,.68,c)
    line(s,x,y+size+3*u,x,y+size+13*u,.68,c)

end
function H.Draw(s,blackHot,wx,wy,loaded,hit,switchName,polName)
    local w,h=s.width,s.height
    local fh=getTextManager():getFontHeight(UIFont.Small)
    local mh=getTextManager():getFontHeight(UIFont.Medium)
    local margin=math.max(18,math.floor(h*.035))
    local cx,cy=w*.5,h*.49
    local rail=math.min(w*.12,150*h/900)
    local half=math.min(h*.18,155)
    local top=cy-half
    -- Bars match the reference silhouette; only real game information is labelled.
    for _,side in ipairs({-1,1})do
        local x=cx+side*rail
        line(s,x,top,x,cy+half,.75)
        line(s,x,top,x-side*7,top,.8)
        line(s,x,cy+half,x-side*7,cy+half,.8)
        for i=-8,8 do
            local y=cy+i*half/8
            local len=(i%4==0 and 8 or 3)
            line(s,x,y,x-side*len,y,i%4==0 and .75 or .38)
        end
        local inner=x+side*14
        line(s,inner,cy-3,inner,cy+3,.9)
        line(s,inner-side*3,cy-3,inner+side*3,cy-3,.9)
        line(s,inner-side*3,cy+3,inner+side*3,cy+3,.9)
        line(s,cx+side*(rail+25),cy,w*(side<0 and .10 or .90),cy,.36)
    end
    line(s,cx,top-28,cx,top-12,.75)
    centre(s,names[s.weapon] or "25MM",cx,cy+half+16,WHITE)
    local reload=S.GunnerReload(s.weapon)
    local ready=math.max(0,math.min(1,1-reload/math.max(1,S.GunnerReloadTotal(s.weapon))))
    if (S.Ammo(s.weapon) or 0)<=0 then ready=0 end
    -- Slim mirrored readiness bars: backed by the real weapon cooldown.
    for _,side in ipairs({-1,1})do
        local bx=cx+side*(rail+34)
        line(s,bx,cy-half*.58,bx,cy+half*.58,.24)
        s:drawRect(bx-1,cy+half*.58-half*1.16*ready,2,half*1.16*ready,.7,GOLD[1],GOLD[2],GOLD[3])
    end
    if reload>0 and s.weapon=="he" then centre(s,getText("IGUI_SH_HUD_ReloadSeconds",string.format("%.1f",reload/1000)),cx,cy+half+fh+22,GOLD) end
    -- Restrained corner framing; no opaque panel across the sensor picture.
    line(s,margin,margin,margin+205,margin,.65)
    label(s,getText("IGUI_SH_HUD_FireControl"),margin,margin+8,GOLD)
    label(s,getText(blackHot and "IGUI_SH_HUD_BlackHot" or "IGUI_SH_HUD_WhiteHot"),margin,margin+fh+13,DIM)
    local _,left=S.Clock("ac130")
    local title=getText("IGUI_SH_HUD_Gunship")
    local titleW=D.textW(title,UIFont.Medium)+16
    s:drawRect(w-margin-titleW,margin+2,titleW,mh+5,.86,GOLD[1],GOLD[2],GOLD[3])
    label(s,title,w-margin-D.textW(title,UIFont.Medium)-8,margin+5,{.10,.09,.065},UIFont.Medium)
    local station=getText("IGUI_SH_Gun_Station",left~="" and left or "--")
    label(s,station,w-margin-D.textW(station),margin+mh+12,GOLD)
    line(s,w-margin-170,margin+mh+fh+21,w-margin,margin+mh+fh+21,.55)
    local status=getText((S.Ammo(s.weapon) or 0)<=0 and "IGUI_SH_HUD_Empty" or reload>0 and "IGUI_SH_HUD_Reloading" or "IGUI_SH_HUD_Armed")
    label(s,"AC-130  /  "..status,w-margin-D.textW("AC-130  /  "..status),margin+mh+fh+26,DIM)
    -- Reference-style corner rails; leave the centre free for targets.
    for _,side in ipairs({-1,1})do
        local x1=side<0 and margin or w-margin
        local x2=side<0 and w*.26 or w*.74
        line(s,x1,h-margin-fh-5,x2,h-margin-fh-5,.38)
        line(s,x1,margin-3,x2,margin-3,.22)
    end
    if hit then centre(s,getText("IGUI_SH_Gun_Hit"),cx,margin+8,RED,UIFont.Medium) end
    -- Match MW4's horizontal ammunition strip, while keeping PZ's actual keys and counts.
    local gap=8
    local card=math.min(145,math.floor((w-2*margin-2*gap)/3))
    local strip=card*3+gap*2
    local x0=math.floor((w-strip)/2)
    local ch=fh*2+20
    local y0=h-margin-fh-18-ch
    for i,weapon in ipairs(weapons)do
        local x=x0+(i-1)*(card+gap)
        local selected=weapon==s.weapon
        local c=selected and WHITE or DIM
        s:drawRect(x,y0,card,ch,selected and .35 or .20,.08,.07,.045)
        line(s,x,y0,x+card,y0,selected and .9 or .3,selected and GOLD or DIM)
        if selected then s:drawRect(x,y0,3,ch,.85,GOLD[1],GOLD[2],GOLD[3]) end
        label(s,keys[weapon].."  "..names[weapon],x+11,y0+5,c)
        -- Calibre silhouette, sized to stay clear of the label and live ammo counter.
        local gx,gy=x+card-30,y0+8
        local n=weapon=="gun25" and 3 or weapon=="gun" and 2 or 1
        for k=0,n-1 do
            local yy=gy+k*3
            s:drawRect(gx,yy,16-k*2,2,selected and .8 or .35,c[1],c[2],c[3])
            line(s,gx+16-k*2,yy,gx+20-k*2,yy+1,.7,c)
        end
        local ammo=S.Ammo(weapon)or 0
        local count=tostring(ammo)
        label(s,count,x+card-10-D.textW(count,UIFont.Medium),y0+fh+7,c,UIFont.Medium)
        local left=S.GunnerReload(weapon)
        local full=math.max(1,S.GunnerReloadTotal(weapon))
        local ready=ammo>0 and left<=0
        local st=getText(ammo<=0 and "IGUI_SH_HUD_Empty" or ready and "IGUI_SH_HUD_Ready" or "IGUI_SH_HUD_ReloadShort")
        label(s,st,x+11,y0+fh+10,ammo<=0 and RED or selected and (ready and GREEN or GOLD) or DIM)
        local fill=ammo>0 and math.max(0,math.min(1,1-left/full))or 0
        for j=0,9 do
            local bw=(card-20)/10-2
            s:drawRect(x+10+j*(bw+2),y0+ch-4,bw,2,j/10<fill and .7 or .15,c[1],c[2],c[3])
        end
    end
    local info=getText("IGUI_SH_HUD_Grid",string.format("%d",math.floor(wx)),string.format("%d",math.floor(wy)),string.format("%d",s.aimZ or 0))
    local infoY=w<1100 and y0-fh-12 or y0+ch-fh
    label(s,info,margin,infoY,loaded and GOLD or RED)
    local z=getText("IGUI_SH_HUD_Zoom",string.format("%.2f",s.zoom or 1))
    label(s,z,w-margin-D.textW(z),infoY,GOLD)
    local help=getText("IGUI_SH_HUD_Controls",switchName,polName)
    if D.textW(help)>w-2*margin then help=getText("IGUI_SH_HUD_ControlsShort",polName) end
    centre(s,help,cx,h-margin-fh,DIM)
end
