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
from .cog_utils import SAVE_COG_CONFIG, LOAD_COG_CONFIG

class MemberLeveling(commands.Cog):
    """Member Leveling System."""

    config = None 
    delete_after = 15
    
    def __init__(self, bot):
        self.bot = bot
        #MemberLeveling.config = Config()
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
                avatar_bytes = await msg.author.avatar_url_as(format='png', static_format='webp', size=128).read()

                ###= GENERATE THE MEMBER LEVELED UP IMAGE
                fn = partial(self.GenLevelUPImage, avatar_bytes, msg.author, r['new_level'], rank, total_gems, incgems)
                final_buffer = await self.bot.loop.run_in_executor(None, fn)


                file = discord.File(filename="levelup.png", fp=final_buffer)
                await msg.channel.send(file=file)

        return

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

  #-------------------- STATIC METHOD --------------------
    @staticmethod
    def GenLevelUPImage(avatar_bytes: bytes, member: Union[discord.User, discord.Member], level: int, rank: int, gems: int, reward:int) -> BytesIO:
        #===== VARS
        out_image = BytesIO()

        head = os.path.split(os.path.realpath(__file__))[0]
        imagedir = os.path.join(head, "images")

        mstat = member.status.__str__()
        if mstat not in ["offline", "online", "dnd", "idle"]:
            mstat = "online"

        ###===== OPEN STATUS IMAGE
        status = Image.open(os.path.join(imagedir, f"{mstat}.png")).convert('RGBA')

        ###===== ADD A SMALL BLUR TO THE EDGES OF THE USER AVATAR
        with Image.open(BytesIO(avatar_bytes)).convert('RGBA') as rgba_avatar:

            RADIUS = 2
            diam = 2*RADIUS
    
            background = Image.new('RGBA', (rgba_avatar.size[0]+diam, rgba_avatar.size[1]+diam), (0,0,0,0))
            background.paste(rgba_avatar, (RADIUS, RADIUS))

            ###=== CREATE PASTE MASK
            mask = Image.new('L', background.size, 0)
            draw = ImageDraw.Draw(mask)
            x0, y0 = 0, 0
            x1, y1 = background.size
            for d in range(diam+RADIUS):
                x1, y1 = x1-1, y1-1
                alpha = 255 if d<RADIUS else int(255*(diam+RADIUS-d)/diam)
                draw.rectangle([x0, y0, x1, y1], outline=alpha)
                x0, y0 = x0+1, y0+1

            blur = background.filter(ImageFilter.GaussianBlur(RADIUS/2))
            background.paste(blur, mask=mask)
            
            img = Image.alpha_composite(background, status)

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
            draw.text((160, 105), f"{member.name}#{member.discriminator}", fill=(230, 230, 230, 255), font=sfont)
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


def setup(bot):
    bot.add_cog(MemberLeveling(bot))