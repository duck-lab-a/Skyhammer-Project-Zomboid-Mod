import pathlib,sys
import sim_gunner_realview as rv
from lupa import lua51
R=pathlib.Path(__file__).resolve().parent
checks=0
def run(label,script):
    global checks
    L=rv.world();L.execute(script);checks+=1;print('PASS',label)

run('camera remains on original ground projection without render elevation hooks',r'''
ME.offsetY=167.5;ME.x=123.4;ME.y=87.6
G.Enter();frames(100)
for _,event in ipairs({'OnTick','OnPostRender','OnRenderTick','OnTickEvenPaused'})do
 fire(event);assert(ME.z==0 and ME.offsetY==167.5,event)
end
assert(#(HANDLERS.OnPostRender or {})==0 and #(HANDLERS.OnRenderTick or {})==0)
fire('OnSave');assert(ME.z==0 and ME.offsetY==167.5 and ME.x==123.4)
frames(100);G.Exit('player')
assert(ME.z==0 and ME.offsetY==167.5 and ME.x==123.4 and ME.y==87.6)
''')
SURFACES=r'''
ROOFS={}
function key3(x,y,z)return math.floor(x)..','..math.floor(y)..','..z end
local base=newSquare
function surface(x,y,z,sloped,room)
 local sq=base(x,y,z)
 function sq:getFloor()return not sloped and {} or nil end
 function sq:HasSlopedRoof()return sloped==true end
 function sq:hasRainBlockingTile()return false end
 function sq:getRoom()return room and {} or nil end
 function sq:isCanSee()return true end
 ROOFS[key3(x,y,z)]=sq;return sq
end
CELL.getGridSquare=function(_,x,y,z)return ROOFS[key3(x,y,z)]end
ISCoordConversion.ToWorld=function(sx,sy,z)return 100+sy/32+sx/64+z*3,100+sy/32-sx/64+z*3 end
'''
run('highest flat/sloped roof, holes and destroyed-room metadata',SURFACES+r'''
G.Enter();local s=G.Screen();local mx,my=100,100
local x2,y2=ISCoordConversion.ToWorld(mx*ZOOM,my*ZOOM,2)
local x4,y4=ISCoordConversion.ToWorld(mx*ZOOM,my*ZOOM,4)
local sq=surface(x2,y2,2,false,true)
local x,y,z=s:aimPoint(mx,my,true);assert(z==2 and x==x2 and y==y2)
surface(x4,y4,4,true,false);x,y,z=s:aimPoint(mx,my,true);assert(z==4)
ROOFS[key3(x4,y4,4)]=nil;x,y,z=s:aimPoint(mx,my,true);assert(z==2)
surface(x2,y2,3,false,false);assert(not S.GunnerSkySurface(sq))
ROOFS[key3(x2,y2,3)]=nil;assert(S.GunnerSkySurface(sq))
ROOFS={};x,y,z=s:aimPoint(mx,my,true);assert(z==0)
''')
run('thermal hides covered targets, clears mask and caps large hordes',SURFACES+r'''
G.Enter();local s=G.Screen()
s.toUI=function(_,x,y,z)return 960+(x-100)*2,540+(y-100)*2 end
function zed(x)
 local sq=surface(x,100,0,false,false)
 local z={x=x,y=100,z=0,outline=false}
 function z:getX()return self.x end;function z:getY()return self.y end;function z:getZ()return self.z end
 function z:isDead()return false end;function z:getSquare()return sq end
 function z:setOutlineHighlight(_,on)self.outline=on end;function z:setOutlineHighlightCol()end
 return z
end
for i=1,200 do ZOMBIES[i]=zed(100+i)end
surface(101,100,1,false,false)
CLOCK=500;s:everyFrame(CLOCK)
assert(not ZOMBIES[1].outline)
local count=0;for _,z in ipairs(ZOMBIES)do if z.outline then count=count+1 end end
assert(count==128)
ROOFS[key3(101,100,1)]=nil;CLOCK=2700;s:everyFrame(CLOCK);assert(ZOMBIES[1].outline)
G.Exit('player');for _,z in ipairs(ZOMBIES)do assert(not z.outline)end
''')
# (2026-10-25, the user: infected glowed on the thermal but rounds hit the roof above them) one
# standing in the open behind a building, drawn under its roof: the screen ray at its feet meets
# the roof first, so the rounds land there; it must not glow either (nothing is right above it)
run('thermal hides infected drawn under a roof, the same ray the aim uses',SURFACES+r'''
ISCoordConversion.ToScreen=function(x,y,z)z=z or 0;local a,b=x-z*3,y-z*3;return (a-b)*32,(a+b-200)*16 end
G.Enter();local s=G.Screen()
local zsq=surface(110.5,110.5,0,false,false)
local z={x=110.5,y=110.5,z=0,outline=false}
function z:getX()return self.x end;function z:getY()return self.y end;function z:getZ()return self.z end
function z:isDead()return false end;function z:getSquare()return zsq end
function z:setOutlineHighlight(_,on)self.outline=on end;function z:setOutlineHighlightCol()end
ZOMBIES[1]=z
assert(S.GunnerOpenSky(zsq),'nothing right above it')
surface(113.5,113.5,1,false,true)
local ux,uy=s:toUI(z.x,z.y,0)
local _,_,az=s:aimPoint(ux,uy,true);assert(az==1,'the aim at its feet lands on the roof')
CLOCK=500;s:everyFrame(CLOCK);assert(not z.outline,'drawn under the roof: no glow')
ROOFS[key3(113.5,113.5,1)]=nil
_,_,az=s:aimPoint(ux,uy,true);assert(az==0)
-- (a square's cover is kept COVER_MS = 2 s: roofs hardly change)
CLOCK=2700;s:everyFrame(CLOCK);assert(z.outline,'in the open: it glows')
-- (the user: "not only the thermal you enter with B, the seat's view too") the same in both polarities
G.TogglePolarity();s:applyPolarity();assert(G.BlackHot())
surface(113.5,113.5,1,false,true)
CLOCK=4900;s:everyFrame(CLOCK);assert(not z.outline,'black-hot: drawn under the roof, no glow')
ROOFS[key3(113.5,113.5,1)]=nil
CLOCK=7100;s:everyFrame(CLOCK);assert(z.outline,'black-hot: in the open, it glows')
G.TogglePolarity()
''')
# (2026-10-25, the user: "the seat got laggy"; 29.7 -> 15.8 fps with the roof ray) a square's cover
# is looked up once and kept a while, not 62 floors a zombie ten times a second
run('thermal cover is cached per square, not rescanned every glow pass',SURFACES+r'''
ISCoordConversion.ToScreen=function(x,y,z)z=z or 0;local a,b=x-z*3,y-z*3;return (a-b)*32,(a+b-200)*16 end
G.Enter();local s=G.Screen()
local calls=0;local get=CELL.getGridSquare
CELL.getGridSquare=function(...)calls=calls+1;return get(...)end
for i=1,150 do
 local sq=surface(100.5+(i%15),100.5+math.floor(i/15),0,false,false)
 local z={x=sq:getX()+.5,y=sq:getY()+.5,z=0}
 function z:getX()return self.x end;function z:getY()return self.y end;function z:getZ()return self.z end
 function z:isDead()return false end;function z:getSquare()return sq end
 function z:setOutlineHighlight()end;function z:setOutlineHighlightCol()end
 ZOMBIES[i]=z
end
CLOCK=500;s:everyFrame(CLOCK);local first=calls
calls=0;CLOCK=650;s:everyFrame(CLOCK);local second=calls
assert(first>0,'the first pass looks')
assert(second<first/10,'the next pass reuses it: '..first..' then '..second)
''')
# (2026-10-25, the user: "can the infected inside buildings not show at all? it lags") in the seat
# an infected in a roofed room is not drawn (the game then also updates it less often); out of the
# building, or the seat left, it is drawn again
run('infected inside buildings are not drawn while seated',SURFACES+r'''
G.Enter();local s=G.Screen()
s.toUI=function(_,x,y,z)return 960+(x-100)*2,540+(y-100)*2 end
local inside=surface(101,100,0,false,true);function inside:haveRoofFull()return true end
local ruin=surface(102,100,0,false,true);function ruin:haveRoofFull()return false end
local street=surface(103,100,0,false,false)
local function zed(sq)
 local z={x=sq:getX()+.5,y=sq:getY()+.5,z=0,sq=sq,drawn=true}
 function z:getX()return self.x end;function z:getY()return self.y end;function z:getZ()return self.z end
 function z:isDead()return false end;function z:getSquare()return self.sq end
 function z:setOutlineHighlight()end;function z:setOutlineHighlightCol()end
 function z:setDoRender(on)self.drawn=on end;function z:getDoRender()return self.drawn end
 return z
end
local a,b,c=zed(inside),zed(ruin),zed(street)
ZOMBIES[1],ZOMBIES[2],ZOMBIES[3]=a,b,c
CLOCK=500;s:everyFrame(CLOCK)
assert(a.drawn==false,'in a roofed room: not drawn')
assert(b.drawn==true,'its roof gone: drawn')
assert(c.drawn==true,'outdoors: drawn')
a.sq=street;CLOCK=650;s:everyFrame(CLOCK)
assert(a.drawn==true,'out of the building: drawn again')
a.sq=inside;CLOCK=800;s:everyFrame(CLOCK);assert(a.drawn==false)
G.Exit('player')
assert(a.drawn==true,'the seat left: drawn again')
''')
run('25/40/105 tracers and impacts retain roof height',SURFACES+r'''
G.Enter();surface(105,105,2,false,false)
PHASE.gun25='ON_STATION';AMMO.gun25=600
local trace,impact={},{}
S.AddGunnerTracer=function(w,x,y,z,ms,key) trace[w]={x=x,y=y,z=z};return key end
S.GunnerImpactAudio=function(w,x,y,z)impact[w]={x=x,y=y,z=z};return true end
for _,w in ipairs({'gun25','gun','he'})do assert(S.GunnerFire(w,105.2,105.2,2))end
run_until(2400)
assert(trace.gun25 and trace.gun25.z==2 and not impact.gun25,'the 25mm lands silently')
for _,w in ipairs({'gun','he'})do
 assert(trace[w] and impact[w],w)
 assert(trace[w].z==2 and impact[w].z==2,w)
 assert(trace[w].x==impact[w].x and trace[w].y==impact[w].y,w)
end
''')
print(f'{checks}/{checks} passed')
