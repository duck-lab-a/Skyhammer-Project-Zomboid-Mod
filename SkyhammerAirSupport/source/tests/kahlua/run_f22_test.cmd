@echo off
rem The F-22 flight strike (Skyhammer_F22, 2026-11-23) on the game's Kahlua with the REAL
rem Skyhammer_PvP / Core / Killstreak / Comms / Ops / Apache / A10 / F22 files, one fresh world
rem per group of checks.
set M=%~dp0..\..\..\42\media\lua
set RUN="%~dp0..\..\..\..\..\tools\kahlua-run\run.cmd"
set FILES="%~dp0f22_stubs.lua" "%M%\shared\Skyhammer_PvP.lua" "%M%\client\Skyhammer_Core.lua" "%M%\client\Skyhammer_Killstreak.lua" "%M%\client\Skyhammer_Comms.lua" "%M%\client\Skyhammer_Ops.lua" "%M%\client\Skyhammer_Apache.lua" "%M%\client\Skyhammer_A10.lua" "%M%\client\Skyhammer_F22.lua" "%~dp0f22_after.lua"
set FAILED=0
for %%c in (tables strike marks reload recall) do (
    echo === %%c
    call %RUN% %FILES% "%~dp0f22_checks_%%c.lua" || set FAILED=1
)
if %FAILED%==1 (echo F22 CHECKS FAILED & exit /b 1)
echo F22 CHECKS PASSED
