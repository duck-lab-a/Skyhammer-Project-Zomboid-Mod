import io,pathlib
from lupa import lua51
SOURCE=pathlib.Path(r'C:\Users\user\Zomboid\mods\SkyhammerAirSupport\42\media\lua\shared\Skyhammer_Craters.lua')
BOOT=r'''
CLOCK,COST,LOOKUPS,CHANGES,RECALCS=0,0,0,0,0
FLOORS={};FAIL=false
function getTimestampMs()return CLOCK end
function ZombRand()return 0 end
IsoFlagType={water='water',canBeRemoved='remove',vegitation='veg'}
IsoObjectType={tree='tree'}
luautils={stringStarts=function(s,p)return s:sub(1,#p)==p end}
function sprite(name)return {getName=function()return name end,getProperties=function()return {has=function()return false end}end}end
function getSprite(n)return sprite(n)end
local cell={}
function cell:getGridSquare(x,y,z)
 LOOKUPS=LOOKUPS+1
 local key=x..','..y..','..z
 local sq=FLOORS[key]
 if not sq then
  local floor={spr=sprite('grass')}
  function floor:getSprite()return self.spr end
  function floor:setSprite(s)if FAIL then error('test failure')end;self.spr=s;CHANGES=CHANGES+1;CLOCK=CLOCK+COST end
  function floor:RemoveAttachedAnims()end
  function floor:transmitUpdatedSpriteToClients()end
  sq={getFloor=function()return floor end,getRoom=function()return nil end,
      getObjects=function()return {size=function()return 0 end}end,
      RecalcProperties=function()RECALCS=RECALCS+1 end}
  FLOORS[key]=sq
 end
 return sq
end
getCell=function()return cell end
'''
tests=[
('100 overlapping requests are coalesced',"for i=1,100 do C.add(.5,.5,0,0,0)end;for i=1,30 do C.tick()end;assert(LOOKUPS==1 and CHANGES==1 and RECALCS==1)"),
('already burnt clean square does not invalidate again',"C.add(.5,.5,0,0,0);C.tick();C.add(.5,.5,0,0,0);C.tick();assert(CHANGES==1 and RECALCS==1)"),
('time budget stops after an expensive atomic operation',"COST=3;C.add(.5,.5,0,2,2);C.tick();assert(CHANGES==1);C.tick();assert(CHANGES==2)"),
('at most four cheap tiles processed per tick',"C.add(.5,.5,0,2,2);C.tick();assert(CHANGES==4)"),
('failure can be retried and reset clears pending work',"FAIL=true;C.add(.5,.5,0,0,0);C.tick();FAIL=false;C.add(.5,.5,0,0,0);C.tick();assert(CHANGES==1);C.add(4.5,4.5,0,0,0);C.reset();C.tick();assert(CHANGES==1);C.add(4.5,4.5,0,0,0);C.tick();assert(CHANGES==2)")]
for name,script in tests:
 L=lua51.LuaRuntime();L.execute(BOOT);L.execute(io.open(SOURCE,encoding='utf-8').read());L.execute('C=SkyhammerCraters;'+script);print('PASS',name)
print(f'{len(tests)}/{len(tests)} passed')
