import sys
import json
import random
import dblogin 
import discord
import asyncio
import asyncpg
import datetime
from typing import Union
from discord.ext import commands

from apscheduler import events
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from nuggetbot.config import Config
from nuggetbot.util import gen_embed as GenEmbed
from nuggetbot.utils import get_next
from nuggetbot.database import DatabaseCmds as pgCmds
from nuggetbot.util.chat_formatting import RANDOM_DISCORD_COLOR, GUILD_URL_AS, AVATAR_URL_AS

from .cog_utils import SAVE_COG_CONFIG, LOAD_COG_CONFIG
from .util import checks

class NewMembers(commands.Cog):
    """Private feedback system."""

    config = None 
    delete_after = 15
    
    def __init__(self, bot):
        self.bot = bot
        NewMembers.bot = self
        NewMembers.config = Config()
        self.cogset = dict()
        self.db = None

        self.tguild = None

        self.jobstore = SQLAlchemyJobStore(url='sqlite:///jobs.sqlite')
        jobstores = {"default": self.jobstore}
        self.scheduler = AsyncIOScheduler(jobstores=jobstores)
        self.scheduler.add_listener(self.job_missed, events.EVENT_JOB_MISSED)

  #-------------------- LOCAL COG STUFF --------------------
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


  #-------------------- LISTENERS --------------------
    @commands.Cog.listener()
    async def on_ready(self): 
        self.tguild = self.bot.get_guild(NewMembers.config.target_guild_id)

        self.roles = {}
        
        self.roles['member']=       discord.utils.get(self.tguild.roles, id=NewMembers.config.roles['member'])
        self.roles['newmember']=    discord.utils.get(self.tguild.roles, id=NewMembers.config.roles['newmember'])
        self.roles['gated']=        discord.utils.get(self.tguild.roles, id=NewMembers.config.roles['gated'])

    @commands.Cog.listener()
    async def on_member_join(self, m): 
        ###===== WAIT FOR THE BOT TO BE FINISHED SETTING UP
        await self.bot.wait_until_ready()

        #------------------------- GET INVITE INFO -------------------------
        invite = await self.__get_invite_used()

        #------------------------- LOG NEW MEMBER -------------------------
        embed = await GenEmbed.getMemJoinStaff(member=m, invite=invite)
        await self.safe_send_msg_chid(NewMembers.config.channels['bot_log'], embed=embed)

        #------------------------- SEND WELCOME MESSAGE -------------------------
        fmt = random.choice([f'Oh {m.mention} steps up to my dinner plate, I mean to {m.guild.name}!',
                            f"I'm so excited to have {m.mention} join us, that I think I'll tear up the couch!",
                            f"Well dip me in batter and call me a nugget, {m.mention} has joined us at {m.guild.name}!",
                            f"The gates of {m.guild.name} have opened to: {m.mention}.",
                            f"Attention {m.mention}, all new members of {m.guild.name} must be approved by me and I approve of you *hugs*."])

        #fmt += "\nPlease give the rules in <#" + NewMembers.config.channels['public_rules_id'] + "> a read and when you're ready make a post in <#" + NewMembers.config.channels['entrance_gate'] + "> saying that you agreed to the rules."

        await asyncio.sleep(0.5)
        welMSG = await self.safe_send_msg_chid(NewMembers.config.channels['bot_log'], fmt)

        #------------------------- Update Database -------------------------
        await self.db.execute(pgCmds.ADD_WEL_MSG, welMSG.id, welMSG.channel.id, welMSG.guild.id, m.id)
        await self.db.execute(pgCmds.ADD_MEMBER_FUNC, m.id, m.joined_at, m.created_at)

        #------------------------- AUTO ROLES -------------------------
        if NewMembers.config.roles["autoroles"]:
            for r_id in NewMembers.config.roles['autoroles']:
                asyncio.wait(0.4)
                role = discord.utils.get(m.guild.roles, id=r_id)
                await m.add_roles(role, reason="Auto Roles")

        #------------------------- Schedule a kick -------------------------
        await self.schedule_kick(m, daysUntilKick=14, days=14)
    
    @commands.Cog.listener()
    async def on_member_remove(self, m):
        ###===== WAIT FOR THE BOT TO BE FINISHED SETTING UP
        await self.bot.wait_until_ready()

        #===== Ignore non target servers
        if m.guild.id != NewMembers.config.target_guild_id:
            return 
        
        #-------------------------Cancel scheduled kick -------------------------
        await self.cancel_scheduled_kick(member=m)

        #------------------------- IF MEMBER IS KICKED OR BANNED -------------------------
        #===== WAIT A BIT TO MAKE SURE THE GUILD AUDIT LOGS ARE UPDATED BEFORE READING THEM
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
            self.safe_print("[Info]  HTTP error occured, likly being rate limited or blocked by cloudflare. Restart recommended.")

        #------------------------- Removed User Logging -------------------------
        #=== STAFF ONLY LOGGING
        embed = await GenEmbed.getMemLeaveStaff(m, banOrKick)
        await self.safe_send_msg_chid(NewMembers.config.channels['bot_log'], embed=embed)

        #==== PUBLIC VISABLE LOGGING, ONLY APPLICABLE IF EXMEMBER WAS GIVEN THE CORE ROLE
        if discord.utils.get(m.roles, id=NewMembers.config.roles['member']):
            embed = await GenEmbed.getMemLeaveUser(m, banOrKick)
            await self.safe_send_msg_chid(NewMembers.config.channels['public_bot_log'], embed=embed)

        #------------------------- Remove User Welcome Messages -------------------------
        await self.del_user_welcome(m)
        
        #------------------------- Update Database -------------------------
        await self.db.execute(pgCmds.REMOVE_MEMBER_FUNC, m.id)
    
    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        """When there is an update to a users user data"""

        ###===== WAIT FOR THE BOT TO BE FINISHED SETTING UP
        await self.bot.wait_until_ready()

        ###===== IGNORE NON-TARGET GUILDS
        if before.guild.id != self.config.target_guild_id:
            return

        ###===== IF USER JUST GOT THE CORE ROLE AND HAS THE GATED ROLE
        if  (   (self.roles['member'] not in before.roles) 
            and (self.roles['member'] in before.roles) 
            and (self.roles['gated'] in before.roles)
            ):

            ###=== ADD AND REMOVE NEW MEMBER AND GATED ROLES
            await after.add_roles(self.roles['newmember'], reason="Added new member role")
            await asyncio.sleep(0.2)
            await after.remove_roles(self.roles['gated'], reason="Removed Gated Role")

            ###=== SCHEDULE REMOVAL OF NEW MEMBER ROLE
            await self.schedule_rem_newuser_role(after, daysUntilRemove=7, days=7)

            ###=== CANCEL EXISTING MEMBER KICK
            await self.cancel_scheduled_kick(after)

            ###=== TELL THE USERS A NEW MEMBER HAS JOINED
            embed = await GenEmbed.getMemJoinUser(after)
            await self.safe_send_msg_chid(self.config.channels['public_bot_log'], embed=embed)

            ###=== DELETE USER MESSAGES IN THE GATE
            await self.del_user_welcome(after)

    @commands.Cog.listener()
    async def on_message(self, msg):
        ###===== WAIT FOR THE BOT TO BE FINISHED SETTING UP
        await self.bot.wait_until_ready()

        ###===== IF MESSAGE WAS NOT IN ENTRANCE GATE
        if msg.channel.id != NewMembers.config.channels['entrance_gate']:
            return

    @commands.Cog.listener()        
    async def on_guild_role_update(self, before, after):
        ###===== WAIT FOR THE BOT TO BE FINISHED SETTING UP
        await self.bot.wait_until_ready()

        if self.roles['member'] == before:
            self.roles['member'] = after

        elif self.roles['newmember'] == before:
            self.roles['newmember'] = after

        elif self.roles['gated'] == before:
            self.roles['gated'] = after
        
        return

  #-------------------- FUNCTIONS --------------------
    @asyncio.coroutine
    async def safe_send_msg_chid(self, chid, content=None, embed:discord.Embed = None, tts=False, expire_in:int = 0, also_delete:discord.Message = None, quiet=True):
        """Alt version of safe send message were message will send to a channel id"""
        
        ###===== ENTURE CONTENT IS A STRING OR NONE
        content = str(content) if content is not None else None
        
        ###===== SERIALIZE EMBEDS
        if embed is not None:
            embed = embed.to_dict()

        msg = None

        try:
            msg = await self.bot.http.send_message(chid, content=content, embed=embed, tts=tts)

            ###=== SCHEDULE SENT MESSAGE FOR DELETION
            if expire_in:
                asyncio.ensure_future(self.__del_msg_later(msg, expire_in))

            ###=== DELETE ADDITIONAL MESSAGE IF APPLICABLE
            if also_delete:
                asyncio.ensure_future(self.__del_msg_later(also_delete, expire_in))

        except discord.Forbidden:
            if not quiet:
                self.safe_print(f"[Error] [new_members] Unable to send to channel {chid} due to lack of permissions.")

        except discord.NotFound:
            if not quiet:
                self.safe_print(f"[Error] [new_members] Cannot send message to channel {chid}, invalid channel?")

        return msg
    
    @asyncio.coroutine
    async def safe_delete_msg(self, message:discord.Message, *, quiet=False):
        """
        Messages to be deleted are routed though here to handle the exceptions.
        Args:
            (discord.Message) Message to be deleted
        """

        try:
            await message.delete()

        except discord.Forbidden:
            if not quiet:
                self.safe_print("[Warning] Cannot delete message \"{message.clean_content}\", no permission")

        except discord.NotFound:
            if not quiet:
                self.safe_print("[Warning] Cannot delete message \"{message.clean_content}\", message not found")

        return
    
    @asyncio.coroutine
    async def safe_delete_msg_id(self, message:int, channel:int, reason:str = None, quiet=False):
        """
        Messages to be deleted are routed though here to handle the exceptions.
        This deletes using bot.http functions to bypass having to find each message before deleting it.

        Args:
            (int) Message ID of message to be deleted.
            (int) Channel ID of channel the message was posted in.
            (str) Reason for message being deleted
        """
        
        try:
            await self.bot.http.delete_message(channel_id=channel, message_id=message, reason=reason)

        except discord.Forbidden:
            if not quiet:
                self.safe_print("[Warning] Cannot delete message \"{message}\", no permission")

        except discord.NotFound:
            if not quiet:
                self.safe_print("[Warning] Cannot delete message \"{message}\", message not found")

        return

    @asyncio.coroutine
    async def del_user_welcome(self, user):
        """
        Custom func to delete a users welcome message
        #re.findall(r"<@(.*?)>",t)
        
        """
        
        #===== get any and all user welcome messages from the database
        welcomeMessages = await self.db.fetch(pgCmds.GET_MEM_WEL_MSG, user.id)
        if welcomeMessages:
            for MYDM in welcomeMessages:
                #= create a fake message object to delete the welcome message
                await self.safe_delete_msg_id(MYDM["msg_id"], MYDM["ch_id"], reason="Welcome message cleanup.")

            #=== Delete welcome messages for the user from the database
            await self.db.execute(pgCmds.REM_MEM_WEL_MSG, user.id)

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
        await self.safe_delete_msg(message)
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
                await self.safe_send_msg_chid(NewMembers.config.channels['bot_log'], "```css\nAn error has occurred```I do not have proper permissions to get the invite information.")

            return None

        except discord.HTTPException:
            if not quiet:
                await self.safe_send_msg_chid(NewMembers.config.channels['bot_log'], "```css\nAn error has occurred```An error occurred when getting the invite information.")

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


  #-------------------- SCHEDULING STUFF --------------------

   #-------------------- Remove New User Role --------------------
    @asyncio.coroutine
    async def schedule_rem_newuser_role(self, member:Union[discord.User, discord.Member], daysUntilRemove=7, **kwargs):
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
        await self.safe_send_msg_chid(self.config.channels['bot_log'], embed=embed)

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
            await self.safe_send_msg_chid(self.config.channels['bot_log'], embed=embed)

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
    async def schedule_kick(self, member, daysUntilKick=14, quiet=False, **kwargs):
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
                    await self.safe_send_msg_chid(NewMembers.config.channels['bot_log'], "{0.mention} already scheduled for a kick".format(member))
                return

        embed = await GenEmbed.getScheduleKick( member=member, 
                                                daysUntilKick=daysUntilKick, 
                                                kickDate=(datetime.datetime.now() + datetime.timedelta(seconds=((daysUntilKick*24*60*60) + 3600))))

        await self.safe_send_msg_chid(NewMembers.config.channels['bot_log'], embed=embed)

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
                await self.safe_send_msg_chid(NewMembers.config.channels['bot_log'], embed=embed)
        
        #===== Error if bot lacks permission
        except discord.errors.Forbidden:
            self.safe_print("[Error] (Scheduled event) I do not have permissions to kick members")
            await self.safe_send_msg_chid(NewMembers.config.channels['bot_log'], content="I could not kick <@{0.id}> | {0.name}#{0.discriminator}, due to lack of permissions".format(member))
        
        #===== Error for generic error, eg discord api gateway down
        except discord.errors.HTTPException:
            self.safe_print("[Error] (Scheduled event) I could not kick a member")
            await self.safe_send_msg_chid(NewMembers.config.channels['bot_log'], content="I could not kick <@{0.id}> | {0.name}#{0.discriminator}, due to an error".format(member))

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