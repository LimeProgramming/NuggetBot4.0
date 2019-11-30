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
#from nuggetbot.plugin import Plugin
#import discord
#import asyncio
#import logging

#from discord.ext import commands
#bot = commands.Bot(command_prefix='~', description="I don't fucking care")

#log = logging.getLogger('discord')



#async def test_print(r):
#    print(r) 

#@bot.listen()
#async def on_message(self, message):
#    print("test plugin is alive")

#class Test(Plugin):
#    is_global = True


#    async def on_ready(self):
#        pass

#    async def on_message(self, message):
#        print("test plugin is alive")
from functools import partial
import discord
import random
from discord.ext import commands
import asyncio
from nuggetbot import exceptions
from nuggetbot.config import Config
from typing import Union
import os
import re
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from .util.misc import GET_AVATAR_BYTES

def to_emoji(c):
    base = 0x1f1e6
    return chr(base + c)

class Test(commands.Cog):
    """Poll voting system."""

    def __init__(self, bot):
        self.bot = bot


    @commands.Cog.listener()
    async def on_ready(self):
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
            final_buffer = await self.bot.loop.run_in_executor(None, partial(self.GenWelcomeImg, avatar_bytes, member))

            # === SEND THE RETURN IMAGE
            await ctx.send(file=discord.File(filename="welcome.png", fp=final_buffer))

    @staticmethod
    def GenWelcomeImg(avatar_bytes: bytes, member: Union[discord.User, discord.Member]) -> BytesIO:
        #===== VARS
        out_image = BytesIO()
        imagedir = os.path.join(os.path.split(os.path.realpath(__file__))[0], "images")
        highLight = os.path.join(imagedir, "wel", 'c', f'{random.randint(1,61)}.png')

        ###===== BLUR THE EDGES OF A MEMBERS PFP AND ADD THEIR STATUS
        img = Test.__square_blur_icon(avatar_bytes, member.status.__str__(), imagedir, status=False)


        with Image.open(os.path.join(imagedir, "wel", 'welbg.png')).convert('RGBA') as welbg:
            with Image.open(highLight).convert('RGBA') as hl:
                
                # = ADD THE HIGHLIGHT TO THE IMAGE
                workingImg = Image.alpha_composite(welbg, hl)

                # = ADD THE PFP TO THE IMAGE
                workingImg.paste(img, (44, 29), mask=img)

                # = MAKE OUR FONT
                font = ImageFont.truetype(os.path.join(imagedir, "OpenSans-Regular.ttf"), 24)

                draw = ImageDraw.Draw(workingImg)
                draw.text((188, 98), Test.__gen_member_name(member, 30, at=True), fill=(135, 134, 142, 255), font=font)

                workingImg.save(out_image, "png")

        out_image.seek(0)

        return out_image

    @staticmethod
    def __square_blur_icon(avatar_bytes, mstat, imgdir, *, RADIUS=2, status=True):
        """
        This just blurs the edges of a members pfp
        """

        diam = 2*RADIUS

        ###===== OPEN THE MEMBERS STATUS IMAGE
        if status:
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
        if status:
            return Image.alpha_composite(Image.new('RGBA', canvas.size, (35,39,42,255)), Image.alpha_composite(canvas, status))
        else:
            return Image.alpha_composite(Image.new('RGBA', canvas.size, (35,39,42,255)), canvas)

    @staticmethod
    def __gen_member_name(member, maxlen=22, *, at=False):

        ###===== IF THE MEMBER HAS A NICKNAME, USE THAT AND IGNORE THE DISCRIMINATOR
        if member.nick:
            name = f'@{member.nick}' if at else member.nick
            re.sub(r'[^\x00-\x7f]',r'', name).strip()

            if len(name) > maxlen: 
                name = f"{name[:maxlen]}..."
        
        ###===== IF MEMBER ONLY HAS THEIR USERNAME, USE THAT AND INCLUDE DISCRIMINATOR      
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