import io,json,pathlib,sys,importlib
HERE=pathlib.Path(__file__).resolve().parent
TESTS=HERE
sys.path.insert(0,str(TESTS))
base=importlib.import_module('sim_killqueue')

def world():
    L=base.world()
    L.execute('''
    CALLS, CREDIT, ERRORS = 0, 0, 0
    S.AirKills = function(n) CREDIT = CREDIT + n end
    S.log = function() ERRORS = ERRORS + 1 end
    function realZombie(mode)
        local z = { health=1, killed=false, corpse=false, attempts=0, mode=mode }
        function z:isDead() return self.health <= 0 end
        function z:getHealth() return self.health end
        function z:isOnKillDone() return self.killed end
        function z:isOnDeathDone() return self.corpse end
        function z:getModData() return {} end
        function z:Kill(p)
            self.attempts=self.attempts+1; CALLS=CALLS+1
            if self.mode=='noop' then return end
            self.health=0
            if self.mode=='alwaysFail' then error('persistent hook failure') end
            if self.mode=='weaponFail' and p~=nil then error('weapon/XP failure') end
            if self.mode=='onceFail' and self.attempts==1 then error('onKilled interruption') end
            self.killed=true; KILLS=KILLS+1
        end
        return z
    end
    function waitTicks(n) for i=1,n do tick() end end
    ''')
    return L
cases=[]
def test(name,script,expected):
    L=world();L.execute(script)
    values={k:L.eval(k) for k in expected}
    ok=values==expected;cases.append(dict(name=name,passed=ok,actual=values,expected=expected))
test('zero_health_incomplete_death_recovered','A=realZombie(); A.health=0; ACCEPTED=K.takeDown(A,SQ,2); waitTicks(30)',{'ACCEPTED':True,'A.killed':True,'ME.kills':1})
test('exception_after_health_zero_retried','A=realZombie("onceFail"); K.takeDown(A,SQ,2); waitTicks(30)',{'A.killed':True,'A.attempts':2,'ME.kills':1,'CREDIT':1})
test('weapon_dependent_failure_uses_safe_retry','A=realZombie("weaponFail"); K.takeDown(A,SQ,2); waitTicks(30)',{'A.killed':True,'A.attempts':2,'ME.kills':1})
test('noop_does_not_credit_false_kill','A=realZombie("noop"); K.takeDown(A,SQ,2); waitTicks(35)',{'ME.kills':0,'CREDIT':0,'A.attempts':3,'ERRORS':1})
test('persistent_failure_bounded_and_can_be_retargeted','A=realZombie("alwaysFail"); K.takeDown(A,SQ,2); waitTicks(200); A.mode=nil; ACCEPTED=K.takeDown(A,SQ,2); waitTicks(30)',{'A.killed':True,'A.attempts':4,'ACCEPTED':True,'ME.kills':1})
test('already_handled_death_not_rekilled','A=realZombie(); A.health=0; A.killed=true; ACCEPTED=K.takeDown(A,SQ,2); waitTicks(30)',{'ACCEPTED':False,'CALLS':0,'ME.kills':0})
test('corpse_not_rekilled','A=realZombie(); A.health=0; A.corpse=true; ACCEPTED=K.takeDown(A,SQ,2); waitTicks(30)',{'ACCEPTED':False,'CALLS':0})
test('pending_not_duplicated_when_four_second_marker_expires','A=realZombie(); K.takeDown(A,SQ,2); CLOCK=5000; ACCEPTED=K.takeDown(A,SQ,2); waitTicks(30)',{'ACCEPTED':False,'CALLS':1,'ME.kills':1})
test('failures_respect_frame_budget','for i=1,1000 do K.takeDown(realZombie("alwaysFail"),SQ,2) end; tick()',{'CALLS':30,'ME.kills':0})
test('healthy_kill_counted_once','A=realZombie(); K.takeDown(A,SQ,2); K.takeDown(A,SQ,2); waitTicks(40)',{'CALLS':1,'ME.kills':1,'CREDIT':1,'SPLATS':1})
test('reset_drops_pending_deaths','A=realZombie("onceFail"); K.takeDown(A,SQ,2); for _,fn in ipairs(HANDLERS.OnGameStart or {}) do pcall(fn) end; waitTicks(30)',{'CALLS':0})
test('online_incomplete_death_not_locally_recovered','isClient=function() return true end; A=realZombie(); A.health=0; ACCEPTED=K.takeDown(A,SQ,2); waitTicks(30)',{'ACCEPTED':False,'CALLS':0})
for r in cases:print(('PASS ' if r['passed'] else 'FAIL ')+r['name']+('' if r['passed'] else ' '+str(r['actual'])))
print(f'{sum(r["passed"] for r in cases)}/{len(cases)} passed')
sys.exit(0 if all(r['passed'] for r in cases) else 1)
