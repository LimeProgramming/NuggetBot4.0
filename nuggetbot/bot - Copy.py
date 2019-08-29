import discord
from discord.ext import commands
import asyncio
import aiohttp
import time #TIME.SLEEP
from random import randint
import datetime
import sys
import os
import random
import json
import re
from functools import wraps
#from discord.ext.commands.bot import _get_variable
import asyncio
import asyncpg
import time
from enum import Enum
import logging
import traceback

from apscheduler import events
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from configparser import ConfigParser
from .config import Config
from .database import DatabaseLogin, DatabaseCmds
from .database import DatabaseCmds as pgCmds
from . import exceptions
from .utils import get_next, Response
from .fun import Fun
#from .artists import Artists
from .util.chat_formatting import escape_mass_mentions, AVATAR_URL_AS, GUILD_URL_AS, RANDOM_DISCORD_COLOR
from .util import fake_objects
from .util import gen_embed as GenEmbed

from .decorators import in_channel, in_channel_name, in_reception, is_core, has_role, is_high_staff
from .decorators import is_any_staff, turned_off, owner_only

from .plugins.test_plugin import Test

import config2

logging.basicConfig(level=logging.INFO)
dblog = logging.getLogger("pgDB")
log = logging.getLogger("bot")

description = """
NuggetBot
"""

log = logging.getLogger(__name__)

initial_extensions = (
    'nuggetbot.plugins.test_plugin',
    'nuggetbot.plugins.giveaway',
    'nuggetbot.plugins.image'
)

class ChnlID():
    reception = int()
    giveaway = int()

    artistcorner = "463559553775042562"
    commissions = "382167265673609226"
    advertself = "382167213521633280"
    nsfwadvertself = "392465704865103873"
    blessrng = "436548720515874817"

class NuggetBot(commands.Bot):

    RafEntryActive = False
    RafDatetime = {}
    reactionmsgs = ""

#======================================== Bot init Setup ========================================
    def __init__(self):
        NuggetBot.bot = self
        self.config = Config()
        self.databaselg = DatabaseLogin()
        self.init_ok = True
        self.exit_signal = None
        self.logging = ConfigParser()
        self.bot_commands = [att.replace('cmd_', '').lower() for att in dir(self) if att.startswith('cmd_')]
        self.bot_oneline_commands = ["giveaway", "checkblacklist", "checkprewinners",
                                    "callgiveawaywinner", "endraffle", "allowentries",
                                    "stopentries", "giveawayentries", "rp", "rp_lewd",
                                    "artist", "book_wyrm", "notifyme", "vore", "nuggethelp",
                                    "clearentrancegate", "adminhelp",
                                    "togglechannellogging", "loginvites", "restart","shutdown", "cancel_hideserver",
                                    "opencommissions", "pingcommissioners", "findartists", "commissioner", 
                                    "leaderboard"]

        super().__init__(command_prefix='?', description=description,
                         pm_help=None, help_attrs=dict(hidden=True), fetch_offline_members=False)

        self.aiosession = aiohttp.ClientSession(loop=self.loop)

        self.jobstore = SQLAlchemyJobStore(url='sqlite:///jobs.sqlite')
        jobstores = {"default": self.jobstore}
        self.scheduler = AsyncIOScheduler(jobstores=jobstores)
        self.scheduler.add_listener(self.job_missed, events.EVENT_JOB_MISSED)

        self.shard = [0, 1]

        for extension in initial_extensions:
            try:
                self.load_extension(extension)
            except Exception:
                print(f'Failed to load extension {extension}.', file=sys.stderr)
                traceback.print_exc()


#======================================== Bot Object Setup ========================================
    def _cleanup(self):
        try:
            self.loop.run_until_complete(self.logout())
        except: pass

        pending = asyncio.Task.all_tasks()
        gathered = asyncio.gather(*pending)

        try:
            gathered.cancel()
            self.loop.run_until_complete(gathered)
            gathered.exception()
        except: pass

    # noinspection PyMethodOverriding
    def run(self):
        try:
            self.loop.run_until_complete(self.start(*self.config.auth))

        except discord.errors.LoginFailure:
            # Add if token, else
            raise exceptions.HelpfulError(
                "Bot cannot login, bad credentials.",
                "Fix your token in the options file.  "
                "Remember that each field should be on their own line."
            )

        finally:
            try:
                self._cleanup()
            except Exception:
                pass
                #log.error("Error in cleanup", exc_info=True)

            self.loop.close()

            if self.exit_signal:
                raise self.exit_signal


#======================================== BOT ON READY FUNCS ========================================
    async def pgdb_on_ready(self):

        #===== Log into database
        credentials = {"user": self.databaselg.user, "password": self.databaselg.pwrd, "database": self.databaselg.name, "host": self.databaselg.host}
        try:
            self.db = await asyncpg.create_pool(**credentials)
        except Exception as e:
            dblog.critical(f"There was an error connecting to the database {e}\nPlease make sure the login information in dblogin.ini is correct.")

            self.exit_signal = exceptions.TerminateSignal
            await self.logout()
            await self.close()



        #===== CREATE DATABASE TABLES AT STARTUP
        database_tables = [
            {"exists":"EXISTS_MSGS_TABLE",          "create":"CREATE_MSGS_TABLE",           "log":"Created messages table."},
            {"exists":"EXISTS_GALL_MSGS_TABLE",     "create":"CREATE_GALL_MSGS_TABLE",      "log":"Created gallery messages table."},
            {"exists":"EXISTS_ARTIST_INFO_TABLE",   "create":"CREATE_ARTIST_INFO_TABLE",    "log":"Created artist_info table."},
            {"exists":"EXISTS_INVITE_TABLE",        "create":"CREATE_INVITE_TABLE",         "log":"Created invite table."},
            {"exists":"EXISTS_WEL_MSG_TABLE",       "create":"CREATE_WEL_MSG_TABLE",        "log":"Created welcome msg table."},
            {"exists":"EXISTS_MEMBERS_TABLE",       "create":"CREATE_MEMBERS_TABLE",        "log":"Created members table."},
            {"exists":"EXISTS_RECT_MSG_TABLE",      "create":"CREATE_RECT_MSG_TABLE",       "log":"Created reaction messages table."},
            {"exists":"EXISTS_GVWY_PRE_WINS_TABLE", "create":"CREATE_GVWY_PRE_WINS_TABLE",  "log":"Created giveaway winners table."},
            {"exists":"EXISTS_GVWY_BLOCKS_TABLE",   "create":"CREATE_GVWY_BLOCKS_TABLE",    "log":"Created giveaway blacklist table."},
            {"exists":"EXISTS_GVWY_ENTRIES_TABLE",  "create":"CREATE_GVWY_ENTRIES_TABLE",   "log":"Created giveaway entries table."},
            {"exists":"EXISTS_DM_FEEDBACK",         "create":"CREATE_DM_FEEDBACK",          "log":"Created DM Feedback table."}
        ]

        for dbTables in database_tables:
            if not await self.db.fetchval(getattr(pgCmds, dbTables['exists'])):
                await self.db.execute(getattr(pgCmds, dbTables['create']))
                dblog.info(f" {dbTables['log']}")


        #===== Create database triggers
        if not await self.db.fetchval(pgCmds.EXISTS_MSGINCREMENTER):
            await self.db.execute(pgCmds.CREATE_MSGINCREMENTER)
            dblog.info(f" Created msgincrementer trigger.")


        #===== Create database functions
        database_funtion = [
            {"exists":"EXISTS_FUNC_UPDATE_INVITES",         "create":"CREATE_FUNC_UPDATE_INVITES",          "log":"Created UPDATE_INVITES function."},
            {"exists":"EXISTS_FUNC_HAS_MEMBER_LEVELED_UP",  "create":"CREATE_FUNC_HAS_MEMBER_LEVELED_UP",   "log":"Created HAS_MEMBER_LEVELED_UP function."},
            {"exists":"EXISTS_FUNC_ARTIST_INFO",            "create":"CREATE_FUNC_ARTIST_INFO",             "log":"Created ARTIST_INFO function."},
            {"exists":"EXISTS_FUNC_MEMBER_LEVEL_REWARD",    "create":"CREATE_FUNC_MEMBER_LEVEL_REWARD",     "log":"Created MEMBER_LEVEL_REWARD function."}
        ]

        for dbFunc in database_funtion:
            if not await self.db.fetchval(getattr(pgCmds, dbFunc['exists'])):
                await self.db.execute(getattr(pgCmds, dbFunc['create']))
                dblog.info(f" {dbFunc['log']}")


        guild = self.get_guild(self.config.target_guild_id)
        guildMems = sorted(guild.members, key=lambda x: x.joined_at)
        memids = [member.id for member in guildMems]

        ###Deal with members joining and leaving while bot is off.
        i = j = x = 0

        ### If members table is empty
        if len(await self.db.fetch(pgCmds.member_table_empty_test)) == 0:
            for m in guildMems:
                j += 1 
                await self.db.execute(pgCmds.add_a_member, m.id, m.joined_at, m.created_at, True)                

        
        for memid in await self.db.fetch(pgCmds.get_all_members_joinleave):
            member = guild.get_member(memid["user_id"])

            #=== remove from db
            if member is None and memid["ishere"] == True:
                i += 1
                await self.db.execute(pgCmds.REMOVE_MEMBER_FUNC, memid["user_id"])

            #=== add to db
            elif member and not member.bot and memid["user_id"] not in memids:
                j += 1 
                await self.db.execute(  pgCmds.add_a_member,
                                        member.id,
                                        member.joined_at,
                                        member.created_at,
                                        True
                                    )
            #=== readd to db
            elif member and str(memid["user_id"]) in memids and not memid["ishere"]:
                x += 1
                await self.db.execute(  pgCmds.readd_a_member, int(member.id))

        dblog.info(f" {i} old members removed from the database.")
        dblog.info(f" {j} new members added to the database.")
        dblog.info(f" {x} members rejoined.")

        #===== messages
        #===== I'm using async code here because this can take a long ass time.
        asyncio.ensure_future(self._db_add_new_messages(guild=guild))

        return

    async def setup_chnlID(self):
        """
        Some permission wrappers need an ID but I can't feed them this ID from self, so an external class is used.
        """
        ChnlID.reception = self.config.channels['reception_id']
        ChnlID.giveaway = self.config.gvwy_channel_id

    async def minimum_permissions_check(self, ch_reqs=['send_messages', 'add_reactions', 'create_instant_invite', 'attach_files'], guild_reqs=['kick_members']):

        raw_perms = ['create_instant_invite', 'kick_members', 'ban_members', 'administrator', 
                    'manage_channels', 'manage_guild', 'add_reactions', 'view_audit_log', 'priority_speaker', 
                    'stream', 'read_messages', 'send_messages', 'send_tts_messages', 'manage_messages', 
                    'embed_links', 'attach_files', 'read_message_history', 'mention_everyone', 'external_emojis', 
                    '', 'connect', 'speak', 'mute_members', 'deafen_members', 'move_members', 'use_voice_activation', 
                    'change_nickname', 'manage_nicknames', 'manage_roles', 'manage_webhooks', 'manage_emojis']

        missing_perms = ""

        guild = self.get_guild(self.config.target_guild_id)
        me = guild.get_member(self.user.id)

        #===== ADMIN HAS ALL THE PERMS, NO NEED TO SCAN THE CHANNELS
        if me.guild_permissions.administrator:
            log.info(f" Bot has Admin permissions in target guild.")
            return

        #===== SCAN THROUGH ALL THE CHANNELS LOOKING FOR THE REQUIRED PERMS
        for channel in guild.channels:
            perm = channel.permissions_for(me)

            for req in ch_reqs:
                
                try:
                    sel_perm = raw_perms.index(req)

                except ValueError:
                    missing_perms = missing_perms + f"Unknown Channel Permission {req}"
                    continue

                if not bool((perm.value >> sel_perm) & 1):
                    missing_perms = missing_perms + f"Missing: {req} in {channel.name}\n"
        
        #===== SCAN SERVER PERMS
        for req in guild_reqs:

            try:
                sel_perm = raw_perms.index(req)

            except ValueError:
                missing_perms = missing_perms + f"Unknown Server Permission {req}"
                continue

            if not bool((me.guild_permissions.value >> sel_perm) & 1):
                missing_perms = missing_perms + f"Missing: {req} in {guild.name}\n"

            #for req in guild_regs:

        #===== IF ANYTHING HAS BEEN APPENED TO THIS STRING THEN THAT MEANS THE BOT IS MISSING CRITIAL PERMS
        if missing_perms:
            log.critical(f"{missing_perms}")

            self.exit_signal = exceptions.TerminateSignal
            await self.logout()
            await self.close()

        return


