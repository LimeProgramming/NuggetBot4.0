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

      # -------------------------------------------------- CREDENTIALS --------------------------------------------------
        self._login_token = config.get('Credentials', 'Token', fallback=ConfigDefaults.token)
        self.owner_id=      config.get('Credentials', 'Owner', fallback=ConfigDefaults.owner_id)


      # -------------------------------------------------- BOT --------------------------------------------------
        self.delete_invoking=   config.getboolean(  'Bot', 'DeleteInvoking',    fallback=ConfigDefaults.delete_invoking)
        self.command_prefix=    config.get(         'Bot', 'command_prefix',    fallback=ConfigDefaults.command_prefix)
        self.playing_game=      config.get(         'Bot', 'game',              fallback=ConfigDefaults.playing_game)

        #guild targetting
        self.target_guild_id = config.getint('Guild', 'guild_id', fallback=ConfigDefaults.target_guild_id)


      # -------------------------------------------------- CHANNELS --------------------------------------------------
        self.channels = {}

        self.channels['bot_log']=                       config.getint( 'Channel', 'Bot Log',         fallback=default_value)
        self.channels['public_bot_log']=                config.getint( 'Channel', 'Public Bot Log',  fallback=default_value)
        self.channels['feedback_id']=                   config.getint( 'Channel', 'Feedback',        fallback=default_value)
        self.channels['reception_id']=                  config.getint( 'Channel', 'Reception',       fallback=default_value)


        self.channels['nugget_welcome_id']=             config.getint(  'Channel', 'Welcome MSG',    fallback=default_value)
        self.channels['entrance_gate']=                 config.getint(  'Channel', 'Entrance Gate',  fallback=default_value)
        self.channels['public_rules_id']=               config.getint(  'Channel', 'Public Rules',   fallback=default_value)


      # -------------------------------------------------- ROLES --------------------------------------------------
        self.roles = {}
    
       # ===== MEMBER ROLES
        self.roles['member']=                           config.getint(  'Roles', 'Member',          fallback=None)
        self.roles['newmember']=                        config.getint(  'Roles', 'New-Member',      fallback=None)
        self.roles['gated']=                            config.getint(  'Roles', 'Gated',           fallback=None)
        autoroles=                  self.none_if_empty( config.get(     'Roles', 'Auto-Roles',      fallback=None))

        if autoroles:
            self.roles['autoroles']= self.split_id_list(autoroles)
        else:
            self.roles['autoroles'] = False

        self.roles['bottester']=                       config.getint(  'Roles', 'Bot-Tester',       fallback=None)

       #===== STAFF ROLES

        self.roles['admin']=                            config.getint('Roles', 'Admin',    fallback=ConfigDefaults.admin_role)
        self.roles['mod']=                              config.getint('Roles', 'Mod',      fallback=ConfigDefaults.mod_role)
        self.roles['tmod']=                             config.getint('Roles', 'Tmod',     fallback=ConfigDefaults.tmod_role)


        self.roles['high_staff']= [self.roles['admin'], self.roles['mod']]
        self.roles['any_staff']=  [self.roles['admin'], self.roles['mod'], self.roles['tmod']]
        self.roles['user_staff']= [self.roles['admin'], self.roles['mod'], self.roles['tmod'], self.roles['member']]


      # -------------------------------------------------- GIVEAWAY --------------------------------------------------
        self.gvwy_channel_id=       config.getint(     'Giveaway', 'Channel',                fallback=None)
        self.gvwy_role_name=        config.get(        'Giveaway', 'role_name',              fallback=None)
        self.gvwy_role_id=          config.getint(     'Giveaway', 'role_id',                fallback=None)
        self.gvwy_enforce_blacklist=config.getboolean( 'Giveaway', 'enforce_blacklist',      fallback=None)
        self.gvwy_min_time_on_srv=  config.get(        'Giveaway', 'required_time_on_srv',   fallback=None)
        self.gvwy_min_msgs=         config.getint(     'Giveaway', 'min_messages_required',  fallback=26)
        self.gvwy_end_message=      config.get(        'Giveaway', 'end_message',            fallback='The giveaway is over.')

        self.gvwy_role_name=        self.none_if_empty(     self.gvwy_role_name)
        self.gvwy_min_time_on_srv=  self.time_pat_to_hrs(   self.gvwy_min_time_on_srv)


      # -------------------------------------------------- ARTISTS --------------------------------------------------

        self.art_reasons = dict()

        self.art_reasons["Toggle Open Commissions"] = "Artist toggled the Open for commissions role"
        self.art_reasons["Commissioner_mentionable"] = "Toggling the mentionable perm in the commissioner role."
        
        #Roles
        self.art_roles={}

        self.art_roles['artist']=   config.getint(  'Artist', 'Artist-Role',            fallback=None)
        self.art_roles['commer']=   config.getint(  'Artist', 'Commissioner-Role',      fallback=None)
        self.art_roles['opencoms']= config.getint(  'Artist', 'Open-Commissions-Role',  fallback=None)


      # -------------------------------------------------- GALLERY CHANNELS --------------------------------------------------
        self.gallerys = {}

        self.galEnable=             config.getboolean(  'Gallery', 'Enable',            fallback=False)
        self.gallerys["chls"]=      config.get(         'Gallery', 'Channels',          fallback=list())
        self.gallerys['expire_in']= config.get(         'Gallery', 'Text-MSG-ExpireIn', fallback=24)
        self.gallerys['rem_low']=   config.getboolean(  'Gallery', 'Delete-Low-Quality',fallback=False)
        self.gallerys["user_wl"]=   config.get(         'Gallery', 'User-Whitelist',    fallback=list())
        self.gallerys["links"]=     config.getboolean(  'Gallery', 'Allow-Links',       fallback=False)
        self.gallerys['link_wl']=   config.get(         'Gallery', 'Link-Whitelist',    fallback=list())
        
        #=== CLEAN UP GALLERY DATA
        self.gallerys["chls"]=      self.split_id_list(     self.gallerys["chls"])
        self.gallerys['expire_in']= (self.time_pat_to_hrs(   self.gallerys['expire_in']) or 24)
        self.gallerys["user_wl"]=   self.split_id_list(     self.gallerys["user_wl"])
        self.gallerys['link_wl']=   self.clean_glry_links(  self.gallerys['link_wl'])


      # -------------------------------------------------- SELF ASSIGN ROLES --------------------------------------------------
        self.roles_channel_id =     config.getint(      'Channel',  'Self Assign Roles',    fallback=None)

        # ===== NAME COLORS
        self.name_colors = list()

        for i in config.items("Name Color Roles"):
            try:
                j = int(i[1])

            except ValueError:
                raise HelpfulError(
                    f'Under section "Name Color Roles" {i[1]} is not a digit.',
                    'All role ID\'s provided must be a digit.',
                    preface=self._confpreface2
                )

            self.name_colors.append(j)


      # -------------------------------------------------- WALLETS --------------------------------------------------
        self.wallets = dict()

        for i in config.items("Guild Wallets"):
            fname, sname = i[0].split('-')
            wallet = i[1]

            self.wallets[sname.upper()] = (fname.title(), wallet)


      # -------------------------------------------------- CHECKS --------------------------------------------------
        self.__int_chl_ids()
        self.run_checks()

      # -------------------------------------------------- END INIT --------------------------------------------------

    def run_checks(self):

        if not self._login_token:
            raise HelpfulError(
                'No bot token was specified in the config.',
                'Add one',
                preface=self._confpreface
            )

        else:
            self.auth = (self._login_token,)

        #-------------------- BOT OWNER --------------------
        if self.owner_id:

            if not isinstance(self.owner_id, int):
                self.owner_id = self.__rem_illegal(self.owner_id)
                self.owner_id = int(self.owner_id)


            if self.owner_id < 10000:
                raise HelpfulError(
                    "An invalid OwnerID was set: {}".format(self.owner_id),
                    "Correct your OwnerID. The ID should be just a number, approximately18 characters long",
                    preface=self._confpreface
                )           

        if not self.owner_id:
            raise HelpfulError(
                "No OwnerID was set.",
                "Please set the OwnerID option in {}".format(self.config_file),
                preface=self._confpreface
                )

        #-------------------- GUILD TARGETTING -------------------- 
        if not self.target_guild_id:
            raise HelpfulError(
                "Target guild has not been specified in the config.",
                "Add one",
                preface=self._confpreface
            )

        if not isinstance(self.target_guild_id, int):
            try:
                if not self.target_guild_id.isdigit():
                    self.target_guild_id = self.__rem_illegal(self.target_guild_id)

                self.target_guild_id = int(self.target_guild_id)

            except ValueError:
                raise HelpfulError(
                    "Guild ID provided is not valid.",
                    "Guild ID should be numerical.",
                    preface=self._confpreface2
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
        Takes a string and devides it into two lists, one list on numbers and one list of letters.

        Args:
            (str)

        Returns:
            (tuple(list, list)), [0] list of letters [1] list of numbers 
        """

        letters = []
        numbers = []

        for k in stringtosplit:
            if k.isalpha() == True:
                letters.append(k)

            elif k.isdigit() == True:
                numbers.append(int(k))

        return (letters, numbers)

    def none_if_empty(self, val:str):
        """
        Returns None is string is either empty or 'none'.

        Args:
            (str)

        Returns:
            (str) or None
        """

        if bool(val) and val.lower() != "none":
            return val 

        return None 
    
    def split_id_list(self, strids):
        '''
        Converts a string of Discord id's and converts it to a list of id's of type int.

        Args:
            (str) List of Discord id's seperated by a space.

        Returns:
            (list) Set of Discord id's converted to an int.
        '''

        if not isinstance(strids, list):
            #=== REMOVE SOME COMMON ILLEGAL CHARACTERS
            strids = self.__rem_illegal(strids)
            strids = strids.split(" ")

        strid = ""
        intids = []

        try:
            for strid in strids:

                if strid == "" or strid is None:
                    continue

                #= CONVERT THE ID TO AN INT
                intids.append(int(strid))

        #===== IF ID IS NOT AN INT.
        except ValueError:
            raise HelpfulError(
                "An invalid id was set: {}".format(strid),

                "Please ensure all ids provided are numerical.\n"
                "Unless specified, no names should be provided.",
                preface=self._confpreface2
            )

        #===== RETURN A LIST OF INTS    
        return intids
        
    def time_pat_to_hrs(self, t):
        '''
        Converts a string in format <xdxh> (d standing for days and h standing for hours) to amount of hours.
        eg: 3d5h would be 77 hours

        Args:
            (str) or (int)

        Returns:
            (int) or (None)
        '''
        
        if not t:
            return None 

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

    def clean_glry_links(self, links):
        '''
        Takes the gallery links from the setup.ini and removes any qoutes or double qoutes,

        Args:
            str
        
        Returns:
            list
        '''
        clinks = []

        for link in links.split("\n"):
            if link == "":
                continue
            link = link.strip()

            link = link.replace('\'', '').replace('"', '').replace(',', '')
            clinks.append(link)

        return clinks


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


    def __rem_illegal(self, val):
        '''
        Removes invalid characters from a string, ie common mistakes made when entering data into an ini
        '''
        val = re.sub('[<>?*|\'",.]', '', val)
        
        return val

    def __int_chl_ids(self):
        '''
        Just does a basic conversion from strings to int.
        Required since discord.py rewrite switched from string id's to int id's
        '''
        #===== FOR CHANNEL DICT
        for key in self.channels.keys():

            #=== SKIP IF VALUE IS ALREADY AN INT
            if isinstance(self.channels[key], int):
                continue

            try:
                #= REMOVE SOME COMMON ILLEGAL CHARACTERS
                self.channels[key] = self.__rem_illegal(self.channels[key])
                self.channels[key] = int(self.channels[key])

            #=== IF CHANNEL ID IS NOT AN INT.
            except ValueError:
                raise HelpfulError(
                    "An invalid channel id was set: {}".format(key),

                    "Please ensure all channel ids provided are numerical.\n"
                    "Unless specified, no channel names should be provided.",
                    preface=self._confpreface2
                )
        
        #===== FOR GIVEAWAY CHANNEL
        if not isinstance(self.gvwy_channel_id, int):
            try:
                #= REMOVE SOME COMMON ILLEGAL CHARACTERS
                if not self.gvwy_channel_id.isdigit():
                    self.gvwy_channel_id = self.__rem_illegal(self.gvwy_channel_id)

                self.gvwy_channel_id = int(self.gvwy_channel_id)

            except ValueError:
                raise HelpfulError(
                    "An invalid channel id was set: Giveaway, channel_id",

                    "Please ensure all channel ids provided are numerical.\n"
                    "Unless specified, no channel names should be provided.",
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
