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

import sys
import json
import random
import dblogin 
import discord
import asyncio
import asyncpg
import datetime
from typing import Union
from functools import partial
from discord.ext import commands

from apscheduler import events
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from nuggetbot.config import Config
from nuggetbot.util import gen_embed as GenEmbed
from nuggetbot.utils import get_next
from nuggetbot.database import DatabaseCmds as pgCmds
from nuggetbot.util.chat_formatting import RANDOM_DISCORD_COLOR, GUILD_URL_AS, AVATAR_URL_AS

from .util import checks
from .util import images
from .util.misc import GET_AVATAR_BYTES

description = """
Handling of new members to the guild.

**Newly Joined Members**
    > When a member joins the guild they will receive the auto roles and be scheduled for a kick 14 days after they join. 
    > Every message from them posted or mentioning them in the entrance gate channel will be logged to the database.
    > IF the new user Runs the agree command, it'll do the following 
        - Cancel the kick
        - Grant the member and newmember role
        - Remove the gated role
        - Schedule the removal of newmember role 14 days from the run time.
        - Delete messages from the member or pinging the member from the gate channel.

**Logging Entrance Gate MSG'S**
    > Messages sent by a member with the gated role to the entrance gate channel get logged into the databases welcome_msg table.
    > This also applies to member pings, when a gated member is pinged in a message that msg gets logged to the database as if it were from them. This is for the sake of deleting these messages at a later time.
    > When 'del_user_welcome' is called it will delete any *logged* messages from the guild and from the database which are applicable to the reliant user. This keeps the entrance channel clear from clutter for the sake of mobile users and anonymity.


    

"""


class Days():
    gated = 14
    newmember = 14

