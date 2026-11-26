"""Camera targets are rejected only during real-view ownership; body blast alerts survive."""
import sys
import sim_gunner_realview as real

def world():
    L=real.world()
    L.execute(r'''
    next=nil
    function fire(name, ...) for _,fn in ipairs(HANDLERS[name] or {}) do fn(...) end end
    Events.OnZombieUpdate={
      Add=function(fn) HANDLERS.OnZombieUpdate=HANDLERS.OnZombieUpdate or {};table.insert(HANDLERS.OnZombieUpdate,fn) end,
      Remove=function(fn) for i=#(HANDLERS.OnZombieUpdate or {}),1,-1 do if HANDLERS.OnZombieUpdate[i]==fn then table.remove(HANDLERS.OnZombieUpdate,i) end end end}
    function enemy(target,friendly)
      local z={target=target,clears=0,cancels=0,states=0,friendly=friendly}
      function z:getTarget() return self.target end
      function z:setTarget(t) self.target=t;self.clears=self.clears+1 end
      function z:isDead() return false end
      function z:setTargetSeenTime(t) self.seen=t end
      function z:getPathFindBehavior2() return {cancel=function() z.cancels=z.cancels+1 end} end
      function z:setPath2(v) self.path=v end
      function z:setDefaultState() self.states=self.states+1 end
      function z:setVariable() end
      function z:getX() return 100 end;function z:getY() return 100 end;function z:getZ() return 0 end
      return z
    end
    S.IsFriendlyNPC=function(z) return z.friendly==true end
    HP=100
    function ME:getBodyDamage() return {
      getOverallBodyHealth=function() return HP end,
      ReduceGeneralHealth=function(_,d) HP=HP-d end} end
    ''')
    return L

def entry_and_exit():
    L=world()
    L.execute('z=enemy(ME);other={};z2=enemy(other);friend=enemy(ME,true);ZOMBIES={z,z2,friend};G.Enter()')
    assert L.eval('z:getTarget()==nil and z.cancels==1 and z.states==1'), 'entry must clear pre-existing camera target'
    assert L.eval('z2:getTarget()==other and friend:getTarget()==ME'), 'other targets/friends preserved'
    assert L.eval('#HANDLERS.OnZombieUpdate')==1
    L.execute('z.target=ME;fire("OnZombieUpdate",z)')
    assert L.eval('z:getTarget()==nil'), 'reacquisition blocked'
    L.execute('G.Exit("player");z.target=ME;fire("OnZombieUpdate",z)')
    assert L.eval('z:getTarget()==ME and #HANDLERS.OnZombieUpdate==0'), 'normal targeting restored'
    assert L.eval('ME.flags.ghost==false and ME.flags.god==false'), 'original flags restored'

def lifecycle():
    L=world();L.execute('G.Enter();G.SaveBody()')
    assert L.eval('#HANDLERS.OnZombieUpdate')==0
    L.execute('G.Screen():everyFrame(CLOCK)')
    assert L.eval('#HANDLERS.OnZombieUpdate')==1
    L.execute('G.Exit("error");G.Enter();G.Exit("player");G.Enter()')
    assert L.eval('#HANDLERS.OnZombieUpdate')==1, 'no duplicate listeners'
    L.execute('fire("OnMainMenuEnter")')
    assert L.eval('#HANDLERS.OnZombieUpdate')==0

def body_damage():
    L=world();L.execute('OPTVALS.protectPlayer=false;PLAYED={};G.Enter();ME.x=130;ME.y=130')
    L.execute('S.Kit.hurtPlayer(130,130,0,{{2,100}},{10})')
    assert L.eval('HP==100 and G.Screen().hitAt==nil'), 'camera-area blast is not a body hit'
    L.execute('S.Kit.hurtPlayer(100,100,0,{{2,100}},{10})')
    assert L.eval('HP==90 and G.Screen().hitAt~=nil'), 'actual body blast must alert'
    assert L.eval('PLAYED[#PLAYED]=="SH_Gunner_Alert"')
    L.execute('before=#PLAYED;S.Kit.hurtPlayer(100,100,0,{{2,100}},{10})')
    assert L.eval('#PLAYED==before'), 'alert sound rate-limited'

def camera_noise_and_protection():
    L=world();L.execute('G.Enter();frames(300);HP=80;frames(300)')
    assert L.eval('G.Screen().hitAt==nil'), 'arbitrary camera health drop must not warn'
    L=world();L.execute('OPTVALS.protectPlayer=true;G.Enter();S.Kit.hurtPlayer(100,100,0,{{2,100}},{10})')
    assert L.eval('HP==100 and G.Screen().hitAt==nil'), 'player protection retained'
    L=world();L.execute('OPTVALS.protectPlayer=false;G.Enter();G.Exit("player");S.Kit.hurtPlayer(100,100,0,{{2,100}},{10})')
    assert L.eval('HP==90'), 'ground damage retained'

def map_view():
    L=world();L.execute('''
    G.RealViewAvailable=function() return false end
    function SkyhammerFeed:instantiate()
      self.mapAPI={centerOn=function()end,setZoom=function()end,
        uiToWorldX=function(_,x,y)return 100 end,uiToWorldY=function(_,x,y)return 100 end}
    end
    SkyhammerFeed.loadMap=function()end
    SkyhammerFeed.thermalStyle=function()end
    G.Enter()
    ''')
    assert L.eval('#(HANDLERS.OnZombieUpdate or {})')==0, 'no camera guard in map fallback'
    # Existing map-mode HP polling remains enabled.
    L.execute('G.Screen():step();HP=80;G.Screen():step()')
    assert L.eval('G.Screen().hitAt~=nil'), 'map mode still warns on health loss'

