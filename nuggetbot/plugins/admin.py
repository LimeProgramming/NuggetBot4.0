import os
import copy
import psutil
import discord
import asyncio
import aiohttp
import datetime
import platform
from io import BytesIO
from discord.ext import commands
from typing import Union, Optional
from discord import Webhook, AsyncWebhookAdapter
from discord.utils import _bytes_to_base64_data

from nuggetbot.config import Config
from nuggetbot.util.chat_formatting import RANDOM_DISCORD_COLOR, GUILD_URL_AS, AVATAR_URL_AS
from nuggetbot.plugins.cog_utils import SAVE_COG_CONFIG, LOAD_COG_CONFIG, is_high_staff, is_highest_staff, is_owner, turned_off

class GlobalChannel(commands.Converter):
    async def convert(self, ctx, argument):
        try:
            return await commands.TextChannelConverter().convert(ctx, argument)
        except commands.BadArgument:
            # Not found... so fall back to ID + global lookup
            try:
                channel_id = int(argument, base=10)
            except ValueError:
                raise commands.BadArgument(f'Could not find a channel by ID {argument!r}.')
            else:
                channel = ctx.bot.get_channel(channel_id)
                if channel is None:
                    raise commands.BadArgument(f'Could not find a channel by ID {argument!r}.')
                return channel

