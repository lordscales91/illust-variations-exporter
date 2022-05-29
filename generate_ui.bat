@CALL C:\Anaconda3\Scripts\activate.bat

REM I'm not sure why, but it seems pyuic5 terminates the script
cmd /c pyuic_call src\gui\mainwindow.ui src\gui\mainwindow.py
cmd /c pyuic_call src\gui\variationsettings.ui src\gui\variationsettings.py
cmd /c pyuic_call src\gui\modifiersettings.ui src\gui\modifiersettings.py
cmd /c pyuic_call src\gui\modifiercombinationsdialog.ui src\gui\modifiercombinationsdialog.py