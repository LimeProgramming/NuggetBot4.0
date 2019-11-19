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

import discord
from discord.ext import commands
import asyncio
from nuggetbot import exceptions
from nuggetbot.config import Config
from typing import Union
import os
from PIL import Image
from io import BytesIO

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


        channel = self.bot.get_channel(614956834771566594)
        Webhook = discord.utils.get(await channel.webhooks(), name='NugBotErrors')


        await self.execute_webhook(
            Webhook, 
            content=    'This is a text message <a:foxban:405724216197906455>', 
            username=   'NuggetBotErrors', 
            avatar_url= self.bot.user.avatar_url
            )

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


def setup(bot):
    bot.add_cog(Test(bot))