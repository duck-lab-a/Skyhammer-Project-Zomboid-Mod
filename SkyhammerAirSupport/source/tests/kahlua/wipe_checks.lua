-- (2026-11-18, bug report on the Vanilla Edition, ~190 mod server: every call "sortie 1", aircraft
-- never arriving.) Online, Skyhammer keeps this player's aircraft, killstreak ledger and quest
-- progress in the character's mod data, which the server never gets. Whenever anything on the
-- server sends the character's mod data (player:transmitModData(), common in server mods), the
-- game's ObjectModDataPacket wipes the client's table and loads the server's copy. These checks
-- wipe it the same way and expect Skyhammer's state to still be there.
local S = Skyhammer
S.log = function(s) LOG[#LOG + 1] = s end
local fails, names = 0, {}
local function check(ok, name) if not ok then fails = fails + 1; names[#names + 1] = name end end
local function fresh(name) ME = newPlayer(name); ONLINE = true end

-- an aircraft on its way survives the wipe
fresh("a")
check(S.Call("ac130") == true, "first call")
serverSends({})
check(S.Sortie("ac130") == 1, "sortie kept after the wipe")
check(S.Store().craft.ac130.phase == "INBOUND", "still inbound after the wipe")
check(S.Store().craft.ac130.arriveAtC ~= nil, "arrival time kept")
check(ME:getModData().SkyhammerAirSupport ~= nil, "put back in the mod data")

-- a second call while inbound is busy, not a new sortie 1
fresh("b")
S.Call("ac130"); serverSends({})
local ok, why = S.Call("ac130")
check(ok == false and why == "BUSY", "second AC-130 call while inbound: BUSY (" .. tostring(why) .. ")")
S.Call("a10"); serverSends({})
ok, why = S.Call("a10")
check(ok == false and S.Sortie("a10") == 1, "A-10 not called twice")

-- an old copy on the server does not win over the live state
fresh("c")
local OLD = { v2 = { craft = { ac130 = { phase = "READY", sortie = 0 } }, ammo = {} } }
S.Call("ac130"); serverSends({ SkyhammerAirSupport = OLD })
check(S.Sortie("ac130") == 1, "our sortie, not the server's old copy")
check(S.Store().craft.ac130.phase == "INBOUND", "still inbound with an old server copy")

-- the server's other keys are left alone
fresh("d")
S.Call("ac130"); serverSends({ OtherMod = { x = 5 } })
S.Store()
check(ME:getModData().OtherMod and ME:getModData().OtherMod.x == 5, "other mods' data stays")

-- the killstreak ledger survives
fresh("e")
local id = S.LedgerId()
check(type(id) == "string", "ledger made")
serverSends({})
check(S.LedgerId() == id, "same ledger after the wipe")

-- quest progress survives
fresh("f")
S.Quest().contacted = true
serverSends({})
check(S.Quest().contacted == true, "quest contact kept after the wipe")
check(ME:getModData().SkyhammerQuest ~= nil, "quest put back in the mod data")

-- a new character (death, respawn) starts over
fresh("g")
S.Call("ac130"); S.Quest().contacted = true
ME = newPlayer("g2")
check(S.Sortie("ac130") == 0, "a new character has no aircraft out")
check(S.Quest().contacted == nil, "a new character's quest starts over")

-- the character's saved state is picked up at login
ME = newPlayer("loaded")
ME.md.SkyhammerAirSupport = { v2 = { craft = { b2 = { phase = "REARM", sortie = 4, readyAtH = 1e9 } }, ammo = {} } }
check(S.Sortie("b2") == 4, "saved state used at login")

-- single player still uses the save's ModData
fresh("sp"); ONLINE = false
S.Call("ac130")
check(WORLD.v2 and WORLD.v2.craft.ac130.sortie == 1, "single player: the save's ModData")
check(ME:getModData().SkyhammerAirSupport == nil, "single player: nothing in the character")

if fails > 0 then error("mod data wipe checks failed: " .. table.concat(names, " | ")) end
print("skyhammer mod data wipe checks: all passed")
