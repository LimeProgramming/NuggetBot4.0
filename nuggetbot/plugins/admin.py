import os
import copy
import json
import psutil
import discord
import asyncio
import asyncpg
import aiohttp
import datetime
import platform
from io import BytesIO
from discord.ext import commands
from typing import Union, Optional
from discord import Webhook, AsyncWebhookAdapter
from discord.utils import _bytes_to_base64_data

from nuggetbot.config import Config
from nuggetbot.util import gen_embed as GenEmbed
from nuggetbot.database import DatabaseCmds as pgCmds
from nuggetbot.util.chat_formatting import RANDOM_DISCORD_COLOR, GUILD_URL_AS, AVATAR_URL_AS
from .cog_utils import SAVE_COG_CONFIG, LOAD_COG_CONFIG
from .util import checks
import dblogin 

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

        self.raw_perms = [  'create_instant_invite', 'kick_members', 'ban_members', 'administrator', 
                    'manage_channels', 'manage_guild', 'add_reactions', 'view_audit_log', 'priority_speaker', 
                    'stream', 'read_messages', 'send_messages', 'send_tts_messages', 'manage_messages', 
                    'embed_links', 'attach_files', 'read_message_history', 'mention_everyone', 'external_emojis', 
                    '', 'connect', 'speak', 'mute_members', 'deafen_members', 'move_members', 'use_voice_activation', 
                    'change_nickname', 'manage_nicknames', 'manage_roles', 'manage_webhooks', 'manage_emojis']

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

    async def _del_msg_later(self, message, after):
        """Custom function to delete messages after a period of time"""

        await asyncio.sleep(after)
        await message.delete()
        return

    @asyncio.coroutine
    async def ask_yn(self, msg, question, timeout=60, expire_in=0):
        """Custom function which ask a yes or no question using reactions, returns True for yes | false for no | none for timeout"""

        message = await msg.channel.send(question)
        error = None

        try:
            await message.add_reaction("👍")
            await message.add_reaction("👎")

        except discord.errors.Forbidden:
            error = '`I do not have permission to add reactions, defaulting to "No"`'

        except discord.errors.NotFound:
            error = '`Emoji not found, defaulting to "No"`'

        except discord.errors.InvalidArgument:
            error = '`Error in my programming, defaulting to "No"`'

        except discord.errors.HTTPException:
            error = '`Error with adding reaction, defaulting to "No"`'

        if error is not None:
            await message.delete()
            await message.channel.send(error)
            return False
        
        def check(reaction, user):
            return user == msg.author and str(reaction.emoji) in ["👍", "👎"] and not user.bot
        
        try:
            reaction = await self.bot.wait_for('reaction_add', timeout=timeout, check=check)

            #=== If msg is set to auto delete
            if expire_in:
                asyncio.ensure_future(self._del_msg_later(message, expire_in))
            
            #=== Thumb up
            if str(reaction[0].emoji) == "👍":
                return True

            #=== Thumb down
            else:
                return False
                    
        #===== Time out error
        except asyncio.TimeoutError:
            return None

    async def get_avatar(self, user: Union[discord.User, discord.Member]) -> bytes:

        # generally an avatar will be 1024x1024, but we shouldn't rely on this
        avatar_url = AVATAR_URL_AS(user, format="png", size=128)

        async with self.http.get(avatar_url) as response:
            avatar_bytes = await response.read()

        return avatar_bytes


  #-------------------- LOCAL COG STUFF --------------------
    async def cog_command_error(self, ctx, error):
        if isinstance(error, discord.ext.commands.errors.NotOwner):
            try:
                owner = (self.bot.application_info()).owner
            except:
                owner = self.bot.get_guild(Admin.config.target_guild_id).owner()

            await ctx.channel.send(content=f"```diff\n- {ctx.prefix}{ctx.invoked_with} is an owner only command, this will be reported to {owner.name}.")
            await owner.send(content=f"{ctx.author.mention} tried to use the owner only command{ctx.invoked_with}")
            return 

        if isinstance(error, discord.ext.commands.errors.CheckFailure):
            print(error)
            pass

    async def cog_before_invoke(self, ctx):
        '''THIS IS CALLED BEFORE EVERY COG COMMAND, IT'S SOLE PURPOSE IS TO CONNECT TO THE DATABASE'''

        credentials = {"user": dblogin.user, "password": dblogin.pwrd, "database": dblogin.name, "host": dblogin.host}
        self.db = await asyncpg.create_pool(**credentials)

        return

    async def cog_after_invoke(self, ctx):
        await self.db.close()

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

    @checks.HIGH_STAFF()
    @commands.command(pass_context=True, hidden=False, name='loginvites', aliases=['logInvites', 'LogInvites'])
    async def cmd_loginvites(self, ctx):
        """
        [High Staff] When called the function will make the init invite log in a json file

        Useage:
            [prefix]LogInvites
        """

        inviteLog = list()

        try:
            for invite in await ctx.guild.invites():
                invit = {'max_age' : invite.max_age, 'created_at' : invite.created_at.__str__(), 'uses' : invite.uses, 
                         'max_uses' : invite.max_uses, 'code' : invite.id}

                if invite.inviter is None:
                    invit['inviter'] = {'name' : "N/A", 'id' : "N/A", 'discriminator' : "N/A", 'mention': "N/A",
                                        'avatar_url' : "https://discordapp.com/assets/6debd47ed13483642cf09e832ed0bc1b.png?size=128"}
                else:
                    invit['inviter'] = {'name' : invite.inviter.name, 'id' : invite.inviter.id, 'discriminator' : invite.inviter.discriminator,
                                        'avatar_url' : AVATAR_URL_AS(invite.inviter), 'mention' : invite.inviter.mention}

                invit['channel'] = {'name' : invite.channel.name, 'id' : invite.channel.id, 'mention' : invite.channel.mention}

                inviteLog.append(invit)

        except (discord.errors.Forbidden, discord.errors.HTTPException):
            inviteLog =  None

        if inviteLog is not None and len(inviteLog) != 0:
            with open(os.path.join('data','inviteHistory.json'), 'w', encoding='utf-8') as logHistory:
                json.dump(inviteLog, logHistory)

            await ctx.channel.send(content="Current invite information has been logged.", delete_after=15)

        else:
            await ctx.channel.send(content="Current invite information could not be found.", delete_after=15)

        return

    @checks.ANY_STAFF()
    @commands.command(pass_context=True, hidden=False, name='userperms', aliases=['UserPerms', 'userPerms'])
    async def cmd_userperms(self, ctx):
        """
        [All Staff] Gets all the perms for a role both default and channel overwrite. Obviously, member needs to be part of the guild for this to work.
        
        Useage:
            [prefix]UserPerms <userID/userMention>
        """

        try:
            
            user_id = ctx.message.content.split(" ")[1]
            member = ctx.guild.get_member_named(user_id)

            ###=== remove the user mention
            if user_id.isdigit() or user_id.startswith("<@"):
                user_id = user_id.replace("<", "").replace("@", "").replace("!", "").replace(">", "")
                user_id = int(user_id)

                member = ctx.guild.get_member(user_id)
            
            else:
                raise ValueError

        #if user == idiot
        except (IndexError, ValueError):
            await ctx.send_help('userperms', delete_after=15)

        #===== If user is owner; end function early
        if member == ctx.guild.owner:
            try:
                embed = await GenEmbed.getUserPermsOwner(member, msg=ctx.message)

                await ctx.channel.send(embed=embed)
                return
            except Exception as e:
                print(e)
                return

        #===== If user has Admin perms; end function early
        isAdmin = False
        for role in member.roles:
            if role.permissions.administrator:
                isAdmin = True

        if isAdmin:
            embed = await GenEmbed.getUserPermsAdmin(member, msg=ctx.message)
            await ctx.channel.send(embed=embed)
            return

        #===== Variable setup
        server_wide_perms = list()
        channel_specific_perms = list()
        embeds = list()

        #===== server wide
        for role in member.roles:
            for i in range(31):
                if bool((role.permissions.value >> i) & 1):
                    server_wide_perms.append(self.raw_perms[i].replace("_", " ").title())

        #===== one entry for each item
        server_wide_perms = list(set(server_wide_perms))


        #===== channel
        """
            Getting the channel perms for the role sorted.
            The channels are sorted by position for readability of results. 
            Normally they are sorted by position anyway but sometimes they come back in a mess of an order.
            """
        for channel in sorted(ctx.guild.channels, key=lambda x: x.position):
            temp = list()
            cleanedTemp = list()

            for role in ([member] + member.roles):
                channelPerms = channel.overwrites_for(role)

                for i in range(31):
                    if not self.raw_perms[i] == "":
                        #Making sure voice channels are not checked for buggy text channel perms
                        if (channel.type == discord.ChannelType.voice) and (self.raw_perms[i] in ["read_messages", "send_messages"]):
                            continue

                        #Making sure text channels are not checked for voice channel perms
                        if (channel.type == discord.ChannelType.text) and (self.raw_perms[i] in ["speak", "connect", "mute_members", "deafen_members", "move_members", "use_voice_activation", "stream"]):
                            continue

                        result = channelPerms._values.get(self.raw_perms[i])

                        if isinstance(role, discord.Member):
                            if result == True:
                                temp.append("**[User]** {}".format(self.raw_perms[i].replace("_", " ").title()))

                            elif result == False:
                                temp.append("**[User]** Not {}".format(self.raw_perms[i].replace("_", " ").title()))

                        else:
                            if result == True:
                                temp.append(self.raw_perms[i].replace("_", " ").title())

                            elif result == False:
                                temp.append("Not {}".format(self.raw_perms[i].replace("_", " ").title()))

            """
                Because discord will take a yes over a no when it comes to perms,
                we remove the Not {perm} is the perm is there as a yes
                """
            for item in temp:
                if item.startswith("Not"):
                    if not any([i for i in temp if i == item[4:]]):
                        cleanedTemp.append(item)

                else: 
                    cleanedTemp.append(item)

            #=== If at end of loop no perms where found, log nothing.
            if len(cleanedTemp) > 0:
                channel_specific_perms.append(dict(channelName=channel.name,
                                                    perms=cleanedTemp,
                                                    channelType=channel.type.__str__()))


        #===== results, processing them into an actual reply
        #You can only have 25 fields in a discord embed. So I'm breaking up my list of possible fields into a 2d array.
        channel_specific_perms = await self.split_list(channel_specific_perms, size=24)
        firstLoop = True

        for channelSpecificPerms in channel_specific_perms:
            
            #=== Set up the first embed
            if firstLoop:
                text = " | ".join(server_wide_perms)
                if text == "":
                    text = "None"

                embed = discord.Embed(  
                    title=      "Server Wide:",
                    description="{}\n"
                                "**Hierarchy: {}**".format(text,
                                                            (len(ctx.guild.roles) - member.top_role.position)
                                                            ),
                    colour=     RANDOM_DISCORD_COLOR(),
                    timestamp=  datetime.datetime.utcnow(),
                    type=       "rich"
                                     )

                embed.set_author(       
                    name=       "{0.name}#{0.discriminator}".format(member),
                    icon_url=   AVATAR_URL_AS(member)
                                )

                embed.add_field(       
                    name=       "Roles[{}]".format(len(member.roles) - 1),
                    value=      (" ".join([role.mention for role in member.roles if not role.is_everyone])) 
                                if len(member.roles) > 1 else 
                                ("Member has no roles.")
                                )

            #=== Set up additional embeds
            else:
                embed = discord.Embed(  
                    description="",
                    colour=     RANDOM_DISCORD_COLOR(),
                    timestamp=  datetime.datetime.utcnow(),
                    type=       "rich"
                                     )

                embed.set_author(       
                    name=       "{0.name}#{0.discriminator} | Information Continued".format(member.name),
                    icon_url=   AVATAR_URL_AS(member)
                                )

            for i in channelSpecificPerms:
                #= The category channel type does not have a name, instead it's called "4"
                embed.add_field(        
                    name=       i["channelName"] + (":" if not i["channelType"] == "4" else " - Category:"),
                    value=      " | ".join(i["perms"]),
                    inline=     False
                                )


            #=== since these are always going to be the same
            embed.set_thumbnail(        
                url=        AVATAR_URL_AS(member)
                               )
            embed.set_footer(           
                icon_url=   GUILD_URL_AS(ctx.guild), 
                text=       f"{ctx.guild.name} | ID: {member.id}"
                            )

            embeds.append(embed)
            firstLoop = False
        
        #===== send each generated embed as it's own message
        for embed in embeds:
            await ctx.channel.send(embed=embed)

        return    

    @checks.ANY_STAFF()
    @commands.command(pass_context=True, hidden=False, name='roleperms', aliases=['RolePerms', 'rolePerms'])
    async def cmd_roleperms(self, ctx):
        """
        [All Staff] Gets all the perms for a role both default and channel overwrite. Does not accept member ID's or at-here mentions.

        Useage:
            [prefix]RolePerms <roleName/roleID/roleMention>
        """

        try: 
            role = None
            rolep = ctx.message.content.split(" ")[1]
            guild_roles =  sorted(ctx.guild.roles, key=lambda x: x.position)

            ###=== dealing with the @here mention
            if "here" in rolep.lower():
                pass

            ###=== dealing with the @everyone mention
            elif "everyone" in rolep.lower():
                role = ctx.guild.default_role

            ###=== IF ROLE PROVIDED IS AN ID OR A MENTION
            elif rolep.isdigit() or rolep.startswith("<@"):
                rolep = rolep.replace("<", "").replace("@", "").replace("!", "").replace(">", "")
                rolep = int(rolep)

                role = discord.utils.get(guild_roles, id = rolep)

            ###=== IF ROLE PROVIDED IS A NAME
            elif rolep in [role.name for role in guild_roles]:
                role = [role for role in guild_roles if role.name == rolep][0]

            ###==== IF PROVIDED INFORMATION IS INVALID OR ROLE NOT FOUND
            if role is None:
                raise ValueError

        except (IndexError, ValueError):
            await ctx.send_help('roleperms')
            return

        ###===== If role as Admin perms end function early
        if role.permissions.administrator:
            embed = discord.Embed(  
                title=      "Administrator",
                description="{} role has Admin permission and can do everything.".format(role.name),
                colour=     RANDOM_DISCORD_COLOR,
                type=       "rich",
                timestamp=  datetime.datetime.utcnow()
                                 )

            embed.set_author(       
                name=       "{} Information".format(role.name),
                icon_url=   AVATAR_URL_AS(self.bot.user)
                            )

            embed.set_footer(       
                icon_url=   GUILD_URL_AS(ctx.guild),
                text=       ctx.guild.name
                            )

            await ctx.channel.send(embed=embed)
            return

        ###===== Variable setup
        server_wide_perms = list()
        channel_specific_perms = list()
        embeds = list()

        ###===== server wide
        for i in range(31):
            if bool((role.permissions.value >> i) & 1):
                server_wide_perms.append(self.raw_perms[i].replace("_", " ").title())

        #===== channel
        """
            Getting the channel perms for the role sorted.
            The channels are sorted by position for readability of results. 
            Normally they are sorted by position anyway but sometimes they come back in a mess of an order.
            """
        for channel in sorted(ctx.guild.channels, key=lambda x: x.position):
            temp = list()
            channelPerms = channel.overwrites_for(role)

            for i in range(31):
                if not self.raw_perms[i] == "":
                    #Making sure voice channels are not checked for buggy text channel perms
                    if (channel.type == discord.ChannelType.voice) and (self.raw_perms[i] in ["read_messages", "send_messages"]):
                        continue

                    #Making sure text channels are not checked for voice channel perms
                    if (channel.type == discord.ChannelType.text) and (self.raw_perms[i] in ["speak", "connect", "mute_members", "deafen_members", "move_members", "use_voice_activation", "stream"]):
                        continue

                    """
                        Channel overwrite perms do not have a value unlike regular permissions.
                        So it's easier to feed the "_values.get()" function a perm you're looking for than to try and retrive a value you can use yourself.
                        Technically I could have looped through 27*2 if statements but this is cleaner. 
                        """
                    result = channelPerms._values.get(self.raw_perms[i])

                    if result == True:
                        temp.append(self.raw_perms[i].replace("_", " ").title())

                    elif result == False:
                        temp.append(("Not {}".format(self.raw_perms[i].replace("_", " ").title())))
            
            #=== If at end of loop no perms where found, log nothing.
            if len(temp) > 0:
                channel_specific_perms.append(dict(channelName=channel.name,
                                                    perms=temp,
                                                    channelType=channel.type.__str__()))


        #===== results, processing them into an actual reply
        #You can only have 25 fields in a discord embed. So I'm breaking up my list of possible fields into a 2d array.
        channel_specific_perms = await self.split_list(channel_specific_perms, size=25)
        firstLoop = True

        for channelSpecificPerms in channel_specific_perms:
            
            #=== Set up the first embed
            if firstLoop:
                text = " | ".join(server_wide_perms)
                if text == "":
                    text = "None"

                embed = discord.Embed(  
                    title=      "Server Wide:",
                    description="{}\n".format(text),
                    colour=     0x51B5CC,
                    timestamp=  datetime.datetime.utcnow(),
                    type=       "rich"
                                     )

                embed.set_author(      
                    name=       "{} Information".format(role.name),
                    icon_url=   AVATAR_URL_AS(self.bot.user)
                                )

            #=== Set up additional embeds
            else:
                embed = discord.Embed(  
                    description="",
                    colour=     0x51B5CC,
                    timestamp=  datetime.datetime.utcnow(),
                    type=       "rich"
                                     )

                embed.set_author(       
                    name=       "{} information continued".format(role.name),
                    icon_url=   AVATAR_URL_AS(self.bot.user)
                                )

            for i in channelSpecificPerms:
                #= The category channel type does not have a name, instead it's called "4"
                embed.add_field(        name=       i["channelName"] + (":" if not i["channelType"] == "4" else " - Category:"),
                                        value=      " | ".join(i["perms"]),
                                        inline=     False
                                )

            embed.set_footer(           
                icon_url=   GUILD_URL_AS(ctx.guild), 
                text=       ctx.guild.name
                            )

            embeds.append(embed)
            firstLoop = False
        
        #===== send each generated embed as it's own message
        for embed in embeds:
            await ctx.channel.send(embed=embed)

        return

    @checks.GUILD_OWNER()
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

    @checks.HIGH_STAFF() #new
    @commands.command(pass_context=True, hidden=False, name='banbyid', aliases=[])
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
    
    @checks.GUILD_OWNER()
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
    
    @checks.GUILD_OWNER()
    @commands.command(hidden=True)
    async def load(self, ctx, *, module):
        """Loads a module."""
        try:
            self.bot.load_extension(module)
        except commands.ExtensionError as e:
            await ctx.send(f'{e.__class__.__name__}: {e}')
        else:
            await ctx.send('\N{OK HAND SIGN}')

    @checks.GUILD_OWNER()
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

    @checks.GUILD_OWNER()
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

