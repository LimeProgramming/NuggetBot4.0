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
import re
import random
import asyncpg
import discord
import asyncio

from io import BytesIO
from typing import Union
from pathlib import Path
from functools import partial
from discord.ext import commands
from PIL import (Image, ImageDraw, ImageFilter, ImageFont)

from .util.misc import GET_AVATAR_BYTES
from .util import images
from nuggetbot import exceptions
from nuggetbot.config import Config
from nuggetbot.database import DatabaseCmds as pgCmds

import dblogin 

def to_emoji(c):
    base = 0x1f1e6
    return chr(base + c)

class Test(commands.Cog):
    """Poll voting system."""

    def __init__(self, bot):
        self.bot = bot
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

    @asyncio.coroutine
    async def cog_command_error(self, ctx, error):
        print(error)

  # -------------------- LISTENERS -------------------- 
    @commands.Cog.listener()
    async def on_ready(self):
        await self.connect_db()
        #print(f"from test {os.getcwd()}")
        return
        await asyncio.sleep(4)


        # webhook test
        #channel = self.bot.get_channel(614956834771566594)
        #Webhook = discord.utils.get(await channel.webhooks(), name='NugBotErrors')


        #await self.execute_webhook(
        #    Webhook, 
        #    content=    'This is a text message <a:foxban:405724216197906455>', 
        #    username=   'NuggetBotErrors', 
        #    avatar_url= self.bot.user.avatar_url
        #    )



        #config = Config()
        #print(config.roles['user_staff'])
        #print(type(config.roles['user_staff']))
        #p#rint(self.bot.http.token)
        #print(self.bot.http.bot_token)

        #return
        #test = self.bot.get_guild(348609968292888577)
        #for e in test.emojis:
        #    if e.animated:
        #        print("{0.name}:{0.id}".format(e))

        #raise exceptions.PostAsWebhook("This issue is a test, please ignore. <a:foxban:405724216197906455>")

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        return
        if not payload.guild_id:
            return 

        if payload.message_id in [647568320991592473]:
            print(dir(payload.emoji))

            print(payload.emoji.id)
            print(payload.emoji.url)
            print(payload.emoji.is_unicode_emoji())
            print(payload.emoji.name)


