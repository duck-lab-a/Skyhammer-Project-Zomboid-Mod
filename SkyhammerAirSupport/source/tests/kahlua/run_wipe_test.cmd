@echo off
rem Skyhammer online state survives the server wiping the character's mod data (2026-11-18 MP fix), on the game's
rem Kahlua with the REAL Skyhammer_PvP / Core / Killstreak / Quest files.
rem (Rewritten 2026-11-21: the 11-18 file was removed by the Windows System Restore of 11-20.)
set M=%~dp0..\..\..\42\media\lua
call "%~dp0..\..\..\..\..\tools\kahlua-run\run.cmd" "%~dp0wipe_stubs.lua" "%M%\shared\Skyhammer_PvP.lua" "%M%\client\Skyhammer_Core.lua" "%M%\client\Skyhammer_Killstreak.lua" "%M%\client\Skyhammer_Quest.lua" "%~dp0wipe_checks.lua"
