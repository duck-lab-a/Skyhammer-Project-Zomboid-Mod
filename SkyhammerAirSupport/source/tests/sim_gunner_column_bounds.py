"""Same roof results with fewer empty-level Lua/engine calls; no world caches."""
import sim_gunner_realview as rv

L=rv.world()
L.execute(r'''
CALLS=0;XY=0;TOP=2;ROOF={};CHUNK={}
function CHUNK:getMaxLevel()return TOP end
SQ={}
function SQ:getX()XY=XY+1;return 100 end
function SQ:getY()XY=XY+1;return 100 end
function SQ:getZ()return BASE or 0 end
function SQ:getChunk()return CHUNK end
CELL.getGridSquare=function(_,x,y,z)
 CALLS=CALLS+1;assert(x==100 and y==100)
 local kind=ROOF[z];if not kind then return nil end
 return {getFloor=function()if kind==1 then return {} end end,
  HasSlopedRoof=function()return kind==2 end,
  hasRainBlockingTile=function()return kind==3 end}
end
function reference(sq)
 if not sq then return false end
 for z=sq:getZ()+1,31 do
  if S.GunnerSurface(CELL:getGridSquare(sq:getX(),sq:getY(),z)) then return false end
 end
 return true
end
function compare()
 local before=reference(SQ)
 assert(S.GunnerOpenSky(SQ)==before,'roof result changed')
end
-- Every possible upper level, three surface types, and negative floors.
for base=-4,31 do
 BASE=base
 for top=base,31 do
  TOP=top;ROOF={};compare()
  for z=base+1,top do
   for kind=1,3 do ROOF={[z]=kind};compare() end
  end
 end
end
BASE=0;TOP=0;ROOF={};assert(S.GunnerOpenSky(SQ))
TOP=3;ROOF={[3]=1};assert(not S.GunnerOpenSky(SQ),'new roof must be noticed immediately')
ROOF={};assert(S.GunnerOpenSky(SQ),'demolished roof must open sky')
-- APIs absent or returning unusable data retain the complete old scan.
local getter=SQ.getChunk
for _,mode in ipairs({'absent','throw','nil','noMax','badMax','nan','low','high','fraction'})do
 SQ.getChunk=getter;TOP=3;ROOF={[3]=1}
 if mode=='absent' then SQ.getChunk=nil
 elseif mode=='throw' then SQ.getChunk=function()error('unavailable')end
 elseif mode=='nil' then SQ.getChunk=function()return nil end
 elseif mode=='noMax' then SQ.getChunk=function()return {} end
 elseif mode=='badMax' then TOP='3'
 elseif mode=='nan' then TOP=0/0
 elseif mode=='low' then TOP=-1
 elseif mode=='high' then TOP=100
 elseif mode=='fraction' then TOP=2.5 end
 compare()
end
SQ.getChunk=getter;BASE=0;TOP=2;ROOF={}
CALLS=0;XY=0
for i=1,128 do assert(reference(SQ)) end
BEFORE_CALLS=CALLS;BEFORE_XY=XY
CALLS=0;XY=0
for i=1,128 do assert(S.GunnerOpenSky(SQ)) end
AFTER_CALLS=CALLS;AFTER_XY=XY
assert(AFTER_CALLS==256,'empty upper levels still scanned: '..AFTER_CALLS)
assert(AFTER_XY==256,'coordinates fetched more than once per column')
assert(S.GunnerOpenSky(nil)==false)
''')
print('PASS exhaustive roof/floor bounds, dynamic roofs and fallback behavior')
print('128 open columns, highest level 2: square lookups',L.globals().BEFORE_CALLS,'->',L.globals().AFTER_CALLS,
      '; XY getters',L.globals().BEFORE_XY,'->',L.globals().AFTER_XY)
