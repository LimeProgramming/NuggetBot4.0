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
import random
import logging
import discord
import asyncio
import asyncpg
import datetime
from typing import Union
from discord.ext import commands, tasks

from .util import checks, cogset
from nuggetbot.config import Config
from nuggetbot.database import DatabaseCmds as pgCmds
from nuggetbot.util.chat_formatting import RANDOM_DISCORD_COLOR

import dblogin 

log = logging.getLogger("bot")

class GuildDB(commands.Cog):
    """Handle the Gallery channels."""

    config = None 
    delete_after = 15
    
    def __init__(self, bot):
        self.bot = bot
        self.db = None
        self.cog_ready = False
        self.cogset = None
        GuildDB.config = Config()


  # -------------------- STATIC METHOD --------------------  
    @staticmethod
    async def oneline_valid(content):
        try:
            args = content.split(" ")
            if len(args) > 1:
                return False 

            return True

        except (IndexError, ValueError):
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
    async def StripMention(content):
        try:
            if isinstance(content, int):
                return content

            #=== SPLIT, REMOVE MENTION WRAPPER AND CONVERT TO INT
            content = content.replace("<", "").replace("@", "").replace("!", "").replace(">", "")
            content = int(content)
            return content

        except (IndexError, ValueError):
            return False


  # -------------------- LOCAL COG STUFF --------------------  
    @asyncio.coroutine
    async def cog_command_error(self, ctx, error):
        if isinstance(error, discord.ext.commands.errors.NotOwner):
            await ctx.guild.owner.send(content=f"{ctx.author.mention} tried to use the owner only command{ctx.invoked_with}")

        elif isinstance(error, discord.ext.commands.errors.MissingRequiredArgument):
            await ctx.send_help(ctx.command)

        elif isinstance(error, discord.ext.commands.errors.MissingPermissions):
            await ctx.channel.send('Admin permissions are required to use this command.')

        else:
            print('Ignoring exception in {}'.format(ctx.invoked_with), file=sys.stderr)
            print(error)

    async def cog_after_invoke(self, ctx):
        if GuildDB.config.delete_invoking:
            await ctx.message.delete()

        return

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


  # -------------------- COMMANDS --------------------
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    @commands.command(pass_context=True, hidden=False, name='logstaff', aliases=[], brief='[Admin] Log history of staff change.')
    async def cmd_logstaff(self, ctx, *, staff_id: Union[int, str], maker_id=0, received_role=0, removed_role=0, reason="None"):
        """
        [Admin] Log history of staff change.

        Args:
            staff_id : ID of the member who has been added/removed from staff
            maker_id : ID of the existing staff who added/removed staff_id from staff. If not provided, it is assumed the owner edited the roles of ex/staff.
            received_role : Role ID of the staff role which has been applied to the new guy, this is 0 if role was removed.
            removed_role : Role ID of the staff tole which has been removed from the ex-staff, this is 0 if the role was added.
            reason : Reason for this changed, limited to 1000 chatactors.
        """

        # ===== MAKE SURE A ROLE IS EITHER ADDED OR REMOVED.
        if received_role == 0 and removed_role == 0:
            await ctx.send("`A role needs to be added or removed.`")
            await ctx.send_help('logstaff')
            return

        # ===== ASSUME THE COMMAND INVOKER EDITED THE EX/STAFF
        if maker_id == 0:
            maker_id = ctx.author.id


        # ===== MAKE SURE ALL VARIABLES WHICH SHOULD BE INTS, ARE INT. 
        try:
            maker_id = GuildDB.StripMention(maker_id)
            staff_id = GuildDB.StripMention(staff_id)
            maker_id = int(maker_id)
            received_role = int(received_role)
            removed_role = int(received_role)

        # ===== IF A VARIABLE IS NOT AN INT, THEN CALL THE USER A MORON.
        except ValueError:
            await ctx.send("`All id's provided **must** be a number.`")
            await ctx.send_help('logstaff')
            return

        # ===== COMMIT DATA TO DATABASE
        staff_data = staff_id, maker_id, received_role, removed_role, reason[:1000]

        await self.db.execute(pgCmds.APPEND_GUILD_STAFF, staff_data, ctx.guild.id)

        # ===== GIVE A RETURN SO THE INVOKER DOESN'T THINK THAT NOTHING HAPPENED.
        embed = discord.Embed(  
            description=f"Ex/Staff:         <@{staff_id}>"
                        f"Maker:            <@{maker_id}>"
                        f"Received Role:    <@{received_role}>"
                        f"Removed Role:     <@{removed_role}>"
                        f"Reason:           {reason}", 
                        colour=     RANDOM_DISCORD_COLOR(),
                        type=       "rich",
                        timestamp=  datetime.datetime.utcnow()
                    )

        await ctx.channel.send(embed=embed)

        return
 
 
  # -------------------- READY LISTENER --------------------
    @commands.Cog.listener()
    async def on_ready(self):
        # ===== CONNECT TO THE POSTGRE DATABASE    
        await self.connect_db()

        # ===== LOAD THE COGSET
        self.cogset = await cogset.LOAD(cogname=self.qualified_name)

        if not self.cogset:
            self.cogset= dict(
                lastAuditLog=    None
            )

            await cogset.SAVE(self.cogset, cogname=self.qualified_name)

        # ===== DELAY THE COG BY 2 MINUTES TO LET THE MAIN BOT DO IT'S WORK
        await asyncio.sleep(120)

        # ===== GET THE GUILD INFO FROM DATABASE
        data = await self.db.fetchrow(pgCmds.GET_GUILD_DATA, GuildDB.config.target_guild_id)

        # ===== IF THE THERE IS NO INFORMATION ABOUT THE GUILD IN THE DATABASE
        if not data:
            # === GET THE GUILD
            guild = self.bot.get_guild(GuildDB.config.target_guild_id)

            await self.db.execute(pgCmds.PRIME_GUILD_DATA, guild.id, guild.owner_id, guild.created_at, [channel.id for channel in guild.channels])

            # === GETS THE GUILDS ICON
            icon_type = "gif" if guild.is_icon_animated() else "webp"
            i_bytes = guild.icon_url_as(format=icon_type).read()

            guild_icon = guild.icon, icon_type, i_bytes, datetime.datetime.utcnow()

            #---------- Ship to the DB
            await self.db.execute(pgCmds.SET_GUILD_ICON, guild_icon, guild.id)

            # === CYCLE THROUGH A GUILDS EMOJIS, ADDING THEM TO THE DATABASE
            for emoji in guild.emojis:

                e_id, ext = (emoji.url.__str__().split("/").pop()).split(".")

                e_bytes = await emoji.url.read()

                emoji_byte = str(emoji.name), int(e_id), ext, e_bytes, emoji.created_at

                await self.db.execute(pgCmds.APPEND_GUILD_EMOJIS, emoji_byte, guild.id)

            # === GUILD AUDIT LOGS
            async for entry in guild.audit_logs(limit=None, oldest_first=True):
                # = GUILD BANS
                if entry.action == discord.AuditLogAction.ban:
                    ban = entry.target.id, entry.user.id, str(entry.reason)[:250] or "None", entry.id, entry.created_at
                    await self.db.execute(pgCmds.APPEND_GUILD_BANS, ban, guild.id)

                # = GUILD UNBANS
                elif entry.action == discord.AuditLogAction.unban:
                    unban = entry.target.id, entry.user.id, str(entry.reason)[:250] or "None", entry.id, entry.created_at
                    await self.db.execute(pgCmds.APPEND_GUILD_UNBANS, unban, guild.id)

                # = TAKE NOTE OF THE LAST AUDIT LOG ID
                if self.cogset['lastAuditLog'] < entry.id:
                    self.cogset['lastAuditLog'] = entry.id

            # === ROLES
            for role in sorted(guild.roles, key=lambda x: x.position):
                role_info = role.id, role.name, role.permissions.value, role.hoisted, role.is_default(), role.colour.value, role.created_at, False
                await self.db.execute(pgCmds.APPEND_GUILD_ROLES, role_info, guild.id)

        self.cog_ready = True 


  # -------------------- OTHER LISTENERS --------------------
    @commands.Cog.listener()        
    async def on_guild_update(self, before, after):
        # ===== OWNER CHECK
        if before.owner_id != after.owner_id:
            await self.db.execute(pgCmds.SET_GUILD_OWNER, after.owner_id, after.id)

        # ===== GUILD ICON CHECK
        elif before.icon != after.icon:

            icon_type = "gif" if after.is_icon_animated() else "webp"
            i_bytes = after.icon_url_as(format=icon_type).read()

            guild_icon = after.icon, icon_type, i_bytes, datetime.datetime.utcnow()

            #---------- Ship to the DB
            await self.db.execute(pgCmds.SET_GUILD_ICON, guild_icon, after.id)


        return

   # -------------------- ROLE MANAGEMENT --------------------
    @commands.Cog.listener()        
    async def on_guild_role_create(self, role):

        role_info = role.id, role.name, role.permissions.value, role.hoisted, role.is_default(), role.colour.value, role.created_at, False
        await self.db.execute(pgCmds.APPEND_GUILD_ROLES, role_info, role.guild.id)

        return

    @commands.Cog.listener()        
    async def on_guild_role_delete(self, role): 
        # ===== FETCH DATA FROM THE DATABASE
        dbroles = await self.db.fetch(pgCmds.GET_GUILD_ROLES, role.guild.id)
        oldentry = None 
        newentry = None 

        #id, name, perms, hoisted, default, colour, date, deleted
        for dbrole in dbroles:
            # === IF THE DELETED ROLE ID MATCHES A ROLE ID FROM THE DATABASE
            if dbrole[0] == role.id:

                newentry = dbrole
                oldentry = dbrole
                newentry[7] = True

                break
        
        # ===== IF DELETED ROLE WAS NOT FOUND IN THE DATABASE, ADD IT AS A DELETED ROLE.
        if not oldentry:
            role_info = role.id, role.name, role.permissions.value, role.hoisted, role.is_default(), role.colour.value, role.created_at, True
            await self.db.execute(pgCmds.APPEND_GUILD_ROLES, role_info, role.guild.id)

        # ===== ELSE IS THE ROLE WAS FOUND IN THE DATABASE, UPDATE THE ENTRY TO MARK THE ROLE AS DELETED
        else:
            await self.db.execute(pgCmds.UPDATE_GUILD_ROLE, oldentry, newentry, role.guild.id) 

        return

    @commands.Cog.listener()        
    async def on_guild_role_update(self, before, after):
        # ===== IF ROLE CHANGE IS NOT SOMETHING WHICH WE STORE IN THE DATABASE, IGNORE THE CHANGE
        if not ((after.name != before.name)         or (after.permissions.value != before.permissions.value)
            or (after.hoisted != before.hoisted)    or (after.colour.value != before.colour.value)):
            return

        # ===== FETCH DATA FROM THE DATABASE
        dbroles = await self.db.fetch(pgCmds.GET_GUILD_ROLES, after.guild.id)
        role_found = False

        # ===== LOOP THROUGH THE DATA STORED IN THE DB
        for dbrole in dbroles:
            # === IF THE EDITED ROLE ID MATCHES A ROLE ID FROM THE DATABASE
            if dbrole[0] == after.id:
                role_found = dbrole
                break
        
        # ===== IF ROLE WAS FOUND IN THE DB STORE
        if role_found:
            role_info = after.id, after.name, after.permissions.value, after.hoisted, after.is_default(), after.colour.value, after.created_at, False
            await self.db.execute(pgCmds.UPDATE_GUILD_ROLE, role_found, role_info, after.guild.id) 

        # ===== IF TOLE WAS NOT FOUND IN THE DB STORE, ADD IT TO THE DB STORE
        else:
            role_info = after.id, after.name, after.permissions.value, after.hoisted, after.is_default(), after.colour.value, after.created_at, False
            await self.db.execute(pgCmds.APPEND_GUILD_ROLES, role_info, after.guild.id)

        return


   # -------------------- EMOJI MANAGEMENT --------------------
    @commands.Cog.listener()        
    async def on_guild_emojis_update(self, guild, before, after):
        # ===== Wait for the cog to be ready. This should help avoid data becoming corrupt or going out of order.
        while not self.cog_ready:
            await asyncio.sleep(5)

        # ===== If the list of new emojis is not greater than the list of old emojis
        # if this check fails it means that an emoji has been removed and the point of this function is to log all emojis ever added to the guild.
        if not len(after) > len(before):
            return 

        # ===== Cycle through the emojis, old ones are removed in the implied list.
        for emoji in [emoji for emoji in after if emoji not in before]:

            e_id, ext = (emoji.url.__str__().split("/").pop()).split(".")

            e_bytes = await emoji.url.read()

            emoji_byte = str(emoji.name), int(e_id), ext, e_bytes, emoji.created_at

            await self.db.execute(pgCmds.APPEND_GUILD_EMOJIS, emoji_byte, guild.id)

        return


   # -------------------- CHANNEL MANAGEMENT --------------------
    @commands.Cog.listener()  
    async def on_guild_channel_delete(self, channel):
        r = [ch.id for ch in channel.guild.channels]
        
        await self.db.execute(pgCmds.SET_GUILD_CHANNELS, r , channel.guild.id) 

        return

    @commands.Cog.listener()  
    async def on_guild_channel_create(self, channel):
        r = [ch.id for ch in channel.guild.channels]
        
        await self.db.execute(pgCmds.SET_GUILD_CHANNELS, r , channel.guild.id) 

        return

    @commands.Cog.listener()  
    async def on_guild_channel_update(self, before, after):
        pass
    

   # -------------------- MEMBER MANAGEMENT --------------------
    @commands.Cog.listener()
    async def on_member_join(self, member):
        pass

    @commands.Cog.listener()        
    async def on_member_remove(self, member):
        try:
            banned = await member.guild.fetch_ban(member)

        except discord.Forbidden:
            #=== You do not have proper permissions to get the information.
            log.info("Bot does not have ban_members permission in guild.")
            return

        except discord.NotFound:
            #=== This user is not banned.
            return
        
        except discord.HTTPException:
            #=== An error occurred while fetching the information.
            log.critial("An error occured retreving information, might need restarting.")
            return
        
        ban = member.guild.audit_logs(limit=1, action=discord.AuditLogAction.ban, oldest_first=False, after=(datetime.datetime.utcnow() - datetime.timedelta(seconds=10))).flatten()
        return

    @commands.Cog.listener()        
    async def on_member_ban(self, guild, user):
        #(User banned, staff_id, Reason, timestamp)
        data = self.get_ban_unban_data(discord.AuditLogAction.ban, user, guild)
        
        await self.db.execute(pgCmds.APPEND_GUILD_BANS, data)

    @commands.Cog.listener()        
    async def on_member_unban(self, guild, user):
        #(User banned, staff_id, Reason, timestamp)
        data = self.get_ban_unban_data(discord.AuditLogAction.unban, user, guild)

        await self.db.execute(pgCmds.APPEND_GUILD_UNBANS, data)


  # -------------------- FUNCTIONS --------------------

    async def get_ban_unban_data(self, action, user: Union[discord.User, discord.Member], guild: discord.Guild):
        """
        Gets most recent Audit Log data about a ban or unban. 
        Returns Generic data if bot lacks permission to view the audit log

        Args:
            action [discord.AuditLogAction]
            user   [discord.Member, discord.User]
            guild  [discord.Guild]

        Returns
            list
        """
        past_id = discord.utils.time_snowflake(datetime.datetime.utcnow() - datetime.timedelta(seconds=10), high=True)
        data = []

        try:
            async for entry in guild.audit_logs(limit=10, action=action, oldest_first=False):
                if entry.id >= past_id and entry.target.id == user.id:
                    
                    if data and data[4] > entry.id:
                        data = [entry.target.id, entry.user.id, entry.reason[:1000] or "None", entry.created_at, entry.id]
                    else:
                        data = [entry.target.id, entry.user.id, entry.reason[:1000] or "None", entry.created_at, entry.id]

        except discord.errors.Forbidden:
            data = [user.id, 0, "None", datetime.datetime.utcnow(), 0]
            print("[Info]  Missing view_audit_log permission.")

        except discord.errors.HTTPException:
            data = [user.id, 0, "None", datetime.datetime.utcnow(), 0]
            print("[Info]  HTTP error occured, likly being rate limited or blocked by cloudflare. Restart recommended.")

        return data[:4]


  # -------------------- TASKS --------------------
    @tasks.loop(hours=24.0)
    async def auditlog_update(self):
        """
        Daily task:
            This stores the last the most recent audit log id into the cogset store.
            The value is used to pull relivant audit log data upon a bot restart.
        """
        guild = self.bot.get_guild(GuildDB.config.target_guild_id)

        entry = await guild.audit_logs(limit=1, oldest_first=False, action=None).flatten()

        self.cogset['lastAuditLog'] = entry[0].id

        await cogset.SAVE(self.cogset, cogname=self.qualified_name)

def setup(bot):
    bot.add_cog(GuildDB(bot))