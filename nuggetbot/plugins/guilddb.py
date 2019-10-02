from discord.ext import commands
import discord
import asyncio
import asyncpg
import datetime
import random
import logging

from typing import Union

from nuggetbot.config import Config
from nuggetbot.database import DatabaseLogin
from nuggetbot.database import DatabaseCmds as pgCmds
from .cog_utils import in_channel, IS_CORE, in_channel_name, IN_RECEPTION, has_role, IS_HIGH_STAFF, IS_ANY_STAFF

import dblogin 

log = logging.getLogger("bot")

class GuildDB(commands.Cog):
    """Handle the Gallery channels."""

    config = None 
    delete_after = 15
    
    def __init__(self, bot):
        self.RafEntryActive = False
        self.RafDatetime = []
        self.bot = bot
        self.db = None

  #-------------------- STATIC METHOD --------------------  
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


  #-------------------- LOCAL COG STUFF --------------------  
    async def on_cog_command_error(self, ctx, error):
        if isinstance(error, discord.ext.commands.errors.NotOwner):
            ctx.guild.owner.send(content=f"{ctx.author.mention} tried to use the owner only command{ctx.invoked_with}")

    async def cog_after_invoke(self, ctx):
        if GuildDB.config.delete_invoking:
            await ctx.message.delete()

        return


  #-------------------- COMMANDS --------------------
    @commands.is_owner()
    @commands.command(pass_context=True, hidden=True, name='GuildPopulateBans', aliases=[])
    async def GuildPopulateBans(self, ctx):
        valid = GuildDB.oneline_valid(ctx.message.content)

        if not valid:
            ctx.channel.send(content="`Useage: [p]GuildPopulateBans, [Bot Owner] adds any missing ban information to the database.`")
            return 
        
        return


    
    #-------------------- LISTENERS --------------------
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
    async def on_guild_update(self, before, after):
        ###===== OWNER CHECK
        if before.owner_id != after.owner_id:
            await self.db.execute(pgCmds.SET_GUILD_OWNER, after.owner_id, after.id)

        ###=====

    @commands.Cog.listener()        
    async def on_guild_role_create(self, role):
        r = [role.id for role in role.guild.roles]
        
        await self.db.execute(pgCmds.SET_GUILD_ROLES, r , role.guild.id) 

    @commands.Cog.listener()        
    async def on_guild_role_delete(self, role):
        r = [role.id for role in role.guild.roles]
        
        await self.db.execute(pgCmds.SET_GUILD_ROLES, r , role.guild.id) 

    @commands.Cog.listener()        
    async def on_guild_role_update(self, before, after):
        pass

    @commands.Cog.listener()        
    async def on_guild_emojis_update(self, guild, before, after):
        pass

    @commands.Cog.listener()        
    async def on_member_ban(self, guild, user):
        #(User banned, staff_id, Reason, timestamp)
        data = self.get_ban_unban_data(discord.AuditLogAction.ban, user, guild)
        
        await self.db.execute(pgCmds.UPDATE_GUILD_BANS, data)


    @commands.Cog.listener()        
    async def on_member_unban(self, guild, user):
        #(User banned, staff_id, Reason, timestamp)
        data = self.get_ban_unban_data(discord.AuditLogAction.unban, user, guild)

        await self.db.execute(pgCmds.UPDATE_GUILD_UNBANS, data[:4])

    #-------------------- FUNCTIONS --------------------

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

def setup(bot):
    bot.add_cog(GuildDB(bot))