#webhook testing

    async def execute_webhook(self, webhook:discord.Webhook, content:str, username:str = None, avatar_url:Union[discord.Asset, str] = None, embed:discord.Embed = None, embeds = None, tts:bool = False):
        '''
        Custom discord.Webhook executer. 
        Using this webhook executer forces the discord.py libaray to POST a webhook using the http.request function rather than the request function built into WebhookAdapter.
        The big difference between the two functions is that http.request preforms the POST with an "Authorization" header which allows for the use of emojis and other bot level privilages.
        
        Parameters
        ------------
        webhook :class:`discord.Webhook`
            The webhook you want to POST to.
        content :class:`str`
            Content of the POST message
        username Optional[:class:`str`]
            Username to post the webhook under. Overwrites the default name of the webhook.
        avatar_url Optional[:class:`discord.Asset`]
            Avatar for the webhook poster. Overwrites the default avatar of the webhook.
        embed Optional[:class:`discord.Embed`]
            discord Embed opject to post.
        embeds List[:class:`discord.Embed`]
            List of discord Embed object to post, maximum of 10 allowable.
        tts :class:`bool`
            Indicates if the message should be sent using text-to-speech.
        '''

        if embeds is not None and embed is not None:
            raise discord.errors.InvalidArgument('Cannot mix embed and embeds keyword arguments.')

        payload = {
            'tts':tts
        }

        if content is not None:
            payload['content'] = str(content).replace("@everyone", "@\u200beveryone").replace("@here", "@\u200bhere")

        if username:
            payload['username'] = username

        if avatar_url:
            payload['avatar_url'] = str(avatar_url)

        if embeds is not None:
            if len(embeds) > 10:
                raise discord.errors.InvalidArgument('embeds has a maximum of 10 elements.')
            payload['embeds'] = [e.to_dict() for e in embeds]

        if embed is not None:
            payload['embeds'] = [embed.to_dict()]

        await self.bot.http.request(route=discord.http.Route('POST', f'/webhooks/{webhook.id}/{webhook.token}'), json=payload)

        return

  # -------------------- COMMANDS -------------------- 
    @commands.Cog.listener()
    async def on_message(self, msg):
        return
        print(msg.clean_content)

    @commands.command(pass_context=True, hidden=True, name='webhook2', aliases=[])
    async def cmd_webhook2(self, ctx):
        if not ctx.message.attachments:
            return 

        print("here")
        await self.bot.execute_webhook2(ctx.channel, content="this is a test", username='Lime testing broken things', avatar_url = ctx.author.avatar_url_as(format='png', size=128).__str__(), files=ctx.message.attachments)
        print('done')

    @commands.command(pass_context=True, hidden=True, name='welcomemsgtest', aliases=[])
    async def cmd_welmsgtest(self, ctx, member:discord.Member = None):
        if member is None:
            member = ctx.author 

        async with ctx.typing():
            # === GET THE USERS PFP AS BYTES
            avatar_bytes = await GET_AVATAR_BYTES(user = member, size = 128)

            # === SAFELY RUN SOME SYNCRONOUS CODE TO GENERATE THE IMAGE
            final_buffer = await self.bot.loop.run_in_executor(None, partial(images.GenWelcomeImg, avatar_bytes, member))

            # === SEND THE RETURN IMAGE
            await ctx.send(file=discord.File(filename="welcome.png", fp=final_buffer))


    @commands.command(pass_context=True, hidden=True, name='leaderboardtest', aliases=[])
    async def cmd_leaderboardtest(self, ctx):
        
        results = dict()
        
        for i, result in enumerate(await self.db.fetch(pgCmds.GET_MEMBER_LEADERBOARD)):
            mem = ctx.guild.get_member(result['user_id'])
            
            rpfp = BytesIO()

            with Image.open(BytesIO(await GET_AVATAR_BYTES(user = mem, size = 128))).convert('RGBA') as rgba_avatar:
                out = rgba_avatar.resize((80,80), Image.LANCZOS)
                out.save(rpfp, "png")
            
            rpfp.seek(0)

            results[i] = dict(
                member = mem,
                avatar = rpfp,
                db = result
                )

        async with ctx.typing():
            final_buffer = await self.bot.loop.run_in_executor(None, partial(self.GenLeaderboard, results))

            # === SEND THE RETURN IMAGE
            await ctx.send(file=discord.File(filename="profile.png", fp=final_buffer))
            


    @staticmethod
    def GenLeaderboard(l) -> BytesIO:
        # ===== VARS
        out_image = BytesIO()
        imagedir = Path(__file__).parents[0].joinpath('images')
        barmax = l[0]['db']['nummsgs']
        top = 100
        inc = 100

        with Image.open(os.path.join(imagedir, "leaderboardbg.png")) as background:
            
            draw = ImageDraw.Draw(background)

            # ==== MAKE OUR FONT
            nameFont = ImageFont.truetype(os.path.join(imagedir, "OpenSans-Regular.ttf"), 32)
            levelNumberFont = ImageFont.truetype(os.path.join(imagedir, "OpenSans-Semibold.ttf"), 42)
            leaderboardFont = ImageFont.truetype(os.path.join(imagedir, "OpenSans-Semibold.ttf"), 62)
            levelFont = ImageFont.truetype(os.path.join(imagedir, "OpenSans-Regular.ttf"), 38)

            draw.text((206, 7), "Leaderboard", fill=(205, 205, 205, 255), font=leaderboardFont)

            for i in l.values():
                pfp = Test.__round_pfp_blur(i['avatar'], (i['member']).status.__str__(), imagedir, RADIUS=1)

                # = PASTE IN THE PFP
                background.paste(pfp, (30, top), mask=pfp)

                # = PASTE IN THE PROGRESS BAR
                background.paste(Image.new("RGBA", (640, 12), (0, 85, 183, 255)), (120, (top + 61)), mask=None)
                
                if i['db']['nummsgs'] == barmax:
                    x = 640
                
                else:
                    x = int(round((i['db']['nummsgs'] / barmax) * 640))

                    # JUST IN CASE
                    if x < 1:
                        x = 1 

                    elif x > 640:
                        x = 640

                # = PASTE IN THE PROGRESS ONTO PROGRESS BAR
                background.paste(Image.new("RGBA", (x, 12), (0, 175, 96, 255)), (120, (top + 61)), mask=None)

                # - LEVEL
                draw.text((600, (top + 3)), "LV:", fill=(230, 230, 230, 255), font=levelFont)
                draw.text((680, (top - 1)), f"{i['db']['level']}", fill=(230, 230, 230, 255), font=levelNumberFont)
                # - NAME
                draw.text((130, (top + 8)), Test.__get_clean_name(i['member'], 30, at=True), fill=(135, 134, 142, 255), font=nameFont)

                # = INCREMENT
                top = top + inc

            background.save(out_image, "png")

        out_image.seek(0)

        return out_image


    @staticmethod
    def __round_pfp_blur(avatar_bytes, mstat, imgdir, *, RADIUS=2, status=True, basecolour=(35,39,42,255)):
        
        if isinstance(avatar_bytes, BytesIO):
            avatar_bytes = avatar_bytes.getvalue()

        diam = 2*RADIUS

        with Image.open(BytesIO(avatar_bytes)).convert('RGBA') as ava:
            with Image.new('L', ava.size, 0) as mask:
                draw = ImageDraw.Draw(mask)
                draw.ellipse([(diam, diam), (ava.size[0] - diam, ava.size[1] - diam)], fill=255)
                mask = mask.filter(ImageFilter.GaussianBlur(RADIUS))
                im = Image.alpha_composite(Image.new('RGBA', ava.size, basecolour), Image.composite(ava, Image.new('RGBA', ava.size, (0,0,0,0)), mask))

        return im
    

    @staticmethod
    def __get_clean_name(member, maxlen=22, *, at=False):

        # ===== IF THE MEMBER HAS A NICKNAME, USE THAT AND IGNORE THE DISCRIMINATOR
        if member.nick:
            name = f'@{member.nick}' if at else member.nick
            re.sub(r'[^\x00-\x7f]',r'', name).strip()

            if len(name) > maxlen: 
                name = f"{name[:maxlen]}..."
        
        # ===== IF MEMBER ONLY HAS THEIR USERNAME, USE THAT AND INCLUDE DISCRIMINATOR      
        else:
            mname = f'@{member.name}' if at else member.name
            re.sub(r'[^\x00-\x7f]',r'', mname).strip()

            if len(f"{mname}#{member.discriminator}") <= maxlen:
                name = f"{mname}#{member.discriminator}"

            elif len(mname) <= maxlen:
                name = mname

            else:
                name = f"{mname[:maxlen]}..."
            
        return name 


def setup(bot):
    bot.add_cog(Test(bot))