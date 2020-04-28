#!/usr/bin/env python3

from __future__ import print_function

import os
import sys
import time
import logging
import asyncio
import tempfile
import traceback
import subprocess

from shutil import disk_usage, rmtree
from base64 import b64decode

try:
    import pathlib
    import importlib.util
except ImportError:
    pass

# ======================================== Logging Stuff ========================================

tmpfile = tempfile.TemporaryFile('w+', encoding='utf8')
log = logging.getLogger('launcher')
log.setLevel(logging.DEBUG)

sh = logging.StreamHandler(stream=sys.stdout)
sh.setFormatter(logging.Formatter(
    fmt="[%(levelname)s] %(name)s: %(message)s"
))

sh.setLevel(logging.INFO)
log.addHandler(sh)

tfh = logging.StreamHandler(stream=tmpfile)
tfh.setFormatter(logging.Formatter(
    fmt="[%(relativeCreated).9f] %(asctime)s - %(levelname)s - %(name)s: %(message)s"
))
tfh.setLevel(logging.DEBUG)
log.addHandler(tfh)


def finalize_logging():
    if os.path.isfile("logs/nuggetbot.log"):
        log.info("Moving old nuggetbot log")
        try:
            if os.path.isfile("logs/nuggetbot.log.last"):
                os.unlink("logs/nuggetbot.log.last")
            os.rename("logs/nuggetbot.log", "logs/nuggetbot.log.last")
        except:
            pass

    with open("logs/nuggetbot.log", 'w', encoding='utf8') as f:
        tmpfile.seek(0)
        f.write(tmpfile.read())
        tmpfile.close()

        f.write('\n')
        f.write(" PRE-RUN SANITY CHECKS PASSED ".center(80, '#'))
        f.write('\n\n')

    global tfh
    log.removeHandler(tfh)
    del tfh

    fh = logging.FileHandler("logs/nuggetbot.log", mode='a')
    fh.setFormatter(logging.Formatter(
        fmt="[%(relativeCreated).9f] %(name)s-%(levelname)s: %(message)s"
    ))
    fh.setLevel(logging.DEBUG)
    log.addHandler(fh)

    sh.setLevel(logging.INFO)

    dlog = logging.getLogger('discord')
    dlh = logging.StreamHandler(stream=sys.stdout)
    dlh.terminator = ''
    dlh.setFormatter(logging.Formatter('.'))
    dlog.addHandler(dlh)

# ======================================== Sanity Check ========================================

def sanity_checks(optional=True):
    log.info("Starting sanity checks")
    ## Required

    # Make sure we're on Python 3.5+
    req_ensure_py3()

    # Fix windows encoding fuckery
    req_ensure_encoding()

    # Make sure we're in a writeable env
    #req_ensure_env()

    # Make our folders if needed
    req_ensure_folders()

    # For rewrite only
    req_check_deps()

    log.info("Required checks passed.")

    ## Optional
    if not optional:
        return

    # Check disk usage
    opt_check_disk_space()

    log.info("Optional checks passed.")

# ======================================== Various Checks ========================================

def req_ensure_py3():
    log.info("Checking for Python 3.6+")

    if sys.version_info < (3, 6):
        log.warning("Python 3.6+ is required. This version is %s", sys.version.split()[0])
        log.warning("Attempting to locate Python 3.6...")

        pycom = None

        if sys.platform.startswith('win'):
            log.info('Trying "py -3.6"')
            try:
                subprocess.check_output('py -3.6 -c "exit()"', shell=True)
                pycom = 'py -3.6'
            except:

                log.info('Trying "python3"')
                try:
                    subprocess.check_output('python3 -c "exit()"', shell=True)
                    pycom = 'python3'
                except:
                    pass

            if pycom:
                log.info("Python 3 found.  Launching bot...")
                pyexec(pycom, 'runbot.py')

                # I hope ^ works
                os.system('start cmd /k %s runbot.py' % pycom)
                sys.exit(0)

        else:
            log.info('Trying "python3.6"')
            try:
                pycom = subprocess.check_output('python3.6 -c "exit()"'.split()).strip().decode()
            except:
                pass

            if pycom:
                log.info("\nPython 3 found.  Re-launching bot using: %s run.py\n", pycom)
                pyexec(pycom, 'run.py')

        log.critical("Could not find Python 3.6 or higher.  Please run the bot using Python 3.6")
        bugger_off()

