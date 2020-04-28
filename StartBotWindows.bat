@ECHO OFF
setlocal enableExtensions 
setlocal enableDelayedExpansion 

SET /A X = 1

GOTO :loop

:loop
    IF %X% EQU 1 (
        
        python runbot.py 

        SET /p texte=<"data\reboot.txt"

        IF "!texte!"=="1" (
            SET /A X = 1
            ECHO 0 > data\reboot.txt 
        ) ELSE (
            SET /A X = 0
        )

        TIMEOUT 5 /nobreak > NUL

        GOTO :loop
    )

ENDLOCAL
