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
import discord
import datetime
import collections
from io import BytesIO
from discord.ext import commands

from nuggetbot.config import Config
from nuggetbot.util.chat_formatting import RANDOM_DISCORD_COLOR, GUILD_URL_AS, AVATAR_URL_AS, escape

#from .cog_utils import SAVE_COG_CONFIG, LOAD_COG_CONFIG
from .util import checks, cogset

class DelMsgLogging(commands.Cog):
    """
    Deleted message logging.
    It can work on a channel by channel basis or a member by member basis
    """
    config = None
    compare = lambda x, y: collections.Counter(x) == collections.Counter(y)

    def __init__(self, bot):
        self.bot = bot
        self.cogset = dict()
        self.report_ch = None
        DelMsgLogging.config = Config()

  #-------------------- LISTENERS --------------------
    @commands.Cog.listener()
    async def on_ready(self):

        self.cogset = await cogset.LOAD(cogname=self.qualified_name)

        if not self.cogset:
            self.cogset= dict(
                enableDelMsgLog=    False,
                save_attach=        False,
                lis_channels=       list(),
                lis_members=        list(),
                report_ch_id=       DelMsgLogging.config.channels['bot_log'],
            )

            await cogset.SAVE(self.cogset, cogname=self.qualified_name)

    @commands.Cog.listener()
    async def on_message_delete(self, msg):
        if not msg.guild or msg.author.bot or not self.cogset['enableDelMsgLog'] or not msg.type == discord.MessageType.default:
            return 

        if not self.report_ch:
            self.report_ch = msg.guild.get_channel(self.cogset['report_ch_id'])

        if msg.channel.id in self.cogset['lis_channels'] or msg.author.id in self.cogset['lis_members']:
            msg_attach = list()
            reason = ""

            embed = discord.Embed(  
                title=              "Message Deleted.",
                description=        "**Author:** <@{}>\n"
                                    "**Sent:** {}\n"
                                    "**Channel:** <#{}>".format(
                                        msg.author.id,
                                        msg.created_at,
                                        msg.channel.id
                                        ),
                colour=             RANDOM_DISCORD_COLOR(),
                timestamp=          datetime.datetime.utcnow(),
                type=               "rich"
                                    )

            embed.add_field (
                name=       "**Content**",
                value=      escape(msg.content, mass_mentions=True, formatting=True),
                inline=     False
                            )

            embed.set_author(
                name=       f"{msg.author.name}#{msg.author.discriminator}",
                icon_url=   AVATAR_URL_AS(msg.author),
                url=        AVATAR_URL_AS(msg.author)
                            )

            embed.set_footer(
                icon_url=   GUILD_URL_AS(msg.guild), 
                text=       msg.guild.name
                            )

            if self.cogset['save_attach'] and msg.attachments:

                for attach in msg.attachments:
                    try:
                        fb = await attach.read(use_cached=True)
                        filename = attach.filename

                        msg_attach.append(discord.File(BytesIO(fb), filename=filename, spoiler=False))
                    
                    except discord.errors.Forbidden:
                        msg_attach = None
                        reason = 'I do not have permissions to access this attachment.'
                        break

                    except discord.errors.NotFound:
                        msg_attach = None
                        reason = 'The attachment was deleted.'
                        break

                    except discord.errors.HTTPException:
                        msg_attach = None
                        reason = 'Downloading the attachment failed.'
                        break

                if msg_attach is None:
                    embed.add_field (
                        name=       "**Attachments Failed**",
                        value=      f"**Reason:** {reason}",
                        inline=     False
                                    )

            await self.report_ch.send(embed=embed, files=msg_attach)

        
        return
   
        
  #-------------------- LOCAL COG STUFF --------------------      
    async def cog_after_invoke(self, ctx):
        '''THIS IS CALLED AFTER EVERY COG COMMAND, IT DISCONNECTS FROM THE DATABASE AND DELETES INVOKING MESSAGE IF SET TO.'''

        if ctx.message.guild and DelMsgLogging.config.delete_invoking:
            await ctx.message.delete()

        return

    async def on_cog_command_error(self, ctx, error):
        pass


  #-------------------- STATIC METHODS --------------------
    @staticmethod
    async def Get_user_id(content):
        try:
            args= content.split(" ")
            if len(args) > 2:
                return False 

            #=== SPLIT, REMOVE MENTION WRAPPER AND CONVERT TO INT
            user_id = args[1]
            user_id = user_id.replace("<", "").replace("@", "").replace("!", "").replace(">", "")
            user_id = int(user_id)
            return user_id

        except (IndexError, ValueError):
            return False

    @staticmethod
    async def Get_user_id_reason(content):
        try:
            args = content.split(" ")
            if len(args) < 2:
                return (False, False)

            #=== SPLIT, REMOVE MENTION WRAPPER AND CONVERT TO INT
            user_id = args[1]
            user_id = user_id.replace("<", "").replace("@", "").replace("!", "").replace(">", "")
            user_id = int(user_id)

            if len(args) > 2:
                reason = " ".join(args[2:])
                reason = reason[:1000]

            else:
                reason = None

            return (user_id, reason)

        except (IndexError, ValueError):
            return (False, False)

    @staticmethod
    async def oneline_valid(content):
        try:
            args = content.split(" ")
            if len(args) > 1:
                return False 

            return True

        except (IndexError, ValueError):
            return False

    @staticmethod
    async def split_list(arr, size=100):
        """Custom function to break a list or string into an array of a certain size"""

        arrs = []

        while len(arr) > size:
            pice = arr[:size]
            arrs.append(pice)
            arr = arr[size:]

        arrs.append(arr)
        return arrs

    @staticmethod
    async def get_channel_id(content):
        try:
            args= content.split(" ")
            if len(args) > 2:
                return False 

            #=== SPLIT, REMOVE MENTION WRAPPER AND CONVERT TO INT
            ch_id = args[1]
            ch_id = ch_id.replace("<", "").replace("#", "").replace(">", "")
            ch_id = int(ch_id)
            return ch_id

        except (IndexError, ValueError):
            return False

    @staticmethod
    async def add_to_list(l : list, i):
        
        nl = list(set(l) + {i})

        if DelMsgLogging.compare(nl, l):
            return (False, l)

        return (True, nl)


  #-------------------- COG COMMANDS --------------------
    
    @checks.HIGHEST_STAFF()
    @commands.command(pass_context=True, hidden=False, name='toggledelmsglog', aliases=['toggleDelMsgLog'])
    async def cmd_toggleDelMsgLog(self, ctx):
        """
        Useage:
            [prefix]toggledelmsglog
        
        [Admin Staff] Enables deleted message logging. Reports messages deleted either in a channel or on a user by user basis. Useful for suspected troll.
        """

        valid = await DelMsgLogging.oneline_valid(ctx.message.content)

        if not valid:
            await ctx.channel.send(content="`[p]toggledelmsglog [Admin Staff] Enables deleted message logging. Reports messages deleted either in a channel or on a user by user basis.`")
            return 

        self.cogset['enableDelMsgLog'] = not self.cogset['enableDelMsgLog']

        await cogset.SAVE(self.cogset, cogname=self.qualified_name)

        await ctx.channel.send(f"Deleted message logging has been set to {self.cogset['enableDelMsgLog']}")
        return

    @checks.HIGHEST_STAFF()
    @commands.command(pass_context=True, hidden=False, name='toggledelmsgattach', aliases=['toggleDelMsgAttach'])
    async def cmd_toggleDelMsgAttach(self, ctx):
        """
        Useage:
            [prefix]toggleDelMsgAttach
        
        [Admin Staff] When enabled, the deleted message logger will try to download any attachments from discord caches.
        """

        valid = await DelMsgLogging.oneline_valid(ctx.message.content)

        if not valid:
            await ctx.channel.send(content="`[p]toggleDelMsgAttach [Admin Staff] When enabled, the deleted message logger will try to download any attachments from discord caches.`")
            return 

        self.cogset['save_attach'] = not self.cogset['save_attach']

        await cogset.SAVE(self.cogset, cogname=self.qualified_name)

        await ctx.channel.send(f"Deleted message logging download attachments has been set to {self.cogset['save_attach']}")
        return

    @checks.HIGHEST_STAFF()
    @commands.command(pass_context=True, hidden=False, name='delmsglogchannel', aliases=['DelMsgLogChannel'])
    async def cmd_DelMsgLogChannel(self, ctx):
        """
        Useage:
            [prefix]DelMsgLogChannel <chid/channelMention>

        [Admin Staff] Toggle deleted message logging on a channel by channel basis
        """

        ###===== CHECKING IF THE INPUT IS VALID
        ch_id = await DelMsgLogging.get_channel_id(ctx.message.content)

        if not ch_id:
            await ctx.channel.send(content="`[p]DelMsgLogChannel <chid/channelMention>, [Admin Staff] Toggle deleted message logging on a channel by channel basis`", delete_after=15)
            return 

        ###===== CHECKING IF THE PROVIDED CHANNEL IS ALREADY IN THE LIST OF WATCHED CHANNELS
        if bool(self.cogset['lis_channels'].count(ch_id)):
            ###=== REMOVE THE CHANNEL FROM THE LIST
            self.cogset['lis_channels'].remove(ch_id)
            await ctx.channel.send(content=f"<#{ch_id}> has been removed from the list of monitored channels.", delete_after=15)

        else:
            ###=== ADD THE CHANNEL TO THE LIST
            self.cogset['lis_channels'].append(ch_id)
            await ctx.channel.send(content=f"<#{ch_id}> is added to the list of monitored channels.", delete_after=15)

        ###===== SAVE THE SETTINGS
        await cogset.SAVE(self.cogset, cogname=self.qualified_name)
        return

    @checks.HIGHEST_STAFF()
    @commands.command(pass_context=True, hidden=False, name='delmsglogmember', aliases=['DelMsgLogMember'])
    async def cmd_DelMsgLogMember(self, ctx):
        """
        Useage:
            [prefix]DelMsgLogMember <userid/userMention>

        [Admin Staff] Toggle deleted message logging on a member by member basis
        """
        
        user_id = await DelMsgLogging.Get_user_id(ctx.message.content)

        if not user_id:
            await ctx.channel.send(content="`[p]DelMsgLogMember <userid/userMention>, [Admin Staff] Toggle deleted message logging on a member by member basis`", delete_after=15)
            return 

        ###===== CHECKING IF THE PROVIDED CHANNEL IS ALREADY IN THE LIST OF WATCHED CHANNELS
        if bool(self.cogset['lis_members'].count(user_id)):
            self.cogset['lis_members'].append(user_id)
            await ctx.channel.send(content=f"<@{user_id}> has added to the list of monitored members.", delete_after=15)
        
        else:
            self.cogset['lis_members'].remove(user_id)
            await ctx.channel.send(content=f"<@{user_id}> is no longer on the list of monitored members.", delete_after=15)

        ###===== SAVE THE SETTINGS
        await cogset.SAVE(self.cogset, cogname=self.qualified_name)
        return

    @checks.HIGHEST_STAFF()
    @commands.command(pass_context=True, hidden=False, name='delmsgreportchannel', aliases=['DelMsgReportChannel'])
    async def cmd_DelMsgReportChannel(self, ctx):
        """
        Useage:
            [prefix]DelMsgReportChannel <chid/channelMention>

        [Admin Staff] Sets the channel the bot will report deleted channels to. By default this channel is the bot log as defined in setup.ini
        """

        ###===== CHECKING IF THE INPUT IS VALID
        ch_id = await DelMsgLogging.get_channel_id(ctx.message.content)

        if not ch_id:
            await ctx.channel.send(content="`[p]DelMsgReportChannel <chid/channelMention>, [Admin Staff] Sets the channel the bot will report deleted channels to. By default this channel is the bot log as defined in setup.ini`", delete_after=15)
            return 

        channelReal = ctx.message.guild.get_channel(ch_id)

        if not channelReal:
            await ctx.channel.send(content="`[p]DelMsgReportChannel <chid/channelMention>, [Admin Staff] Sets the channel the bot will report deleted channels to. By default this channel is the bot log as defined in setup.ini \nN.B. the channel needs to actually exist`", delete_after=15)
            return 

        ###===== SAVE THE SETTINGS
        self.cogset['report_ch_id'] = ch_id
        self.report_ch = None
        await cogset.SAVE(self.cogset, cogname=self.qualified_name)

        ###===== REPORT TO INVOKER
        await ctx.channel.send(content=f"https://discordapp.com/channels/{channelReal.guild.id}/{channelReal.id} \nIs now the current channel I will report deleted messages to.", delete_after=60)
        return


def setup(bot):
    bot.add_cog(DelMsgLogging(bot))