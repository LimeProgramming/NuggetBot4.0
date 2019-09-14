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
from nuggetbot.plugins.cog_utils import SAVE_COG_CONFIG, LOAD_COG_CONFIG
from nuggetbot.config import Config
from nuggetbot.database import DatabaseCmds as pgCmds
from .ctx_decorators import in_channel, is_core, in_channel_name, in_reception, has_role, is_high_staff, is_any_staff
#https://discordpy.readthedocs.io/en/latest/ext/commands/api.html#bot
import dblogin 

class Gallery(commands.Cog):
    """Handle the Gallery channels."""


    delete_after = 15
    compare = lambda x, y: collections.Counter(x) == collections.Counter(y)

    def __init__(self, bot):
        Gallery.bot = self
        self.bot = bot
        self.db = None

        self.cogset = dict()

        self.gal_channels=      []

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
        await ctx.message.delete()

        return

    async def on_cog_command_error(self, ctx, error):
        if isinstance(error, discord.ext.commands.errors.NotOwner):
            try:
                owner = (self.bot.application_info()).owner
            except:
                owner = self.bot.get_guild(self.cogset['guild_id']).owner()

            await ctx.channel.send(content=f"```diff\n- {ctx.prefix}{ctx.invoked_with} is an owner only command, this will be reported to {owner.name}.")
            await owner.send(content=f"{ctx.author.mention} tried to use the owner only command{ctx.invoked_with}")
            return 


  #-------------------- STATIC METHODS --------------------
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

  #-------------------- LISTENERS --------------------
    @commands.Cog.listener()
    async def on_ready(self):
        self.cogset = await LOAD_COG_CONFIG(cogname="gallery")
        if not self.cogset:
            self.cogset= dict(
                guild_id=      0,
                enable=        False, 
                channel_ids=   [],
                text_expirein= None,
                user_wl=       [],
                allow_links=   False,
                link_wl=       []
            )

            await SAVE_COG_CONFIG(self.cogset, cogname="gallery")

        ###===== SCHEDULER
        self.scheduler.start()

    @commands.Cog.listener()
    async def on_message(self, msg):
        ###===== RETURN IF GALLERYS ARE DISABLED
        if not self.cogset['enable']:
            return 
        
        ###===== RETURN IF MESSAGE IS NOT FROM A GUILD
        if not msg.guild:
            return
        
        ###===== RETURN IF MESSAGE TYPE IS ANYTHING OTHER THAN A NORMAL MESSAGE.
        if not bool(msg.type == discord.MessageType.default):
            return

        if msg.channel in self.gal_channels:
            
            ###=== IF AUTHOR IS ALLOWED TO POST MESSAGES FREELY IN GALLERY CHANNELS
            if msg.author.id in self.cogset['user_wl']:
                return 

            valid = False

            ###=== IF MESSAGE HAS ATTACHMENTS ASSUME THE MESSAGE IS OF ART.
            if msg.attachments:
                valid = True 
            
            ###=== IF LINKS ARE ALLOWED IN GALLERY CHANNELS
            if self.cogset['allow_links']:
                #- get the links from msg content
                links = re.findall(r"(?P<url>http[s]?://[^\s]+)", msg.content)

                ###= IF ONLY CERTAIN LINKS ARE ALLOWED
                if self.cogset['link_wl']:
                    
                    #= LOOP THROUGH THE LINKS FROM THE MESSAGE CONTENT AND THE WHITELISTED LINKS
                    #= ASSUME VALID IF ONE LINK MATCHES. 
                    for link in links:
                        for wl_link in self.cogset['link_wl']:

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


  #-------------------- COMMANDS --------------------
    @commands.is_owner()
    @commands.command(pass_context=True, hidden=True, name='galenable', aliases=[])
    async def cmd_galenable(self, ctx):
        """
        [Bot Owner] Enables the gallery feature.

        Useage:
            [prefix]galenable
        """

        ###===== SET LOCAL COG VARIABLE
        self.cogset['enable']= True

        ###===== ADD THE FUNCTION TO THE SCHEDULER
        self.scheduler.add_job(call_schedule,
                                'date',
                                id="_delete_gallery_messages",
                                run_date=get_next(hours=self.cogset['text_expirein']),
                                kwargs={"func": "_delete_gallery_messages"}
                                )

        ###===== SAVE SETTINGS  
        await SAVE_COG_CONFIG(self.cogset, cogname="gallery")

        await ctx.channel.send(content="Galleries are **enabled**.")

        return
        
    @commands.is_owner()
    @commands.command(pass_context=True, hidden=True, name='galdisable', aliases=[])
    async def cmd_galdisable(self, ctx):
        """
        [Bot Owner] Disables the gallery feature.

        Useage:
            [prefix]galdisable
        """
        ###===== SET LOCAL COG VARIABLE
        self.cogset['enable']= False

        ###===== SAVE SETTINGS  
        await SAVE_COG_CONFIG(self.cogset, cogname="gallery")

        ###===== DELETE THE JOB IF IT EXISTS
        for job in self.jobstore.get_all_jobs():
            if ["_delete_gallery_messages"] == job.id.split(" "):
                self.scheduler.remove_job(job.id)

        await ctx.channel.send(content="Galleries are disabled.")

        return

    @commands.is_owner()
    @commands.command(pass_context=True, hidden=True, name='galtogglechannel', aliases=[])
    async def cmd_galtogglechannel(self, ctx, channel):
        """
        [Bot Owner] Add or remove a channel to the list of active gallery channels

        Useage:
            [prefix]galaddchannel <channelid/mention>
        """

        ###===== GET CHANNEL ID
        try:
            ch_id = int(channel.lower().replace('<').replace('>').replace('#').strip())

        except ValueError:
            ctx.send_help('galtogglechannel', delete_after=Gallery.delete_after)
        
        ret_msg=""

        ###===== REMOVE CHANNEL ID FROM LIST
        if ch_id in self.cogset['channel_ids']:
            self.cogset['channel_ids'].remove(ch_id)

            ret_msg = f"<#{ch_id}> is no longer a gallery channel."

            ###=== DELETE LOGGED MESSAGES FROM DATABASE
            await self.db.execute(pgCmds.DEL_GALL_MSGS_FROM_CH, ch_id, self.cogset['guild_id'])

        ###===== ADD CHANNEL ID TO LIST
        else:
            self.cogset['channel_ids'] = list(set(self.cogset['channel_ids']) + {ch_id})
            ret_msg = f"<#{ch_id}> has been made a gallery channel."

        ###===== GET THE CHANNELS
        if ctx.guild:
            guild = ctx.guild 
        else:
            guild = self.bot.get_guild(self.cogset['guild_id'])

        self.gal_channels = [channel for channel in guild.channels if channel.id in self.cogset['channel_ids']]

        ###===== SAVE SETTINGS  
        await SAVE_COG_CONFIG(self.cogset, cogname="gallery")

        ###===== END
        await ctx.channel.send(content=ret_msg, delete_after=Gallery.delete_after)
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
        
        self.cogset['text_expirein'] = new_time

        await SAVE_COG_CONFIG(self.cogset, cogname="gallery")

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
                                    run_date=get_next(hours=self.cogset['text_expirein']),
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
            await ctx.send_help('galadduserwl', delete_after=15)
            return

        ###===== ADD USER ID TO THE WHITELIST
        new_user_whitelist = list(set(self.cogset['user_wl']) + {user_id})

        if Gallery.compare(self.cogset['user_wl'], new_user_whitelist):
            await ctx.channel.send(content=f"<@{user_id}> is alreadt in the gallery whitelist.", delete_after=Gallery.delete_after)
            return 

        else:
            self.cogset['user_wl'] = new_user_whitelist

        ###===== WRITE TO THE DATABASE
        await SAVE_COG_CONFIG(self.cogset, cogname="gallery")

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
            await ctx.send_help('galremuserwl', delete_after=15)
            return

        ###===== REMOVE USER FROM WHITELIST
        try:
            self.cogset['user_wl'].remove(user_id)

        except ValueError:
            #=== IF USER IS NOT ON THE WHITELIST
            await ctx.channel.send(content=f"<@{user_id}> was not on the gallery whitelist.", delete_after=Gallery.delete_after)
            return

        ###===== WRITE TO DATABASE
        await SAVE_COG_CONFIG(self.cogset, cogname="gallery")

        ###===== RETURN 
        await ctx.channel.send(content=f"<@{user_id}> has been removed from the gallery whitelist.", delete_after=Gallery.delete_after)
        return

    @commands.is_owner()
    @commands.command(pass_context=True, hidden=False, name='galltogglelinks', aliases=[])
    async def cmd_galtogglelinks(self, ctx, tog=None):
        """
        [Bot Owner] Toggle links in the gallery channels or you can set if links are allowed with true or false.

        Useage:
            [prefix]galltogglelinks []
        """

        update = not self.cogset['allow_links']

        ###===== IF EXPLICITLY SETTING LINK STATUS
        if tog is not None:
            if tog.lower() in ['y', 'true', 'ture', 't']:
                update = True 

                if self.cogset['allow_links']:
                    await ctx.channel.send("Galleries are already **enabled**.", delete_after=Gallery.delete_after)

            elif tog.lower() in ['n', 'false', 'flase', 'f']:
                update = False 

                if not self.cogset['allow_links']:
                    await ctx.channel.send("Galleries are already **disabled**.", delete_after=Gallery.delete_after)
        
        self.cogset['allow_links']=update
            
        ###===== WRITE TO THE DATABASE
        await SAVE_COG_CONFIG(self.cogset, cogname="gallery")

        ###===== RETURN
        await ctx.channel.send(content=f"Links in the gallery channels is now set to{update}.", delete_after=Gallery.delete_after)
        return

    ### ADD LINK WHITELIST
    @commands.is_owner()
    @commands.command(pass_context=True, hidden=False, name='galaddlinkuwl', aliases=[])
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
        new_gal_link_wl = list(set(self.cogset['link_wl']) + set(links))

        if Gallery.compare(new_gal_link_wl, self.cogset['link_wl']):
            await ctx.channel.send(content="{}\n are already in the gallery link whitelist.".format('\n'.join(links)), delete_after=Gallery.delete_after)
            return  
        
        else:
            self.cogset['link_wl'] = new_gal_link_wl

        ###===== WRITE TO THE DATABASE
        await SAVE_COG_CONFIG(self.cogset, cogname="gallery")

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
        new_gal_link_wl = list(set(self.cogset['link_wl']) - set(links))

        if Gallery.compare(new_gal_link_wl, self.cogset['link_wl']):
            await ctx.channel.send(content="{}\n are not in the gallery link whitelist.".format('\n'.join(links)), delete_after=Gallery.delete_after)
            return  
        
        else:
            self.cogset['link_wl'] = new_gal_link_wl

        ###===== WRITE TO THE DATABASE
        await SAVE_COG_CONFIG(self.cogset, cogname="gallery")

        ###===== RETURN
        await ctx.channel.send(content="{}\n have been removed from the gallery link whitelist.".format('\n'.join(links)), delete_after=Gallery.delete_after)
        return

    ### SPECIAL
    @commands.is_owner()
    @commands.command(pass_context=True, hidden=True, name='galloadsettings', aliases=[])
    async def cmd_galloadsettings(self, ctx):
        """
        [Bot Owner] Loads gallery settings from the setup.ini file

        Useage:
            [prefix]galloadsettings
        """

        config = Config()

        ###===== UPDATE THE SETTINGS IN THE LOCAL COG
        self.cogset['guild_id'] =       config.target_guild_id
        self.cogset['enable']=          config.galEnable
        self.cogset['channel_ids'] =    config.gallerys["chls"]
        self.cogset['text_expirein']=   config.gallerys['expire_in']
        self.cogset['user_wl']=         config.gallerys["user_wl"]
        self.cogset['allow_links']=     config.gallerys["links"]
        self.cogset['link_wl']=         config.gallerys['link_wl']

        guild =                 self.bot.get_guild(self.cogset['guild_id'])
        self.gal_channels=      [channel for channel in guild.channels if channel.id in self.cogset['channel_ids']]
        
        ###===== SAVE COG SETTINGS
        await SAVE_COG_CONFIG(self.cogset, cogname="gallery")

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
                               run_date=get_next(hours=self.cogset['text_expirein']),
                               kwargs={"func": "_delete_gallery_messages"}
                               )

        ###===== RETURN
        ctx.channel.send(content=f"Gallery schedule has been set for {get_next(hours=self.cogset['text_expirein'])}")

        return


    async def _delete_gallery_messages(self):
        ###===== QUIT ID GALLERIES ARE DISABLED.
        if not self.cogset['enable']:
            return 

        ###===== CONNECT TO THE DATABASE
        credentials = {"user": dblogin.user, "password": dblogin.pwrd, "database": dblogin.name, "host": dblogin.host}
        self.db = await asyncpg.create_pool(**credentials)

        after = datetime.datetime.utcnow() - datetime.timedelta(hours=self.cogset['text_expirein'])

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
                                run_date=get_next(hours=self.cogset['text_expirein']),
                                kwargs={"func": "_delete_gallery_messages"}
                                )
        return

def setup(bot):
    bot.Gallery(Gallery(bot))

async def call_schedule(func=None, arg=None):
    await getattr(Gallery.bot, func)(arg)