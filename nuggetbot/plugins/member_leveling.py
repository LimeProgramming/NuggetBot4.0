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



def setup(bot):
    bot.add_cog(MemberLeveling(bot))