#======================================== Bot Events ========================================
    async def on_ready(self):
        print('\rConnected!  NuggetBot v3.1\n')

        self.safe_print("--------------------------------------------------------------------------------")
        self.safe_print("Bot:   {0.name}#{0.discriminator} | ID: {0.id}".format(self.user))

        owner = await self._get_owner()

        self.safe_print("Owner: {0.name}#{0.discriminator} | ID: {0.id}".format(owner))

        #===== the "r" prefix means that the string is a literal, think raw string where "\n" prints "\n" and not a new line
        self.safe_print(r"--------------------------------------------------------------------------------")
        self.safe_print(r" _______                              __ __________        __                   ")
        self.safe_print(r" \      \  __ __  ____   ____   _____/  |\______   \ _____/  |_                 ")
        self.safe_print(r" /   |   \|  |  \/ ___\ / ___\_/ __ \   __\    |  _//  _ \   __\                ")
        self.safe_print(r"/    |    \  |  / /_/  > /_/  >  ___/|  | |    |   (  <_> )  |                  ")
        self.safe_print(r"\____|__  /____/\___  /\___  / \___  >__| |______  /\____/|__|                  ")
        self.safe_print(r"        \/     /_____//_____/      \/            \/                             ")
        self.safe_print(r"--------------------------------------------------------------------------------")
        self.safe_print("\n")

       #===== PREFORM BASIC REQUIREMENTS CHECKS
        await self.minimum_permissions_check()

       #===== CONNECT TO AND PRIME THE POSTGRE DATABASE
        await self.pgdb_on_ready()
        
       #===== LOG INVITES
        inviteLog = await self._get_invite_info()

        if inviteLog is not None:
            await self.db.execute(pgCmds.ADD_INVITES, json.dumps(inviteLog))
            self.safe_print("[Log] Invite information has been logged.")
        
        else:
            self.safe_print("[Log] No invite information to log.")

       #===== Set logging
        #self.logging.read("logging.ini")
        #self.safe_print("[Log] Loaded logging ini file")

       #===== presence
        await self.change_presence( activity=discord.Game(name="{0.command_prefix}{0.playing_game}".format(self.config)),
                                    status=discord.Status.online)

        #try:
        #    await self.bot.http.ban(190586062727282688, 605100382569365573, reason="test")
        #except Exception as e:
        #    print(e)


        #var = {
        #    '1⃣' : self.config.name_colors[1],
        #    '2⃣' : self.config.name_colors[2],
        #    '3⃣' : self.config.name_colors[3],
        #    '4⃣' : self.config.name_colors[4],
        #    '5⃣' : self.config.name_colors[5],
        #    '6⃣' : self.config.name_colors[6]
        #}

        #var2 = json.dumps(var)

        #print(var2) 
        
        #try:
        #    await self.db.execute(pgCmds.ADD_RECT_MSG, 609145721546866722, 605100383169413132, 605100382569365573, "_name_colors", var2)
        #except Exception as e:
        #    print(e)
        
        #try:

        #    ch = self.get_guild(605100382569365573).get_channel(605100383169413132)
        #    msg = await ch.fetch_message(609145721546866722)

        #    await msg.add_reaction('1⃣')
        #    await msg.add_reaction('2⃣')
        #    await msg.add_reaction('3⃣')
        #    await msg.add_reaction('4⃣')
        #    await msg.add_reaction('5⃣')
        #    await msg.add_reaction('6⃣')

        #except Exception as e:
        #    print(e)

        NuggetBot.reactionmsgs = [609145721546866722] 

       #===== scheduler
        self.scheduler.start()
        self.scheduler.print_jobs()
        await self.check_new_members()

        #ch = self.get_guild(605100382569365573).owner
        #print(AVATAR_URL_AS(user=ch))

    ###Updated
    async def on_resume(self):
        #===== If the bot is still setting up
        await self.wait_until_ready()

        self.safe_print("Bot resumed")

        #===== Log invites
        inviteLog = await self._get_invite_info()

        if inviteLog is not None:
            await self.db.execute(pgCmds.ADD_INVITES, json.dumps(inviteLog))
            self.safe_print("[Log] Invite information has been logged.")
        
        else:
            self.safe_print("[Log] No invite information to log.")

    async def on_error(self, event, *args, **kwargs):
        ex_type, ex, stack = sys.exc_info()

        if ex_type == exceptions.HelpfulError:
            print("Exception in", event)
            print(ex.message)
            
            await asyncio.sleep(2)
            await self.db.close()
            await self.logout()
            await self.close()

        elif issubclass(ex_type, exceptions.Signal):
            self.exit_signal = ex_type
            await self.db.close()
            await self.logout()
            await self.close()

        else:
            pass
            print(stack)

    async def on_raw_reaction_add(self, payload):
        #===== Block reactions in DM's
        if not payload.guild_id:
            return 

        if payload.message_id in NuggetBot.reactionmsgs:

            info = await self.db.fetchrow(pgCmds.GET_RECT_MSG_MSGID, payload.message_id) 

            guild = self.get_guild(info['srv_id'])
            member = guild.get_member(payload.user_id)

            #=== Quit if the reaction was added by a bot
            if member.bot:
                return

            #=== decode the stored json entry
            emojiIndex = json.loads(info['emojikey'])

            if payload.emoji.name in emojiIndex.keys() or payload.emoji.id in emojiIndex.keys():
                #color = emojiIndex[payload.emoji.name]
                await getattr(self, info["function_name"])(guild, member, emojiIndex, payload)

            #=== Delete the reaction
            msg = await guild.get_channel(info["ch_id"]).fetch_message(info["msg_id"])

            for react in msg.reactions:
                await react.remove(member)

    async def _name_colors(self, guild, member, emojiIndex, payload):
        color = emojiIndex[payload.emoji.name]

        for role in guild.roles:
            if role.name in emojiIndex.values() and role in member.roles:
                await member.remove_roles(role, reason="Name Colours")
                await asyncio.sleep(0.25)

            if color == role.name:
                await member.add_roles(role, reason="Name Colours")
                await asyncio.sleep(0.25)

        await member.send("Your name colour on {} has been changed to {}".format(guild.name, color))

        return

    #updated
    async def on_member_join(self, m): 
        #===== If the bot is still setting up
        await self.wait_until_ready()

        #--------------------------------------------------get the invite info--------------------------------------------------
        invite = await self._get_invite_used()

        #--------------------------------------------------New User Logging--------------------------------------------------
        embed = await GenEmbed.getMemJoinStaff(member=m, invite=invite)
        await self.safe_send_message(dest=m.guild.get_channel(self.config.channels['bot_log']), embed=embed)

        #-------------------------------------------------- Welcome message --------------------------------------------------
        fmt = random.choice([f'Oh {m.mention} steps up to my dinner plate, I mean to {m.guild.name}!',
                            f"I'm so excited to have {m.mention} join us, that I think I'll tear up the couch!",
                            f"Well dip me in batter and call me a nugget, {m.mention} has joined us at {m.guild.name}!",
                            f"The gates of {m.guild.name} have opened to: {m.mention}.",
                            f"Attention {m.mention}, all new members of {m.guild.name} must be approved by me and I approve of you *hugs*."])

        #fmt += "\nPlease give the rules in <#" + self.config.channels['public_rules_id'] + "> a read and when you're ready make a post in <#" + self.config.channels['entrance_gate_id'] + "> saying that you agreed to the rules."

        await asyncio.sleep(0.5)
        welMSG = await self.safe_send_message(m.guild.get_channel(self.config.channels['bot_log']), fmt)

        #-------------------------------------------------- Update Database --------------------------------------------------
        await self.db.execute(pgCmds.ADD_WEL_MSG, welMSG.id, welMSG.channel.id, welMSG.guild.id, m.id)
        await self.db.execute(pgCmds.ADD_MEMBER_FUNC, m.id, m.joined_at, m.created_at)

        #-------------------------------------------------- AUTO ROLES --------------------------------------------------
        if self.config.roles["autorole"]:
            fresh = discord.utils.get(m.guild.roles, name=self.config.roles["autorole"])
            await m.add_roles(fresh, reason="Auto Roles")

        #-------------------------------------------------- Schedule a kick --------------------------------------------------
        await self.schedule_kick(m, daysUntilKick=14, days=14)

    async def on_member_remove(self, m):
        #===== If the bot is still setting up
        await self.wait_until_ready()

        #===== Ignore non target servers
        if m.guild.id != self.config.target_guild_id:
            return 
        
        #--------------------------------------------------Cancel scheduled kick--------------------------------------------------
        await self.cancel_scheduled_kick(member=m)

        #--------------------------------------------------Get if banned member--------------------------------------------------
        #===== wait a bit to make sure the list of banned members got updated
        await asyncio.sleep(0.2)

        bans = await self._get_banned_members(m.guild) or []
        memberBanned = bool([x for x in bans if x.user.id == m.id])

        #--------------------------------------------------Removed User Logging--------------------------------------------------
        embed = await GenEmbed.getMemLeaveStaff(m, memberBanned)
        await self.safe_send_msg_chid(self.config.channels['bot_log'], embed=embed)

        #=public version
        if bool([x for x in m.roles if x.name == self.config.user_role]):
            embed = await GenEmbed.getMemJoinLeaveUser(member=m, joining="banned" if memberBanned else False)
            await self.safe_send_msg_chid(self.config.channels['public_bot_log'], embed=embed)

        #--------------------------------------------------Remove User Welcome Messages--------------------------------------------------
        await self.del_user_welcome(m)
        
        #--------------------------------------------------Update Database--------------------------------------------------
        await self.db.execute(pgCmds.REMOVE_MEMBER_FUNC, m.id)
        await self.db.execute(pgCmds.REM_MEM_GVWY_ENTRIES, m.id)

    async def on_member_update(self, before, after):
        """When there is an update to a users user data"""

        #===== If the bot is still setting up
        await self.wait_until_ready()

        #===== Ignore non target servers
        if before.guild.id != self.config.target_guild_id:
            return

        #===== Gets the names of the roles
        before_roles = [role.name for role in before.roles]
        after_roles = [role.name for role in after.roles]

        #===== If a user gets the core role
        if (self.config.user_role not in before_roles) and (self.config.user_role in after_roles):

            if self.config.newuser_role in after_roles:
                #= schedule role removeal
                await self.schedule_rem_newuser_role(after, daysUntilRemove=7, days=7)

                #= cancel the kick
                await self.cancel_scheduled_kick(after)

                #= Tell the users a new comer has joined
                embed = await GenEmbed.getMemJoinLeaveUser(after, joining=True)
                await self.safe_send_msg_chid(self.config.channels['public_bot_log'], embed=embed)

            await self.del_user_welcome(after)
        
        #===== ASSUMING STAFF GIVE A MEMBER THE GIVEAWAY ROLE
        elif (self.config.gvwy_role_name not in before_roles) and (self.config.gvwy_role_name in after_roles):
            past_wins = await self.db.fetchval(pgCmds.GET_GVWY_NUM_WINS, after.id)

            #=== LEVELED ENTRY SYSTEM
            if not past_wins:
                entries=3
            elif past_wins == 1:
                entries=2
            else:
                entries=1
    
            await self.db.execute(pgCmds.ADD_GVWY_ENTRY, after.id, entries, datetime.datetime.utcnow())
            await after.add_roles(discord.utils.get(after.guild.roles, name=self.config.gvwy_role_name), reason="Staff added user to giveaway.")

        #===== ASSUMING STAFF REMOVED THE GIVEAWAY ROLE FROM A MEMBER
        elif (self.config.gvwy_role_name in before_roles) and (self.config.gvwy_role_name not in after_roles):
            await after.remove_roles(discord.utils.get(after.guild.roles, name=self.config.gvwy_role_name), reason="Staff removed user from a giveaway.")
            await self.db.execute(pgCmds.REM_MEM_GVWY_ENTRIES, after.id)

        #===== If a user gets their NSFW role removed
        #elif ("NSFW" not in after_roles) and ("NSFW" in before_roles):

        #    for role in before.roles:
        #        if role.name in ["RP-LEWD"]:
        #            await self.remove_roles(after, role)

    async def on_message(self, message):

        #===== If the bot is still setting up
        await self.wait_until_ready()

        #===== Block self messages
        if message.author == self.user:
            return
        
        #--------------------------------------------------Private feedback system--------------------------------------------------
        if isinstance(message.channel, discord.abc.PrivateChannel):
            #=== Handle the cancel serverhide
            #if message.clean_content.strip().lower() == "{}{}".format(self.config.command_prefix, "cancel_hideserver"):
            #    await self.cmd_cancel_hideserver(message)
            #    return
            
            #=== Block Feedback without command
            if not message.clean_content.strip().lower().startswith("{}{}".format(self.config.command_prefix, "feedback")):
                return

            srv = self.get_guild(self.config.target_guild_id)
            srvUser = srv.get_member(message.author.id)

            #=== if user is member of guild
            if not srvUser == None:

                #= if user has fresh role
                if (self.config.newuser_role in srvUser.roles):
                    await self.safe_send_message(message.channel,
                                                "Not much point in messaging me. \n"
                                                "I suggest pinging the helpdesk in <#" + self.config.channels['entrance_gate_id'] + "> to be let in to the rest of the server first.")
                #= if user was let into the server
                else:
                    await self.handle_survey(message)

            #if user is not a member of server
            else:
                await self.safe_send_message(message.channel,"It seems you're not a member {0}.\nI suggest joining {0}.".format(srv.name))

        #--------------------------------------------------Everything else--------------------------------------------------
        if message.guild.id == self.config.target_guild_id:
            
            #=== Cleanup Dyno messages
            if (message.author.id == "155149108183695360") and (message.channel.id == self.config.channels['reception_id']) and (message.clean_content.startswith("<:dynoSuccess:314691591484866560> Changed roles for")):
                asyncio.ensure_future(self._del_msg_later(message, 1.5))
            
            #=== Make the commands work
            if message.clean_content.startswith(self.config.command_prefix):
                command = message.clean_content[len(self.config.command_prefix):].lower().split(" ")

                if (len(command) > 1) and command[0] in self.bot_oneline_commands:
                    return


                handler = getattr(self, "cmd_" + command[0], None)

                if not handler:
                    return

                try:
                    r = await handler(message)
                    
                    if isinstance(r, Response):
                        if r.reply:

                            if r.content and r.embed:
                                await self.safe_send_message(message.channel, content=r.content, embed=r.embed, expire_in=r.delete_after)

                            elif r.content:
                                await self.safe_send_message(message.channel, content=r.content, expire_in=r.delete_after)
                            
                            elif r.embed:
                                await self.safe_send_message(message.channel, embed=r.embed, expire_in=r.delete_after)

                        await self.safe_delete_message(message)

                except exceptions.Signal:
                    raise
                
                except Exception as e:
                    print(e)   

            #=== log messages
            else:
                if message.type != discord.MessageType.default or message.author.bot:
                    return

                await self.db.execute(pgCmds.ADD_MSG, message.id, message.channel.id, message.guild.id, message.author.id, message.created_at)

                #= MEMBER LEVELING
                r = await self.db.fetchrow(pgCmds.HAS_MEMBER_LEVELED_UP, message.author.id)

                if r["has_leveled_up"]: 
                    #gets: reward total 
                    g = await self.db.fetchrow(pgCmds.GET_LEVEL_UP_REWARD, message.author.id, r["new_level"])
                    await self.db.execute(pgCmds.MEMBER_LEVELED_UP, r["new_level"], g['total'], message.author.id)

                    #= tell user they leveled up
                    embed = await GenEmbed.getMemberLeveledUP(message, level=r["new_level"], reward=g['reward'], total=g['total'])
                    await self.safe_send_message(dest=message.channel, embed=embed)

        await NuggetBot.bot.process_commands(message)



