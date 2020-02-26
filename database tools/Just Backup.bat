@ECHO OFF
GOTO START


:SET_THESE
REM Database login with replication credentials. 
REM This information must relate to the target server.
SET PGHOST=
SET PGPORT=5432
SET PGLOGIN=
SET PGPASSWORD=
SET DBNAME=

EXIT /B 0





:START

REM Get items as set by the user.
CALL :SET_THESE

REM Make the name for the backup file using the time and date.
CALL :NAME_BACKUP_FILE

REM Log pg_dump's verbose output to logfile, useful for errors.
2>logs\%DBNAME%_%datetime%_DLog.txt (
    bin\pg_dump --host="%PGHOST%" --port=%PGPORT% --username="%PGLOGIN%" --dbname="%DBNAME%" --format c --blobs -v -f "%BACKUP_FILE%"
)

ECHO -------------------- Finished dump. Check Log for details. --------------------
ECHO.
TIMEOUT 5 /nobreak > NUL

REM Quit Bat File
EXIT /B





:: Some Functions.
:NAME_BACKUP_FILE
REM Get the date.
FOR /f "tokens=1-4 delims=/ " %%i in ("%date%") do (
    SET month=%%j
    SET day=%%i
    SET year=%%k
)

REM Get the time.
SET HH=%TIME:~0,2%
SET MI=%TIME:~3,2%
SET SS=%TIME:~6,2%

REM Set the datetime.
SET datetime=%day%-%month%-%year%-%HH%%MI%%SS%

REM Set the datetime.
SET BACKUP_FILE=backups\%DBNAME%_%datetime%.sql

EXIT /B 0