def cleanup_failures():
    injections=[
        'G.Screen().removeFromUIManager=function()error("UI removal failed")end',
        'G.Screen().hide=function()error("UI hide failed")end',
        'S.StopGunnerShotAudio=function()error("audio stop failed")end',
        'LocalGunnerViewLock={clear=function()error("view lock failed")end}',
        'LocalGunnerVision={clear=function()error("vision bridge failed")end}',
    ]
    for injection in injections:
        L=world();L.execute('G.Enter();ME.x=140;ME.y=150;'+injection+';G.Exit("player")')
        assert L.eval('not G.Active() and #HANDLERS.OnZombieUpdate==0 and ME.x==100 and ME.y==100 and ME.flags.god==false and ME.blocked==false'), injection

def entry_failure():
    for injection in [
        'getSearchMode=function()error("sensor unavailable")end',
        'G.makeScreen=function()error("screen allocation failed")end',
        'G.makeIntro=function()error("video allocation failed")end',
    ]:
        L=world();L.execute(injection+';entered=G.Enter()')
        assert L.eval('entered==false and not G.Active() and ME.flags.god==false and ME.flags.ghost==false and ME.blocked==false and #(HANDLERS.OnZombieUpdate or {})==0'), injection

def entry_video_protects_the_body():
    # (2026-10-31, the user) the video hides the screen and holds the body still, so nothing may hurt it,
    # and god mode must not outlive it: a save keeps the flag, and the camera saves the body's own value
    def video():
        L=world();L.execute("""
        FRAMES=0
        G.makeIntro=function() return {show=function() end,hide=function() end,render=G.IntroFrame} end
        assert(G.Enter())""")
        return L
    L=video()
    assert L.eval('G.Stage()=="intro" and ME.flags.god==true'), 'safe during the video'
    L.execute('G.SaveBody()')
    assert L.eval('ME.flags.god==false'), 'a save finds the flag as it was'
    L.execute('G.IntroFrame()')
    assert L.eval('ME.flags.god==true'), 'and the next frame is safe again'
    L.execute('G.IntroDone()')
    assert L.eval('G.Stage()=="seat" and ME.flags.god==true'), 'the camera takes over'
    L.execute('G.Exit("player")')
    assert L.eval('ME.flags.god==false'), 'the body leaves as it was'
    L=video();L.execute('G.Exit("player")')
    assert L.eval('ME.flags.god==false'), 'leaving during the video'
    L=video();L.execute('G.Exit("player");G.IntroFrame()')
    assert L.eval('ME.flags.god==false'), 'a late frame of a closed video'
    L=world();L.execute("""
    ME.flags.god=true
    G.makeIntro=function() return {show=function() end,hide=function() end} end
    assert(G.Enter());G.Exit("player")""")
    assert L.eval('ME.flags.god==true'), 'a god-mode player stays one'
    L=video();L.execute('fire("OnMainMenuEnter")')
    assert L.eval('ME.flags.god==false'), 'to the main menu during the video'
    L=world();L.execute("""
    G.RealViewAvailable=function() return false end
    G.makeIntro=function() return {show=function() end,hide=function() end} end
    assert(G.Enter())""")
    assert L.eval('ME.flags.god==false'), 'the map view stays as it was'

def repeated_sessions():
    L=world();L.execute('''
    ME.flags={ghost=true,invisible=false,noclip=true,god=true};ME.seeAll=true;MODEL=false
    for i=1,100 do
        G.Enter();assert(#HANDLERS.OnZombieUpdate==1)
        ME.x=140;ME.y=150;G.SaveBody()
        assert(ME.x==100 and ME.y==100 and #HANDLERS.OnZombieUpdate==0)
        G.Screen():everyFrame(CLOCK);assert(#HANDLERS.OnZombieUpdate==1)
        G.Exit('player');assert(#HANDLERS.OnZombieUpdate==0)
    end
    ''')
    assert L.eval('ME.flags.ghost and not ME.flags.invisible and ME.flags.noclip and ME.flags.god and ME.seeAll and MODEL==false and ME.blocked==false')

def no_repeated_scan():
    L=world();L.execute('''
    scans=0;oldList=CELL.getZombieList
    CELL.getZombieList=function(...)scans=scans+1;return oldList(...)end
    z=enemy(ME);G.Enter();assert(scans==1)
    for i=1,20000 do z.target=ME;fire('OnZombieUpdate',z);assert(z.target==nil)end
    ''')
    assert L.eval('scans==1 and z.clears==20000 and z.cancels==20000 and z.states==20000')

tests=[entry_and_exit,lifecycle,body_damage,camera_noise_and_protection,map_view,
       cleanup_failures,entry_failure,entry_video_protects_the_body,repeated_sessions,no_repeated_scan]
failed=[]
for test in tests:
    try:test();print('PASS',test.__name__)
    except Exception as e:failed.append(test.__name__);print('FAIL',test.__name__,str(e)[:250])
print(f'{len(tests)-len(failed)}/{len(tests)} passed')
sys.exit(bool(failed))