#======================================== Custom Functions ========================================
    #updated
    async def del_user_welcome(self, user):
        """Custom func to delete a users welcome message"""
        
        #===== get any and all user welcome messages from the database
        welcomeMessages = await self.db.fetch(pgCmds.GET_MEM_WEL_MSG, int(user.id))
        if welcomeMessages:
            for MYDM in welcomeMessages:
                #= create a fake message object to delete the welcome message
                await self.safe_delete_message_id(MYDM["msg_id"], MYDM["ch_id"], reason="Welcome message cleanup.")

            #=== Delete welcome messages for the user from the database
            await self.db.execute(pgCmds.REM_MEM_WEL_MSG, user.id)

    #Reads all messages from a specified Channel #updated
    async def read_channel_messages(self, channel, num_of_msg=1000, before=None, after=None):
        """Custom function that reads all of the messages in a specified channel"""

        message_list = []
        amount_msg = num_of_msg

        done = False
        while not done:
            i = 0

            async for message in channel.history(before=before, after=after, limit=num_of_msg):
               message_list.append(message)
               i += 1

            if i == 0 and not message_list:
               done = True

            elif i == num_of_msg:
               before = message
               amount_msg += num_of_msg

            elif i != num_of_msg:
               done = True

        return message_list
    
    #updated
    async def handle_survey(self, msg):
        """Custom function to handle the private feedback system"""

        react = await self.ask_yn(msg,
                             "Are you sure you want to submit this feedback anonymously?\n"
                             "You must add a reaction for feedback to be submitted!",
                             timeout=120)

        #===== if user says yes
        if react:
            header = "```css\nAnonymous User Feedback\n```"

        #===== Time out handing
        elif react == None:
            await self.safe_send_message(msg.channel, "You took too long respond. Cancelling action, feedback **not** sent.")
            return

        #===== if user says no
        else:
            await self.safe_send_message(msg.channel, "Feedback **not** sent, repost it if you change your mind.\nThanks.")
            return

        msg_content = msg.content.strip()[10:]
        msg_attach = ""
        feedback_channel = discord.utils.get(self.get_guild(self.config.target_guild_id).channels, id=self.config.channels['feedback_id'])

        #===== if msg has an attachment
        if msg.attachments:
            for attach in msg.attachments:
                msg_attach += attach["url"] + "\n"

        #===== if feedback cannot be sent as one message
        if len(msg_content) > ((2000 - len(header)) - len(msg_attach)):
            m = await self.safe_send_message(feedback_channel, header)
            await self.safe_send_message(feedback_channel, msg_content)

            if not msg_attach == "":
                await self.safe_send_message(feedback_channel, msg_content)

        else:
            m = await self.safe_send_message(feedback_channel, "{}{}\n{}".format(header, msg_content, msg_attach))
        
        #===== Log info to database
        await self.db.execute(pgCmds.ADD_DM_FEEDBACK, msg.author.id, msg.channel.id, m.id, m.channel.id, m.guild.id, m.created_at)

        #===== Tell the user their feedback is sent
        await self.safe_send_message(msg.channel, "Your feedback has been submitted.\nThank You!")

        return

    #updated
    async def ask_yn(self, msg, question, timeout=60, expire_in=0):
        """Custom function which ask a yes or no question using reactions, returns True for yes | false for no | none for timeout"""

        message = await self.safe_send_message(msg.channel, question)
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
            await self.safe_delete_message(message)
            await self.safe_send_message(msg.channel, error)
            return False
        
        def check(reaction, user):
            return user == msg.author and str(reaction.emoji) in ["👍", "👎"] and not user.bot
        
        try:
            reaction = await self.wait_for('reaction_add', timeout=timeout, check=check)

            #=== If msg is set to auto delete
            if expire_in:
                asyncio.ensure_future(self._del_msg_later(message, expire_in))
            
            #=== Thumb up
            if str(reaction[0].emoji) == "👍":
                return True

            #=== Thumb down
            else:
                return False
                    
        #===== Time out error
        except asyncio.TimeoutError:
            return None

    #updated
    async def ask_yn_msg(self, msg, question, timeout=60, expire_in=0):
        """Custom function which ask a yes or no question using messages, returns True for yes | false for no | none for timeout"""

        message = await self.safe_send_message(msg.channel, question)

        if message is None:
            return None

        def check(m):
            if m.author == msg.author and m.channel == msg.channel:
                return (m.clean_content.lower().strip().startswith('y')
                        or m.clean_content.lower().strip().startswith('n'))

        try:
            responce = await self.wait_for('message', timeout=timeout, check=check)

            #=== If msg is set to auto delete
            if expire_in:
                asyncio.ensure_future(self._del_msg_later(message, expire_in))
                if responce is not None:
                    asyncio.ensure_future(self._del_msg_later(responce, expire_in))

            #=== yes
            if responce.clean_content.lower().strip().startswith("y"):
                return True

            #=== no
            return False

        #===== Time out error
        except asyncio.TimeoutError:
            return None

    #updated
    async def safe_send_message(self, dest, content=None, embed=None, tts=False, expire_in=None, also_delete=None, quiet=True):
        #===== If destination is a message
        if isinstance(dest, discord.Message):
            dest = dest.channel 

        msg = None
        try:
            msg = await dest.send(content=content, embed=embed, tts=tts, delete_after=expire_in)

            if also_delete and isinstance(also_delete, discord.Message):
                asyncio.ensure_future(self._del_msg_later(also_delete, expire_in))

        except discord.Forbidden:
            if not quiet:
                self.safe_print("[Warning] Cannot send message to {dest.name}, no permission")

        except discord.NotFound:
            if not quiet:
                self.safe_print("[Warning] Cannot send message to {dest.name}, invalid channel?")

        return msg

    async def safe_send_msg_chid(self, chid, content=None, *, embed=None, tts=False, expire_in=None, also_delete=None, quiet=True):
        """Alt version of safe send message were message will send to a channel id"""
        
        #===== Backwards compatibility 
        if isinstance(chid, discord.Object):
            chid = int(chid.id)
        
        content = str(content) if content is not None else None
        
        #===== Serialize any embeds
        if embed is not None:
            embed = embed.to_dict()

        msg = None

        try:
            msg = await self.bot.http.send_message(chid, content=content, embed=embed, tts=tts)

            if also_delete and isinstance(also_delete, discord.Message):
                asyncio.ensure_future(self._del_msg_later(also_delete, expire_in))

        except discord.Forbidden:
            if not quiet:
                self.safe_print("[Warning] Cannot send message to channel {chid}, no permission")

        except discord.NotFound:
            if not quiet:
                self.safe_print("[Warning] Cannot send message to channel {chid}, invalid channel?")

        return msg

    #updated
    async def safe_delete_message(self, message, *, quiet=False):
        """
        Messages to be deleted are routed though here to handle the exceptions.
        """

        try:
            return await message.delete()

        except discord.Forbidden:
            if not quiet:
                self.safe_print("[Warning] Cannot delete message \"{message.clean_content}\", no permission")

        except discord.NotFound:
            if not quiet:
                self.safe_print("[Warning] Cannot delete message \"{message.clean_content}\", message not found")
    
    #updated
    async def safe_delete_message_id(self, message, channel, reason=None, quiet=False):
        """
        Message ID's are to be routed though here
        """
        #===== Included for backwards compatibility
        if isinstance(message, fake_objects.MessageSC):
            channel = message.channel.id
            message = message.id 

        try:
            await self.bot.http.delete_message(channel_id=channel, message_id=message, reason=reason)

        except discord.Forbidden:
            if not quiet:
                self.safe_print("[Warning] Cannot delete message \"{message}\", no permission")

        except discord.NotFound:
            if not quiet:
                self.safe_print("[Warning] Cannot delete message \"{message}\", message not found")


    ###Deletes a lot of messages
    async def delete_channel_messages(self, message_list):
        return
        #     """Custom delete method. Will use the fastest way possible to delete large amounts of messages."""

        #     slow_message_list = None
        #     fast_message_list = None
        #     curr_datetime = datetime.datetime.utcnow()

        #     #===== messages less than 14 days old
        #     fast_message_list = [message for message in message_list if (curr_datetime - message.timestamp).days < 14]

        #     #===== if all messages are less than 14 days old
        #     if not len(message_list) == len(fast_message_list):
        #         slow_message_list = [message for message in message_list if not message in fast_message_list]

        #     #===== if less than 14 days old messages exist
        #     if not fast_message_list == None:

        #         #=== if fast_message_list is greater than 100 THAN break list into a 2d list of 100 sized arrays
        #         if len(fast_message_list) > 100:
        #             twoD_Message_list = await self.split_list(fast_message_list)

        #             for i in range(len(twoD_Message_list)):

        #                 #= Last item AND last set of messages is less than 2 THAN delete one by one
        #                 if ((i + 1) == len(twoD_Message_list)) and len(twoD_Message_list[i]) < 2:
        #                     for MYDM in enumerate(reversed(twoD_Message_list[i])):
        #                         await self.delete_message(MYDM)

        #                 #= if not last item OR last set of messages is greater than 1 THAN delete in bulk
        #                 else:
        #                     await self.delete_messages(twoD_Message_list[i])

        #         #=== if fast_message_list is less than 100 THAN delete bulk
        #         else:
        #             await self.delete_messages(fast_message_list)

        #     #===== if old messages exist THAN delete one by one
        #     if not slow_message_list == None:
        #         for MYDM in enumerate(reversed(slow_message_list)):
        #             await self.delete_message(MYDM)

        #     return

    #updated
    async def _get_private_channel(self, user):
        """
            Doesn't work but has logic I might find handy for something else
        """
        channel = user.dm_channel

        if channel is None:
            channel = await user.create_dm()

        return channel

    #updated
    def safe_print(self, content, *, end='\n', flush=True):
        """Custom function to allow printing to console with less issues from asyncio"""

        sys.stdout.buffer.write((content + end).encode('utf-8', 'replace'))
        if flush:
            sys.stdout.flush()

    #updated
    async def _del_msg_later(self, message, after):
        """Custom function to delete messages after a period of time"""

        await asyncio.sleep(after)
        await self.safe_delete_message(message)
        return

    #updated
    async def split_list(self, arr, size=100):
        """Custom function to break a list or string into an array of a certain size"""

        arrs = []

        while len(arr) > size:
            pice = arr[:size]
            arrs.append(pice)
            arr = arr[size:]

        arrs.append(arr)
        return arrs

    #updated
    async def _has_guild_perms(self, member, perm):
        """
        Input:
            member: member of a guild 
            perm: name of perm as list below.

        Output:
            True:   if member has specified perm
            False:  if member is not member type
                    or member does not have specified perm
                    or specified perm does not exist
        """

        if not isinstance(member, discord.Member):
            return False

        raw_perms = ["create_instant_invite", "kick_members", "ban_members", "administrator", "manage_channels",
                    "manage_server","add_reactions", "view_audit_logs", "", "", "read_messages", "send_messages",
                    "send_tts_messages", "manage_messages", "embed_links", "attach_files", "read_message_history",
                    "mention_everyone", "external_emojis", "", "connect", "speak", "mute_members", "deafen_members",
                    "move_members", "use_voice_activation", "change_nickname", "manage_nicknames", "manage_roles",
                    "manage_webhooks", "manage_emojis"]

        try:
            sel_perm = raw_perms.index(perm)

        except ValueError:
            return False

        for role in member.roles:
            if bool((role.permissions.value >> sel_perm) & 1):
                return True 

        return False

    ###===== Invite stuff ===== #updated
    async def _get_invite_info(self, quiet=False):
        """Returns a dict with the information on the invites of selected guild"""

        try:
            invites = await self.get_guild(self.config.target_guild_id).invites()

        except discord.Forbidden:
            if not quiet:
                await self.safe_send_msg_chid(self.config.channels['bot_log'], "```css\nAn error has occurred```I do not have proper permissions to get the invite information.")

            return None

        except discord.HTTPException:
            if not quiet:
                await self.safe_send_msg_chid(self.config.channels['bot_log'], "```css\nAn error has occurred```An error occurred when getting the invite information.")

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

    #updated
    async def _get_invite_used(self):
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
        inviteLog = await self._get_invite_info()

        #=== if info cannot be gotten
        if inviteLog == None:
            invite = None

        #=== if info received
        else:
            invite = await self._get_invite_used_handler(inviteLog)
            await self.db.execute(pgCmds.ADD_INVITES, json.dumps(inviteLog))

        return invite

    #updated untested
    async def _get_invite_used_handler(self, current_invite_info):
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
        guild = self.get_guild(self.config.target_guild_id)

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

    @asyncio.coroutine
    def _db_add_new_messages(self, guild):
        """
        add missed messages to the database. Async used because it could take a long ass time to do.
        """
        j = 0
        c = 0

        for channel in guild.channels:
            
            if not channel.type == discord.ChannelType.text:
                continue

            MRLoggedMessage = yield from self.db.fetchrow(f"SELECT * FROM messages WHERE ch_id = {channel.id} AND timestamp = (SELECT MAX(timestamp) from messages where ch_id = {channel.id})")

            if not MRLoggedMessage:
                MRLoggedMessage = None
            else:
                MRLoggedMessage = MRLoggedMessage["timestamp"] + datetime.timedelta(seconds = 1)

            #if ((channel.id in [self.config.channels['entrance_gate_id'],
            #                    self.config.channels['ministry_archive_id'],
            #                    self.config.channels['reception_id'],
            #                    self.config.channels['servey_id'],
            #                    self.config.channels['sys_ops_id'],
            #                    self.config.channels['nugget_welcome_id'],
            #                    self.config.channels['public_ministry_archive_id'],
            #                    self.config.channels['embassy_id'],
            #                    self.config.channels['warning_log_id']])

            #or (channel.permissions_for(guild.get_member(self.user.id)).read_message_history == False)):
            #    continue

            channelMessages = yield from self.read_channel_messages(channel, after=MRLoggedMessage)

            if channelMessages:
                c += 1

            for cm in channelMessages:
                if cm.author.bot:
                    continue

                j += 1
                yield from self.db.execute(pgCmds.ADD_MSG, cm.id, cm.channel.id, cm.guild.id, cm.author.id, cm.created_at)
        
        if j == 0:
            self.safe_print("[pgLog] No new messages added to the database.")
        else:
            self.safe_print(f"[pgLog] {j} messages from {c} channels added to the Database.")

        return

    ###===== More
    #updated
    async def _get_banned_members(self, guild):
        if not isinstance(guild, discord.Guild):
            return None

        try:
            bans = await guild.bans()
            return bans

        except discord.errors.Forbidden:
            self.safe_print("[Warning] Does not have permissions needed to get banned member for {0.name}\nI need permission to ban members.".format(guild))

        except discord.errors.HTTPException:
            self.safe_print("[Warning] Could not get list of banned members for {0.name}".format(guild))

        return None

    #updated
    async def _get_owner(self):
        return (await self.application_info()).owner