def req_check_deps():
    try:
        import discord
        if discord.version_info.major < 1:
            log.critical("This version of nuggetbot requires a newer version of discord.py (1.0+). Your version is {0}. Try running update.py.".format(discord.__version__))
            bugger_off()

    except ImportError:
        # if we can't import discord.py, an error will be thrown later down the line anyway
        pass

def req_ensure_encoding():
    log.info("Checking console encoding")

    if sys.platform.startswith('win') or sys.stdout.encoding.replace('-', '').lower() != 'utf8':
        log.info("Setting console encoding to UTF-8")

        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.detach(), encoding='utf8', line_buffering=True)
        # only slightly evil    
        sys.__stdout__ = sh.stream = sys.stdout

        if os.environ.get('PYCHARM_HOSTED', None) not in (None, '0'):
            log.info("Enabling colors in pycharm pseudoconsole")
            sys.stdout.isatty = lambda: True

def req_ensure_folders():
    pathlib.Path('logs').mkdir(exist_ok=True)
    pathlib.Path('data').mkdir(exist_ok=True)

def opt_check_disk_space(warnlimit_mb=200):
    if disk_usage('.').free < warnlimit_mb*1024*2:
        log.warning("Less than %sMB of free space remains on this device" % warnlimit_mb)

def pyexec(pycom, *args, pycom2=None):
    pycom2 = pycom2 or pycom
    os.execlp(pycom, pycom2, *args)

# ======================================== Quit ========================================

def bugger_off(msg="Press enter to continue . . .", code=1):
    input(msg)
    sys.exit(code)

#################################################

def main():
    # TODO: *actual* argparsing

    if '--no-checks' not in sys.argv:
        sanity_checks()

    finalize_logging()

    if sys.platform == 'win32':
        loop = asyncio.ProactorEventLoop()  # needed for subprocesses
        asyncio.set_event_loop(loop)

    tried_requirementstxt = False
    tryagain = True
    loops = 0
    max_wait_time = 60

    while tryagain:
        # Maybe I need to try to import stuff first, then actually import stuff
        # It'd save me a lot of pain with all that awful exception type checking

        m = None
        try:
            from nuggetbot.bot import NuggetBot
            m = NuggetBot()

            sh.terminator = ''
            sh.terminator = '\n'

            m.run()

        except SyntaxError:
            log.exception("Syntax error (this is a bug, not your fault)")
            break

        except ImportError:
            # TODO: if error module is in pip or dpy requirements...

            if not tried_requirementstxt:
                tried_requirementstxt = True

                log.exception("Error starting bot")
                log.info("Attempting to install dependencies...")

                subprocess.check_call(['pip3', 'install', '--upgrade', '-r', 'requirements.txt'])

                print()
                log.info("Ok lets hope it worked")
                print()

            else:
                log.exception("Unknown ImportError, exiting.")
                print()
                log.critical("You may need to %s to install dependencies." %
                            ['use sudo', 'run as admin'][sys.platform.startswith('win')])

                break

        except Exception as e:
            if hasattr(e, '__module__') and e.__module__ == 'nuggetemoji.util.exceptions':
                print(e.__class__.__name__)

                if e.__class__.__name__ == 'HelpfulError':
                    log.info(e.message)

                    file='data/reboot.txt' 
                    with open(file, 'w') as filetowrite:
                        filetowrite.write('0')

                    tryagain = False
                    break

                elif e.__class__.__name__ == "TerminateSignal":
                    file='data/reboot.txt' 
                    with open(file, 'w') as filetowrite:
                        filetowrite.write('0')

                    tryagain = False
                    break

                elif e.__class__.__name__ == "RestartSignal":
                    file='data/reboot.txt' 
                    with open(file, 'w') as filetowrite:
                        filetowrite.write('1')

                    tryagain = False
                    break
            else:
                log.exception("Error starting bot")

        finally:
            if not m or not m.init_ok:
                if any(sys.exc_info()):
                    # How to log this without redundant messages...
                    traceback.print_exc()
                break

            asyncio.set_event_loop(asyncio.new_event_loop())
            loops += 1

        sleeptime = min(loops * 2, max_wait_time)
        if sleeptime:
            log.info("Restarting in {} seconds...".format(loops*2))
            time.sleep(sleeptime)

    print()
    log.info("All done.")


if __name__ == '__main__':
    main()