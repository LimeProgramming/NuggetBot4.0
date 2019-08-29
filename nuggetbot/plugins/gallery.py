from discord.ext import commands
import discord
import asyncio
import asyncpg
import datetime
import random
import re
import collections

from apscheduler import events
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from nuggetbot.utils import get_next
from nuggetbot.config import Config
from nuggetbot.database import DatabaseCmds as pgCmds
from .ctx_decorators import in_channel, is_core, in_channel_name, in_reception, has_role, is_high_staff, is_any_staff
#https://discordpy.readthedocs.io/en/latest/ext/commands/api.html#bot
import dblogin 

class Gallery(commands.Cog):
    """Handle the Gallery channels."""

    config = None 
    delete_after = 15
    compare = lambda x, y: collections.Counter(x) == collections.Counter(y)

    def __init__(self, bot):
        Gallery.bot = self
        self.bot = bot
        self.db = None
        #Gallery.config = Config()
        
        self.gal_guild_id=      0
        self.gal_enable=        False 
        self.gal_channel_ids=   []
        self.gal_channels=      []
        self.gal_text_expirein= None
        self.gal_user_wl=       []
        self.gal_allow_links=   False
        self.gal_link_wl=       []

        self.jobstore = SQLAlchemyJobStore(url='sqlite:///gallery.sqlite')
        jobstores = {"default": self.jobstore}
        self.scheduler = AsyncIOScheduler(jobstores=jobstores)
        self.scheduler.add_listener(self.job_missed, events.EVENT_JOB_MISSED)


  #-------------------- LOCAL COG EVENTS --------------------
    async def cog_before_invoke(self, ctx):
        '''THIS IS CALLED BEFORE EVERY COG COMMAND, IT'S SOLE PURPOSE IS TO CONNECT TO THE DATABASE'''

        credentials = {"user": dblogin.user, "password": dblogin.pwrd, "database": dblogin.name, "host": dblogin.host}
        self.db = await asyncpg.create_pool(**credentials)

        return

    async def cog_after_invoke(self, ctx):
        '''THIS IS CALLED AFTER EVERY COG COMMAND, IT DISCONNECTS FROM THE DATABASE AND DELETES INVOKING MESSAGE IF SET TO.'''

        await self.db.close()

        if Gallery.config.delete_invoking:
            await ctx.message.delete()

        return

    async def on_cog_command_error(self, ctx, error):
        if isinstance(error, discord.ext.commands.errors.NotOwner):
            try:
                owner = self.bot.application_info()
            except:
                owner = self.bot.get_guild(self.gal_guild_id).owner()

            await ctx.channel.send(content=f"```diff\n- {ctx.prefix}{ctx.invoked_with} is an owner only command, this will be reported to {owner.name}.")
            await owner.send(content=f"{ctx.author.mention} tried to use the owner only command{ctx.invoked_with}")
            return 


  #-------------------- STATIC METHODS --------------------
    @staticmethod
    async def get_channel_id(content):
        try:
            args= content.split(" ")
            if len(args) > 2:
                return False 

            #=== SPLIT, REMOVE MENTION WRAPPER AND CONVERT TO INT
            ch_id = args[1]
            ch_id = ch_id.replace("<", "").replace("#", "").replace(">", "")
            ch_id = int(ch_id)
            return ch_id

        except (IndexError, ValueError):
            return False

    @staticmethod
    async def get_user_id(content):
        try:
            args= content.split(" ")
            if len(args) > 2:
                return False 

            #=== SPLIT, REMOVE MENTION WRAPPER AND CONVERT TO INT
            user_id = args[1]
            user_id = user_id.replace("<", "").replace("@", "").replace("!", "").replace(">", "")
            user_id = int(user_id)
            return user_id

        except (IndexError, ValueError):
            return False
    
    @staticmethod
    def time_pat_to_hrs(content):
        '''
        Converts a string in format <xdxh> (d standing for days and h standing for hours) to amount of hours.
        eg: 3d5h would be 77 hours

        Args:
            (str) or (int)

        Returns:
            (int) or (None)
        '''
        args= content.split(" ")

        if len(args) > 2:
            return False 
        
        t = args[1]

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

        return False

    @staticmethod
    async def split_list(arr, size=100):
        """Custom function to break a list or string into an array of a certain size"""

        arrs = []

        while len(arr) > size:
            pice = arr[:size]
            arrs.append(pice)
            arr = arr[size:]

        arrs.append(arr)
        return arrs

    @staticmethod
    async def oneline_valid(content):
        try:
            args = content.split(" ")
            if len(args) > 1:
                return False 

            return True

        except (IndexError, ValueError):
            return False


  #-------------------- LISTENERS --------------------
    @commands.Cog.listener()
    async def on_ready(self):
        credentials = {"user": dblogin.user, "password": dblogin.pwrd, "database": dblogin.name, "host": dblogin.host}
        self.db = await asyncpg.create_pool(**credentials)
        dbconfig = await self.db.fetchrow(pgCmds.GET_GUILD_GALL_CONFIG)
        await self.db.close()

        self.gal_guild_id=      dbconfig['guild_id']
        self.gal_enable=        dbconfig['gall_nbl']

        self.gal_channel_ids=   dbconfig['gall_ch']
        guild = self.bot.get_guild(self.gal_guild_id)
        self.gal_channels=      [channel for channel in guild.channels if channel.id in dbconfig['gall_ch']]

        self.gal_text_expirein= dbconfig['gall_text_exp']
        self.gal_user_wl=       dbconfig['gall_user_wl']
        self.gal_allow_links=   dbconfig['gall_nbl_links']
        self.gal_link_wl=       dbconfig['gall_links']

        ###===== SCHEDULER
        self.scheduler.start()

    @commands.Cog.listener()
    async def on_message(self, msg):
        ###===== RETURN IF GALLERYS ARE DISABLED
        if not self.gal_enable:
            return 
        
        ###===== RETURN IF MESSAGE IS NOT FROM A GUILD
        if not msg.guild:
            return
        
        ###===== RETURN IF MESSAGE TYPE IS ANYTHING OTHER THAN A NORMAL MESSAGE.
        if not isinstance(msg, discord.MessageType.default):
            return

        if msg.channel in self.gal_channels:
            
            ###=== IF AUTHOR IS ALLOWED TO POST MESSAGES FREELY IN GALLERY CHANNELS
            if msg.author.id in self.gal_user_wl:
                return 

            valid = False

            ###=== IF MESSAGE HAS ATTACHMENTS ASSUME THE MESSAGE IS OF ART.
            if msg.attachments:
                valid = True 
            
            ###=== IF LINKS ARE ALLOWED IN GALLERY CHANNELS
            if self.gal_allow_links:
                #- get the links from msg content
                links = re.findall(r"(?P<url>http[s]?://[^\s]+)", msg.content)

                ###= IF ONLY CERTAIN LINKS ARE ALLOWED
                if self.gal_link_wl:
                    
                    #= LOOP THROUGH THE LINKS FROM THE MESSAGE CONTENT AND THE WHITELISTED LINKS
                    #= ASSUME VALID IF ONE LINK MATCHES. 
                    for link in links:
                        for wl_link in self.gal_link_wl:

                            if link.startswith(wl_link):
                                valid = True  
                                break

                else:
                    valid = True

            ###=== IF THE MESSAGE IS NOT VALID.
            if not valid:
                credentials = {"user": dblogin.user, "password": dblogin.pwrd, "database": dblogin.name, "host": dblogin.host}
                self.db = await asyncpg.create_pool(**credentials)

                self.db.execute(pgCmds.ADD_GALL_MSG, msg.id, msg.channel.id, msg.guild.id, msg.author.id, msg.created_at)
                await self.db.close()



            #regex = r"^(([^:/?#]+):)?(//([^/?#]*))?([^?#]*)(\?([^#]*))?(#(.*))?"
            #urls = re.findall( regex, text )

            #re.findall("(?P<url>http[s]?://[^\s]+)", t)
            #re.findall('http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\), ]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', t)

            #credentials = {"user": dblogin.user, "password": dblogin.pwrd, "database": dblogin.name, "host": dblogin.host}
            #self.db = await asyncpg.create_pool(**credentials)


  #-------------------- COMMANDS --------------------
    @commands.is_owner()
    @commands.command(pass_context=True, hidden=True, name='galenable', aliases=[])
    async def cmd_galenable(self, ctx):
        """
        [Bot Owner] Enables the gallery feature.

        Useage:
            [prefix]galenable
        """

        ###===== Write to database
        await self.db.execute(pgCmds.SET_GUILD_GALL_ENABLE, self.gal_guild_id)

        ###===== SET LOCAL COG VARIABLE
        self.gal_enable= True

        ###===== DELETE THE JOB IF IT EXISTS
        for job in self.jobstore.get_all_jobs():
            if ["_delete_gallery_messages"] == job.id.split(" "):
                self.scheduler.remove_job(job.id)

        ###===== ADD THE FUNCTION TO THE SCHEDULER
        self.scheduler.add_job(call_schedule,
                               'date',
                               id="_delete_gallery_messages",
                               run_date=get_next(hours=self.gal_text_expirein),
                               kwargs={"func": "_delete_gallery_messages"}
                               )

        await ctx.channel.send(content="Galleries are disabled.")

        return
        
    @commands.is_owner()
    @commands.command(pass_context=True, hidden=True, name='galdisable', aliases=[])
    async def cmd_galdisable(self, ctx):
        """
        [Bot Owner] Disables the gallery feature.

        Useage:
            [prefix]galdisable
        """
        ###===== Write to database
        await self.db.execute(pgCmds.SET_GUILD_GALL_DISABLE, self.gal_guild_id)

        ###===== SET LOCAL COG VARIABLE
        self.gal_enable= False

        ###===== DELETE THE JOB IF IT EXISTS
        for job in self.jobstore.get_all_jobs():
            if ["_delete_gallery_messages"] == job.id.split(" "):
                self.scheduler.remove_job(job.id)

        await ctx.channel.send(content="Galleries are disabled.")

        return

    @commands.is_owner()
    @commands.command(pass_context=True, hidden=True, name='enablegalleries', aliases=[])
    async def cmd_galaddchannel(self, ctx):
        """
        [Bot Owner] Add a channel to the list of active gallery channels

        Useage:
            [prefix]galaddchannel <channelid/mention>
        """

        ###===== VALIDATE INPUT
        ch_id = await Gallery.get_channel_id(ctx.message.content)

        if not ch_id:
            ctx.channel.send(content="`Useage: [p]galaddchannel <channelid/mention>, [Bot Owner] Add a channel to the list of active gallery channels.`", delete_after=Gallery.delete_after)

        ###===== ADD NEW CHANNEL ID TO LIST
        new_channel_ids = list(set(self.gal_channel_ids) + {ch_id})

        if Gallery.compare(self.gal_channel_ids, new_channel_ids):
            await ctx.channel.send(content=f"<#{ch_id}> is already a gallery channel.")
            return

        else:
            self.gal_channel_ids = new_channel_ids

        ###===== GET THE ACTUAL CHANNEL FROM THE GUILD
        if ctx.guild:
            guild = ctx.guild 
        else:
            guild = self.bot.get_guild(self.gal_guild_id)

        self.gal_channels = [channel for channel in guild.channels if channel.id in self.gal_channel_ids]

        ###===== WRITE DATA TO DATABASE
        await self.db.execute(pgCmds.SET_GUILD_GALL_CHLS, self.gal_channel_ids)

        ###===== END
        await ctx.channel.send(content=f"<#{ch_id}> has been made a gallery channel.")
        return

    @commands.is_owner()
    @commands.command(pass_context=True, hidden=True, name='galremchannel', aliases=[])
    async def cmd_galremchannel(self, ctx):
        """
        [Bot Owner] Removes a channel to the list of active gallery channels

        Useage:
            [prefix]galremchannel <channelid/mention>
        """

        ch_id = await Gallery.get_channel_id(ctx.message.content)

        if not ch_id:
            ctx.channel.send(content="`Useage: [p]galremchannel <channelid/mention>, [Bot Owner] Removes a channel to the list of active gallery channels.`", delete_after=Gallery.delete_after)

        ###===== REMOVE CHANNEL ID FROM LIST
        try:
            self.gal_channel_ids.remove(ch_id)

        except ValueError:
            await ctx.channel.send(content=f"<#{ch_id}> isn't a gallery channel.")
            return  

        ###===== GET THE ACTUAL CHANNEL FROM THE GUILD
        if ctx.guild:
            guild = ctx.guild 
        else:
            guild = self.bot.get_guild(self.gal_guild_id)

        self.gal_channels = [channel for channel in guild.channels if channel.id in self.gal_channel_ids]

        ###===== WRITE DATA TO DATABASE
        await self.db.execute(pgCmds.SET_GUILD_GALL_CHLS, self.gal_channel_ids)
        await self.db.execute(pgCmds.DEL_GALL_MSGS_FROM_CH, ch_id, self.gal_guild_id)

        ###===== END
        await ctx.channel.send(content=f"<#{ch_id}> is no longer a gallery channel.")
        return

    @commands.is_owner()
    @commands.command(pass_context=True, hidden=True, name='galsetexpirehours', aliases=[])
    async def cmd_galsetexpirehours(self, ctx):
        """
        [Bot Owner] Sets how long the bot should wait to delete text only messages from gallery channels

        Useage:
            [prefix]galsetexpirehours <hours>
        """
        new_time = Gallery.time_pat_to_hrs(ctx.message.content)

        await self.db.execute(pgCmds.SET_GUILD_GALL_EXP, new_time)

        resetJob = False

        ###===== RESET THE JOB IF IT EXISTS
        for job in self.jobstore.get_all_jobs():
            if ["_delete_gallery_messages"] == job.id.split(" "):
                self.scheduler.remove_job(job.id)
                resetJob = True

        if resetJob:
            ###===== ADD THE FUNCTION TO THE SCHEDULER
            self.scheduler.add_job(call_schedule,
                                    'date',
                                    id="_delete_gallery_messages",
                                    run_date=get_next(hours=self.gal_text_expirein),
                                    kwargs={"func": "_delete_gallery_messages"}
                                    )

            await ctx.channel.send(content=f"Text message expirey time has been set to {new_time} hours and the scheduler was reset.")
            return

        await ctx.channel.send(content=f"Text message expirey time has been set to {new_time} hours.")
        return
    
    @commands.is_owner()
    @commands.command(pass_context=True, hidden=True, name='galadduserwl', aliases=[])
    async def cmd_galadduserwl(self, ctx):
        """
        [Bot Owner] Adds a user to the gallery user whitelist. Allowing them to post in Gallery channels.

        Useage:
            [prefix]galadduserwl <userid/mention>
        """ 

        ###===== CHECK IF INPUT IS VALID
        user_id = Gallery.get_user_id(ctx.message.content)

        if not user_id:
            return

        ###===== ADD USER ID TO THE WHITELIST
        new_user_whitelist = list(set(self.gal_user_wl) + {user_id})

        if Gallery.compare(self.gal_user_wl, new_user_whitelist):
            await ctx.channel.send(content=f"<@{user_id}> is alreadt in the gallery whitelist.", delete_after=Gallery.delete_after)
            return 

        else:
            self.gal_user_wl = new_user_whitelist

        ###===== WRITE TO THE DATABASE
        await self.db.execute(pgCmds.SET_GUILD_GALL_USER_WL, self.gal_user_wl, self.gal_guild_id)

        ###===== RETURN
        await ctx.channel.send(content=f"<@{user_id}> has been added to the gallery whitelist.", delete_after=Gallery.delete_after)
        return

    @commands.is_owner()
    @commands.command(pass_context=True, hidden=True, name='galremuserwl', aliases=[])
    async def cmd_galremuserwl(self, ctx):
        """
        [Bot Owner] Remomes a user to the gallery user whitelist.

        Useage:
            [prefix]galremuserwl <userid/mention>
        """

        ###===== CHECK IF INPUT IS VALID
        user_id = Gallery.get_user_id(ctx.message.content)
        
        if not user_id:
            return

        ###===== REMOVE USER FROM WHITELIST
        try:
            self.gal_user_wl.remove(user_id)

        except ValueError:

            #=== IF USER IS NOT ON THE WHITELIST
            await ctx.channel.send(content=f"<@{user_id}> was not on the gallery whitelist.", delete_after=Gallery.delete_after)
            return

        ###===== WRITE TO DATABASE
        await self.db.execute(pgCmds.SET_GUILD_GALL_USER_WL, self.gal_user_wl, self.gal_guild_id)

        ###===== RETURN 
        await ctx.channel.send(content=f"<@{user_id}> has been removed from the gallery whitelist.", delete_after=Gallery.delete_after)
        return

    ### ENABLE LINKS
    @commands.is_owner()
    @commands.command(pass_context=True, hidden=True, name='galenablelinks', aliases=[])
    async def cmd_galenablelinks(self, ctx):
        """
        [Bot Owner] Allow links in the gallery channels.

        Useage:
            [prefix]galenablelinks <channelid/mention>
        """

        valid = Gallery.oneline_valid(ctx.message.content)

        if not valid:
            return

        self.gal_allow_links=True
        
        ###===== WRITE TO THE DATABASE
        await self.db.execute(pgCmds.SET_GUILD_GALL_LINK_ENABLE)

        ###===== RETURN
        await ctx.channel.send(content="Links are now allowed in the gallery channels.", delete_after=Gallery.delete_after)
        return

    ### BLOCK LINKS
    @commands.is_owner()
    @commands.command(pass_context=True, hidden=True, name='galdisablelinks', aliases=[])
    async def cmd_galdisablelinks(self, ctx):
        """
        [Bot Owner] Block links in the gallery channels.

        Useage:
            [prefix]galdisablelinks <channelid/mention>
        """

        valid = Gallery.oneline_valid(ctx.message.content)

        if not valid:
            return

        self.gal_allow_links=False

        ###===== WRITE TO THE DATABASE
        await self.db.execute(pgCmds.SET_GUILD_GALL_LINK_DISABLE)

        ###===== RETURN
        await ctx.channel.send(content="Links are no longer allowed in the gallery channels.", delete_after=Gallery.delete_after)
        return

    ### ADD LINK WHITELIST
    @commands.is_owner()
    @commands.command(pass_context=True, hidden=True, name='galaddlinkuwl', aliases=[])
    async def cmd_galaddlinkuwl(self, ctx):
        """
        [Bot Owner] Adds a link from gallery link whitelist.

        Useage:
            [prefix]galaddlinkuwl <startoflink>
        """

        links = re.findall(r"(?P<url>http[s]?://[^\s]+)", ctx.message.content)

        if not links:
            await ctx.channel.send('`Useage: [p]galaddlinkuwl <startoflink>, [Bot Owner] Adds a link from gallery link whitelist.`')
        
        ###===== ADD THE NEW LINKS TO THE WHITELIST
        new_gal_link_wl = list(set(self.gal_link_wl) + set(links))

        if Gallery.compare(new_gal_link_wl, self.gal_link_wl):
            await ctx.channel.send(content="{}\n are already in the gallery link whitelist.".format('\n'.join(links)), delete_after=Gallery.delete_after)
            return  
        
        else:
            self.gal_link_wl = new_gal_link_wl

        ###===== WRITE TO THE DATABASE
        await self.db.execute(pgCmds.SET_GUILD_GALL_LINKS, self.gal_link_wl, self.gal_guild_id)

        ###===== RETURN
        await ctx.channel.send(content="{}\n have been added to the gallery link whitelist.".format('\n'.join(links)), delete_after=Gallery.delete_after)
        return
 
    ### REM LINK WHITELIST
    @commands.is_owner()
    @commands.command(pass_context=True, hidden=True, name='galremlinkuwl', aliases=[])
    async def cmd_galremlinkuwl(self, ctx):
        """
        [Bot Owner] Removes a link from gallery link whitelist.

        Useage:
            [prefix]galremlinkuwl <startoflink>
        """

        links = re.findall(r"(?P<url>http[s]?://[^\s]+)", ctx.message.content)

        if not links:
            await ctx.channel.send('Useage: [p]galremlinkuwl <startoflink>, [Bot Owner] Removes a link from gallery link whitelist.')

        ###===== REMOVE THE LINKS FROM THE LIST
        new_gal_link_wl = list(set(self.gal_link_wl) - set(links))

        if Gallery.compare(new_gal_link_wl, self.gal_link_wl):
            await ctx.channel.send(content="{}\n are not in the gallery link whitelist.".format('\n'.join(links)), delete_after=Gallery.delete_after)
            return  
        
        else:
            self.gal_link_wl = new_gal_link_wl

        ###===== WRITE TO THE DATABASE
        await self.db.execute(pgCmds.SET_GUILD_GALL_LINKS, self.gal_link_wl, self.gal_guild_id)

        ###===== RETURN
        await ctx.channel.send(content="{}\n have been removed from the gallery link whitelist.".format('\n'.join(links)), delete_after=Gallery.delete_after)
        return

    ### SPECIAL
    @commands.is_owner()
    @commands.command(pass_context=True, hidden=True, name='galloadsettings', aliases=[])
    async def cmd_galloadsettings(self, ctx):
        ###===== OPEN THE SETUP.INI FILE
        config = Config()

        ###===== WRITE DATA FROM THE SETUP.INI FILE TO THE DATABASE
        await self.db.execute(pgCmds.SET_GUILD_GALL_CONFIG, config.galEnable, config.gallerys["chls"], config.gallerys['expire_in'], config.gallerys["user_wl"], config.gallerys["links"], config.gallerys['link_wl'])

        ###===== UPDATE THE SETTINGS IN THE LOCAL COG
        self.gal_enable=        config.galEnable

        guild = self.bot.get_guild(self.gal_guild_id)
        self.gal_channels=      [channel for channel in guild.channels if channel.id in config.gallerys["chls"]]

        self.gal_text_expirein= config.gallerys['expire_in']
        self.gal_user_wl=       config.gallerys["user_wl"]
        self.gal_allow_links=   config.gallerys["links"]
        self.gal_link_wl=       config.gallerys['link_wl']

        ###===== RETURN
        await ctx.channel.send(content="Gallery information has been updated from the setup.ini file", delete_after=15)
        return


  #-------------------- SCHEDULING --------------------
    def job_missed(self, event):
        """
        This exists too
        """

        asyncio.ensure_future(call_schedule(*event.job_id.split(" ")))

    @staticmethod
    def get_id_args(func, arg):
        """
        I have no damn idea what this does
        """

        return "{} {}".format(func.__name__, arg)

    @commands.is_owner()
    @commands.command(pass_context=True, hidden=True, name='galinitiateschedule', aliases=[])
    async def cmd_galinitiateschedule(self, ctx):
        
        ###===== DELETE THE JOB IF IT ALREADY EXISTS
        for job in self.jobstore.get_all_jobs():
            if ["_delete_gallery_messages"] == job.id.split(" "):
                self.scheduler.remove_job(job.id)

        ###===== ADD THE FUNCTION TO THE SCHEDULER
        self.scheduler.add_job(call_schedule,
                               'date',
                               id="_delete_gallery_messages",
                               run_date=get_next(hours=self.gal_text_expirein),
                               kwargs={"func": "_delete_gallery_messages"}
                               )

        ###===== RETURN
        ctx.channel.send(content=f"Gallery schedule has been set for {get_next(hours=self.gal_text_expirein)}")

        return


    async def _delete_gallery_messages(self):
        ###===== QUIT ID GALLERIES ARE DISABLED.
        if not self.gal_enable:
            return 

        ###===== CONNECT TO THE DATABASE
        credentials = {"user": dblogin.user, "password": dblogin.pwrd, "database": dblogin.name, "host": dblogin.host}
        self.db = await asyncpg.create_pool(**credentials)

        after = datetime.datetime.utcnow() - datetime.timedelta(hours=self.gal_text_expirein)

        t = await self.db.fetch(pgCmds.GET_GALL_MSG_AFTER, after)
        ch_ids = await self.db.fetch(pgCmds.GET_GALL_CHIDS_AFTER, after)

        await self.db.close()

        ###===== TURNING THE DATA INTO SOMETHING MORE USEFUL
        ch_ids = [ch_id['ch_id'] for ch_id in ch_ids]
        fast_delete = dict()
        slow_delete = []

        for ch_id in ch_ids:
            fast_delete[ch_id] = []

        now = datetime.datetime.utcnow()
        delta = datetime.timedelta(days=13, hours=12)

        for record in t:
            ###=== IF MESSAGE IS OLDER THAN 13 DAYS AND 12 HOURS
            if bool((now - record['timestamp']) > delta):
                slow_delete.append(record)

            ###=== IF MESSAHE IS YOUNGER THAN 13 DAYS AND 12 HOURS
            else:
                fast_delete[record['ch_id']].append(record['msg_id'])

        ###===== IF THERE IS FAST DELETE DATA   
        # WITH FAST DELETE MESSAGES WE CAN DELETE MESSAGES IN BULK OF 100
        if fast_delete:
            for ch_id in fast_delete.keys():
                msgs_ids = Gallery.split_list(fast_delete[ch_id], 100)

                for msg_ids in msgs_ids:
                    if len(msg_ids) > 1:

                        await self.bot.http.delete_messages(ch_id, msg_ids, reason="Deleting Gallery Messages")
                        await asyncio.sleep(0.5)

                    else:
                        msg_id = msg_ids[0]
                        await self.bot.http.delete_message(ch_id, msg_id, reason="Deleting Gallery Messages")
                        await asyncio.sleep(0.5)

        ###===== IF THERE IS SLOW DELETE DATA
        # WE CANNOT DELETE THESE MESSAGES IN BULK, ONLY ONE BY ONE.
        if slow_delete:
            for record in slow_delete:

                await self.bot.http.delete_message(record['ch_id'], record['msg_id'], reason="Deleting Gallery Messages")
                await asyncio.sleep(0.5)


        ###==== LOOP THE SCHEDULER
        self.scheduler.add_job( call_schedule,
                                'date',
                                id="_delete_gallery_messages",
                                run_date=get_next(hours=self.gal_text_expirein),
                                kwargs={"func": "_delete_gallery_messages"}
                                )
        return



def setup(bot):
    bot.Gallery(Gallery(bot))


async def call_schedule(func=None, arg=None):
    await getattr(Gallery.bot, func)(arg)