#======================================== Schedule stuff ========================================
  #-------------------- Auto Kick Members --------------------
    async def check_new_members(self):
        """
        [Called on_ready]
        
        Adds members with the fresh role and not the core role to the scheduler via self.schedule_kick with the warning for member already in the scheduler turned off.
        Really only useful if the scheduled data in the SQL file has been lost.
        """

        #===== If the bot is still setting up
        await self.wait_until_ready()

        #===== variable setup
        guild = self.get_guild(self.config.target_guild_id)
        now = datetime.datetime.utcnow()
        fresh = discord.utils.get(guild.roles, name=self.config.newuser_role)
        core = discord.utils.get(guild.roles, name=self.config.user_role)

        for member in guild.members:
            #=== is member has the fresh role and not the core role
            if (fresh in member.roles) and (core not in member.roles):

                #= work out the time the user has left to register
                diff = 14 - int((now - member.joined_at).days)

                #= If member has been on the guild for greater then 14 days
                if diff < 1:
                    diff = 1

                await self.schedule_kick(member, daysUntilKick=diff, quiet=True, days=diff)

  #-------------------- Remove New User Role --------------------
    async def schedule_rem_newuser_role(self, member, daysUntilRemove=7, **kwargs):
        """
        [Called on_member_update]

        Adds the removal of a new member's fresh role to the scheduler.
        Handles:
            If member is already scheduled.

        It passes on the time allotted for an automatic kick to self._rem_newuser_role via the scheduler in the form of **kwargs
        """
        
        #===== Bot Log Channel
        report_channel = discord.utils.get(member.guild.channels, id=self.config.channels['bot_log'])

        #===== If member is already scheduled to have Fresh role removed, it'll ignore the command.
        for job in self.jobstore.get_all_jobs():
            if ["_rem_newuser_role", str(member.id)] == job.id.split(" "):
                return
        
        #===== Report to the report channel
        embed = await GenEmbed.getScheduleRemNewRole(member=member, daysUntilRemove=daysUntilRemove)
        await self.safe_send_message(report_channel, embed=embed)

        #===== add the kicking of member to the scheduler
        self.scheduler.add_job(call_schedule,
        'date',
        id=self.get_id_args(self._rem_newuser_role, member.id),
        run_date=get_next(**kwargs),
        kwargs={"func": "_rem_newuser_role",
                "arg": str(member.id)})

    async def cancel_rem_newuser_role(self, member):
        """
        Cancels the scheduled kick of a member
        """

        for job in self.jobstore.get_all_jobs():
            if ["_rem_newuser_role", str(member.id)] == job.id.split(" "):
                self.scheduler.remove_job(job.id)

    async def _rem_newuser_role(self, user_id):
        """
        [Assumed to be called by the scheduler]

        Takes a user id and removes their fresh role.
        Handles:
            If member is not on the guild.
            if bot lacks permission to edit roles
        """

        #===== If the bot is still setting up
        await self.wait_until_ready()

        guild = self.get_guild(self.config.target_guild_id)
        member = guild.get_member(int(user_id))
        report_channel = discord.utils.get(guild.channels, id=self.config.channels['bot_log'])

        #===== if member is no-longer on the guild
        if member == None:
            return
        
        try:
            await member.remove_roles(discord.utils.get(guild.roles, name=self.config.newuser_role), reason="Auto remove Fresh role")
        
            embed = await GenEmbed.genRemNewRole(member=member)
            await self.safe_send_message(report_channel, embed=embed)

        except discord.Forbidden:
            self.safe_print(f"I could not remove {member.mention}'s Fresh role due to Permission error.")

        except discord.HTTPException:
            self.safe_print(f"I could not remove {member.mention}'s Fresh role due to generic error.")

  #-------------------- Kick new members --------------------
    async def cancel_scheduled_kick(self, member):
        """
        Cancels the scheduled kick of a member
        """

        for job in self.jobstore.get_all_jobs():
            if ["_kick_entrance", str(member.id)] == job.id.split(" "):
                self.scheduler.remove_job(job.id)

    async def schedule_kick(self, member, daysUntilKick=14, quiet=False, **kwargs):
        """
        [Called on_member_join and check_new_members]

        Adds the automatic kick of a member from entrance gate after 14 days to the scheduler.
        Handles:
            If member is already scheduled to be kicked.

        It passes on the time allotted for an automatic kick to self._kick_entrance via the scheduler in the form of **kwargs
        """

        report_channel = discord.utils.get(member.guild.channels, id=self.config.channels['bot_log'])
        
        for job in self.jobstore.get_all_jobs():
            if ["_kick_entrance", str(member.id)] == job.id.split(" "):
                if not quiet:
                    await self.safe_send_message(report_channel, "{0.mention} already scheduled for a kick".format(member))
                return

        embed = await GenEmbed.getScheduleKick( member=member, 
                                                daysUntilKick=daysUntilKick, 
                                                kickDate=(datetime.datetime.now() + datetime.timedelta(seconds=((daysUntilKick*24*60*60) + 3600))))

        await self.safe_send_message(report_channel, embed=embed)

        #===== add the kicking of member to the scheduler
        self.scheduler.add_job(call_schedule,
                               'date',
                               id=self.get_id_args(self._kick_entrance, member.id),
                               run_date=get_next(**kwargs),
                               kwargs={"func": "_kick_entrance",
                                       "arg": str(member.id)})

    async def _kick_entrance(self, user_id):
        """
        [Assumed to be called by the scheduler]

        Takes a user id and kicks them from entrance gate.
        Handles:
            If member is not on the guild.
            if bot lacks permission to kick members
        """

        #===== If the bot is still setting up
        await self.wait_until_ready()

        guild = self.get_guild(self.config.target_guild_id)
        member = guild.get_member(int(user_id))
        report_channel = discord.utils.get(guild.channels, id=self.config.channels['bot_log'])

        #===== if member is no-longer on the guild
        if member == None:
            return
        
        freshRole = discord.utils.get(guild.roles, name=self.config.newuser_role)
        userRole = discord.utils.get(guild.roles, name=self.config.user_role)

        try:
            #=== if member has fresh role and not core role
            if (freshRole in member.roles) and (userRole not in member.roles):
                #= kick member
                await member.kick(reason="Waited in entrance for too long.")

                #= report event
                embed = await GenEmbed.genKickEntrance(member, self.config.channels['entrance_gate_id'])
                await self.safe_send_message(report_channel, embed=embed)
        
        #===== Error if bot lacks permission
        except discord.errors.Forbidden:
            self.safe_print("[Error] (Scheduled event) I do not have permissions to kick members")
            await self.safe_send_message(report_channel, "I could not kick <@{0.id}> | {0.name}#{0.discriminator}, due to lack of permissions".format(member))
        
        #===== Error for generic error, eg discord api gateway down
        except discord.errors.HTTPException:
            self.safe_print("[Error] (Scheduled event) I could not kick a member")
            await self.safe_send_message(report_channel, "I could not kick <@{0.id}> | {0.name}#{0.discriminator}, due to an error".format(member))

        return

  #-------------------- Hide guild --------------------
    #@has_core_role
    #@in_reception
    async def cmd_hideserver(self, msg):
        """
        Useage:
            [prefix]hideserver <xDxHxMxS/seconds>
        [Core] Hides the server from you for a specified amount of time.
        """

        valid = None
        filterSeconds = True

        try:
            string = msg.content.split(" ")[1].lower()

        except IndexError:
            valid = False

        #===== Return error message if bot lacks permissions to manage roles.
        if not await self._has_guild_perms(msg.author.guild.get_member(self.user.id), "manage_roles"):
            return Response(content="```cs\n# Permission Error```\nI do not have permission to manage roles, so I can't hide the server for you.")

        #===== if member added just numbers, treat as seconds.
        if (valid is None) and (string.isdigit()):
            total_seconds = int(string)
            filterSeconds = False
            valid = True

        #===== if input doesn't match basic pattern
        if (valid is None) and (re.match(r'(\d+[DHMSdhms])+', string)):
            
            #=== if all acsii chars in the string are unique 
            letters = re.findall(r'[DHMSdhms]', string)
            if len(letters) == len(set(letters)):
                
                #= if more then 1 letter side by side
                #= ie. if string was 2dh30m then after the split you'd have ["", "dh", "m", ""]
                if not ([i for i in re.split(r'[0-9]', string) if len(i) > 1]):
                    
                    # if letters are in order.
                    if letters == sorted(letters, key=lambda letters: ["d", "h", "m", "s"].index(letters[0])):
                        valid = True
        
        #===== if invalid input
        if not valid: 
            return Response(content="`Useage: [p]hideserver <xDxHxMxS/seconds> | Hides the server from you for a specified amount of time.`")
        
        #===== sort out the input into just seconds.
        if filterSeconds:
            total_seconds = 0

            for data in re.findall(r'(\d+[DHMSdhms])', string):
                if data.endswith("d"):
                    total_seconds += int(data[:-1])*86400
                if data.endswith("h"):
                    total_seconds += int(data[:-1])*3600
                if data.endswith("m"):
                    total_seconds += int(data[:-1])*60
                if data.endswith("s"):
                    total_seconds += int(data[:-1])

        #===== if total seconds is stupidly small
        if total_seconds < 11:
            return Response(content="`Useage: [p]hideserver <xDxHxMxS/seconds> | Hides the server from you for a specified amount of time. More then 10 second timer please.`")
        
        elif total_seconds > 1209600:  
            return Response(content="`Useage: [p]hideserver <xDxHxMxS/seconds> | Hides the server from you for a specified amount of time. Less then 2 week timer please.`")

        await self.hide_server(msg.author, seconds=total_seconds)
        return Response(reply=False)
    
    async def cmd_cancel_hideserver(self, msg):
        """
        Useage:
            [prefix]cancel_hideserver
        Cancels the hide server schedule
        """
        job_found = False
        user_job = None

        for job in self.jobstore.get_all_jobs():
            if ["_show_server", msg.author.id] == job.id.split(" "):
                job_found = True
                user_job = job

        #===== if there is no job there for the user.
        if not job_found:
            #=== if msg from DM, send message to user as a bot can't send directly to a DM channel
            if msg.channel.is_private:
                await self.safe_send_message(msg.author, "You are not scheduled to have your roles re-added.")
                return None 
            else:
                return Response(content="You are not scheduled to have your roles re-added.")

        guild = self.get_guild(self.config.target_guild_id)

        #===== Return error message if bot lacks permissions to manage roles.
        if not await self._has_guild_perms(guild.get_member(self.user.id), "manage_roles"):
            if msg.channel.is_private:
                await self.safe_send_message(msg.author, "```cs\n# Permission Error```\nI do not have permission to manage roles, so I can't un-hide the server for you.")
                return None 
            else:
                return Response(content="```cs\n# Permission Error```\nI do not have permission to manage roles, so I can't un-hide the server for you.")
            

        member = guild.get_member(msg.author.id)
        bot_top_role = (guild.get_member(self.user.id)).top_role
        #===== weed out the roles the bot can't edit.
        user_roles = [role for role in guild.roles if role.name in user_job.kwargs['roles'] and role.position < bot_top_role.position and not role.is_everyone]
        hidden_role = discord.utils.get(guild.roles, name="Hidden")

        if not member:
            return

        #===== Try to edit roles for member
        try:
            for role in user_roles:
                await member.add_roles(role, reason="Cancel Hide Server")
                await asyncio.sleep(1.0)

            await member.remove_roles(hidden_role, reason="Cancel Hide Server")

        #===== Error if bot lacks permission
        except discord.errors.Forbidden:
            self.safe_print("[Error] (Scheduled event) could not complete show server for a user.")
            await self.safe_send_message(discord.Object(id=self.config.channels['ministry_archive_id']), 'I could not complete "show server" for <@{0.id}> | {0.name}#{0.discriminator}, due to lack of permissions'.format(member))
            await self.safe_send_message(msg.author, "```cs\n# Permission Error```\nI do not have permission to manage roles, so I can't un-hide the server for you.")
            return None
        
        #===== Error for generic error, eg discord api gateway down
        except discord.errors.HTTPException:
            self.safe_print("[Error] (Scheduled event) could not complete show server for a user.")
            await self.safe_send_message(discord.Object(id=self.config.channels['ministry_archive_id']), 'I could not complete "show server" for <@{0.id}> | {0.name}#{0.discriminator}, due to an error'.format(member))
            await self.safe_send_message(msg.author, "```cs\n# Generic Error```\nDue to an error I can't un-hide the server for you.")
            return None

        #===== Dm the user
        #===== build an embed for the user
        embed = await GenEmbed.getCancelHideServer(member)
        await self.safe_send_message(member, embed=embed)

        self.scheduler.remove_job(user_job.id)

        return None
            
    async def hide_server(self, member, quiet=True, **kwargs):
        #===== Bots top role
        bot_top_role = (member.guild.get_member(self.user.id)).top_role

        #===== Weed out roles the bot can't edit.
        user_roles = [role for role in member.roles if role.position < bot_top_role.position and not role.is_everyone]
        n_user_roles = [role.name for role in user_roles]
        hidden_role = discord.utils.get(member.guild.roles, name="Hidden")

        for job in self.jobstore.get_all_jobs():
            if ["_show_server", member.id] == job.id.split(" "):
                if not quiet:
                    await self.safe_send_message(member, "The server is already hidden from you.")
                return 

        #===== Dm the user
        embed = discord.Embed(  description="{} has been hidden from you for a time; as requested.\n"
                                            "You can cancel this with post {}cancel_hideserver here.".format(member.guild.name,
                                                                                                            self.config.command_prefix),
                                type=       'rich',
                                timestamp=  datetime.datetime.utcnow(),
                                color=      0x6953B2,
                            )

        embed.set_footer(       icon_url=   member.guild.icon_url,
                                text=       member.guild.name
                        )
            
        embed.set_author(       name=       'Server Hidden',
                                icon_url=   (member.avatar_url.__str__() if member.avatar_url.__str__() else member.default_avatar_url.__str__())
                        )

        #===== remove roles and add hidden role
        #===== sleep added to fix the bot spazzing out.
        try:
            await member.add_roles(hidden_role, reason="Hide Server")

            for role in user_roles:
                await asyncio.sleep(1.0)
                await member.remove_roles(role, reason="Hide Server")

        except discord.errors.Forbidden:
            self.safe_print('[Error] (Scheduled event) could not complete "hide server" for a user.')
            await self.safe_send_message(discord.Object(id=self.config.channels['ministry_archive_id']), 'I could not complete "hide server" for <@{0.id}> | {0.name}#{0.discriminator}, due to lack of permissions'.format(member))
            return None

        except discord.errors.HTTPException:
            self.safe_print('[Error] (Scheduled event) could not complete "hide server" for a user.')
            await self.safe_send_message(discord.Object(id=self.config.channels['ministry_archive_id']), 'I could not complete "hide server" for <@{0.id}> | {0.name}#{0.discriminator}, due to an error'.format(member))
            return None

        await self.safe_send_message(member, embed=embed)

        #===== add the kicking of member to the scheduler
        self.scheduler.add_job(call_schedule,
                               'date',
                               id=self.get_id_args(self._show_server, member.id),
                               run_date=get_next(**kwargs),
                               kwargs={"func": "_show_server",
                                       "user_id": member.id,
                                       "roles": n_user_roles})

    async def _show_server(self, user_id, roles):
        guild = self.get_guild(self.config.target_guild_id)
        member = guild.get_member(user_id)
        bot_top_role = (guild.get_member(self.user.id)).top_role
        #===== weed out the roles the bot can't edit.
        user_roles = [role for role in guild.roles if role.name in roles and role.position < bot_top_role.position and not role.is_everyone]
        hidden_role = discord.utils.get(guild.roles, name="Hidden")

        if not member:
            return

        #===== Try to edit roles for member
        try:
            for role in user_roles:
                await member.add_roles(role, reason="Show Server")
                await asyncio.sleep(1.0)
            await member.remove_roles(hidden_role, reason="Show Server")

        #===== Error if bot lacks permission
        except discord.errors.Forbidden:
            self.safe_print("[Error] (Scheduled event) could not complete show server for a user.")
            await self.safe_send_message(discord.Object(id=self.config.channels['ministry_archive_id']), 'I could not complete "show server" for <@{0.id}> | {0.name}#{0.discriminator}, due to lack of permissions'.format(member))
        
        #===== Error for generic error, eg discord api gateway down
        except discord.errors.HTTPException:
            self.safe_print("[Error] (Scheduled event) could not complete show server for a user.")
            await self.safe_send_message(discord.Object(id=self.config.channels['ministry_archive_id']), 'I could not complete "show server" for <@{0.id}> | {0.name}#{0.discriminator}, due to an error'.format(member))

        #===== Dm the user
        embed = discord.Embed(  description="{} has been made available to you again.\n"
                                            "Welcome back.".format(guild.name),
                                type=       'rich',
                                timestamp=  datetime.datetime.utcnow(),
                                color=      0x6953B2,
                            )

        embed.set_footer(       icon_url=   member.guild.icon_url,
                                text=       member.guild.name
                        )
            
        embed.set_author(       name=       'Server Available',
                                icon_url=   (member.avatar_url.__str__() if member.avatar_url.__str__() else member.default_avatar_url.__str__())
                        )

        await member.send(embed=embed)

        return

  #-------------------- General --------------------
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


