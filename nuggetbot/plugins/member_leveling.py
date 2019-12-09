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

import os
import json
import dblogin 
import discord
import asyncio
import asyncpg
import datetime
from io import BytesIO
from typing import Union
from functools import partial
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont, ImageFilter

from nuggetbot.config import Config
from nuggetbot.util import gen_embed as GenEmbed
from nuggetbot.database import DatabaseCmds as pgCmds
from nuggetbot.util.chat_formatting import RANDOM_DISCORD_COLOR, GUILD_URL_AS, AVATAR_URL_AS

import dblogin 
from .util.misc import GET_AVATAR_BYTES
from .util import cogset, checks
from .util.images import GenGiftedGemsImage, GenLevelUPImage, GenProfileImage


class MemberLeveling(commands.Cog):
    """Member Leveling System."""
    lvMSGS= ((0, 10), (10, 75), (75, 200), (200, 350), (350, 500), (500, 575), (575, 661), (661, 760), (760, 874), (874, 1005), (1005, 1156), (1156, 1318), (1318, 1503), (1503, 1713), (1713, 1953), (1953, 2226), (2226, 2538), (2538, 2893), (2893, 3298), (3298, 3760), (3760, 4286), (4286, 4843), (4843, 5473), (5473, 6184), (6184, 6988), (6988, 7896), (7896, 8922), (8922, 10082), (10082, 11393), (11393, 12874), (12874, 14548), (14548, 16294), (16294, 18249), (18249, 20439), (20439, 22892), (22892, 25639), (25639, 28716), (28716, 32162), (32162, 36021), (36021, 40344), (40344, 45185), (45185, 50155), (50155, 55672), (55672, 61796), (61796, 68594), (68594, 76139), (76139, 84514), (84514, 93811), (93811, 104130), (104130, 115584), (115584, 128298), (128298, 141769), (141769, 156655), (156655, 173104), (173104, 191280), (191280, 211364), (211364, 233557), (233557, 258080), (258080, 285178), (285178, 315122), (315122, 348210), (348210, 383031), (383031, 421334), (421334, 463467), (463467, 509814), (509814, 560795), (560795, 616874), (616874, 678561), (678561, 746417), (746417, 821059), (821059, 903165), (903165, 988966), (988966, 1082918), (1082918, 1185795), (1185795, 1298446), (1298446, 1421798), (1421798, 1556869), (1556869, 1704772), (1704772, 1866725), (1866725, 2044064), (2044064, 2238250), (2238250, 2439692), (2439692, 2659264), (2659264, 2898598), (2898598, 3159472), (3159472, 3443824), (3443824, 3753768), (3753768, 4091607), (4091607, 4459852), (4459852, 4861239), (4861239, 5298751), (5298751, 5749145), (5749145, 6237822), (6237822, 6768037), (6768037, 7343320), (7343320, 7967502), (7967502, 8644740), (8644740, 9379543), (9379543, 10176804), (10176804, 11041832))
    
    config = None 
    delete_after = 15
    
    def __init__(self, bot):
        self.bot = bot
        self.cogset = dict()
        self.db = None

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

    async def cog_command_error(self, ctx, error):
        if isinstance(error, discord.ext.commands.errors.CheckFailure):
            pass
        
        elif isinstance(error, discord.ext.commands.errors.BadArgument):
            await ctx.send_help(ctx.invoked_with, delete_after=30)

            if self.config.config.delete_invoking:
                await ctx.message.delete()

        else:
            print(type(error))
            print(error)

        return 
        
        #    #'discord.ext.commands.errors.CommandInvokeError'

    async def cog_after_invoke(self, ctx):
        """
        Delete invoker message
        """

        if self.bot.config.delete_invoking:
            await ctx.message.delete()

        return


  # -------------------- LISTENERS --------------------
    @commands.Cog.listener()
    async def on_ready(self):
        self.cogset = await cogset.LOAD(cogname=self.qualified_name)
        if not self.cogset:
            self.cogset= dict(
                enablelogging=False
            )

            await cogset.SAVE(self.cogset, cogname=self.qualified_name)

        all_cmds = list()

        for command in self.bot.commands:
            all_cmds = all_cmds + command.aliases + [command.name]

        self.all_cmds = all_cmds
        self.all_prefixs = [self.bot.command_prefix, '>', '<', '?', '.']

        await self.connect_db()

    @commands.Cog.listener()
    async def on_message(self, msg):
        """
        This is the on_message handler for member leveling. 
        """

        # ===== IF THE USER IS JUST USING A BOT COMMAND (OR AT LEAST FAILING AT USING A BOT COMMAND) IGNORE IT AND DO NOT CREDIT THE MEMBER WITH A NEW MESSAGE.
        if msg.content[:1] in self.all_prefixs or (msg.content[1:].split(" "))[0] in self.all_cmds:
            return
        
        # ===== IF MESSAGE IS NOT A NORMAL TEXT MSG, IF AUTHOR IS A BOT OR MESSAGE WAS IN DMS. IGNORE IT.
        if msg.type != discord.MessageType.default or msg.author.bot or not msg.guild:
            return

        # ===== IGNORE GATED MESSAGES
        if msg.channel.id == self.bot.config.channels['entrance_gate']:
            return 

        # ===== WRITE THE DATA TO THE DATABASE
        r = await self.db.fetchrow(pgCmds.LOG_MSG, msg.id, msg.channel.id, msg.guild.id, msg.author.id, msg.created_at)

        # ===== IF MEMBER HAS LEVELED UP
        if r["has_leveled_up"]:
            
            incgems = 0

            # === IF MEMBER IS LEVELING UP BY MORE THAN ONE LEVEL. 
            for i in range(r['old_level'], r['new_level'], 1):
                i = i + 1

                # = GET THE REWARD FOR INCREASE IN LEVEL.
                g = await self.db.fetchrow(pgCmds.GET_LEVEL_UP_REWARD, msg.author.id, i)

                incgems = incgems + g['reward']

            # === SEND THIS TYPING MESSAGE JUST FOR FUN
            async with msg.channel.typing():
                # = UPDATE THE TOTAL GEMS AND LEVEL OF THE MEMBER IN THE DATABASE WHILE ALSO GETTING THEIR RANK AND TOTAL GEMS
                total_gems, rank = await self.db.fetchrow(pgCmds.LEVELUP_MEMBER, r['new_level'], incgems, msg.author.id)

                # = GET USER AVATAR AS BYTES
                avatar_bytes = await GET_AVATAR_BYTES(user=msg.author, size=128)

                # = GENERATE THE MEMBER LEVELED UP IMAGE
                fn = partial(GenLevelUPImage, avatar_bytes, msg.author, r['new_level'], rank, total_gems, incgems)
                final_buffer = await self.bot.loop.run_in_executor(None, fn)


                file = discord.File(filename="levelup.png", fp=final_buffer)
                await msg.channel.send(file=file)

        return


  # -------------------- COMMANDS --------------------  
    @checks.GUILD_OWNER()
    @commands.command(pass_context=False, hidden=False, name='giftGems', aliases=['giftgems'])
    async def cmd_giftGems(self, ctx, member: discord.Member, gems: int):
        """
        [Guild Owner] Gifts a selected member a specified amount of gems.

        Useage:
            [p]giftGems <member mention/memberID> <amount of gems to gift>
        """

        async with ctx.typing():

            # === WRITE CHANGES TO THE DATABASE
            await self.db.execute(pgCmds.ADDREM_MEMBER_GEMS, gems, member.id)

            # === GET THE USERS PFP AS BYTES
            avatar_bytes = await GET_AVATAR_BYTES(user = member, size = 128)

            # === SAFELY RUN SOME SYNCRONOUS CODE TO GENERATE THE IMAGE
            final_buffer = await self.bot.loop.run_in_executor(None, partial(GenGiftedGemsImage, avatar_bytes, member, gems))
            
            # === SEND THE RETURN IMAGE
            await ctx.send(file=discord.File(filename="profile.png", fp=final_buffer))

        return

    @checks.GUILD_OWNER()
    @commands.command(pass_context=False, hidden=False, name='getProfile', aliases=['getprofile'])
    async def cmd_getProfile(self, ctx, *, member: discord.Member = None):
        """
        [guild owner] This returns the profile of other members.
        Useage:
            [p]getProfile memberMention/memberID
        """

        # ===== CALL THE USER AN IDIOT IF THEY DON'T USE THE COMMAND CORRECTLY 
        if not member:
            await ctx.send_help('getProfile')
            return 

        # ===== THIS WILL MAKE THE BOT APPEAR AS TYPING WHILE PROCESSING AND UPLOADING THE GENERATED IMAGE
        async with ctx.typing():

            # === GET THE USERS PFP AS BYTES
            avatar_bytes = await GET_AVATAR_BYTES(user = member, size = 128)

            # === GET MEMBERS PROFILE INFO FROM THE DATABASE
            level, nummsgs, gems, rank  = await self.db.fetchrow(pgCmds.GET_MEMBER_PROFILE, member.id)

            # === SAFELY RUN SOME SYNCRONOUS CODE TO GENERATE THE IMAGE
            final_buffer = await self.bot.loop.run_in_executor(None, partial(GenProfileImage, avatar_bytes, member, level, rank, gems, nummsgs))

            # === SEND THE RETURN IMAGE
            await ctx.send(file=discord.File(filename="profile.png", fp=final_buffer))

    @checks.CORE()
    @checks.RECEPTION()
    @commands.command(pass_context=False, hidden=False, name='profile', aliases=[])
    async def cmd_profile(self, ctx):
        """Display the user's avatar on their colour."""

        # ===== THIS WILL MAKE THE BOT APPEAR AS TYPING WHILE PROCESSING AND UPLOADING THE GENERATED IMAGE
        async with ctx.typing():

            # === GET THE USERS PFP AS BYTES
            avatar_bytes = await GET_AVATAR_BYTES(user = ctx.author, size = 128)

            # === GET MEMBERS PROFILE INFO FROM THE DATABASE
            level, nummsgs, gems, rank  = await self.db.fetchrow(pgCmds.GET_MEMBER_PROFILE, ctx.author.id)

            # === SAFELY RUN SOME SYNCRONOUS CODE TO GENERATE THE IMAGE
            final_buffer = await self.bot.loop.run_in_executor(None, partial(GenProfileImage, avatar_bytes, ctx.author, level, rank, gems, nummsgs))

            # === SEND THE RETURN IMAGE
            await ctx.send(file=discord.File(filename="profile.png", fp=final_buffer))

    @checks.CORE()
    @checks.RECEPTION()
    @commands.command(pass_context=False, hidden=False, name='leaderboard', aliases=[])
    async def cmd_leaderboard(self, ctx):

        printout = ""

        for i, result in enumerate(await self.db.fetch(pgCmds.GET_MEMBER_LEADERBOARD)):
            printout += f"{(i+1)}:\t<@{result['user_id']}>\tLvl: {result['level']}\n"

        embed = discord.Embed(  description=printout,
                                colour=     RANDOM_DISCORD_COLOR(),
                                type=       'rich',
                                timestamp = datetime.datetime.utcnow()
                            )

        embed.set_author(       name=       "FurSail Leaderboard",
                                icon_url=   ctx.guild.icon_url
                        )
        embed.set_footer(       text=       ctx.guild.name,
                                icon_url=   ctx.guild.icon_url
                        )

        await ctx.send(embed=embed)
        return

def setup(bot):
    bot.add_cog(MemberLeveling(bot))