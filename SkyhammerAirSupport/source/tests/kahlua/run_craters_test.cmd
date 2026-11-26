@echo off
rem Skyhammer_Craters.lua on the game's Kahlua: blasts fell trees (2026-11-25) and still burn craters.
set M=%~dp0..\..\..\42\media\lua
call "%~dp0..\..\..\..\..\tools\kahlua-run\run.cmd" "%~dp0craters_stubs.lua" "%M%\shared\Skyhammer_Craters.lua" "%~dp0craters_checks.lua"