#======================================== GIVEAWAY COMMANDS ========================================
    ###Users assign themselves the giveaway role
    @in_channel([ChnlID.giveaway])
    @is_core #updated
    async def cmd_giveaway(self, msg):
        """
        Useage:
            [prefix]giveaway
        [Core] Users can give themselves the giveaway role
        """
        #===== GET RAFLE ROLE
        giveawayRole = discord.utils.get(msg.guild.roles, name=self.config.gvwy_role_name)

        ##===== IF RAFFLE IS OPEN
        if NuggetBot.RafEntryActive:

            #=== IF MEMBER IS IN RAFFLE
            if await self.db.fetchval(pgCmds.GET_MEM_EXISTS_GVWY_ENTRIES, msg.author.id):
                #= REM ROLE
                await msg.author.remove_roles(giveawayRole, reason="User left the giveaway.")
                #= REM FROM DATABASE
                await self.db.execute(pgCmds.REM_MEM_GVWY_ENTRIES, msg.author.id)
                #= RESPOND
                return Response(content="{} has left the giveaway, better luck next time. :negative_squared_cross_mark: ".format(msg.author.nick or msg.author.name), delete_after=10)

            #-------------------- ENTRY BLOCKING --------------------
            #=== IF USER HAS BEEN BLACKLISTED FROM GIVEAWAY    
            if self.config.gvwy_enforce_blacklist:
                if await self.db.fetchval(pgCmds.GET_MEM_EXISTS_GVWY_BLOCKS, msg.author.id):
                    return Response(content=F"Sorry {msg.author.mention}, but you have been barred from giveaways on this server.", delete_after=10)
            
            #=== IF USER JOINED TOO RECENTLY
            if (datetime.datetime.utcnow() - msg.author.joined_at).seconds < self.config.gvwy_min_time_on_srv:
                return Response(content=F"Sorry {msg.author.mention}, but you have to be on the server for a minimum of 30 days to enter the giveaway.", delete_after=10)
            
            #=== IF NOT ACTIVE ENOUGH
            if len(await self.db.fetch(pgCmds.GET_MEMBER_MSGS_BETWEEN, msg.author.id, NuggetBot.RafDatetime["open"], NuggetBot.RafDatetime["past"])) < self.config.gvwy_min_msgs:
                return Response(content=F"Sorry {msg.author.mention}, but you have not been active enough on the server to enter the giveaway.", delete_after=10)   
            #-------------------- ENTER MEMBER --------------------
            past_wins = await self.db.fetchval(pgCmds.GET_GVWY_NUM_WINS, msg.author.id)

            #=== LEVELED ENTRY SYSTEM
            if not past_wins:
                entries=3
            elif past_wins == 1:
                entries=2
            else:
                entries=1

            await self.db.execute(pgCmds.ADD_GVWY_ENTRY, msg.author.id, entries, msg.created_at)
            await msg.author.add_roles(giveawayRole, reason="User joined the giveaway")

            return Response(content="{} has entered the giveaway, goodluck :white_check_mark:".format(msg.author.nick or msg.author.name), delete_after=10)

        #===== IF RAFFLE IS CLOSED
        else:
            if await self.db.fetchval(pgCmds.GET_MEM_EXISTS_GVWY_ENTRIES, msg.author.id):
                #= REM ROLE
                await msg.author.remove_roles(giveawayRole, reason="User left the giveaway")
                #= REM FROM DATABASE
                await self.db.execute(pgCmds.REM_MEM_GVWY_ENTRIES, msg.author.id)
                #= RESPOND TO USER
                return Response(content="{} has left the giveaway after entries have been closed. If this was a mistake ask staff to add you back into the giveaway but no promices that you'll be noticed in time. :negative_squared_cross_mark: ".format(msg.author.nick or msg.author.name), delete_after=15)

            return Response(content="Sorry {}, but giveaway entries are not open right now. Please check back later.".format(msg.author.nick or msg.author.name), delete_after=10)

    ###Adds a user to the blacklist
    @is_high_staff #updated working
    async def cmd_addblacklist(self, msg):
        """
        Useage:
            [prefix]addblacklist <userid/mention> <reason>
        [Admin/Mod] Adds a user to the blacklist.
        """
        try:
            args = msg.content.split(" ")
            if len(args) > 3:
                return Response(content="`Useage: [p]addblacklist <userid/mention> <reason>, [Admin/Mod] Adds a user to the blacklist.`")

            #=== SPLIT, REMOVE MENTION WRAPPER AND CONVERT TO INT
            user_id = args[1]
            user_id = user_id.replace("<", "").replace("@", "").replace("!", "").replace(">", "")
            user_id = int(user_id)

            if len(args) == 3:
                reason = args[2]
                reason = reason[:1000]
            else:
                reason = None

        except (IndexError, ValueError):
            return Response(content="`Useage: [p]addblacklist <userid/mention> <reason>, [Admin/Mod] Adds a user to the blacklist.`")

        #===== IF USER IS NOT ON GUILD
        #if not msg.guild.get_member(user_id):
        #    return Response(content=f"User does not exist or is not a member of {msg.guild.name}")
        
        #===== if a user was already blacklisted
        if await self.db.fetchval(pgCmds.GET_MEM_EXISTS_GVWY_BLOCKS, user_id):
            return Response(content="User already on the raffle blacklist.")
        
        #===== BLACKLIST THE USER
        else:
            await self.db.execute(pgCmds.ADD_GVWY_BLOCKS_NONTIMED, user_id, msg.author.id, reason, msg.author.created_at)
            
            #=== IF MEMBER IS IN THE GIVEAWAY ENTRIES
            if await self.db.fetchval(pgCmds.GET_MEM_EXISTS_GVWY_ENTRIES, user_id):
                #= REMOVE FROM GIVEAWAY ENTRIES
                await self.db.execute(pgCmds.REM_MEM_GVWY_ENTRIES, user_id)
                
                #= REMOVE GIVEAWAY ROLE
                member = msg.guild.get_member(user_id)
                await member.remove_roles(discord.utils.get(msg.guild.roles, name=self.config.gvwy_role_name), reason="User baned from giveaways.")

                return Response(content=f"<@{user_id}> has been added to the raffle blacklist and removed from giveaway entries")

            return Response(content=f"<@{user_id}> has been added to the raffle blacklist.")

    ###Remove a user from the blacklist
    @is_high_staff #updated working
    async def cmd_remblacklist(self, msg):
        """
        Useage:
            [prefix]remblacklist <userid/mention>
        [Admin/Mod] Removes a member from the blacklist.
        """
        try:
            args= msg.content.split(" ")
            if len(args) > 2:
                return Response(content="`Useage: [p]remblacklist <userid/mention>, [Admin/Mod] Removes a member from the blacklist.`")

            #=== SPLIT, REMOVE MENTION WRAPPER AND CONVERT TO INT
            user_id = args[1]
            user_id = user_id.replace("<", "").replace("@", "").replace("!", "").replace(">", "")
            user_id = int(user_id)

        except (IndexError, ValueError):
            return Response(content="`Useage: [p]remblacklist <userid/mention>, [Admin/Mod] Removes a member from the blacklist.`")
        
        #===== IF USER IS NOT ON BLOCK LIST
        if not await self.db.fetchval(pgCmds.GET_MEM_EXISTS_GVWY_BLOCKS, user_id):
            return Response(content=f"<@{user_id}> was not on the raffle blacklist.")
        
        #===== ADD USER TO BLOCK LIST 
        await self.db.execute(pgCmds.REM_MEM_GVWY_BLOCK, user_id)
        return Response(content=f"<@{user_id}> has been removed from the raffle blacklist.")

    ###Returns a list of users who are blacklisted from the raffle
    @is_any_staff #updated #working
    async def cmd_checkblacklist(self, msg):
        """
        Useage:
            [prefix]checkblacklist
        [Any Staff] Returns a list of users who are blacklisted from the raffle
        """
        try:
            args= msg.content.split(" ")
            if len(args) > 1:
                return Response(content="`Useage: [p]checkblacklist, [Any Staff] Returns a list of users who are blacklisted from the raffle.`")

        except (IndexError, ValueError):
            return Response(content="`Useage: [p]checkblacklist, [Any Staff] Returns a list of users who are blacklisted from the raffle.`")

        blacklistMembers = await self.db.fetch(pgCmds.GET_ALL_GVWY_BLOCKS)

        #===== IF NO-ONE IS BLOCKED
        if not blacklistMembers:
            return Response(content="No blacklisted members.", reply=True)
        
        listedMembers = ""

        #===== LOOP ALL MEMBERS IN THE SERVER
        for member in msg.guild.members:

            #=== IF MEMBER IS BLACKLISTED
            if member.id in [i['user_id'] for i in blacklistMembers]:

                for j in blacklistMembers:
                    if member.id == j['user_id']:
                        x = j 
                        break

                listedMembers += "{0.name}#{0.discriminator} | Mention: {0.mention} | Reason: {1} | When: {2}\n".format(member, x["reason"], x["timestamp"].strftime('%b %d, %Y %H:%M:%S'))

        #===== SEND HEADER MESSAGE
        await self.safe_send_message(msg.channel, "```css\nUsers blacklisted from raffle.\n```")
            
        #===== SPLIT MAIN MESSAGE STRING INTO AN ARRAY, LIMITING MAX NUM OF CHARS TO 2000
        listedMembers = await self.split_list(listedMembers, size=2000)
        
        #===== MESSAGE OUT THE BLACKLISTED MEMBERS
        for i in range(len(listedMembers)):
            await self.safe_send_message(msg.channel, listedMembers[i])

        #===== DONE
        return Response(reply=False)

    ###Adds a user to the previous winners list
    @is_high_staff #updated #working
    async def cmd_makeprewinner(self, msg):
        """
        Useage:
            [prefix]makeprewinner <userid/mention>
        [Admin/Mod] Adds a user to the list of previous winners.
        """
        try:
            args = msg.content.split(" ")
            if len(args) > 2:
                return Response(content="`Useage: [p]makeprewinner <userid/mention>,\n[Admin/Mod] Adds a user to the list of previous winners.`")

            #=== SPLIT, REMOVE MENTION WRAPPER AND CONVERT TO INT
            user_id = args[1]
            user_id = user_id.replace("<", "").replace("@", "").replace("!", "").replace(">", "")
            user_id = int(user_id)

        except (IndexError, ValueError):
            return Response(content="`Useage: [p]makeprewinner <userid/mention>,\n[Admin/Mod] Adds a user to the list of previous winners.`")

        #===== IF USER IS NOT ON GUILD
        #if not msg.guild.get_member(user_id):
        #    return Response(content=f"User does not exist or is not a member of {msg.guild.name}")
        
        #===== ADD USER TO WINNERS LIST 
        await self.db.execute(pgCmds.ADD_GVWY_PRE_WINS, user_id, datetime.datetime.utcnow())

        return Response(content=f"<@{user_id}> has been added to the giveaway winner list.")

    ###Remove a user to the previous winners list
    @is_high_staff #updated #working
    async def cmd_remprewinner(self, msg):
        """
        Useage:
            [prefix]remprewinner <userid/mention>
        [Admin/Mod] Removes a member from the previous winners list.
        """
        try:
            args= msg.content.split(" ")
            if len(args) > 2:
                return Response(content="`Useage: [p]remprewinner <userid/mention>, [Admin/Mod] Removes a member from the previous winners list.`")

            #=== SPLIT, REMOVE MENTION WRAPPER AND CONVERT TO INT
            user_id = args[1]
            user_id = user_id.replace("<", "").replace("@", "").replace("!", "").replace(">", "")
            user_id = int(user_id)

        except (IndexError, ValueError):
            return Response(content="`Useage: [p]remprewinner <userid/mention>, [Admin/Mod] Removes a member from the previous winners list.`")
        
        #===== GET DATA FROM DATABASE
        prewindata = await self.db.fetchrow(pgCmds.GET_MEM_GVWY_PRE_WIN, user_id)
        

        #===== IF USER IS NOT ON BLOCK LIST
        if not prewindata:
            return Response(content=f"<@{user_id}> was not on the raffle blacklist.")
        
        pastwins = int(prewindata['num_wins'])

        #===== DEINCREMENT THE USERS NUMBER OF WINS IF NEEDED
        if pastwins > 1:
            await self.db.execute(pgCmds.SET_GVWY_NUM_WINS, (prewindata['num_wins'] - 1), user_id)
            return Response(content=f"<@{user_id}> has had their number of previous wins set to {(pastwins - 1)}.")
        
        #===== OTHERWISE JUST REMOVE THEM FROM THE PREVIOUS WINNERS LIST
        await self.db.execute(pgCmds.REM_MEM_GVWY_PRE_WINS, user_id)
        return Response(content=f"<@{user_id}> has been removed from the previous winners list.")
        
    ###Returns a list of users who have won the raffle before
    @is_any_staff #updated #working
    async def cmd_checkprewinners(self, msg):
        """
        Useage
            [prefix]checkprewinners
        [Any Staff] Returns a list of users who have won the raffle before.
        """
        try:
            args= msg.content.split(" ")
            if len(args) > 1:
                return Response(content="`Useage: [p]checkprewinners, [Any Staff] Returns a list of users who have won the raffle before.`")

        except (IndexError, ValueError):
            return Response(content="`Useage: [p]checkprewinners, [Any Staff] Returns a list of users who have won the raffle before.`")
    
        preWinners = await self.db.fetch(pgCmds.GET_ALL_GVWY_PRE_WINS)
        
        #===== IF NO-ONE WON BEFORE
        if not preWinners:
            return Response(content="No-one ever won before.")

        listedMembers = ""

        #===== LOOP ALL MEMBERS IN THE SERVER
        for member in msg.guild.members:

            #=== IF MEMBER WON BEFORE
            if member.id in [i['user_id'] for i in preWinners]:

                for j in preWinners:
                    if member.id == j['user_id']:
                        x = j 
                        break

                listedMembers += "{0.name}#{0.discriminator} | Mention: {0.mention} | Number Wins: {1} | Last Win: {2}\n".format(member, x["num_wins"], x["last_win"].strftime('%b %d, %Y %H:%M:%S'))

        #===== SEND HEADER MESSAGE
        await self.safe_send_message(msg.channel, "```css\nUsers who have won the raffle before.\n```")
            
        #===== SPLIT MAIN MESSAGE STRING INTO AN ARRAY, LIMITING MAX NUM OF CHARS TO 2000
        listedMembers = await self.split_list(listedMembers, size=2000)
        
        #===== MESSAGE OUT THE PREVIOUS WINNERS MEMBERS
        for i in range(len(listedMembers)):
            await self.safe_send_message(msg.channel, listedMembers[i])

        #===== DONE
        return Response(reply=False)
        
    ###Support or above calls a winner of the raffle
    @is_any_staff
    async def cmd_callgiveawaywinner(self, msg):
        """
        Useage:
            [prefix]callgiveawaywinner
        [Any Staff] Returns a random user who has entered the Giveaway. Base Stats: 3 entries if never won, 2 entries if won once, 1 entry if won more twice or more.
        """
        dbGvwyEntries = await self.db.fetch(pgCmds.GET_ALL_GVWY_ENTRIES)
        draw = list()

        #===== IF NO-ONE IS IN THE GIVEAWAY
        if not dbGvwyEntries:
            return Response(content="No entries in the giveaway.")
        
        #===== BUILD A LIST OF USER ID'S TO DRAW
        for entry in dbGvwyEntries:
            #=== i = LIST WITH USER_ID MULTIPLED BY THE AMOUNT OF ENTRIES THEY HAVE
            i = [entry["user_id"]] * entry['entries']
            draw = draw + i
        
        #===== SHUFFLE THE LIST OF USER ID'S
        random.shuffle(draw)
        
        #===== PICK A WINNER
        winnerid = random.choice(draw)
        
        #===== WRITE WINNER TO DATABASE
        await self.db.execute(pgCmds.ADD_GVWY_PRE_WINS, winnerid, datetime.datetime.utcnow())
        
        #===== GET MEMBER FROM GUILD AND REMOVE GIVEAWAY ROLE
        winner = msg.guild.get_member(winnerid)
        await winner.remove_roles(discord.utils.get(msg.guild.roles, name=self.config.gvwy_role_name), reason="User won giveaway.")
        
        #===== ANNOUNCE WINNER
        return Response(content=f"Congratulations {winner.mention}! You've won a prize in the giveaway.")

    ###Bastion or above close raffle
    @is_high_staff #UPDATED
    async def cmd_endraffle(self, msg):
        """
        Useage:
            [prefix]endraffle
        [Admin/Mod] Closes the raffle.
        """
        #===== CLOSE RAFFLE ENTRY
        NuggetBot.RafEntryActive = False

        #===== GET GIVEAWAY ROLE AND MEMBERS
        giveawayRole = discord.utils.get(msg.guild.roles, name=self.config.gvwy_role_name)
        giveawayMembers = [member for member in msg.guild.members if giveawayRole in member.roles]

        #===== REM GIVEAWAY ROLE FROM EVERYONE
        for member in giveawayMembers:
            await member.remove_roles(giveawayRole, reason="Giveaway ended.")
            await asyncio.sleep(0.1)
        
        #==== CLEAR GIVEAWAY ENTRIES FROM THE DATABASE
        await self.db.execute(pgCmds.REM_ALL_GVWY_ENTRIES)
        
        #==== ANNOUNCE GIVEAWAY CLOSURE
        return Response(content=self.config.gvwy_end_message)

    ###Support or above can allow raffle entries
    @is_any_staff #updated #working
    async def cmd_allowentries(self, msg):
        """
        Useage:
            [prefix]allowentries
        [Any Staff] Turns on raffle entries
        """

        if not NuggetBot.RafEntryActive:
            NuggetBot.RafEntryActive = True
            NuggetBot.RafDatetime = {'open':datetime.datetime.utcnow(), 'past':datetime.datetime.utcnow() + datetime.timedelta(days = -15)}

            return Response(content="Entries now allowed :thumbsup:")
        
        else:
            return Response(content="Entries already allowed :thumbsup:")

    ###Support or above can close raffle entries
    @is_any_staff #updated #working
    async def cmd_stopentries(self, msg):
        """
        Useage:
            [prefix]stopentries
        [Any Staff] Turns off raffle entries
        """

        if NuggetBot.RafEntryActive:
            NuggetBot.RafEntryActive = False

            return Response(content="Entries now turned off :thumbsup:")

        return Response(content="Entries already turned off :thumbsup:")

    ###Support or above can post list of raffle entries
    @in_channel_name([ChnlID.giveaway])
    @is_core #updated #working
    async def cmd_giveawayentries(self, msg):
        """
        Useage:
            [prefix]giveawayentries
        [Core/GiveawayChannel] Posts a list of raffle entries
        """
        #===== GET DATA FROM DATABASE
        gvwyEntries = await self.db.fetch(pgCmds.GET_ALL_GVWY_ENTRIES)

        #===== IF NO-ONE IS IN THE RAFFLE
        if not gvwyEntries:
            return Response(content="There are no entries in the giveaway.", delete_after=20)
        
        entriesMsg = "A total of {} member/s have entered the giveaway.\n".format(len(gvwyEntries))

        for i, entry in enumerate(gvwyEntries, 1):
            member = msg.guild.get_member(entry['user_id'])
            entriesMsg += "No.{}: {}\n".format(i, member.nick or member.name)

        entriesMsg += "Best of luck everyone."

        #===== SPLIT THE MESSAGE ITNO AN ARRAY TO CONFORM WITH THE 2000 CHARACTER LIMIT
        entriesMsg = await self.split_list(entriesMsg, size=2000)

        #===== MESSAGE OUT THE LIST OF RAFFLE ENTRIES
        for i in range(len(entriesMsg)):
            await self.safe_send_message(msg.channel, entriesMsg[i])
        
        return Response(reply=False)
    
    @is_any_staff #updated #working
    async def cmd_giveawayoverride(self, msg):
        """
        Useage:
            [prefix]giveawayoverride <userid/mention>
        [Admin/Mod] Adds a user to a giveaway regardless of qualifcations.
        """
        try:
            args = msg.content.split(" ")
            if len(args) > 2:
                return Response(content="`Useage: [p]giveawayoverride <userid/mention>,\n[Admin/Mod] Adds a user to a giveaway regardless of qualifcations.`")

            #=== SPLIT, REMOVE MENTION WRAPPER AND CONVERT TO INT
            user_id = args[1]
            user_id = user_id.replace("<", "").replace("@", "").replace("!", "").replace(">", "")
            user_id = int(user_id)

        except (IndexError, ValueError):
            return Response(content="`Useage: [p]giveawayoverride <userid/mention>,\n[Admin/Mod] Adds a user to a giveaway regardless of qualifcations.`")

        #===== IF USER DOESN'T EXIST
        if not msg.guild.get_member(user_id):
            return Response(content="User does not exist or is not a member of {}".format(msg.guild.name))

        #-------------------- ENTER MEMBER --------------------
        past_wins = await self.db.fetchval(pgCmds.GET_GVWY_NUM_WINS, user_id)

        #=== LEVELED ENTRY SYSTEM
        if not past_wins:
            entries=3
        elif past_wins == 1:
            entries=2
        else:
            entries=1

        await self.db.execute(pgCmds.ADD_GVWY_ENTRY, user_id, entries, msg.created_at)
        await msg.author.add_roles(discord.utils.get(msg.guild.roles, name=self.config.gvwy_role_name), reason="Staff member added user to giveaway")

        return Response(content=f"<@{user_id}> has been entered to the giveaway by {msg.author.mention}", delete_after=10)


