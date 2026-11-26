@echo off
rem The AC-130 gunner seat online in the Vanilla Edition (2026-11-18), on the game's Kahlua with the REAL
rem Skyhammer_PvP / Core / 25mmAudio / SeatShotAudio / GunnerTracers / Ops / Gunner files.
rem (Rewritten 2026-11-21: the 11-18 file was removed by the Windows System Restore of 11-20.)
set M=%~dp0..\..\..\42\media\lua
call "%~dp0..\..\..\..\..\tools\kahlua-run\run.cmd" "%~dp0seat_online_stubs.lua" "%M%\shared\Skyhammer_PvP.lua" "%M%\client\Skyhammer_Core.lua" "%M%\client\Skyhammer_25mmAudio.lua" "%M%\client\Skyhammer_SeatShotAudio.lua" "%M%\client\Skyhammer_GunnerTracers.lua" "%M%\client\Skyhammer_Ops.lua" "%M%\client\Skyhammer_Gunner.lua" "%~dp0seat_online_checks.lua"
