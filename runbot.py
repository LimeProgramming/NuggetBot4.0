#import os
import sys
import time
import logging
#import tempfile
import traceback
import subprocess

#from shutil import disk_usage, rmtree
#from base64 import b64decode

try:
    import pathlib
    import importlib.util
except ImportError:
    pass

log = logging.getLogger('launcher')

#git
class GIT(object):
    @classmethod
    def works(cls):
        try:
            return bool(subprocess.check_output('git --version', shell=True))
        except:
            return False

#pip
class PIP(object):
    @classmethod
    def run(cls, command, check_output=False):
        if not cls.works():
            raise RuntimeError("Could not import pip.")

        try:
            return PIP.run_python_m(*command.split(), check_output=check_output)
        except subprocess.CalledProcessError as e:
            return e.returncode
        except:
            traceback.print_exc()
            print("Error using -m method")

    @classmethod
    def run_python_m(cls, *args, **kwargs):
        check_output = kwargs.pop('check_output', False)
        check = subprocess.check_output if check_output else subprocess.check_call
        return check([sys.executable, '-m', 'pip'] + list(args))

    @classmethod
    def run_pip_main(cls, *args, **kwargs):
        import pip

        args = list(args)
        check_output = kwargs.pop('check_output', False)

        if check_output:
            from io import StringIO

            out = StringIO()
            sys.stdout = out

            try:
                pip.main(args)
            except:
                traceback.print_exc()
            finally:
                sys.stdout = sys.__stdout__

                out.seek(0)
                pipdata = out.read()
                out.close()

                print(pipdata)
                return pipdata
        else:
            return pip.main(args)

    @classmethod
    def run_install(cls, cmd, quiet=False, check_output=False):
        return cls.run("install %s%s" % ('-q ' if quiet else '', cmd), check_output)

    @classmethod
    def run_show(cls, cmd, check_output=False):
        return cls.run("show %s" % cmd, check_output)

    @classmethod
    def works(cls):
        try:
            import pip
            return True
        except ImportError:
            return False

    # noinspection PyTypeChecker
    @classmethod
    def get_module_version(cls, mod):
        try:
            out = cls.run_show(mod, check_output=True)

            if isinstance(out, bytes):
                out = out.decode()

            datas = out.replace('\r\n', '\n').split('\n')
            expectedversion = datas[3]

            if expectedversion.startswith('Version: '):
                return expectedversion.split()[1]
            else:
                return [x.split()[1] for x in datas if x.startswith("Version: ")][0]
        except:
            pass

    @classmethod
    def get_requirements(cls, file='requirements.txt'):
        from pip.req import parse_requirements
        return list(parse_requirements(file))

#Quit
def bugger_off(msg="Press enter to continue . . .", code=1):
    input(msg)
    sys.exit(code)


def main():
    import asyncio

    tried_requirementstxt = False
    tryagain = True

    loops = 0
    max_wait_time = 60

    while tryagain:

        m = None
        try:
            from nuggetbot import NuggetBot
            m = NuggetBot()
            print("Connecting...", flush=True, end='')
            m.run()

        except SyntaxError:
            log.exception("Syntax error (this is a bug, not your fault)")
            break

        except ImportError:
            if not tried_requirementstxt:
                tried_requirementstxt = True

                log.exception("Error starting bot")
                log.info("Attempting to install dependencies...")

                err = PIP.run_install('--upgrade -r requirements.txt')

                if err: # TODO: add the specific error check back as not to always tell users to sudo it
                    print()
                    log.critical("You may need to %s to install dependencies." %
                                 ['use sudo', 'run as admin'][sys.platform.startswith('win')])
                    break
                else:
                    print()
                    log.info("Ok lets hope it worked")
                    print()
            else:
                log.exception("Unknown ImportError, exiting.")
                break

        except Exception as e:
            if hasattr(e, '__module__') and e.__module__ == 'nuggetbot.exceptions':
                if e.__class__.__name__ == 'HelpfulError':
                    print(e.message)
                    break

                elif e.__class__.__name__ == "TerminateSignal":
                    break

                elif e.__class__.__name__ == "RestartSignal":
                    loops = 0
                    pass
            else:
                log.exception("Error starting bot")

        finally:
            if not m or not m.init_ok:
                if any(sys.exc_info()):
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