#======================================== SELF ASSIGN ROLES ========================================
    #build role edit report
    async def _report_edited_roles(self, msg, nsfwRole, isRoleAdded, changedRoles, expire_in=15, Archive=True):
        embed = discord.Embed(  description=f"Mention: {msg.author.mention}\n"
                                            f"Has NSFW Role: {nsfwRole}\n",
                                type=       "rich",
                                timestamp=  datetime.datetime.utcnow(),
                                colour=     (0x51B5CC if isRoleAdded else 0xCC1234)
                            )
        embed.set_author(       name=       "Roles updated",
                                icon_url=   AVATAR_URL_AS(msg.author)
                        )

        log = ""
        logPrefix = ("+" if isRoleAdded else "-")

        for i, changedRole in enumerate(changedRoles):
            if i == 0:
                log += f"{logPrefix}{changedRole}"
            else:
                log += f"\n{logPrefix}{changedRole}"

        embed.add_field(        name=       ("Assigned Roles" if isRoleAdded else "Removed Roles"),
                                value=      log,
                                inline=     False
                        )
        embed.set_footer(       icon_url=   msg.guild.icon_url, 
                                text=       msg.guild.name
                        )

        await self.safe_send_message(msg.channel, content=None, embed=embed, expire_in=expire_in)

        if Archive:
            await self.safe_send_message(discord.utils.get(msg.guild.channels, id=self.config.channels['bot_log']), content=None, embed=embed)

        return

    ###HANDLER IF ROLE HAS AN NSFW VERSION
    async def _lewd_role_available(self, msg, baseRoleName, nsfwRoleName, expire_in=15, yn_expire_in=2):
        #===== VARIABLE SETUP
        #-- TRUE IF USER HAS NSFW ROLE
        nsfwRole = bool(discord.utils.get(msg.author.roles, name="NSFW"))
        #-- TRUE IF GRANTING THE ROLE, FALSE IF REMOVING THE ROLE
        toggleAdd = not bool(discord.utils.get(msg.author.roles, name=baseRoleName))
        #-- TRUE IF USER HAS NSFW VERSION OF BASE ROLE
        hasNSFWRoleName = bool(discord.utils.get(msg.author.roles, name=nsfwRoleName))

        reportedRoles = [baseRoleName]

        #===== IF MEMBER HAS NSFW ROLE
        if nsfwRole:
            react = False

            #=== IF USER HAS THE NSFW VERSION OF BASE ROLE **AND** IS REMOVING THE BASE ROLE
            #=== ASK IF THEY WANT NSFW ROLE VERSION REMOVED AS WELL
            if hasNSFWRoleName and not toggleAdd:
                react = await self.ask_yn(msg, f"You have the NSFW version of the {baseRoleName} role.\nWould you like to have that **removed** as well?", expire_in=yn_expire_in)

            #=== IF GRANTING BASE ROLE **AND** DOESN'T HAVE NSFW ROLE VERSION
            #=== ASK IF THEY WANT THE NSFW ROLE VERSION ADDED AS WELL
            if not hasNSFWRoleName and toggleAdd:
                react = await self.ask_yn(msg, f"A NSFW version of the {baseRoleName} role is available.\nWould you like to have that **added** as well?", expire_in=yn_expire_in)

            #=== IF USER SAYS YES
            if react:
                reportedRoles.append(nsfwRoleName)
                #= ADD LEWD ROLE IF TOGGLE TRUE
                if toggleAdd:
                    await msg.author.add_roles(discord.utils.get(msg.guild.roles, name=nsfwRoleName))
                #= REMOVE LEWD ROLE IF TOGGLE FALSE
                else:
                    await msg.author.remove_roles(discord.utils.get(msg.guild.roles, name=nsfwRoleName))

            #=== Time out handing
            elif react == None:
                #= Tell the user they took too long
                await self.safe_send_message(msg.channel, "You took too long to respond. Cancelling action.", expire_in=expire_in)
                return

        #===== ADD BASE ROLE IF TOGGLE IS TRUE
        if toggleAdd:
            await msg.author.add_roles(discord.utils.get(msg.guild.roles, name=baseRoleName))
        #===== REM BASE ROLE IF TOGGLE FALSE
        else:
            await msg.author.remove_roles(discord.utils.get(msg.guild.roles, name=baseRoleName))

        await self._report_edited_roles(msg, nsfwRole=nsfwRole, isRoleAdded=toggleAdd, changedRoles=reportedRoles, expire_in=expire_in)
        return

    ###handler is the role is NSFW
    async def _handle_nsfw_role(self, msg, nsfwRoleName, expire_in=15):
        #TRUE IF HAS NSFW ROLE
        nsfwRole = bool(discord.utils.get(msg.author.roles, name="NSFW"))
        #TRUE IF GRANTING ROLE, FALSE IF REMOVING ROLE
        toggleAdd = not bool(discord.utils.get(msg.author.roles, name=nsfwRoleName))

        #if user has the lewd role and getting rid of it
        if not toggleAdd:
            await msg.author.remove_roles(discord.utils.get(msg.guild.roles, name=nsfwRoleName))
            await self._report_edited_roles(msg, nsfwRole=nsfwRole, isRoleAdded=False, changedRoles=[nsfwRoleName], expire_in=expire_in, Archive=True)
            return

        #if user doesn't have nsfw role and wants the lewd role
        if not nsfwRole and toggleAdd:
            await self.safe_send_message(msg.channel, "NSFW role required.", expire_in=expire_in)
            return

        #user has nsfw role and is requesting the lewd role
        if nsfwRole and toggleAdd:
            await msg.author.add_roles(discord.utils.get(msg.guild.roles, name=nsfwRoleName))
            await self._report_edited_roles(msg, nsfwRole=nsfwRole, isRoleAdded=True, changedRoles=[nsfwRoleName], expire_in=expire_in, Archive=True)
            return

    ###Handler to toggle a role
    async def _toggle_role(self, msg, baseRoleName, expire_in=15):
        baseRole = discord.utils.get(msg.author.roles, name=baseRoleName)
        toggleAdd = not bool(baseRole)

        if toggleAdd:
            await msg.author.add_roles(discord.utils.get(msg.guild.roles, name=baseRoleName))

        else:
            await msg.author.remove_roles(baseRole)

        await self._report_edited_roles(msg, nsfwRole="N/A", isRoleAdded=toggleAdd, changedRoles=[baseRoleName], expire_in=expire_in, Archive=True)
        return

    ###RP role
    @in_reception
    @is_core
    async def cmd_rp(self, msg):
        """
        [Core] Users can toggle the RP role. They get the option of the RP-LEWD role if they have the NSFW role
        """

        await self._lewd_role_available(msg, baseRoleName="RP", nsfwRoleName="RP-LEWD", expire_in=10, yn_expire_in=2)
        return Response(reply=False)

    ###RP Lewd role
    @in_reception
    @is_core
    async def cmd_rp_lewd(self, msg):
        """
        Useage:
            [prefix]rp_lewd
        [NSFW] Users can toggle the RP-LEWD role
        """

        await self._handle_nsfw_role(msg=msg, nsfwRoleName="RP-LEWD")
        return Response(reply=False)

    ###artist role
    @in_reception
    @is_core
    async def cmd_artist(self, msg):
        """
        [Core] Users can toggle the artist role
        """

        await self._toggle_role(msg=msg, baseRoleName="Artist")
        return Response(reply=False)

    ###book_wyrm role
    @in_reception
    @is_core
    async def cmd_book_wyrm(self, msg):
        """
        [Core] Users can toggle the book-wyrm role.
        """

        await self._toggle_role(msg=msg, baseRoleName="Book-Wyrm")
        return Response(reply=False)

    ###ping
    @in_channel([ChnlID.reception, ChnlID.giveaway])
    @is_core
    async def cmd_notifyme(self, msg):
        """
        [Core] Users can toggle the ping role
        """

        await self._toggle_role(msg=msg, baseRoleName="NotifyMe")
        return Response(reply=False)

    ###vore role
    @in_reception
    @is_core
    async def cmd_vore(self, msg):
        """
        [Core] Users can toggle the vore role.
        """

        #True if user has RP role
        #hasRPRole = (True if discord.utils.get(msg.author.roles, name="RP") else False)
        #True if user has Vore role
        #hasVoreRole = (True if discord.utils.get(msg.author.roles, name="Vore") else False)

        #if hasRPRole or hasVoreRole:
        await self._toggle_role(msg=msg, baseRoleName="Vore")
        return Response(reply=False)
    
    @in_reception
    @is_core
    async def cmd_commissioner(self, msg):
        """
        [Core] Users can toggle the commissioner role.
        """
        await self._toggle_role(msg=msg, baseRoleName="Commissioner")
        return Response(reply=False)


