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


from discord.ext import commands
import asyncio
from nuggetbot import exceptions

def to_emoji(c):
    base = 0x1f1e6
    return chr(base + c)

class Test(commands.Cog):
    """Poll voting system."""

    def __init__(self, bot):
        self.bot = bot


    @commands.Cog.listener()
    async def on_ready(self):
        await asyncio.sleep(4)

        #p#rint(self.bot.http.token)
        #print(self.bot.http.bot_token)

        #return
        #test = self.bot.get_guild(348609968292888577)
        #for e in test.emojis:
        #    if e.animated:
        #        print("{0.name}:{0.id}".format(e))

        raise exceptions.PostAsWebhook("This issue is a test, please ignore. <a:foxban:405724216197906455>")

    @commands.Cog.listener()
    async def on_message(self, msg):
        return
        print(msg.clean_content)


def setup(bot):
    bot.add_cog(Test(bot))