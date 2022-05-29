REM First activate the Anaconda environment

@CALL C:\Anaconda3\Scripts\activate.bat

REM Normalize filepath
set myScriptPath=%~f0
set myPath=%myScriptPath:\build_win.bat=%

REM Clean dist directory

rd /Q /S dist

REM Bundle the application with pyinstaller

pyinstaller -w -n illust-variations-exporter src\app_gui.py --icon res\icon.ico  

REM Rename the output dir

ren dist\illust-variations-exporter bin

REM Copy the resources

md dist\res

xcopy /S res dist\res

REM Use Chocolatey's ShimGen to create a shim

C:\ProgramData\chocolatey\tools\shimgen --gui --output "%myPath%\dist\illust-variations-exporter.exe" --path ".\bin\illust-variations-exporter.exe" --iconpath ".\dist\bin\illust-variations-exporter.exe"