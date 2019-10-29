import os
import json
import dblogin 
import discord
import asyncio
import asyncpg
import datetime
from io import BytesIO
from discord.ext import commands

from nuggetbot.config import Config
from nuggetbot.util import gen_embed as GenEmbed
from nuggetbot.database import DatabaseCmds as pgCmds
from nuggetbot.util.chat_formatting import RANDOM_DISCORD_COLOR, GUILD_URL_AS, AVATAR_URL_AS

from .cog_utils import SAVE_COG_CONFIG, LOAD_COG_CONFIG

class MemberLeveling(commands.Cog):
    """Member Leveling System."""

    config = None 
    delete_after = 15
    
    def __init__(self, bot):
        self.bot = bot
        MemberLeveling.config = Config()
        self.cogset = dict()
        self.db = None

  #-------------------- LISTENERS --------------------
    @commands.Cog.listener()
    async def on_ready(self):
        self.cogset = await LOAD_COG_CONFIG(cogname="memleveling")
        if not self.cogset:
            self.cogset= dict(
                enablelogging=False
            )

            await SAVE_COG_CONFIG(self.cogset, cogname="memleveling")

        all_cmds = list()

        for command in self.bot.commands:
            all_cmds = all_cmds + command.aliases + [command.name]

        self.all_cmds = all_cmds
        self.all_prefixs = [self.bot.command_prefix, '>', '<', '?', '.']

    @commands.Cog.listener()
    async def on_message(self, msg):
        """
        This is the on_message handler for member leveling. 
        """

        ###===== IF THE USER IS JUST USING A BOT COMMAND (OR AT LEAST FAILING AT USING A BOT COMMAND) IGNORE IT AND DO NOT CREDIT THE MEMBER WITH A NEW MESSAGE.
        if msg.content[:1] in self.all_prefixs or (msg.content[1:].split(" "))[0] in self.all_cmds:
            return
        
        ###===== IF MESSAGE IS NOT A NORMAL TEXT MSG, IF AUTHOR IS A BOT OR MESSAGE WAS IN DMS. IGNORE IT.
        if msg.type != discord.MessageType.default or msg.author.bot or not msg.guild:
            return

        await self.db.execute(pgCmds.ADD_MSG, msg.id, msg.channel.id, msg.guild.id, msg.author.id, msg.created_at)

        ###=== MEMBER LEVELING
        r = await self.db.fetchrow(pgCmds.HAS_MEMBER_LEVELED_UP, message.author.id)

        if r["has_leveled_up"]: 
            #gets: reward total 
            g = await self.db.fetchrow(pgCmds.GET_LEVEL_UP_REWARD, message.author.id, r["new_level"])
            await self.db.execute(pgCmds.MEMBER_LEVELED_UP, r["new_level"], g['total'], message.author.id)

            #= tell user they leveled up
            embed = await GenEmbed.getMemberLeveledUP(message, level=r["new_level"], reward=g['reward'], total=g['total'])
            await self.safe_send_message(dest=message.channel, embed=embed)



def setup(bot):
    bot.add_cog(MemberLeveling(bot))