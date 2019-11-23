"""
----~~~~~ NuggetBot ~~~~~----
Written By Calamity Lime#8500

Disclaimer
-----------
NuggetBots source code as been shared for the purposes of transparency on the FurSail discord server and educational purposes.
Running your own instance of this bot is not recommended.

FurSail Invite URL: http://discord.gg/QMEgfcg

Kind Regards
-Lime
"""

import shutil
import textwrap

# Base class for exceptions
class NuggetbotException(Exception):
    def __init__(self, message, *, expire_in=0):
        super().__init__(message) # ???
        self._message = message
        self.expire_in = expire_in

    @property
    def message(self):
        return self._message

    @property
    def message_no_format(self):
        return self._message

# Error with pretty formatting for hand-holding users through various errors
class HelpfulError(NuggetbotException):
    def __init__(self, issue, solution, *, preface="An error has occured:", footnote='', expire_in=0):
        self.issue = issue
        self.solution = solution
        self.preface = preface
        self.footnote = footnote
        self.expire_in = expire_in
        self._message_fmt = "\n{preface}\n{problem}\n\n{solution}\n\n{footnote}"

    @property
    def message(self):
        return self._message_fmt.format(
            preface  = self.preface,
            problem  = self._pretty_wrap(self.issue,    "  Problem:"),
            solution = self._pretty_wrap(self.solution, "  Solution:"),
            footnote = self.footnote
        )

    @property
    def message_no_format(self):
        return self._message_fmt.format(
            preface  = self.preface,
            problem  = self._pretty_wrap(self.issue,    "  Problem:", width=None),
            solution = self._pretty_wrap(self.solution, "  Solution:", width=None),
            footnote = self.footnote
        )

    @staticmethod
    def _pretty_wrap(text, pretext, *, width=-1):
        if width is None:
            return '\n'.join((pretext.strip(), text))
        elif width == -1:
            pretext = pretext.rstrip() + '\n'
            width = shutil.get_terminal_size().columns

        lines = textwrap.wrap(text, width=width - 5)
        lines = (('    ' + line).rstrip().ljust(width-1).rstrip() + '\n' for line in lines)

        return pretext + ''.join(lines).rstrip()

# Base class for control signals
class Signal(Exception):
    pass

# signal to restart the bot
class RestartSignal(Signal):
    pass

# signal to end the bot "gracefully"
class TerminateSignal(Signal):
    pass

class PostAsWebhook(NuggetbotException):
    def __init__(self, issue, *, preface="```diff\n- An error has occured\n```", expire_in=0):
        self.issue = issue
        self.preface = preface
        self.expire_in = expire_in
        self._message_fmt = "\n{preface}\n{problem}"

    @property
    def message(self):
        return self._message_fmt.format(
            preface  = self.preface,
            problem  = self.issue
        )