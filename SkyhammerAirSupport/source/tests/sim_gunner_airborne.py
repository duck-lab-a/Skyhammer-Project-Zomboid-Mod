"""Continuous camera motion, evaluated against the real gunner Lua and UI harness."""
import io, os
import sim_gunner_realview as rv
from lupa import lua51

source = io.open(os.path.join(rv.LUA, 'client', 'Skyhammer_Gunner.lua'), encoding='utf-8').read()
motion = source[source.index('-- SENSOR MOTION BEGIN'):source.index('-- SENSOR MOTION END')]
count = 0

def check(label, script):
    global count
    L = lua51.LuaRuntime()
    L.execute(motion + '\nMOTION=SensorMotion\n' + script)
    count += 1
    print('PASS', label)

check('idle flight stays visible, continuous and bounded for ten minutes', r'''
local m=MOTION.new(0,0,0)
local minX,maxX,minY,maxY=0,0,0,0
local previousX,previousY=0,0
local twoSeconds={}
for t=0,600000,20 do
 local x,y,px,py=MOTION.step(m,t,0,0)
 assert(x==0 and y==0 and m.shots==0)
 assert(math.abs(px)<=40.4 and math.abs(py)<=22.4)
 assert(math.abs(px-previousX)<.6 and math.abs(py-previousY)<.6,'abrupt frame movement')
 previousX,previousY=px,py
 minX=math.min(minX,px);maxX=math.max(maxX,px)
 minY=math.min(minY,py);maxY=math.max(maxY,py)
 if t%2000==0 then
  local p=twoSeconds[#twoSeconds]
  if p and t>4000 then assert((px-p[1])^2+(py-p[2])^2>1,'idle camera stalled for two seconds') end
  twoSeconds[#twoSeconds+1]={px,py}
 end
end
assert(maxX-minX>70 and maxY-minY>38,'drift was imperceptibly small')
''')

check('entry eases in, paused time freezes, clock reset clears movement', r'''
local m=MOTION.new(500,10,20)
local _,_,px,py=MOTION.step(m,500,10,20);assert(px==0 and py==0)
local _,_,x,y=MOTION.step(m,510,10,20);assert(math.abs(x)<.01 and math.abs(y)<.01)
MOTION.shot(m,'he');MOTION.step(m,650,10,20)
local a,b,c,d=MOTION.step(m,650,10,20)
local aa,bb,cc,dd=MOTION.step(m,650,10,20)
assert(a==aa and b==bb and c==cc and d==dd)
local _,_,rx,ry=MOTION.step(m,100,10,20)
assert(rx==0 and ry==0 and m.dx==0 and m.dy==0)
''')

check('frame rate does not change camera follow or drift', r'''
local a,b=MOTION.new(0,0,0),MOTION.new(0,0,0)
MOTION.shot(a,'he');MOTION.shot(b,'he')
for t=10,12000,10 do MOTION.step(a,t,5,8) end
for t=80,12000,80 do MOTION.step(b,t,5,8) end
local ax,ay,apx,apy=MOTION.step(a,12000,5,8)
local bx,by,bpx,bpy=MOTION.step(b,12000,5,8)
assert(math.abs(ax-bx)<1e-8 and math.abs(ay-by)<1e-8)
assert(math.abs(apx-bpx)<1e-8 and math.abs(apy-bpy)<1e-8)
''')

check('all calibres preserve recoil strength, settle, and stay bounded under bursts', r'''
local peaks={}
for _,w in ipairs({'gun25','gun','he'})do
 local m=MOTION.new(0,0,0);MOTION.shot(m,w);local peak=0
 for t=0,1500,2 do MOTION.step(m,t,0,0);peak=math.max(peak,math.abs(m.ry)) end
 assert(math.abs(m.ry)<.001 and math.abs(m.dy)<.001)
 peaks[w]=peak
 local m=MOTION.new(0,0,0)
 for t=0,60000,10 do
  if t%70==0 then MOTION.shot(m,w)end
  local _,_,x,y=MOTION.step(m,t,0,0)
  assert(math.abs(x)<=50.4 and y>=-38.4 and y<=32.4)
 end
end
assert(peaks.gun25<peaks.gun and peaks.gun<peaks.he)
''')

for vp in (False, True):
    L = rv.world(viewpoint=vp)
    L.execute(r'''
local homeX,homeY=ME.x,ME.y
local homeView=VIEW
assert(G.Enter());frames(1000)
local s=G.Screen()
-- Include the engine's integer screen-coordinate conversion and a moving
-- camera origin, rather than an artificial fixed-origin overlay.
ISCoordConversion.ToWorld=function(sx,sy,z)
 sx=sx<0 and math.ceil(sx) or math.floor(sx)
 sy=sy<0 and math.ceil(sy) or math.floor(sy)
 return ME.x+sy/32+sx/64,ME.y+sy/32-sx/64
end
ISCoordConversion.ToScreen=function(x,y,z)
 return ((x-ME.x)-(y-ME.y))*32,((x-ME.x)+(y-ME.y))*16
end
local reference
for _,zoom in ipairs({.5,1,2.5})do
 ZOOM=zoom;CLOCK=2000;s.sensorMotion=nil;s:centerView()
 assert(ME.x==s.vx and ME.y==s.vy and ME.z==0)
 CLOCK=7000;s:centerView()
 local dx=((ME.x-s.vx)-(ME.y-s.vy))*32/zoom
 local dy=((ME.x-s.vx)+(ME.y-s.vy))*16/zoom
 assert(math.abs(dx)>=29.9,'world camera did not move while idle')
 if reference then assert(math.abs(dx-reference[1])<2 and math.abs(dy-reference[2])<2)end
 reference={dx,dy}
 local x,y=s:toWorld(300,200);local px,py=s:toUI(x,y,0)
 assert(math.abs(px-300)<.00001 and math.abs(py-200)<.00001,'aim/world mismatch')
 local oldX,oldY=ME.x,ME.y;s:centerView()
 assert(ME.x==oldX and ME.y==oldY,'unchanged clock moved the body')
 assert(ME.z==0 and ME.offsetY==192,'camera elevation workaround returned')
end
G.Exit('player');frames(1500)
assert(ME.x==homeX and ME.y==homeY and ME.z==0)
assert(s.sensorMotion==nil and not ME.flags.ghost and not ME.flags.god)
assert(VIEW==homeView,'Viewpoint camera not restored')
assert(G.Enter());s=G.Screen();s:centerView()
assert(ME.x==s.vx and ME.y==s.vy,'re-entry retained drift')
G.Exit('player')
''')
    count += 1
    print('PASS', 'Viewpoint' if vp else 'Vanilla', 'world-camera drift, zoom/aim registration, exit and re-entry')

assert not any(v in source for v in ('roofFrame', 'CAMERA_Z', 'setOffsetY'))
print(f'{count}/{count} passed')
