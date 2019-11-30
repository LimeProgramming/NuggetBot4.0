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
from .util import cogset

from .util import checks


class MemberLeveling(commands.Cog):
    """Member Leveling System."""
    lvMSGS= ((0, 10), (10, 75), (75, 200), (200, 350), (350, 500), (500, 575), (575, 661), (661, 760), (760, 874), (874, 1005), (1005, 1156), (1156, 1318), (1318, 1503), (1503, 1713), (1713, 1953), (1953, 2226), (2226, 2538), (2538, 2893), (2893, 3298), (3298, 3760), (3760, 4286), (4286, 4843), (4843, 5473), (5473, 6184), (6184, 6988), (6988, 7896), (7896, 8922), (8922, 10082), (10082, 11393), (11393, 12874), (12874, 14548), (14548, 16294), (16294, 18249), (18249, 20439), (20439, 22892), (22892, 25639), (25639, 28716), (28716, 32162), (32162, 36021), (36021, 40344), (40344, 45185), (45185, 50155), (50155, 55672), (55672, 61796), (61796, 68594), (68594, 76139), (76139, 84514), (84514, 93811), (93811, 104130), (104130, 115584), (115584, 128298), (128298, 141769), (141769, 156655), (156655, 173104), (173104, 191280), (191280, 211364), (211364, 233557), (233557, 258080), (258080, 285178), (285178, 315122), (315122, 348210), (348210, 383031), (383031, 421334), (421334, 463467), (463467, 509814), (509814, 560795), (560795, 616874), (616874, 678561), (678561, 746417), (746417, 821059), (821059, 903165), (903165, 988966), (988966, 1082918), (1082918, 1185795), (1185795, 1298446), (1298446, 1421798), (1421798, 1556869), (1556869, 1704772), (1704772, 1866725), (1866725, 2044064), (2044064, 2238250), (2238250, 2439692), (2439692, 2659264), (2659264, 2898598), (2898598, 3159472), (3159472, 3443824), (3443824, 3753768), (3753768, 4091607), (4091607, 4459852), (4459852, 4861239), (4861239, 5298751), (5298751, 5749145), (5749145, 6237822), (6237822, 6768037), (6768037, 7343320), (7343320, 7967502), (7967502, 8644740), (8644740, 9379543), (9379543, 10176804), (10176804, 11041832))
    
    config = None 
    delete_after = 15
    
    def __init__(self, bot):
        self.bot = bot
        MemberLeveling.config = Config()
        self.cogset = dict()
        self.db = None

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

    async def cog_command_error(self, ctx, error):
        if isinstance(error, discord.ext.commands.errors.CheckFailure):
            pass
        
        elif isinstance(error, discord.ext.commands.errors.BadArgument):
            await ctx.send_help(ctx.invoked_with, delete_after=30)

            if MemberLeveling.config.delete_invoking:
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

        if MemberLeveling.config.delete_invoking:
            await ctx.message.delete()

        return


  #-------------------- LISTENERS --------------------
    @commands.Cog.listener()
    async def on_ready(self):
        self.cogset = await cogset.LOAD(cogname="memleveling")
        if not self.cogset:
            self.cogset= dict(
                enablelogging=False
            )

            await cogset.SAVE(self.cogset, cogname="memleveling")

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

        ###===== IF THE USER IS JUST USING A BOT COMMAND (OR AT LEAST FAILING AT USING A BOT COMMAND) IGNORE IT AND DO NOT CREDIT THE MEMBER WITH A NEW MESSAGE.
        if msg.content[:1] in self.all_prefixs or (msg.content[1:].split(" "))[0] in self.all_cmds:
            return
        
        ###===== IF MESSAGE IS NOT A NORMAL TEXT MSG, IF AUTHOR IS A BOT OR MESSAGE WAS IN DMS. IGNORE IT.
        if msg.type != discord.MessageType.default or msg.author.bot or not msg.guild:
            return

        ###===== WRITE THE DATA TO THE DATABASE
        r = await self.db.fetchrow(pgCmds.LOG_MSG, msg.id, msg.channel.id, msg.guild.id, msg.author.id, msg.created_at)

        ###===== IF MEMBER HAS LEVELED UP
        if r["has_leveled_up"]:
            
            incgems = 0

            ###=== IF MEMBER IS LEVELING UP BY MORE THAN ONE LEVEL. 
            for i in range(r['old_level'], r['new_level'], 1):
                i = i + 1

                ###= GET THE REWARD FOR INCREASE IN LEVEL.
                g = await self.db.fetchrow(pgCmds.GET_LEVEL_UP_REWARD, msg.author.id, i)

                incgems = incgems + g['reward']

            ###=== SEND THIS TYPING MESSAGE JUST FOR FUN
            async with msg.channel.typing():
                ###= UPDATE THE TOTAL GEMS AND LEVEL OF THE MEMBER IN THE DATABASE WHILE ALSO GETTING THEIR RANK AND TOTAL GEMS
                total_gems, rank = await self.db.fetchrow(pgCmds.LEVELUP_MEMBER, r['new_level'], incgems, msg.author.id)

                ###= GET USER AVATAR AS BYTES
                avatar_bytes = await GET_AVATAR_BYTES(user=msg.author, size=128)

                ###= GENERATE THE MEMBER LEVELED UP IMAGE
                fn = partial(self.GenLevelUPImage, avatar_bytes, msg.author, r['new_level'], rank, total_gems, incgems)
                final_buffer = await self.bot.loop.run_in_executor(None, fn)


                file = discord.File(filename="levelup.png", fp=final_buffer)
                await msg.channel.send(file=file)

        return


  #-------------------- COMMANDS --------------------  
    @checks.GUILD_OWNER()
    @commands.command(pass_context=False, hidden=False, name='giftGems', aliases=['giftgems'])
    async def cmd_giftGems(self, ctx, member: discord.Member, gems: int):
        """
        [Guild Owner] Gifts a selected member a specified amount of gems.

        Useage:
            [p]giftGems <member mention/memberID> <amount of gems to gift>
        """

        async with ctx.typing():

            ###=== WRITE CHANGES TO THE DATABASE
            await self.db.execute(pgCmds.ADDREM_MEMBER_GEMS, gems, member.id)

            ###=== GET THE USERS PFP AS BYTES
            avatar_bytes = await GET_AVATAR_BYTES(user = member, size = 128)

            ###=== SAFELY RUN SOME SYNCRONOUS CODE TO GENERATE THE IMAGE
            final_buffer = await self.bot.loop.run_in_executor(None, partial(self.GenGiftedGemsImage, avatar_bytes, member, gems))
            
            ###=== SEND THE RETURN IMAGE
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

        ###===== CALL THE USER AN IDIOT IF THEY DON'T USE THE COMMAND CORRECTLY 
        if not member:
            await ctx.send_help('getProfile')
            return 

        ###===== THIS WILL MAKE THE BOT APPEAR AS TYPING WHILE PROCESSING AND UPLOADING THE GENERATED IMAGE
        async with ctx.typing():

            ###=== GET THE USERS PFP AS BYTES
            avatar_bytes = await GET_AVATAR_BYTES(user = member, size = 128)

            ###=== GET MEMBERS PROFILE INFO FROM THE DATABASE
            level, nummsgs, gems, rank  = await self.db.fetchrow(pgCmds.GET_MEMBER_PROFILE, member.id)

            ###=== SAFELY RUN SOME SYNCRONOUS CODE TO GENERATE THE IMAGE
            final_buffer = await self.bot.loop.run_in_executor(None, partial(self.GenProfileImage, avatar_bytes, member, level, rank, gems, nummsgs))

            ###=== SEND THE RETURN IMAGE
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
            final_buffer = await self.bot.loop.run_in_executor(None, partial(self.GenProfileImage, avatar_bytes, ctx.author, level, rank, gems, nummsgs))

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

        await ctx.send(emebed=embed)
        return


  #-------------------- IMAGE GENERATORS --------------------
    @staticmethod
    def GenLevelUPImage(avatar_bytes: bytes, member: Union[discord.User, discord.Member], level: int, rank: int, gems: int, reward:int) -> BytesIO:
        #===== VARS
        out_image = BytesIO()
        imagedir = os.path.join(os.path.split(os.path.realpath(__file__))[0], "images")

        ###===== BLUR THE EDGES OF A MEMBERS PFP AND ADD THEIR STATUS
        img = MemberLeveling.__square_blur_icon(avatar_bytes, member.status.__str__(), imagedir)

        ###===== OPEN THE MAIN BACKGROUND IMAGE FOR THE LEVELUP IMAGE
        with Image.open(os.path.join(imagedir, "levelupbg2.png")) as background:

            ###=====    ADD THE PROFILE IMAGE
            background.paste(img, (10, 10), mask=img)

            ###=====    ADD THE GEM IMAGES
            gem1 = Image.open(os.path.join(imagedir, "gem1.png")).convert('RGBA')
            gem2 = Image.open(os.path.join(imagedir, "gem2.png")).convert('RGBA')
            gem3 = Image.open(os.path.join(imagedir, "gem3.png")).convert('RGBA')

            background.paste(gem2, (550, 109), mask=gem2)
            background.paste(gem1, (577, 109), mask=gem1)
            background.paste(gem3, (608, 109), mask=gem3)


            background.paste(gem1, (187, 64), mask=gem1)

            ###=====    ADD THE TEXT
            #-------    FONTS
            lfont = ImageFont.truetype(os.path.join(imagedir, "OpenSans-Semibold.ttf"), 42)
            zfont = ImageFont.truetype(os.path.join(imagedir, "OpenSans-Regular.ttf"), 38)
            sfont = ImageFont.truetype(os.path.join(imagedir, "OpenSans-Light.ttf"), 32)

            draw = ImageDraw.Draw(background)

            #= username
            draw.text((160, 105), MemberLeveling.__gen_member_name(member), fill=(230, 230, 230, 255), font=sfont)
            #= Level up
            draw.text((259, 0), "Level Up", fill=(230, 230, 230, 255), font=lfont)
            #= Reward
            draw.text((222, 50), f"Reward: {reward}", fill=(230, 230, 230, 255), font=zfont)
            #= Level
            draw.text((550, 0), "LV:", fill=(230, 230, 230, 255), font=zfont)
            draw.text((650, 0), f"{level}", fill=(230, 230, 230, 255), font=lfont)
            #= Rank
            draw.text((550, 46), f"Rank:", fill=(230, 230, 230, 255), font=zfont)
            draw.text((650, 46), f"{rank}", fill=(230, 230, 230, 255), font=lfont)
            #= Gems
            draw.text((650, 92), f"{gems}", fill=(230, 230, 230, 255), font=lfont)

            background.save(out_image, "png")

        out_image.seek(0)

        return out_image

    @staticmethod
    def GenProfileImage(avatar_bytes: bytes, member: Union[discord.User, discord.Member], level: int, rank: int, gems: int, nummsgs:int) -> BytesIO:
        #===== VARS
        out_image = BytesIO()
        imagedir = os.path.join(os.path.split(os.path.realpath(__file__))[0], "images")

        ###===== BLUR THE EDGES OF A MEMBERS PFP AND ADD THEIR STATUS
        img = MemberLeveling.__square_blur_icon(avatar_bytes, member.status.__str__(), imagedir)
        
        with Image.open(os.path.join(imagedir, "profilebg.png")) as background:
            ###=====    ADD THE PROFILE IMAGE
            background.paste(img, (10, 10), mask=img)

            ###=====    ADD THE GEM IMAGES
            gem1 = Image.open(os.path.join(imagedir, "gem1.png")).convert('RGBA')
            gem2 = Image.open(os.path.join(imagedir, "gem2.png")).convert('RGBA')
            gem3 = Image.open(os.path.join(imagedir, "gem3.png")).convert('RGBA')

            background.paste(gem2, (550, 109), mask=gem2)
            background.paste(gem1, (577, 109), mask=gem1)
            background.paste(gem3, (608, 109), mask=gem3)

            ###=====    ADD THE PROGRESS BAR
            background.paste(Image.new("RGBA", (776, 30), (0, 85, 183, 255)), (12, 152), mask=None)

            if level < 100:
                a, b = MemberLeveling.lvMSGS[level]
                x = int(((nummsgs - a) / (b - a)) * 776)

                if x < 1:
                    x = 1
                elif x > 776:
                    x = 775
            else:
                x = 776

            background.paste(Image.new("RGBA", (x, 30), (0, 175, 96, 255)), (12, 152), mask=None)

            ###=====    ADD THE TEXT
            #-------    FONTS
            lfont = ImageFont.truetype(os.path.join(imagedir, "OpenSans-Semibold.ttf"), 42)
            zfont = ImageFont.truetype(os.path.join(imagedir, "OpenSans-Regular.ttf"), 38)
            sfont = ImageFont.truetype(os.path.join(imagedir, "OpenSans-Light.ttf"), 32)

            draw = ImageDraw.Draw(background)

            #= username
            draw.text((160, 105), MemberLeveling.__gen_member_name(member), fill=(230, 230, 230, 255), font=sfont)
            #= Level
            draw.text((550, 0), "LV:", fill=(230, 230, 230, 255), font=zfont)
            draw.text((650, 0), f"{level}", fill=(230, 230, 230, 255), font=lfont)
            #= Rank
            draw.text((550, 46), f"Rank:", fill=(230, 230, 230, 255), font=zfont)
            draw.text((650, 46), f"{rank}", fill=(230, 230, 230, 255), font=lfont)
            #= Gems
            draw.text((650, 92), f"{gems}", fill=(230, 230, 230, 255), font=lfont)

            background.save(out_image, "png")

        out_image.seek(0)

        return out_image

    @staticmethod
    def GenGiftedGemsImage(avatar_bytes: bytes, member: Union[discord.User, discord.Member], ggems: int) -> BytesIO:
        #===== VARS
        out_image = BytesIO()
        imagedir = os.path.join(os.path.split(os.path.realpath(__file__))[0], "images")

        ###===== BLUR THE EDGES OF A MEMBERS PFP AND ADD THEIR STATUS
        img = MemberLeveling.__square_blur_icon(avatar_bytes, member.status.__str__(), imagedir)

        ###===== OPEN THE MAIN BACKGROUND IMAGE FOR THE LEVELUP IMAGE
        with Image.open(os.path.join(imagedir, "levelupbg2.png")) as background:

            ###=====    ADD THE PROFILE IMAGE
            background.paste(img, (10, 10), mask=img)

            ###=====    ADD THE GEM IMAGES
            gem1 = Image.open(os.path.join(imagedir, "gem1.png")).convert('RGBA')
            gem2 = Image.open(os.path.join(imagedir, "gem2.png")).convert('RGBA')
            gem3 = Image.open(os.path.join(imagedir, "gem3.png")).convert('RGBA')

            background.paste(gem2, (167, 64), mask=gem2)
            background.paste(gem1, (194, 64), mask=gem1)
            background.paste(gem3, (225, 64), mask=gem3)

            ###=====    ADD THE TEXT
            #-------    FONTS
            lfont = ImageFont.truetype(os.path.join(imagedir, "OpenSans-Semibold.ttf"), 42)
            zfont = ImageFont.truetype(os.path.join(imagedir, "OpenSans-Regular.ttf"), 38)
            sfont = ImageFont.truetype(os.path.join(imagedir, "OpenSans-Light.ttf"), 32)

            draw = ImageDraw.Draw(background)

            #= username
            draw.text((160, 105), MemberLeveling.__gen_member_name(member, 40), fill=(230, 230, 230, 255), font=sfont)
            #= Level up
            draw.text((259, 0), "Received", fill=(230, 230, 230, 255), font=lfont)
            #= Reward
            draw.text((260, 50), f"Gems: {ggems}", fill=(230, 230, 230, 255), font=zfont)

            background.save(out_image, "png")

        out_image.seek(0)

        return out_image

    @staticmethod
    def __square_blur_icon(avatar_bytes, mstat, imgdir, RADIUS=2):
        """
        This just blurs the edges of a members pfp
        """

        diam = 2*RADIUS

        ###===== OPEN THE MEMBERS STATUS IMAGE
        status = Image.open(os.path.join(imgdir, f"{mstat if mstat in ['offline', 'online', 'dnd', 'idle'] else 'online'}.png")).convert('RGBA')

        ###===== WITH OPEN THE MEMBERS PFP
        with Image.open(BytesIO(avatar_bytes)).convert('RGBA') as rgba_avatar:
            canvas = Image.new('RGBA', (rgba_avatar.size[0]+diam, rgba_avatar.size[1]+diam), (35,39,42,0))
            canvas.paste(rgba_avatar, (RADIUS, RADIUS))

        ###===== GENERATE OUR BLUR MASK
        with Image.new('L', canvas.size, 0) as mask:
            draw = ImageDraw.Draw(mask)
            x0, y0 = 0, 0
            x1, y1 = canvas.size
            for d in range(diam+RADIUS):
                x1, y1 = x1-1, y1-1
                alpha = 255 if d<RADIUS else int(255*(diam+RADIUS-d)/diam)
                draw.rectangle([x0, y0, x1, y1], outline=alpha)
                x0, y0 = x0+1, y0+1

            blur = canvas.filter(ImageFilter.GaussianBlur(RADIUS/2))
            canvas.paste(blur, mask=mask)
            
        ###===== RETURN OUR COMPOSITED IMAGE
        # order of layers: new image, blured member pfp, member status image
        return Image.alpha_composite(Image.new('RGBA', canvas.size, (35,39,42,255)), Image.alpha_composite(canvas, status))

    @staticmethod
    def __gen_member_name(member, maxlen=22):

        ###===== IF THE MEMBER HAS A NICKNAME, USE THAT AND IGNORE THE DISCRIMINATOR
        if member.nick:
            if len(member.nick) <= maxlen: 
               name = member.nick 
            else:
                name = member.nick[:maxlen]
        
        ###===== IF MEMBER ONLY HAS THEIR USERNAME, USE THAT AND INCLUDE DISCRIMINATOR      
        else:
            if len(f"{member.name}#{member.discriminator}") <= maxlen:
                name = f"{member.name}#{member.discriminator}"

            elif len(member.name) <= maxlen:
                name = member.name

            else:
                name = f"{member.name[:maxlen]}..."
            
        return name 

def setup(bot):
    bot.add_cog(MemberLeveling(bot))