#======================================== FUN COMMANDS ========================================
    @is_core
    @in_channel([ChnlID.reception, ChnlID.blessrng])
    async def cmd_rps(self, msg):
        """
        Useage:
            [prefix]rps rock/paper/scissors
        [Core] Plays Rock Paper Scissors.
        """

        try:
            choice = msg.content.split(" ")[1]

        except IndexError:
            return Response(content="`Useage: [p]rps rock/paper/scissors, [Core] Plays Rock Paper Scissors.`", reply=True)

        if choice not in ["rock", "paper", "scissors"]:
            return Response(content="`Useage: [p]rps rock/paper/scissors, [Core] Plays Rock Paper Scissors.`", reply=True)

        return await Fun.rps(msg.author, choice)

    @is_core
    @in_channel([ChnlID.reception, ChnlID.blessrng])
    async def cmd_8ball(self, msg):
        """
        Useage:
            [prefix]8ball <question>
        [Core] Rolls an 8ball
        """

        question = msg.content[(len(self.config.command_prefix) + 5):].strip()

        if len(question) == 0:
            return Response(content="`Useage: [p]8ball <question> [Core] Rolls an 8ball.`", reply=True)

        return await Fun._8ball(question, author=msg.author, guild=msg.guild)
    
    @is_core
    @in_channel([ChnlID.reception, ChnlID.blessrng])
    async def cmd_roll(self, msg):
        """
        Useage:
            [prefix]roll <number>
        [Core] Rolls a dice
        """

        try:
            n = msg.content.split(" ")[1]

        except IndexError:
            return Response(content="`Useage: [p]roll <number> [Core] Rolls a dice.`", reply=True)

        if not n.isdigit():
            return Response(content="`Useage: [p]roll <number> [Core] Rolls a dice.`", reply=True)

        return await Fun.roll(msg.author, int(n))
    
    @is_core
    @in_reception
    async def cmd_leaderboard(self, msg):

        printout = ""

        for i, result in enumerate(await self.db.fetch(DatabaseCmds.get_member_leaderboard)):
            printout += f"{(i+1)}:\t<@{result['user_id']}>\tLvl: {result['level']}\n"

        embed = discord.Embed(  description=printout,
                                colour=     RANDOM_DISCORD_COLOR(),
                                type=       'rich',
                                timestamp = datetime.datetime.utcnow()
                            )

        embed.set_author(       name=       "Dragon Roost Leaderboard",
                                icon_url=   msg.guild.icon_url
                        )
        embed.set_footer(       text=       msg.guild.name,
                                icon_url=   msg.guild.icon_url
                        )

        return Response(embed=embed, delete_after=120)

    @is_core
    @in_reception
    async def cmd_profile(self, msg):
        info = await self.db.fetchrow(DatabaseCmds.get_member_id, int(msg.author.id))

        embed = await GenEmbed.getUserProfile(msg, info)
        
        return Response(embed=embed)