class NewMembers(commands.Cog):
    """Private feedback system."""

    config = None 
    delete_after = 15
    
    def __init__(self, bot):
        self.bot = bot
        NewMembers.bot = self
        NewMembers.config = Config()
        self.cogset = dict()
        self.roles = dict()
        self.db = None
        self.tguild = None

        self.jobstore = SQLAlchemyJobStore(url='sqlite:///jobs.sqlite')
        jobstores = {"default": self.jobstore}
        self.scheduler = AsyncIOScheduler(jobstores=jobstores)
        self.scheduler.add_listener(self.job_missed, events.EVENT_JOB_MISSED)

  # -------------------- LOCAL COG STUFF --------------------
    async def connect_db(self):
        """
        Connects to the database using variables set in the dblogin.py file.
        """

        credentials = {"user": dblogin.user, "password": dblogin.pwrd, "database": dblogin.name, "host": dblogin.host}
        self.db = await asyncpg.create_pool(**credentials)

        return

    async def disconnet_db(self):
        """
        Closes the connection to the database.
        """
        await self.db.close()

        return

    @asyncio.coroutine
    async def cog_command_error(self, ctx, error):
        print('Ignoring exception in {}'.format(ctx.invoked_with), file=sys.stderr)
        print(error)

  # -------------------- LISTENERS --------------------
    @commands.Cog.listener()
    async def on_ready(self): 
        
        # ===== LOG INVITES
        inviteLog = await self.__get_invite_info()

        if inviteLog is not None:
            await self.db.execute(pgCmds.ADD_INVITES, json.dumps(inviteLog))
            self.safe_print("[Log] Invite information has been logged.")
        
        else:
            self.safe_print("[Log] No invite information to log.")

        # ===== GET IMPORTANT ROLES READY
        self.tguild = self.bot.get_guild(NewMembers.config.target_guild_id)
        
        self.roles['member']=       discord.utils.get(self.tguild.roles, id=NewMembers.config.roles['member'])
        self.roles['newmember']=    discord.utils.get(self.tguild.roles, id=NewMembers.config.roles['newmember'])
        self.roles['gated']=        discord.utils.get(self.tguild.roles, id=NewMembers.config.roles['gated'])

        # ===== SCHEDULER
        self.scheduler.start()
        self.scheduler.print_jobs()
        await self.check_new_members()
    
    @commands.Cog.listener()
    async def on_resume(self):

        # ===== WAIT FOR BOT TO FINISH SETTING UP
        await self.bot.wait_until_ready()

        # ===== LOG INVITES
        inviteLog = await self.__get_invite_info()

        if inviteLog is not None:
            await self.db.execute(pgCmds.ADD_INVITES, json.dumps(inviteLog))
            self.safe_print("[Log] Invite information has been logged.")
        
        else:
            self.safe_print("[Log] No invite information to log.")

    @commands.Cog.listener()
    async def on_member_join(self, m): 
        ###===== WAIT FOR THE BOT TO BE FINISHED SETTING UP
        await self.bot.wait_until_ready()

        # ------------------------- GET INVITE INFO -------------------------
        invite = await self.__get_invite_used()

        # ------------------------- LOG NEW MEMBER -------------------------
        embed = await GenEmbed.getMemJoinStaff(member=m, invite=invite)
        await self.bot.send_msg_chid(NewMembers.config.channels['bot_log'], embed=embed)

        # ------------------------- SEND WELCOME MESSAGE -------------------------
        fmt = random.choice([f'Oh {m.mention} steps up to my dinner plate, I mean to {m.guild.name}!',
                            f"I'm so excited to have {m.mention} join us, that I think I'll tear up the couch!",
                            f"Well dip me in batter and call me a nugget, {m.mention} has joined us at {m.guild.name}!",
                            f"The gates of {m.guild.name} have opened to: {m.mention}.",
                            f"Attention {m.mention}, all new members of {m.guild.name} must be approved by me and I approve of you *hugs*."])

        #fmt += "\nPlease give the rules in <#" + NewMembers.config.channels['public_rules_id'] + "> a read and when you're ready make a post in <#" + NewMembers.config.channels['entrance_gate'] + "> saying that you agreed to the rules."

        await asyncio.sleep(0.5)
        welMSG = await self.bot.send_msg_chid(NewMembers.config.channels['bot_log'], content=fmt)

        # ------------------------- Update Database -------------------------
        await self.db.execute(pgCmds.ADD_WEL_MSG, welMSG.id, welMSG.channel.id, welMSG.guild.id, m.id)
        await self.db.execute(pgCmds.ADD_MEMBER_FUNC, m.id, m.joined_at, m.created_at)

        # ------------------------- AUTO ROLES -------------------------
        if NewMembers.config.roles["autoroles"]:
            for r_id in NewMembers.config.roles['autoroles']:
                asyncio.wait(0.4)
                role = discord.utils.get(m.guild.roles, id=r_id)
                await m.add_roles(role, reason="Auto Roles")

        # ------------------------- Schedule a kick -------------------------
        await self.schedule_kick(m, daysUntilKick=Days.gated, days=Days.gated)
    
    @commands.Cog.listener()
    async def on_member_remove(self, m):
        # ===== WAIT FOR THE BOT TO BE FINISHED SETTING UP
        await self.bot.wait_until_ready()

        # ===== IGNORE NON-TARGET GUILDS
        if m.guild.id != NewMembers.config.target_guild_id:
            return 
        
        # ------------------------- CANCEL SCHEDULED KICK -------------------------
        await self.cancel_scheduled_kick(member=m)

        # ------------------------- IF MEMBER IS KICKED OR BANNED -------------------------
        # ===== WAIT A BIT TO MAKE SURE THE GUILD AUDIT LOGS ARE UPDATED BEFORE READING THEM
        await asyncio.sleep(0.2)

        banOrKick = list() 
        past_id = discord.utils.time_snowflake(datetime.datetime.utcnow() - datetime.timedelta(seconds=10), high=True)

        try:
            for i in [discord.AuditLogAction.ban, discord.AuditLogAction.kick]:

                async for entry in m.guild.audit_logs(limit=30, action=i, oldest_first=False):
                    if entry.id >= past_id and entry.target.id == m.id:

                        if banOrKick:
                            if entry.id > banOrKick[4]:
                                banOrKick = [entry.action, entry.target, entry.user, entry.reason or "None", entry.id]

                        else:
                            banOrKick = [entry.action, entry.target, entry.user, entry.reason or "None", entry.id]

        except discord.errors.Forbidden:
            self.safe_print("[Info]  Missing view_audit_log permission.")

        except discord.errors.HTTPException:
            self.safe_print("[Info]  HTTP error occurred, likely being rate limited or blocked by CloudFlare. Restart recommended.")

        # ------------------------- REMOVED MEMBER LOGGING -------------------------
        # ===== STAFF ONLY LOGGING
        embed = await GenEmbed.getMemLeaveStaff(m, banOrKick)
        await self.bot.send_msg_chid(NewMembers.config.channels['bot_log'], embed=embed)

        # ===== PUBLIC VISABLE LOGGING, ONLY APPLICABLE IF EXMEMBER WAS GIVEN THE CORE ROLE
        if discord.utils.get(m.roles, id=NewMembers.config.roles['member']):
            embed = await GenEmbed.getMemLeaveUser(m, banOrKick)
            await self.bot.send_msg_chid(NewMembers.config.channels['public_bot_log'], embed=embed)

        # ------------------------- REMOVE WELCOME MESSAGES -------------------------
        await self.del_user_welcome(m)
        
        # ------------------------- UPDATE THE DATABASE -------------------------
        await self.db.execute(pgCmds.REMOVE_MEMBER_FUNC, m.id)

        # ===== END
        return
    
    #@commands.Cog.listener()
    async def on_member_update(self, before, after):
        """When there is an update to a users user data"""

        # ===== WAIT FOR THE BOT TO BE FINISHED SETTING UP
        await self.bot.wait_until_ready()

        # ===== IGNORE NON-TARGET GUILDS
        if before.guild.id != self.config.target_guild_id:
            return

        return

    @commands.Cog.listener()
    async def on_message(self, msg):
        # ===== WAIT FOR THE BOT TO BE FINISHED SETTING UP
        await self.bot.wait_until_ready()

        # ===== IF MESSAGE WAS NOT IN ENTRANCE GATE
        if msg.channel.id != NewMembers.config.channels['entrance_gate']:
            return

        # ===== IF THE AUTHOR IS GATED, LOG THE MESSAGE. IGNORES STAFF SINCE THEY TEND TO MESS AROUND 
        if self.roles['gated'] in msg.author.roles and not any(role.id in NewMembers.config.roles['any_staff'] for role in msg.author.roles):
            await self.db.execute(pgCmds.ADD_WEL_MSG, msg.id, msg.channel.id, msg.guild.id, msg.author.id)
            return

        # ===== CYCLE THROUGH ALL THE MEMBER'S MENTIONED IN THE MESSAGE
        for member in msg.mentions:
            # === IF MENTIONED MEMBER HAS THE GATED ROLE AND IS NOT STAFF
            if self.roles['gated'] in member.roles and not any(role.id in NewMembers.config.roles['any_staff'] for role in member.roles):
                
                await self.db.execute(pgCmds.ADD_WEL_MSG, msg.id, msg.channel.id, msg.guild.id, member.id)
                break 

        return

    @commands.Cog.listener()        
    async def on_guild_role_update(self, before, after):
        # ===== WAIT FOR THE BOT TO BE FINISHED SETTING UP
        await self.bot.wait_until_ready()

        # ===== IF STORED MEMBER ROLE WAS UPDATED
        if self.roles['member'] == before:
            self.roles['member'] = after

        # ===== IF STORED NEWMEMBER ROLE WAS UPDATED
        elif self.roles['newmember'] == before:
            self.roles['newmember'] = after

        # ===== IF STORED GATED ROLE WAS UPDATED
        elif self.roles['gated'] == before:
            self.roles['gated'] = after
        
        return


  # -------------------- COMMANDS --------------------
    @checks.HIGHEST_STAFF()
    @commands.command(pass_context=True, hidden=False, name='clearEntranceGate', aliases=['clearentrancegate'])
    async def cmd_clearentrancegate(self, ctx):
        """
        [Minister] Kick members who have sat in the entrance gate for 14 days or more.
        """

        currDateTime = datetime.datetime.utcnow()

        oldFreshUsers = [member for member in ctx.guild.members if (self.roles['gated'] in member.roles) and (self.roles['member'] not in member.roles) and ((currDateTime - member.joined_at).days > Days.gated)]

        if len(oldFreshUsers) == 0:
            await ctx.send(content="No members need to be kicked at this time.", delete_after=10)
            return

        react = await self.ask_yn(ctx,
                             "{} gated users will be kicked.\nAre you sure you want to continue?".format(len(oldFreshUsers)),
                             timeout=120,
                             expire_in=2)

        #===== if user says yes
        if react:
            try:
                for member in oldFreshUsers:
                    await member.kick(reason=f"Manual clearing of the entrance gate by {ctx.author.id}")
                    await asyncio.sleep(0.5)

                await ctx.send(content=f"Done, {len(oldFreshUsers)} members kicked", delete_after=30)

            except discord.errors.Forbidden:
                await ctx.send(content="Can't kick members due to lack of permissions.", delete_after=30)

            except discord.errors.HTTPException:
                await ctx.send(content="Some error occurred. Go blame discord and try again later.", delete_after=30)

            return

        #===== Time out handing
        elif react == None:
            await ctx.send(content="You took too long respond. Canceling action.", delete_after=30)

        #===== if user says no
        else:
            await ctx.send(content="Alright then, no members kicked.", delete_after=30)

        return 


    @checks.GATED()
    @commands.command(pass_context=False, hidden=False, name='agree', aliases=['iagree', 'letmein'])
    async def cmd_agree(self, ctx):
        """
        [Gated] Lets a new member sitting in the gate into the rest of the guild.
        """

        await ctx.author.add_roles(self.roles['member'])

        # ===== ADD NEW MEMBER AND REMOVE GATED ROLES
        await ctx.author.add_roles(self.roles['newmember'], reason="Added new member role")
        await asyncio.sleep(0.2)
        await ctx.author.remove_roles(self.roles['gated'], reason="Removed Gated Role")

        # ===== SCHEDULE REMOVAL OF NEW MEMBER ROLE
        await self.schedule_rem_newuser_role(ctx.author, daysUntilRemove=7, days=7)

        # ===== CANCEL EXISTING MEMBER KICK
        await self.cancel_scheduled_kick(ctx.author)

        # ===== TELL THE USERS A NEW MEMBER HAS JOINED
        wel_ch = self.bot.get_channel(self.config.channels['public_bot_log'])

        async with wel_ch.typing():
            # === GET THE USERS PFP AS BYTES
            avatar_bytes = await GET_AVATAR_BYTES(user = ctx.author, size = 128)

            # === SAFELY RUN SOME SYNCRONOUS CODE TO GENERATE THE IMAGE
            final_buffer = await self.bot.loop.run_in_executor(None, partial(images.GenWelcomeImg, avatar_bytes, ctx.author))

            # === SEND THE RETURN IMAGE
            await wel_ch.send(file=discord.File(filename="welcome.png", fp=final_buffer))


        # ===== DELETE USER MESSAGES IN THE GATE
        await self.del_user_welcome(ctx.author)

        return

        
  # -------------------- FUNCTIONS --------------------
    @asyncio.coroutine
    async def del_user_welcome(self, user):
        """
        Custom func to delete a users welcome message
        """
        
        # ===== GRAB ALL THE WELCOME MESSAGES FROM THE DATABASE RELATED TO THE USER IN QUESTION.
        welcomeMessages = await self.db.fetch(pgCmds.GET_MEM_WEL_MSG, user.id)
        bulkDelete = {}
        now = datetime.datetime.utcnow()

        # ===== DO NOTHING IF NOT DATA
        if not welcomeMessages:
            return 

        # ===== CYCLE THROUGH OUR DATABASE DATA
        for MYDM in welcomeMessages:

            # === LOG MESSAGES INTO OUR DICT IF THEY CAN BE DELETED IN BULK
            if (now - MYDM["timestamp"]).days < 13:

                # = IF CHANNEL ID DOES NOT EXIST AS A KEY
                if MYDM['ch_id'] not in bulkDelete.keys():
                    bulkDelete[MYDM['ch_id']] = list()

                bulkDelete[MYDM['ch_id']].append(MYDM["msg_id"])

            else:
                # = IF MESSAGE IS TOO OLD, DELETE ONE BY ONE.
                await self.bot.delete_msg_id(MYDM["msg_id"], MYDM["ch_id"], reason="Welcome message cleanup.")
                await asyncio.sleep(0.2)

        # ===== IF THERE ARE MESSAGES TO BE BULK DELETED.
        if bulkDelete:

            # === EVEN THOUGH ALL MESSAGES WILL MOST LIKELY BE FROM THE SAME CHANNEL, THIS ENSURES COMPATIBILTY WITH WELCOME MESSAGES FROM MULTIPLE CHANNELS
            for i in bulkDelete.keys():
                await self.bot.delete_msgs_id(messages=bulkDelete[i], channel=i, reason="Welcome message cleanup.")

        # ===== DELETE WELCOME MESSAGES FROM THE DATABASE
        await self.db.execute(pgCmds.REM_MEM_WEL_MSG, user.id)
    
    @asyncio.coroutine
    async def ask_yn(self, msg, question, timeout=60, expire_in=0):
        """Custom function which ask a yes or no question using reactions, returns True for yes | false for no | none for timeout"""

        message = await self.bot.send_msg(msg.channel, question)
        error = None
        try:
            await message.add_reaction("👍")
            await message.add_reaction("👎")

        except discord.errors.Forbidden:
            error = '`I do not have permission to add reactions, defaulting to "No"`'

        except discord.errors.NotFound:
            error = '`Emoji not found, defaulting to "No"`'

        except discord.errors.InvalidArgument:
            error = '`Error in my programming, defaulting to "No"`'

        except discord.errors.HTTPException:
            error = '`Error with adding reaction, defaulting to "No"`'

        if error is not None:
            await self.bot.delete_msg(message)
            await self.bot.send_msg(msg.channel, error)
            return False
        
        def check(reaction, user):
            return user == msg.author and str(reaction.emoji) in ["👍", "👎"] and not user.bot
        
        try:
            reaction = await self.bot.wait_for('reaction_add', timeout=timeout, check=check)

            #=== If msg is set to auto delete
            if expire_in:
                asyncio.ensure_future(self.__del_msg_later(message, expire_in))
            
            #=== Thumb up
            if str(reaction[0].emoji) == "👍":
                return True

            #=== Thumb down
            else:
                return False
                    
        #===== Time out error
        except asyncio.TimeoutError:
            return None

    def safe_print(self, content, *, end='\n', flush=True):
        """Custom function to allow printing to console with less issues from asyncio"""

        sys.stdout.buffer.write((content + end).encode('utf-8', 'replace'))
        if flush:
            sys.stdout.flush()

    @asyncio.coroutine
    async def __del_msg_later(self, message: discord.Message, after: int):
        """
        Custom function to delete messages after a period of time
        Args:
            (Discord.Message) The message to be deleted 
            (Int) Time to wait before deleting the message
        """

        await asyncio.sleep(after)
        await self.bot.delete_msg(message)
        return

    @asyncio.coroutine
    async def __get_invite_used(self):
        """
        When called it tries to find the invite used by calling the equivalent handler.
        Will return none
            if
                previous history file is not found
                if history file could not be read
                if new invite info cannot be found

        It will try to update the the invite info file as long as the current info can be found.
        """

        #===== Get current invite info
        inviteLog = await self.__get_invite_info()

        #=== if info cannot be gotten
        if inviteLog == None:
            invite = None

        #=== if info received
        else:
            invite = await self.__get_invite_used_handler(inviteLog)
            await self.db.execute(pgCmds.ADD_INVITES, json.dumps(inviteLog))

        return invite

    @asyncio.coroutine
    async def __get_invite_info(self, quiet=False):
        """Returns a dict with the information on the invites of selected guild"""

        try:
            invites = await self.bot.get_guild(NewMembers.config.target_guild_id).invites()

        except discord.Forbidden:
            if not quiet:
                await self.bot.send_msg_chid(NewMembers.config.channels['bot_log'], content="```css\nAn error has occurred```I do not have proper permissions to get the invite information.")

            return None

        except discord.HTTPException:
            if not quiet:
                await self.bot.send_msg_chid(NewMembers.config.channels['bot_log'], content="```css\nAn error has occurred```An error occurred when getting the invite information.")

            return None

        inviteLog = list()
        for invite in invites:
            inviteLog.append(dict(max_age = invite.max_age,
                        created_at = invite.created_at.__str__(),
                        uses = invite.uses,
                        max_uses = invite.max_uses,
                        code = invite.id,
                        inviter = dict(name = invite.inviter.name,
                                        id = invite.inviter.id,
                                        discriminator = invite.inviter.discriminator,
                                        avatar_url= invite.inviter.avatar_url.__str__(),
                                        mention = invite.inviter.mention
                                        )

                                    if invite.inviter != None else

                                    dict(name = "N/A",
                                        id = "N/A",
                                        discriminator = "N/A",
                                        avatar_url= "https://discordapp.com/assets/6debd47ed13483642cf09e832ed0bc1b.png?size=128",
                                        mention = "N/A"
                                        ),
                        channel = dict(name = invite.channel.name,
                                        id = invite.channel.id,
                                        mention = invite.channel.mention
                                        )
                        ))

        if len(inviteLog) == 0:
            return None

        else:
            return inviteLog

    @asyncio.coroutine
    async def __get_invite_used_handler(self, current_invite_info):
        """
        Tries to find which invite was used by a user joining.
        """

        #===== Read old invite info
        past_invite_info = json.loads(await self.db.fetchval(pgCmds.GET_INVITE_DATA))

        #===== Testing the existing invites.
        for past_invite in past_invite_info:
            for curr_invite in current_invite_info:
                if past_invite["code"] == curr_invite["code"]:
                    if past_invite["uses"] < curr_invite["uses"]:
                        return curr_invite

        #===== testing the new invites. should work if new invite is made and a user joins with that invite.
        for curr_invite in [curr_invite for curr_invite in current_invite_info if curr_invite not in past_invite_info]:
            if curr_invite["uses"] == 1:
                return curr_invite

        #===== CHECKING THE AUDIT LOG FOR INVITE CREATIONS
        guild = self.bot.get_guild(NewMembers.config.target_guild_id)

        try:
            logs = await guild.audit_logs(action=discord.AuditLogAction.invite_create, before=(datetime.datetime.utcnow() - datetime.timedelta(days=1))).flatten()

            if len(logs) == 1:
                log = logs[0]
                
                invite = {  "inviter":{ 'mention':"<@{}>".format(log.user.id),
                                        'name':log.user.name,
                                        'discriminator':log.user.discriminator
                            },
                            'code':"N/A",
                            'uses':"N/A",
                            'max_uses':"N/A"
                }
                
                return invite 

        except discord.Forbidden:
            return None

        return None

    @staticmethod
    async def __split_list(arr, size=100):
        """Custom function to break a list or string into an array of a certain size"""

        arrs = []

        while len(arr) > size:
            pice = arr[:size]
            arrs.append(pice)
            arr = arr[size:]

        arrs.append(arr)
        return arrs


  # -------------------- SCHEDULING STUFF --------------------

  # -------------------- Auto Kick Members --------------------
    async def check_new_members(self):
        """
        [Called on_ready]
        
        Adds members with the fresh role and not the core role to the scheduler via self.schedule_kick with the warning for member already in the scheduler turned off.
        Really only useful if the scheduled data in the SQL file has been lost.
        """

        # ===== WAIT FOR THE BOT TO BE FINISHED SETTING UP
        await self.bot.wait_until_ready()

        # ===== VARIABLE SETUP
        guild = self.bot.get_guild(self.config.target_guild_id)
        now = datetime.datetime.utcnow()

        for member in guild.members:
            
            # === IF MEMBER HAS NO ROLES AND HASN'T BEEN ON THE GUILD LONG ENOUGH FOR THE BOT TO AUTOKICK THEM
            if not member.roles and int((now - member.joined_at).days) <= (Days.gated + 1):
                
                # = APPLY THE AUTO ROLES
                if NewMembers.config.roles["autoroles"]:
                    for r_id in NewMembers.config.roles['autoroles']:
                        asyncio.wait(0.4)
                        role = discord.utils.get(guild.roles, id=r_id)
                        await member.add_roles(role, reason="Auto Roles")

            # === IF MEMBER HAS THE GATED ROLE BUT NOT THE MEMBER ROLE
            if (self.roles['gated'] in member.roles) and (self.roles['member'] not in member.roles):

                # = WORK OUT THE TIME THE USER HAS LEFT TO REGISTER
                diff = Days.gated - int((now - member.joined_at).days)

                # = IF MEMBER HAS BEEN ON THE GUILD FOR GREATER THEN 14 DAYS
                if diff < 1:
                    diff = 1

                await self.schedule_kick(member, daysUntilKick=diff, quiet=True, days=diff)

            # === IF MEMBER HAS THE MEMBER ROLE BUT NOT THE NEW MEMBER ROLE
            elif (self.roles['member'] in member.roles) and (self.roles['newmember'] not in member.roles):
                days = (Days.newmember + 1)- int((now - member.joined_at).days)

                # = IF MEMBER HAS BEEN ON GUILD FOR LONGER THAN THE TIME REQUIRED FOR NEW MEMBER ROLE TO EXPIRE
                if days < 1:
                    continue
                
                # = GIVE THE MEMBER THE NEWMEMBER ROLE
                await member.add_roles(self.roles['newmember'], reason="Added new member role")

                # = SCHEDULE THE NEW MEMBER ROLE FOR REMOVAL
                await self.schedule_rem_newuser_role(member, days)

   #-------------------- Remove New User Role --------------------
    @asyncio.coroutine
    async def schedule_rem_newuser_role(self, member:Union[discord.User, discord.Member], daysUntilRemove=Days.newmember, **kwargs):
        """
        [Called on_member_update]

        Adds the removal of a new member's fresh role to the scheduler.
        Handles:
            If member is already scheduled.

        It passes on the time allotted for an automatic kick to self._rem_newuser_role via the scheduler in the form of **kwargs
        """

        ###===== IF MEMBER IS ALREADY SCHEDULED TO HAVE NEW MEMBER ROLE REMOVED, QUIT
        for job in self.jobstore.get_all_jobs():
            if ["_rem_newuser_role", str(member.id)] == job.id.split(" "):
                return
        
        ###===== SEND REPORT MESSAGE TO STAFF
        embed = await GenEmbed.getScheduleRemNewRole(member=member, daysUntilRemove=daysUntilRemove)
        await self.bot.send_msg_chid(self.config.channels['bot_log'], embed=embed)

        ###===== ADD EVENT TO THE SCHEDULER
        self.scheduler.add_job(
            call_schedule,
            'date',
            id=self.get_id_args(self._rem_newuser_role, member.id),
            run_date=get_next(**kwargs),
            kwargs={"func": "_rem_newuser_role",
                    "arg": str(member.id)}
                    )

        return

    @asyncio.coroutine
    async def cancel_rem_newuser_role(self, member):
        """
        Cancels the scheduled kick of a member
        """

        for job in self.jobstore.get_all_jobs():
            if ["_rem_newuser_role", str(member.id)] == job.id.split(" "):
                self.scheduler.remove_job(job.id)

    @asyncio.coroutine
    async def _rem_newuser_role(self, user_id):
        """
        [Assumed to be called by the scheduler]

        Takes a user id and removes their fresh role.
        Handles:
            If member is not on the guild.
            if bot lacks permission to edit roles
        """

        ###===== WAIT FOR THE BOT TO BE FINISHED SETTING UP
        await self.bot.wait_until_ready()

        guild = self.bot.get_guild(self.config.target_guild_id)
        member = guild.get_member(int(user_id))

        ###===== QUIT IF MEMBER HAS LEFT THE GUILD
        if member == None:
            return
        
        try:
            await member.remove_roles(self.roles['newmember'], reason="Auto remove Fresh role")
        
            embed = await GenEmbed.genRemNewRole(member=member)
            await self.bot.send_msg_chid(self.config.channels['bot_log'], embed=embed)

        except discord.Forbidden:
            self.safe_print(f"I could not remove {member.mention}'s Fresh role due to Permission error.")

        except discord.HTTPException:
            self.safe_print(f"I could not remove {member.mention}'s Fresh role due to generic error.")

        return

   #-------------------- Kick new members --------------------
    @asyncio.coroutine
    async def cancel_scheduled_kick(self, member:Union[discord.User, discord.Member]):
        """
        Cancels the scheduled kick of a member

        Args:
            (discord.User/discord.Member) Member you want to cancel kicking
        """

        for job in self.jobstore.get_all_jobs():
            if ["_kick_entrance", str(member.id)] == job.id.split(" "):
                self.scheduler.remove_job(job.id)

    @asyncio.coroutine
    async def schedule_kick(self, member, daysUntilKick=Days.gated, quiet=False, **kwargs):
        """
        [Called on_member_join and check_new_members]

        Adds the automatic kick of a member from entrance gate after 14 days to the scheduler.
        Handles:
            If member is already scheduled to be kicked.

        It passes on the time allotted for an automatic kick to self._kick_entrance via the scheduler in the form of **kwargs
        """

        for job in self.jobstore.get_all_jobs():
            if ["_kick_entrance", str(member.id)] == job.id.split(" "):
                if not quiet:
                    await self.bot.send_msg_chid(NewMembers.config.channels['bot_log'], content="{0.mention} already scheduled for a kick".format(member))
                return

        embed = await GenEmbed.getScheduleKick( member=member, 
                                                daysUntilKick=daysUntilKick, 
                                                kickDate=(datetime.datetime.now() + datetime.timedelta(seconds=((daysUntilKick*24*60*60) + 3600))))

        await self.bot.send_msg_chid(NewMembers.config.channels['bot_log'], embed=embed)

        #===== add the kicking of member to the scheduler
        self.scheduler.add_job(call_schedule,
                               'date',
                               id=self.get_id_args(self._kick_entrance, member.id),
                               run_date=get_next(**kwargs),
                               kwargs={"func": "_kick_entrance",
                                       "arg": str(member.id)})

    @asyncio.coroutine
    async def _kick_entrance(self, user_id):
        """
        [Assumed to be called by the scheduler]

        Takes a user id and kicks them from entrance gate.
        Handles:
            If member is not on the guild.
            if bot lacks permission to kick members
        """

        ###===== WAIT FOR THE BOT TO FINISH IT'S SETUP  
        await self.bot.wait_until_ready()

        guild = self.bot.get_guild(NewMembers.config.target_guild_id)
        member = guild.get_member(int(user_id))

        ###===== IF MEMBER IS NO LONGER ON THE GUILD
        if member == None:
            return
        
        gatedRole =  discord.utils.get(guild.roles, id=NewMembers.config.roles['gated'])
        memberRole = discord.utils.get(guild.roles, id=NewMembers.config.roles['member'])

        try:
            #=== if member has fresh role and not core role
            if (gatedRole in member.roles) and (memberRole not in member.roles):
                #= kick member
                await member.kick(reason="Waited in entrance for too long.")

                #= report event
                embed = await GenEmbed.genKickEntrance(member, NewMembers.config.channels['entrance_gate'])
                await self.bot.send_msg_chid(NewMembers.config.channels['bot_log'], embed=embed)
        
        #===== Error if bot lacks permission
        except discord.errors.Forbidden:
            self.safe_print("[Error] (Scheduled event) I do not have permissions to kick members")
            await self.bot.send_msg_chid(NewMembers.config.channels['bot_log'], content="I could not kick <@{0.id}> | {0.name}#{0.discriminator}, due to lack of permissions".format(member))
        
        #===== Error for generic error, eg discord api gateway down
        except discord.errors.HTTPException:
            self.safe_print("[Error] (Scheduled event) I could not kick a member")
            await self.bot.send_msg_chid(NewMembers.config.channels['bot_log'], content="I could not kick <@{0.id}> | {0.name}#{0.discriminator}, due to an error".format(member))

        return

   #-------------------- TRINKETS --------------------
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


def setup(bot):
    bot.add_cog(NewMembers(bot))

async def call_schedule(func=None, arg=None, user_id=None, roles=None):
    if arg is None:
        await NewMembers.bot._kick_entrance(user_id)
        return
    await getattr(NewMembers.bot, func)(arg)