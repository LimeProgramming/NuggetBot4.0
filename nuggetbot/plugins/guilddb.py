from discord.ext import commands
import discord
import asyncio
import asyncpg
import datetime
import random
import logging

from nuggetbot.config import Config
from nuggetbot.database import DatabaseLogin
from nuggetbot.database import DatabaseCmds as pgCmds
from .ctx_decorators import in_channel, is_core, in_channel_name, in_reception, has_role, is_high_staff, is_any_staff

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
        pass

    @commands.Cog.listener()        
    async def on_guild_role_create(self, role):
        pass

    @commands.Cog.listener()        
    async def on_guild_role_delete(self, role):
        pass

    @commands.Cog.listener()        
    async def on_guild_role_update(self, before, after):
        pass

    @commands.Cog.listener()        
    async def on_guild_emojis_update(self, guild, before, after):
        pass

    @commands.Cog.listener()        
    async def on_member_ban(self, guild, user):
        pass

    @commands.Cog.listener()        
    async def on_member_unban(self, guild, user):
        pass



def setup(bot):
    bot.add_cog(GuildDB(bot))