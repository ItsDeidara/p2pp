@ECHO OFF
SET MYPATH=%~dp0
REM Under normal circumstances, you should not need to edit this file unless the path for Python2.7 is incorrect.
REM Avoid editing the "MYPATH" variable as this will automatically determine the path of the p2pp script.

REM remove "REM" from the line below if you wish to pause before p2pp executes. This is useful for single extrusion prints.
REM pause

REM Edit the line below if you  need to change the python path.
c:\python27\python.exe %MYPATH%\p2pp.py -i %1

pause