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

import re
import sys
import random
import pathlib
import discord
import asyncio
import datetime
from typing import Union
from discord.ext import tasks, commands

from nuggetbot.util import gen_embed as GenEmbed
from nuggetbot.utils import get_next
from nuggetbot.database import DatabaseCmds as pgCmds
from nuggetbot.util.chat_formatting import RANDOM_DISCORD_COLOR, GUILD_URL_AS, AVATAR_URL_AS

from .util import checks, cogset, images
from .util.misc import GET_AVATAR_BYTES


class Moderation(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.cogset = dict()

  # -------------------- LOCAL COG STUFF --------------------
    @asyncio.coroutine
    async def cog_command_error(self, ctx, error):
        print('Ignoring exception in {}'.format(ctx.invoked_with), file=sys.stderr)
        print(error)
        return

    def cog_unload(self):
        pass


  # -------------------- LISTENERS --------------------
    @commands.Cog.listener()
    async def on_ready(self): 
        # ---------- LOAD COGSET ----------
        self.cogset = await cogset.LOAD(cogname=self.qualified_name)
        if not self.cogset:
            self.cogset= dict(
                Blank=None
            )

            await cogset.SAVE(self.cogset, cogname=self.qualified_name)

      # ---------- WAIT FOR BOT TO RUN ON_READY ----------
        await asyncio.sleep(5)

    @commands.Cog.listener()
    async def on_message(self, msg):
        # ---------- Wait for bot setup ----------
        await self.bot.wait_until_ready()

       # ---------- Ignores ----------
        if not msg.guild:
            # === From DM's
            return 

        if msg.author.bot:
            # === If sender is a bot
            return 

        if msg.author.guild_permissions.administrator:
            # === Don't moderate admins
            return

        if any(role.id in self.bot.config.roles["any_staff"] for role in msg.author.roles):
            # === Don't moderate staff
            return

       # ---------- THINGS TO MODERATE ----------
        #https://watchanimeattheoffice.com/invite/invite-code
        #https://discordapp.com/invite/invite-code
        #https://discord.gg/gzyMG8

        if any(i in msg.content for i in ['watchanimeattheoffice.com/', 'discordapp.com/invite/', 'discord.gg/']):
            await self.handle_discord_invite(msg)

        #links = re.findall(r"(?P<url>http[s]?://[^\s]+)", msg.content)

  # -------------------- FUNCTIONS --------------------
    @asyncio.coroutine
    async def handle_discord_invite(self, msg):
        cleanmsg = None
        cleanmsgparts = list()
        invite = str()

        for i in msg.content.split():
            if any(j in i for j in ['watchanimeattheoffice.com/', 'discordapp.com/invite/', 'discord.gg/']):
                invite = i 
                cleanmsgparts.append("**[CENSORED]**") 

            else:
               cleanmsgparts.append(i) 
        
        if len(cleanmsgparts) > 0:
            cleanmsg = " ".join(cleanmsgparts)
            cleanmsg = cleanmsg.replace("@everyone", "@\u200beveryone")
            cleanmsg = cleanmsg.replace("@here", "@\u200bhere")

        embed = discord.Embed(  
            title=      ':octagonal_sign: I\'m not allowed to share discord invites here :octagonal_sign:',
            description="",
            type=       'False',
            timestamp=  datetime.datetime.utcnow(),
            color=      RANDOM_DISCORD_COLOR()
            )

        embed.set_footer(       
            icon_url=   GUILD_URL_AS(msg.guild),
            text=       msg.guild.name
            )

        await self.bot.execute_webhook2(    channel=msg.channel, content=cleanmsg, username=msg.author.display_name, 
                                            avatar_url=AVATAR_URL_AS(msg.author, format='png'), embed=embed)

        await msg.delete()

        return



def setup(bot):
    bot.add_cog(Moderation(bot))