class Admin(commands.Cog):
    """Admin-only commands that make the bot dynamic."""
    
    config = None 

    def __init__(self, bot):
        self.bot = bot
        self._last_result = None
        self.sessions = set()
        self.http = aiohttp.ClientSession(loop=bot.loop)
        Admin.config = Config()

  #-------------------- STATIC METHODS --------------------
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
    async def get_user_id(content):
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
    async def get_user_id_reason(content):
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
    async def content(ctx):
        try:
            args = ctx.message.content.split(" ")
            if len(args) <= 1:
                return False 

            return ctx.message.content[len(ctx.prefix) + len(ctx.invoked_with):]     

        except (IndexError, ValueError):
            return False

    async def get_avatar(self, user: Union[discord.User, discord.Member]) -> bytes:

        # generally an avatar will be 1024x1024, but we shouldn't rely on this
        avatar_url = AVATAR_URL_AS(user, format="png", size=128)

        async with self.http.get(avatar_url) as response:
            avatar_bytes = await response.read()

        return avatar_bytes


  #-------------------- LOCAL COG STUFF --------------------
    async def on_cog_command_error(self, ctx, error):
        if isinstance(error, discord.ext.commands.errors.NotOwner):
            try:
                owner = (self.bot.application_info()).owner
            except:
                owner = self.bot.get_guild(Admin.config.target_guild_id).owner()

            await ctx.channel.send(content=f"```diff\n- {ctx.prefix}{ctx.invoked_with} is an owner only command, this will be reported to {owner.name}.")
            await owner.send(content=f"{ctx.author.mention} tried to use the owner only command{ctx.invoked_with}")
            return 

        if isinstance(error, discord.ext.commands.errors.CheckFailure):
            pass

    async def cog_after_invoke(self, ctx):
        if Admin.config.delete_invoking:
            await ctx.message.delete()

        return


  #-------------------- LISTENERS --------------------
    @commands.Cog.listener()
    async def on_member_join(self, member):
        pass

    @commands.Cog.listener()        
    async def on_member_remove(self, member):
        pass
    
    @commands.Cog.listener()        
    async def on_guild_update(self, before, after):
        pass

    @commands.Cog.listener()        
    async def on_guild_role_create(self, role):
        pass

    @commands.Cog.listener()        
    async def on_guild_role_delete(self, role):
        pass

    @commands.Cog.listener()        
    async def on_guild_role_update(self, before, after):
        pass

    @commands.Cog.listener()        
    async def on_guild_emojis_update(self, guild, before, after):
        pass

    @commands.Cog.listener()        
    async def on_member_ban(self, guild, user):
        pass

    @commands.Cog.listener()        
    async def on_member_unban(self, guild, user):
        pass


  #-------------------- COMMANDS --------------------
    @is_owner()
    @commands.command(pass_context=True, hidden=True, name='postaswebhook', aliases=[])
    async def cmd_postaswebhook(self, ctx):
        """
        Useage:
            [prefix]postaswebhook <text> or <files>
        [Primary bot owner] Reposts whatever you send as a webhook package.
        """

        msgContent = Admin.content(ctx)
        if not msgContent and not ctx.message.attachments:
            await ctx.channel.send(content="[p]postaswebhook <text> or <files> [Primary bot owner] Reposts whatever you send as a webhook package.", delete_after=15)

        ###===== GET OR CREATE A WEBHOOK, REPORT ERROR IF EXISTS
        webhooks = await ctx.channel.webhooks()
        RoostWebhook = discord.utils.get(webhooks, name='postaswebhook')

        if not RoostWebhook:
            avatar_bytes = await self.get_avatar(self.bot.user)

            try:
                RoostWebhook = await ctx.channel.create_webhook(name="postaswebhook", avatar = avatar_bytes, reason= "This is a test")
            
            except discord.errors.Forbidden:
                await ctx.channel.send(content="I do not have permissions to create a webhook.", delete_after=15)

            except discord.errors.HTTPException:
                await ctx.channel.send(content="Creating the webhook failed.", delete_after=15)

        ###===== PREPARE MSG FOR DISPATCH
        files = []
        if ctx.message.attachments:
            for attach in ctx.message.attachments:
                fb = await attach.read()
                filename = attach.filename

                files.append(discord.File(BytesIO(fb), filename=filename, spoiler=False))

        msgContent = ctx.message.clean_content.replace("@everyone", "@\u200beveryone").replace("@here", "@\u200bhere")
        msgContent = msgContent[len(ctx.prefix) + len(ctx.invoked_with):]
        avatar_url = AVATAR_URL_AS(ctx.message.author, format="png", size=128)

        ###===== BOT SHOULD BE ABLE TO SEND MESSAGES BUT STILL
        try:
            await RoostWebhook.send(
                content=        msgContent,
                username=       (ctx.message.author.nick or ctx.message.author.name),
                avatar_url=     avatar_url,
                tts=            False,
                files=          files,
                embeds=         ctx.message.embeds
            )

        except discord.errors.Forbidden:
            print("[Error] I do not have permission to send messages.")

        except discord.errors.HTTPException:
            print("[Error] An error has occurred")

        return

    @is_high_staff() #new
    @commands.command(pass_context=True, hidden=True, name='banbyid', aliases=[])
    async def cmd_banbyid(self, ctx):
        """
        Useage:
            [prefix]banbyid <userid/mention> <reason>
        [Admin/Mod] Bans a user from guild using their ID alone.
        """
        user_id, reason = await Admin.get_user_id_reason(ctx.message.content)

        try:
            await self.bot.http.ban(user_id=user_id, guild_id=ctx.guild.id, delete_message_days=1, reason=reason)
            await ctx.channel.send(content=f"<@{user_id}> has been banned from this Guild.", delete_after = 15)

        #===== REPORT PERMISSION ERROR
        except discord.errors.Forbidden:
            await ctx.channel.send(content=f"`I do not have the permission needed to ban <@{user_id}> from this Guild.`", delete_after = 15)

        #===== REPORT GENERIC ERROR
        except discord.errors.HTTPException:
            await ctx.channel.send(content=f"`I could no ban <@{user_id}> due to generic error.`", delete_after = 15)
        
        return
    
    @is_owner()
    @commands.command(pass_context=True, hidden=True, name='hoststats', aliases=[])
    async def cmd_hoststats(self, ctx):
        valid = await self.oneline_valid(ctx.message.content)
        if not valid:
            return

        def MBorGB(val):
            ret = val/1073741824

            if ret < 1:
                ret = "{0:.1f} MB".format((val/1048576))
                return ret 

            ret = "{0:.1f} GB".format(ret)
            return ret

        #CPU information
        cpu_freq = psutil.cpu_freq()

        #Physical ram
        mem = psutil.virtual_memory()

        #disk drive space
        if (platform.platform()).lower().startswith("linux"):
            d = psutil.disk_usage(r"/")

        elif platform.platform().lower().startswith("win"):
            d = psutil.disk_usage(os.path.splitdrive(os.path.abspath(__file__))[0])


        embed = discord.Embed(  title=      "Host System Stats",
                                description="",
                                colour=     RANDOM_DISCORD_COLOR(),
                                timestamp=  datetime.datetime.utcnow(),
                                type=       "rich"
                                )

        embed.add_field(name=   "CPU:",
                        value=  f"**Cores:** {psutil.cpu_count(logical=False)} ({psutil.cpu_count(logical=True)})\n"
                                f"**Architecture:** {platform.machine()}\n"
                                f"**Affinity:** {len(psutil.Process().cpu_affinity())}\n"
                                f"**Useage:** {psutil.cpu_percent()}%\n"
                                f"**Freq:** {cpu_freq[0]} Mhz",
                        inline= True
                        )
        
        embed.add_field(name=   "Memory:",
                        value=  f"**Total:** {MBorGB(mem[0])}\n"
                                f"**Free:** {MBorGB(mem[1])}\n"
                                f"**Used:** {mem[2]}%",
                        inline= True
                        )
        
        embed.add_field(name=   "Storage:",
                        value=  f"**Total:** {MBorGB(d[0])}\n"
                                f"**Free:** {MBorGB(d[2])}\n"
                                f"**Used:** {d[3]}%",
                        inline= True
                        )


        embed.add_field(name=   "Python:",
                        value=  f"**Version:** {platform.python_version()}\n"
                                f"**Discord.py** {discord.__version__}\n"
                                f"**Bits:** {platform.architecture()[0]}",
                        inline= True
                        )

        embed.set_author(name=   f"{self.bot.user.name}#{self.bot.user.discriminator}",
                        icon_url=AVATAR_URL_AS(self.bot.user)
                        )
        
        embed.set_thumbnail(        url=        AVATAR_URL_AS(user=self.bot.user, format=None, size=512))

        await ctx.channel.send(embed = embed)
        return

    @commands.command(hidden=True)
    async def load(self, ctx, *, module):
        """Loads a module."""
        try:
            self.bot.load_extension(module)
        except commands.ExtensionError as e:
            await ctx.send(f'{e.__class__.__name__}: {e}')
        else:
            await ctx.send('\N{OK HAND SIGN}')

    @commands.command(hidden=True)
    async def unload(self, ctx, *, module):
        """Unloads a module."""
        try:
            self.bot.unload_extension(module)
        except commands.ExtensionError as e:
            await ctx.send(f'{e.__class__.__name__}: {e}')
        else:
            await ctx.send('\N{OK HAND SIGN}')

    def reload_or_load_extension(self, module):
        try:
            self.bot.reload_extension(module)
        except commands.ExtensionNotLoaded:
            self.bot.load_extension(module)


    @commands.command(hidden=True)
    async def sudo(self, ctx, channel: Optional[GlobalChannel], who: discord.User, *, command: str):
        """Run a command as another user optionally in another channel."""
        msg = copy.copy(ctx.message)
        channel = channel or ctx.channel
        msg.channel = channel
        msg.author = channel.guild.get_member(who.id) or who
        msg.content = ctx.prefix + command
        new_ctx = await self.bot.get_context(msg, cls=type(ctx))
        new_ctx._db = ctx._db
        await self.bot.invoke(new_ctx)


def setup(bot):
    bot.add_cog(Admin(bot))

