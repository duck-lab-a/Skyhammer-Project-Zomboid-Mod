import ast, pathlib
import sim_gunner_realview as rv

# The seat's thermal outlines: a roof over the infected hides it, a failing roof check hides every
# outline (no stale masks) and is retried at 10 Hz, not every frame; its error is logged once a
# seat. (2026-10-25, the user: no measurement logs in the release: no per-seat summary, no version)
tree=ast.parse(pathlib.Path(rv.HERE,'sim_gunner_roofs.py').read_text(encoding='utf-8'))
surfaces=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='SURFACES' for t in n.targets))
L=rv.world()
L.execute(surfaces+r'''
LOGS={};S.log=function(s)LOGS[#LOGS+1]=s end
G.Enter();local s=G.Screen()
s.toUI=function()return 960,540 end
local sq=surface(101,100,0,false,false)
local z={outline=false}
function z:getX()return 101 end;function z:getY()return 100 end;function z:getZ()return 0 end
function z:isDead()return false end;function z:getSquare()return sq end
function z:setOutlineHighlight(_,on)self.outline=on end;function z:setOutlineHighlightCol()end
ZOMBIES[1]=z
CLOCK=500;s:everyFrame(CLOCK)
assert(z.outline,'open sky: outlined')
-- (a square's cover is kept up to 2 s, Skyhammer_Gunner COVER_MS: the steps below wait it out)
surface(101,100,1,false,false);CLOCK=2700;s:everyFrame(CLOCK)
assert(not z.outline,'a roof over it: hidden')
ROOFS[key3(101,100,1)]=nil;CLOCK=4900;s:everyFrame(CLOCK)
assert(z.outline,'the roof gone: outlined again')
CALLS=0
S.GunnerOpenSky=function()CALLS=CALLS+1;error('intentional roof-check failure')end
CLOCK=7100;s:everyFrame(CLOCK)
assert(not z.outline and CALLS==1,'stale thermal mask retained after error')
for i=1,20 do s:everyFrame(CLOCK)end
assert(CALLS==1,'failed roof scan retried every frame')
CLOCK=7200;s:everyFrame(CLOCK);assert(CALLS==2,'retried after 100 ms')
G.Exit('player')
local failures=0
for _,line in ipairs(LOGS)do
 if line:find('gunner thermal failed:')then failures=failures+1 end
 assert(not line:find('gunner thermal:') and not line:find('sensor v2'),'measurement log in the release: '..line)
end
assert(failures==1,'the error logged once a seat, got '..failures)
''')
print('PASS roof filtering, fail-closed masks, 10 Hz retries, one error line, no measurement logs')
print('1/1 passed')
