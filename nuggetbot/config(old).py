import re
from configparser import ConfigParser
from .exceptions import HelpfulError


class Config:
    def __init__(self):

        self.config_file = 'setup.ini'
        default_value = None

        config = ConfigParser(interpolation=None)
        config.read(self.config_file, encoding='utf-8')

        confsections = {'Credentials', 'Bot', 'Roles', 'Guild', 'Giveaway'}.difference(config.sections())

        if confsections:
            raise HelpfulError(
                "One or more required config sections are missing.",
                "Fix your config.  Each [Section] should be on its own line with "
                "nothing else on it.  The following sections are missing: {}".format(
                    ', '.join(['[%s]' % s for s in confsections])
                ),
                preface="An error has occured parsing the config:\n"
            )

        self._confpreface = 'An error has occurred reading the config:\n'
        self._confpreface2 = 'An error has occured validating the config:\n'
        self.auth = ()

        #-------------------------------------------------- CREDENTIALS --------------------------------------------------
        self._login_token = config.get('Credentials', 'Token', fallback=ConfigDefaults.token)

        #-------------------------------------------------- BOT --------------------------------------------------
        self.owner_id=          config.getint(      'Bot', 'owner_id',          fallback=ConfigDefaults.owner_id)
        self.delete_invoking=   config.getboolean(  'Bot', 'DeleteInvoking',    fallback=ConfigDefaults.delete_invoking)
        self.command_prefix=    config.get(         'Bot', 'command_prefix',    fallback=ConfigDefaults.command_prefix)
        self.playing_game=      config.get(         'Bot', 'game',              fallback=ConfigDefaults.playing_game)

        #guild targetting
        self.target_guild_id = config.getint('Guild', 'guild_id', fallback=ConfigDefaults.target_guild_id)
        
        #-------------------------------------------------- CHANNELS --------------------------------------------------
        self.channels = {}

        self.channels['bot_log']=        config.getint('Guild', 'bot_log', fallback=default_value)
        self.channels['public_bot_log']= config.getint('Guild', 'public_bot_log', fallback=default_value)
        self.channels['feedback_id']=    config.getint('Guild', 'feedback_id', fallback=default_value)
        self.channels['reception_id']=   config.getint('Guild', 'reception_id', fallback=default_value)
        #self.channels['bot_log_id'] = config.getint('guild', 'bot_log', fallback=None)

        #self.channels['entrance_gate_id'] = config.getint('guild', 'entrance_gate_id', fallback=default_value)

        #self.channels['reception_id'] = config.getint('guild', 'reception_channel', fallback=default_value)


        self.channels['warning_log_id']=        config.getint('Guild', 'warning_log', fallback=default_value)
        self.channels['embassy_id']=            config.getint('Guild', 'embassy', fallback=default_value)
        self.channels['nugget_welcome_id']=     config.getint('Guild', 'nugget_welcome_channel', fallback=default_value)
        self.channels['ministry_archive_id']=   config.getint('Guild', 'ministry_archive_channel', fallback=default_value)
        self.channels['public_ministry_archive_id']= config.getint('Guild', 'public_ministry_archive_channel', fallback=default_value)
        self.channels['entrance_gate_id']= config.getint('Guild', 'entrance_gate_id', fallback=default_value)
        self.channels['sys_ops_id']= config.getint('Guild', 'sys_ops_channel', fallback=default_value)
        self.channels['servey_id']= config.getint('Guild', 'servey_channel', fallback=default_value)
        self.channels['public_rules_id']= config.getint('Guild', 'public_rules', fallback=default_value)
        
        
        
        #-------------------------------------------------- ROLES --------------------------------------------------
        self.roles = {}

        self.roles['admin']=    config.get('Roles', 'Admin',    fallback=ConfigDefaults.admin_role)
        self.roles['mod']=      config.get('Roles', 'Mod',      fallback=ConfigDefaults.mod_role)
        self.roles['tmod']=     config.get('Roles', 'Tmod',     fallback=ConfigDefaults.tmod_role)
        self.roles['user']=     config.get('Roles', 'User',     fallback=ConfigDefaults.user_role)
        self.roles['newuser']=  config.get('Roles', 'Newuser',  fallback=ConfigDefaults.newuser_role)
        self.roles['autorole']= config.get('Roles', 'Autorole', fallback=None)

        self.user_role=     self.roles['user']
        self.newuser_role=  self.roles['newuser']

        self.roles['high_staff']= [self.roles['admin'], self.roles['mod']]
        self.roles['any_staff']=  [self.roles['admin'], self.roles['mod'], self.roles['tmod']]
        self.roles['user_staff']= [self.roles['admin'], self.roles['mod'], self.roles['tmod'], self.roles['user']]

        #-------------------------------------------------- GIVEAWAY --------------------------------------------------

        self.gvwy_channel_id=       config.getint(     'Giveaway', 'channel_id',             fallback=None)
        self.gvwy_role_name=        config.get(        'Giveaway', 'role_name',              fallback=None)
        self.gvwy_enforce_blacklist=config.getboolean( 'Giveaway', 'enforce_blacklist',      fallback=None)
        self.gvwy_min_time_on_srv=  config.get(        'Giveaway', 'required_time_on_srv',   fallback=None)
        self.gvwy_min_msgs=         config.getint(     'Giveaway', 'min_messages_required',  fallback=26)
        self.gvwy_end_message=      config.get(        'Giveaway', 'end_message',            fallback='The giveaway is over.')

        self.gvwy_role_name=        self.none_if_empty(         self.gvwy_role_name)
        self.gvwy_min_time_on_srv=  self.time_pattern_to_hours( self.gvwy_min_time_on_srv)


        #-------------------------------------------------- tests --------------------------------------------------
        self.name_colors = [None]

        self.name_colors.append(config.get('name_colors', '1', fallback=None))
        self.name_colors.append(config.get('name_colors', '2', fallback=None))
        self.name_colors.append(config.get('name_colors', '3', fallback=None))
        self.name_colors.append(config.get('name_colors', '4', fallback=None))
        self.name_colors.append(config.get('name_colors', '5', fallback=None))
        self.name_colors.append(config.get('name_colors', '6', fallback=None))

        self.run_checks()

    def run_checks(self):

        if not self._login_token:
            raise HelpfulError(
                'No bot token was specified in the config.',
                'Add one',
                preface=self._confpreface
            )

        else:
            self.auth = (self._login_token,)

        #===== Owner Targetting
        if self.owner_id:

            if isinstance(self.owner_id, int):
                if self.owner_id < 10000:
                    raise HelpfulError(
                        "An invalid OwnerID was set: {}".format(self.owner_id),

                        "Correct your OwnerID. The ID should be just a number, approximately"
                        "18 characters long, or 'auto'. If you don't know what your ID is, read the "
                        "instructions in the options or ask in the help guild.",
                        preface=self._confpreface
                    )

            elif self.owner_id == 'auto':
                pass # defer to async check

            else:
                self.owner_id = None

        if not self.owner_id:
            raise HelpfulError(
                "No OwnerID was set.",
                "Please set the OwnerID option in {}".format(self.config_file),
                preface=self._confpreface
                )

        #===== guild targetting
        if not self.target_guild_id:
            raise HelpfulError(
                "Target guild has not been specified in the config.",
                "Add one",
                preface=self._confpreface
            )

        if not self.channels["servey_id"]:
            raise HelpfulError(
                "servey_channel channel has not been specified in the config.",
                "Add one",
                preface=self._confpreface
            )

        if not self.channels["reception_id"]:
            raise HelpfulError(
                "Reception channel has not been specified in the config.",
                "Add one",
                preface=self._confpreface
            )

        if not self.channels["nugget_welcome_id"]:
            raise HelpfulError(
                "A Welcome channel has not been specified in the config.",
                "Add one",
                preface=self._confpreface
            )

    def split_string_lists(self, stringtosplit):
        """
            string and devides it into two lists, one list on numbers and one list of letters
        """

        letters = []
        numbers = []

        for k in stringtosplit:
            if k.isalpha() == True:
                letters.append(k)
            elif k.isdigit() == True:
                numbers.append(k)

        return (letters, numbers)

    def none_if_empty(self, val, split=False):
        """
            Returns None is string is either empty or 'none'
        """

        if bool(val) and val.lower() != "none":
            if split:
                return val.split(" ")

            return val 

        return None 
    
    def split_chl_id_list(self, strchls):
        strchls = strchls.split(" ")
        intchls = []

        try:
            for strchl in strchls:
                intchls.append(int(strchl))

                set()
        
        except ValueError:
            raise HelpfulError(
                "List of channel id's is not all numbers and spaces",
                "Fix it",
                preface=self._confpreface
            )

        return set(intchls)
        

    ###
    def time_pattern_to_hours(self, t):
        timeinHours = int() 

        try:
            timeinHours = int(t)
            return timeinHours

        except ValueError:
            valid = False 

            #===== if input doesn't match basic pattern
            if (re.match(r"(\d+[DHdh])+", t)):
                
                #=== if all acsii chars in the string are unique 
                letters = re.findall(r"[DHdh]", t)
                if len(letters) == len(set(letters)):
                    
                    #= if more then 1 letter side by side
                    #= ie. if t was 2dh30m then after the split you'd have ['', 'dh', 'm', '']
                    if not ([i for i in re.split(r"[0-9]", t) if len(i) > 1]):
                        
                        # if letters are in order.
                        if letters == sorted(letters, key=lambda letters: ["d", "h"].index(letters[0])):
                            valid = True

            if valid:
                total_hours = int() 

                for data in re.findall(r"(\d+[DHdh])", t):
                    if data.endswith("d"):
                        total_hours += int(data[:-1])*24
                    if data.endswith("h"):
                        total_hours += int(data[:-1])

            return total_hours 

        return "reject" 

    async def async_validate(self, bot):

        if self.owner_id == "auto":
            if not bot.user.bot:
                raise HelpfulError(
                    "Invalid parameter \'auto\' for OwnerID option.",

                    "Only bot accounts can use the \'auto\' option.  Please "
                    "set the OwnerID in the config.",

                    preface=self._confpreface2
                )

            self.owner_id = bot.cached_app_info.owner.id
            #log.debug("Acquired owner id via API")

        if self.owner_id == bot.user.id:
            raise HelpfulError(
                "Your OwnerID is incorrect or you've used the wrong credentials.",

                "The bot's user ID and the id for OwnerID is identical. "
                "This is wrong. The bot needs a bot account to function, "
                "meaning you cannot use your own account to run the bot on. "
                "The OwnerID is the id of the owner, not the bot. "
                "Figure out which one is which and use the correct information.",

                preface=self._confpreface2
            )

class ConfigDefaults:
    #Bot owner
    owner_id = None

    token = None

    #bot
    command_prefix = '!'
    playing_game = ''
    delete_invoking = False


    #guild targetting
    target_guild_id = None
    servey_channel_id = None
    dyno_archive_id = None
    reception_id = None

    #Roles
    admin_role = 'Admin'
    mod_role = 'Moderator'
    tmod_role = 'Trainee'
    user_role = 'Core'
    newuser_role = 'Fresh'