#======================================== Staff Commands ========================================
    ###Kick members who have sat in the entrance gate for 14 days or more.
    @has_role(["Minister"])
    async def cmd_clearentrancegate(self, msg):
        """
        Useage:
            [prefix]clearentrancegate
        [Minister] Kick members who have sat in the entrance gate for 14 days or more.
        """

        freshRole = discord.utils.get(msg.guild.roles, name=self.config.newuser_role)
        coreRole = discord.utils.get(msg.guild.roles, name=self.config.user_role)
        currDateTime = datetime.datetime.utcnow()

        oldFreshUsers = [member for member in msg.guild.members if (freshRole in member.roles) and (coreRole not in member.roles) and ((currDateTime - member.joined_at).days > 13)]

        if len(oldFreshUsers) == 0:
            return Response(content="No members need to be kicked at this time.", delete_after=10)

        react = await self.ask_yn(msg,
                             "{} fresh users will be kicked.\nAre you sure you want to continue?".format(len(oldFreshUsers)),
                             timeout=120,
                             expire_in=2)

        #===== if user says yes
        if react:
            try:
                for member in oldFreshUsers:
                    await member.kick(reason=f"Manual clearing of the entrance gate by {msg.author.id}")

                return Response(content="Done, {} members kicked".format(len(oldFreshUsers)), delete_after=10)

            except discord.errors.Forbidden:
                return Response(content="Can't kick members due to lack of permissions.", delete_after=10)

            except discord.errors.HTTPException:
                return Response(content="Some error occurred. Go blame discord and try again later.", delete_after=10)

        #===== Time out handing
        elif react == None:
            return Response(content="You took too long respond. Cancelling action.", delete_after=10)

        #===== if user says no
        return Response(content="Alright then, no members kicked.", delete_after=10)

    @is_any_staff
    async def cmd_adminhelp(self, msg):
        """
        Useage:
            [prefix]adminhelp
        [Any Staff] Prints a help message with all staff commands.
        """

        commands = ""

        for att in dir(self):
            if att.startswith('cmd_'):
                commands += '{}{}: {}\n'.format(self.config.command_prefix, att.replace('cmd_', '').lower(), getattr(self, att).__doc__)

        commands = commands[:-2]

        if len(commands) > 1980:

            commandList = await self.split_list(commands, 1980)

            for command in commandList:
                command = "```\n" + command + "\n```\n"
                await self.safe_send_message(msg.author, command)

            return Response(reply=False)

        else:
            commands = "```\n" + commands + "\n```\n"
            await self.safe_send_message(msg.author, commands)

        return Response(reply=False)

    @is_high_staff
    async def cmd_logchannel(self, msg):
        """
        Useage:
            [prefix]logchannel <channelID/channelmention>
        [Minister/Bastion] starts logging a channel for deleted messages
        """

        try:
            channel_id = msg.content.split(" ")[1]

        except IndexError:
            return Response(content="`Useage: [p]logchannel <channelID/channelmention>, [Minister/Bastion] starts logging a channel for deleted messages.`", reply=True)

        #===== remove the channel mention
        if channel_id.startswith("<#"):
            channel_id = channel_id.replace("<", "").replace("#", "").replace("!", "").replace(">", "")

        #===== get the channel
        channel = msg.guild.get_channel(channel_id)

        #===== if channel doesn't exist
        if not channel_id.isdigit() and not channel:
            return Response(content="Channel does not exist or is not a channel of {}".format(msg.guild.name), delete_after=10)

        #===== channel already being logged
        if channel_id in self.logging["message_logging"]["monitored_channels"]:
            return Response(content="Channel is already being monitored", delete_after=10)

        monitored_channels = self.logging["message_logging"]["monitored_channels"]
        monitored_channels_update = ""

        if monitored_channels == "":
            monitored_channels_update = channel_id

        else:
            monitored_channels_update = monitored_channels + " " + channel_id

        self.logging.set("message_logging", "monitored_channels", str(monitored_channels_update))

        with open("logging.ini", "w") as configfile:
            self.logging.write(configfile)

        return Response(content="{} will now be monitored for deleted messages".format(channel.name), delete_after=10)

    @is_high_staff
    async def cmd_stoplogchannel(self, msg):
        """
        Useage:
            [prefix]stoplogchannel <channelID/channelmention>
        [Minister/Bastion] stops logging a channel for deleted messages
        """

        try:
            channel_id = msg.content.split(" ")[1]

        except IndexError:
            return Response(content="`Useage: [p]stoplogchannel <channelID/channelmention>, [Minister/Bastion] stops logging a channel for deleted messages.`")

        #===== remove the channel mention
        if channel_id.startswith("<#"):
            channel_id = channel_id.replace("<", "").replace("#", "").replace("!", "").replace(">", "")

        #===== get the channel
        channel = msg.guild.get_channel(channel_id)

        #===== if channel doesn't exist
        if not channel_id.isdigit():
            return Response("`Channel does not exist or is not a channel of {}`".format(msg.guild.name), delete_after=10)

        #===== channel already being logged
        if channel_id not in self.logging["message_logging"]["monitored_channels"]:
            return Response(content="`{} was not already being monitored`".format(channel.name), delete_after=10)

        monitored_channels = self.logging["message_logging"]["monitored_channels"].split(" ")
        monitored_channels.remove(channel_id)

        monitored_channels_update = " ".join(monitored_channels)

        self.logging.set("message_logging", "monitored_channels", str(monitored_channels_update))

        with open("logging.ini", "w") as configfile:
            self.logging.write(configfile)

        if channel:
            return Response(content="`{} will no longer be monitored for deleted messages`".format(channel.name), delete_after=10)

        return Response(content="`{} will no longer be monitored for deleted messages`".format(channel_id), delete_after=10)

    @has_role(["Minister"])
    async def cmd_logignoremember(self, msg):
        """
        Useage:
            [prefix]logignoremember <userID/mention>
        [Minister] add a member to channel log whitelist, so deleted messages from them do not get logged
        """

        try:
            user_id = msg.content.split(" ")[1]

        except IndexError:
            return Response(content="`Useage: [p]logignoremember <userID/mention>, [Minister] add a member to channel log whitelist, so deleted messages from them do not get logged.`")
        
        #===== remove the user mention
        if user_id.startswith("<@"):
            user_id = user_id.replace("<", "").replace("@", "").replace("!", "").replace(">", "")

        #===== get the member
        tMember = msg.guild.get_member(user_id)

        #===== if member doesn't exist
        if not user_id.isdigit() and not tMember:
            return Response(content="User does not exist or is not a member of {}".format(msg.guild.name), delete_after=10)

        #===== member already being logged
        if user_id in self.logging["message_logging"]["ignored_users"]:
            return Response(content="User is already being ignored.", delete_after=10)

        ignored_users = self.logging["message_logging"]["ignored_users"]
        ignored_users_update = ""

        if ignored_users == "":
            ignored_users_update = user_id

        else:
            ignored_users_update = ignored_users + " " + user_id

        self.logging.set("message_logging", "ignored_users", ignored_users_update)

        with open("logging.ini", "w") as configfile:
            self.logging.write(configfile)

        return Response(content="{}#{} | {} will not have their deleted messages monitored.".format(tMember.name, tMember.discriminator, tMember.mention), delete_after=10)

    @has_role(["Minister"])
    async def cmd_stoplogignoremember(self, msg):
        """
        Useage:
            [prefix]stoplogignoremember <userID/mention>
        [Minister] removes a member to channel log whitelist, so deleted messages from them will get logged
        """

        try:
            user_id = msg.content.split(" ")[1]

        except IndexError:
            return Response(content="`Useage: [p]stoplogignoremember <userID/mention>, [Minister] removes a member to channel log whitelist, so deleted messages from them will get logged.`")

        #===== remove the user mention
        if user_id.startswith("<@"):
            user_id = user_id.replace("<", "").replace("@", "").replace("!", "").replace(">", "")

        #===== get the member
        tMember = msg.guild.get_member(user_id)

        #===== if member doesn't exist
        if not user_id.isdigit():
            return Response(content="Not a valid user", delete_after=10, reply=True)

        #===== member already being logged
        if user_id not in self.logging["message_logging"]["ignored_users"]:
            return Response(content="User is not already being ignored.", delete_after=10, reply=True)

        ignored_users = self.logging["message_logging"]["ignored_users"].split(" ")
        ignored_users.remove(user_id)

        ignored_users_update = " ".join(ignored_users)

        self.logging.set("message_logging", "ignored_users", ignored_users_update)

        with open("logging.ini", "w") as configfile:
            self.logging.write(configfile)

        if tMember:
            return Response(content="{0.name}#{0.discriminator} | {0.mention} has been removed from the logging whitelist.".format(tMember), delete_after=10)

        return Response(content="{} has been removed from the logging whitelist".format(user_id), delete_after=10)

    @has_role(["Minister"])
    async def cmd_togglechannellogging(self, msg):
        """
        Useage:
            [prefix]togglechannellogging
        [Minister] toggles on/off the logging of deleted messages.
        """

        current_setting = self.logging["message_logging"]["enabled"]

        if current_setting == "True":
            updated_setting = "False"
        else:
            updated_setting = "True"

        self.logging.set("message_logging", "enabled", updated_setting)

        with open("logging.ini", "w") as configfile:
            self.logging.write(configfile)

        return Response(content="Channel logging has been set to {}".format(updated_setting))

    @has_role(["Minister"]) #updated
    async def cmd_loginvites(self, msg, quiet=False):
        """
        Useage:
            [prefix]loginvites
        [Minister] When called the function will make the init invite log in a json file
        """
        #===== Log invites
        inviteLog = await self._get_invite_info()

        if inviteLog is not None:
            await self.db.execute(pgCmds.ADD_INVITES, json.dumps(inviteLog))
            return Response(content="Current invite information has been logged.")

        else:
            return Response(content="Invite information could not be found.")

    @is_any_staff #updated
    async def cmd_makeunqiueinvite(self, msg):
        """
        Usage:
            [prefix]makeunqiueinvite <channelid/channelmention>
        [Any Staff] Creates a unique invite for specified channel.
        """
        try:
            chl_id = msg.content.split(" ")[1]

            #=== REMOVE CHANNEL MENTION
            if chl_id.startswith("<#"):
                chl_id = chl_id.replace("<", "").replace("#", "").replace("!", "").replace(">", "")

            #=== CONVERT STR TO INT
            chl_id = int(chl_id)

        except (IndexError, ValueError):
            return Response(content="`Useage: [p]makeunqiueinvite <channelid/channelmention> Creates a unique invite for specified channel.`")

        #===== FIND THE CHANNEL
        chl = msg.guild.get_channel(chl_id)

        #===== IF CHANNEL DOES NOT EXIST
        if chl == None:
            return Response(content='Channel "{}" not found'.format(chl_id))

        #===== MAKE THE INVITE
        try:
            inv = await chl.create_invite(unique = True)

            #=== RETURN INVITE
            return Response(content=f"Invite {inv.url} for {inv.channel.name} has been successfully made")

        except discord.errors.Forbidden:
            #=== REPORT PERMISSION ERROR
            return Response(content="`I do not have the permission needed to create an invite for selected channel`")

        except discord.errors.HTTPException:
            #=== REPORT GENERIC ERROR
            return Response(content= "`I could not create an invite for the selected channel`")

    @is_any_staff
    async def cmd_roleperms(self, msg):
        """
        Useage:
            [prefix]roleperms <roleName/roleMention>
        [Any Staff] Gets all the perms for a role both default and channel overwrite.
        """

        try:
            roleID = msg.content.split(" ")[1]
            roleName = (msg.clean_content.split(" ")[1])

        except IndexError:
            return Response(content="`Useage: [p]roleperms <roleName/roleMention> Gets all the perms for a role both default and channel overwrite.`")

        #===== if mention is a user
        if msg.guild.get_member(roleID.replace("<", "").replace("@", "").replace("!", "").replace(">", "")) is not None:
            return Response(content="`Useage: [p]roleperms <roleName/roleMention> Gets all the perms for a role both default and channel overwrite. (not a user mention)`")

        #===== dealing with the @here mention
        if "here" in roleName.lower():
            return Response(content='`Cannot help you with the @ here mention.`')

        #===== dealing with the @everyone mention
        if "everyone" in roleName.lower():
            role = msg.guild.default_role

            #=== If the everyone role cannot be found
            if role == None:
                return Response(content='`Role not found`')

        #===== Dealing with the rest of the roles
        else:
            #=== remove the channel mention
            if roleID.startswith("<@"):
                roleID = roleID.replace("<", "").replace("@", "").replace("&", "").replace(">", "")

            if roleName.startswith("@"):
                roleName = roleName.replace("@", "")

            #=== get the role
            role = discord.utils.get(msg.guild.roles, id=roleID)

            #=== If role does not exist
            if role == None:
                #role = (role for role in msg.guild.roles if role.name == roleID)[0]
                role = discord.utils.get(msg.guild.roles, name=roleName)

                if role == None:
                    return Response(content='`Role not found`')

        #===== If role as Admin perms end function early
        if role.permissions.administrator:
            embed= await GenEmbed.getRolePermsAdmin(role=role, msg=msg)
            return Response(embed=embed)

        #===== go off and generate the info and embeds
        embeds = await GenEmbed.getRolePerms(msg=msg, role=role, bot_avatar_url=self.user.avatar_url)
        
        #===== send each generated embed as it's own message
        for embed in embeds:
            await self.safe_send_message(msg.channel, embed=embed)

        return Response(reply=False)

    @is_any_staff
    async def cmd_userperms(self, msg):
        """
        Useage:
            [Prefix]userperms <userID/userMention>
        [Any Staff] Gets all the perms for a role both default and channel overwrite.
        """

        try:
            user_id = msg.content.split(" ")[1]

        #if user == idiot
        except IndexError:
            return Response(content="`Useage: [p]userperms <userID/userMention> Gets all the perms for a role both default and channel overwrite.`", delete_after=10)

        #===== remove the user mention
        if user_id.startswith("<@"):
            user_id = user_id.replace("<", "").replace("@", "").replace("!", "").replace(">", "")

        #===== get the member
        member = msg.guild.get_member(user_id)

        #===== if member doesn't exist
        if not user_id.isdigit() and not member:
            return Response(content="`User does not exist or is not a member of {}`".format(msg.guild.name), delete_after=10)
        
        #===== Setting this up now because now I know I will be sending a reply.
        # 1 hour is taken off of the timestamp because discord always reports it 1 hour ahead
        timestamp = datetime.datetime.now()
        timestamp = timestamp - datetime.timedelta(seconds=3600)

        #===== If user is owner; end function early
        if member == msg.guild.owner:
            embed = await GenEmbed.getUserPermsOwner(member=member, msg=msg)
            return Response(embed=embed)

        #===== If user has Admin perms; end function early
        isAdmin = False
        for role in member.roles:
            if role.permissions.administrator:
                isAdmin = True

        if isAdmin:
            embed = await GenEmbed.getUserPermsAdmin(member=member, msg=msg)
            return Response(embed=embed)

        embeds = await GenEmbed.getUserPerms(member=member, msg=msg)
        
        #===== send each generated embed as it's own message
        for embed in embeds:
            await self.safe_send_message(msg.channel, embed=embed)

        return Response(reply=False)

    @is_high_staff #new
    async def cmd_banbyid(self, msg):
        """
        Useage:
            [prefix]banbyid <userid/mention> <reason>
        [Admin/Mod] Bans a user from guild using their ID alone.
        """
        try:
            args = msg.content.split(" ")
            if len(args) > 3:
                return Response(content="`Useage: [p]banbyid <userid/mention> <reason>, [Admin/Mod] Bans a user from guild using their ID alone.`")

            #=== SPLIT, REMOVE MENTION WRAPPER AND CONVERT TO INT
            user_id = args[1]
            user_id = user_id.replace("<", "").replace("@", "").replace("!", "").replace(">", "")
            user_id = int(user_id)

            if len(args) == 3:
                reason = args[2]
                reason = reason[:1000]
            else:
                reason = None

        except (IndexError, ValueError):
            return Response(content="`Useage: [p]banbyid <userid/mention> <reason>, [Admin/Mod] Bans a user from guild using their ID alone.`")


        try:
            await self.bot.http.ban(user_id=user_id, guild_id=self.config.target_guild_id, delete_message_days=1, reason=reason)
            return Response(content=f"<@{user_id}> has been banned from this Guild.")

        #===== REPORT PERMISSION ERROR
        except discord.errors.Forbidden:
            return Response(content=f"`I do not have the permission needed to ban <@{user_id}> from this Guild.`")

        #===== REPORT GENERIC ERROR
        except discord.errors.HTTPException as e:
            print(e)
            return Response(content=f"`I could no ban <@{user_id}> due to generic error.`")

#======================================== GALLARY STUFF ========================================

    #async def delete_logic(self):
    #fast delete = dict()
    #                    channelid = list(msgids)

        #id = self.db.fetch(pgCmds.GET_GALL_CHIDS_AFTER, datetime.datetime.utcnow())

        #id2 = [chid for ch["ch_id"] in id]
    #await self.bot.http.delete_messages(channelID, listofMSGids, reason=reason)
#======================================== OWNER COMMANDS ========================================
    @owner_only
    async def cmd_restart(self, msg):
        """
        Useage:
            [prefix]restart
        [Bot Owner] Restarts the bot.
        """
        embed= await GenEmbed.ownerRestart(msg=msg)

        await self.safe_send_message(msg.channel, embed=embed)
        await self.safe_delete_message(msg)
        #self.exit_signal = exceptions.RestartSignal()

        raise exceptions.RestartSignal

    @owner_only
    async def cmd_shutdown(self, msg):
        """
        Useage:
            [prefix]shutdown
        [Bot Owner] Shuts down the bot.
        """

        embed = await GenEmbed.ownerShutdown(msg)

        await self.safe_send_message(msg.channel, embed=embed)

        #self.exit_signal = exceptions.TerminateSignal()
        await self.safe_delete_message(msg)
        raise exceptions.TerminateSignal

    @owner_only
    async def cmd_findfeedback(self, msg):
        """
        Useage:
            [prefix]findfeedback <msg_id> or <msg_id-ch_id>
        [Bot Owner] Returns user id of who posted anon feedback.
        """
        try:
            args= msg.content.split(" ")

            if len(args) > 2:
                return Response(content="`Useage: findfeedback <msg_id>, [Bot Owner] Returns user id of who posted anon feedback.`")

            #=== SPLIT, REMOVE MENTION WRAPPER AND CONVERT TO INT
            msg_id = args[1]
            if len(msg_id) > 18:
                msg_id, ch_id = msg_id.split('-')

                if len(msg_id) >= 18 and len(ch_id) >= 18:
                    msg_id = int(msg_id)
                    ch_id = int(ch_id)

                else:
                    return Response(content="`Useage: findfeedback <msg_id>, [Bot Owner] Returns user id of who posted anon feedback.`")

            else:
                msg_id = int(msg_id)
                ch_id = None

        except (IndexError, ValueError):
            return Response(content="`Useage: findfeedback <msg_id>, [Bot Owner] Returns user id of who posted anon feedback.`")  
        
        # IF NO CHANNEL ID WAS PROVIDED
        if not ch_id:
            data = await self.db.fetchrow(pgCmds.GET_MEM_DM_FEEDBACK, msg_id, msg.guild.id)

        else:
            data = await self.db.fetchrow(pgCmds.GET_MEM_CH_DM_FEEDBACK, msg_id, ch_id, msg.guild.id)

        #===== IF NO RECORD IN THE DATABASE
        if not data:
            return Response(content=f"No record matching id {msg_id} found.") 


        present = bool(msg.guild.get_member(data['user_id']))
        
        embed = await GenEmbed.genFeedbackSnooping(data['user_id'], data['sent_msg_id'], data['sent_chl_id'], data['sent_srv_id'], present, data['timestamp'], msg.guild)
 
        return Response(embed=embed)

        
        

async def call_schedule(func=None, arg=None, user_id=None, roles=None):
    if roles is not None:
        await NuggetBot.bot._show_server(user_id, roles)
        return
    if arg is None:
        await NuggetBot.bot._kick_entrance(user_id)
        return
    await getattr(NuggetBot.bot, func)(arg)