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

import sys
import json
import random
import dblogin 
import discord
import asyncio
import asyncpg
import datetime
from typing import Union
from discord.ext import commands

from nuggetbot import exceptions
from nuggetbot.config import Config
from nuggetbot.util import gen_embed as GenEmbed
from nuggetbot.utils import get_next
from nuggetbot.database import DatabaseCmds as pgCmds
from nuggetbot.util.chat_formatting import RANDOM_DISCORD_COLOR, GUILD_URL_AS, AVATAR_URL_AS

from .util import checks, cogset

class SelfRoles(commands.Cog):
    """Make Roles Self assignable via reactions."""

    config = None 
    delete_after = 15
    
    def __init__(self, bot):
        self.emojiname =        [':zero:', ':one:', ':two:', ':three:', ':four:', ':five:', ':six:', ':seven:', ':eight:', ':nine:', ':keycap_ten:', ':arrow_up:', ':arrow_right:', ':arrow_down:', ':arrow_left:']
        self.emojistring =      ['0️⃣', '1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣', '🔟', '⬆️', '➡️', '⬇️', '⬅️']
        self.bot = bot
        self.cogset = dict()
        SelfRoles.config = Config()

  # -------------------- LOCAL COG STUFF --------------------

    @asyncio.coroutine
    async def cog_command_error(self, ctx, error):
        if isinstance(error, discord.ext.commands.errors.NotOwner):
            try:
                owner = (self.bot.application_info()).owner
            except:
                owner = self.bot.get_guild(self.bot.config.target_guild_id).owner()

            await ctx.channel.send(content=f"```diff\n- {ctx.prefix}{ctx.invoked_with} is an owner only command, this will be reported to {owner.name}.")
            await owner.send(content=f"{ctx.author.mention} tried to use the owner only command{ctx.invoked_with}")
            return 

        if isinstance(error, discord.ext.commands.errors.CheckFailure):
            print(error)
            pass

        if self.bot.config.delete_invoking:
            try:
                await ctx.message.delete()
            except (discord.errors.NotFound, discord.errors.Forbidden): pass

    @asyncio.coroutine
    async def cog_before_invoke(self, ctx):
        await ctx.channel.trigger_typing()
        return

    @asyncio.coroutine
    async def cog_after_invoke(self, ctx):
        if self.bot.config.delete_invoking:
            try:
                await ctx.message.delete()
            except (discord.errors.NotFound, discord.errors.Forbidden): pass
        
        return


  # -------------------- LISTENERS --------------------
    @commands.Cog.listener()
    async def on_ready(self): 

      # ---------- LOADS THE COGSET ----------
        self.cogset = await cogset.LOAD(self.qualified_name)
        if not self.cogset:
            self.cogset= dict(
                keys = dict(),
                retmsgs = dict(),
                selfroles = []
            )

            await cogset.SAVE(self.cogset, cogname=self.qualified_name)

            await self.post_name_colours_msg()

            return


      # ---------- GET THE ROLES CHANNEL ----------
        try:
            roles_channel = await self.bot.fetch_channel(SelfRoles.config.roles_channel_id)

        except discord.errors.InvalidData:
            raise exceptions.PostAsWebhook(
                f'Could not fetch the self assign roles channel <#{SelfRoles.config.roles_channel_id}>. An unknown channel type was received from Discord.', 
                preface=f"```diff\n- An error has occured in {self.qualified_name}\n```")

        except discord.errors.NotFound:
            raise exceptions.PostAsWebhook(
                f'Could not fetch the self assign roles channel <#{SelfRoles.config.roles_channel_id}>. Invalid Channel ID.', 
                preface=f"```diff\n- An error has occured in {self.qualified_name}\n```")

        except discord.errors.Forbidden:
            raise exceptions.PostAsWebhook(
                f'Could not fetch the self assign roles channel <#{SelfRoles.config.roles_channel_id}>. I lack permissions to access that channel', 
                preface=f"```diff\n- An error has occured in {self.qualified_name}\n```")

        except discord.errors.HTTPException:
            raise exceptions.PostAsWebhook(
                f'Could not fetch the self assign roles channel <#{SelfRoles.config.roles_channel_id}>. Generic HTTP error.', 
                preface=f"```diff\n- An error has occured in {self.qualified_name}\n```")


      # ---------- CHECK FOR CHANGES IN MESSAGES ----------
        for i in self.cogset['retmsgs'].keys():

            try:
                msg = await roles_channel.fetch_message(i)

            except discord.errors.NotFound:
                # = IF THE MESSAGE HAS BEEN DELETED, REMOVE MENTION OF IT FROM THE COGSET AND RE-RUN THE APPROPIATE FUNCTION TO RE-CREATE IT.
                if self.cogset['retmsgs'][i] == 'name_color':
                    await self.post_name_colours_msg()

                del self.cogset['retmsgs'][i]
                del self.cogset['keys'][i]

                continue

            except discord.errors.Forbidden:
                # = IF THERE IS SOME ERROR WITH PERMISSIONS
                raise exceptions.PostAsWebhook(                
                    f'Could not fetch a required message for self assaignable roles https://discordapp.com/channels/{roles_channel.guild.id}/{roles_channel.id}/{i} I lack permissions to access that channel **or** read message history.', 
                    preface=f"```diff\n- An error has occured in {self.qualified_name}\n```")
            
            except discord.errors.HTTPException:
                # = IF THERE IS SOME SILLY ERROR
                raise exceptions.PostAsWebhook(                
                    f'Could not fetch a required message for self assaignable roles https://discordapp.com/channels/{roles_channel.guild.id}/{roles_channel.id}/{i} – Retrieving the message failed.', 
                    preface=f"```diff\n- An error has occured in {self.qualified_name}\n```")

        await cogset.SAVE(self.cogset, cogname=self.qualified_name)
            

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        """
        This function will take care of self assign roles via reactions.
        We are using the "raw" variant of the reaction add event because the self assign roles message may not be cached in the bots memory.


        Since this is one of the critical functions of the bot I'm reporting all the possible errors so that they can be addressed.
        """

      # ---------- IGNORE ----------
        if not payload.guild_id: return # REACTIONS FROM DM'S

        if payload.message_id not in self.cogset['retmsgs'].keys(): return # IRRELIVANT MESSAGES

        if payload.user_id == self.bot.user.id: return # REACTIONS FROM BOT

      # ---------- GET NEEDED VARIABLES ----------
        guild = self.bot.get_guild(payload.guild_id) # Get the guild

        rolesCHL = guild.get_channel(payload.channel_id) # Get the channel

        rolesMSG = await rolesCHL.fetch_message(payload.message_id) # Get the Message Object

        member = guild.get_member(payload.user_id) # Get reacter as a Member Object

        # ===== IF MEMBER SOMEHOW LEFT IMMIDATELY AFTER REACTING
        if not member:
            await self.remove_user_reactions(msg = rolesMSG)
            return

        # ===== GET THE ROLE
        try:
            role = discord.utils.get(guild.roles, id=self.cogset['keys'][payload.message_id][payload.emoji.name])
        except KeyError:
            await self.remove_user_reactions(msg = rolesMSG, member = member)
            return 

      # ---------- APPLY THE ROLE ----------    
        await getattr(self, self.cogset['retmsgs'][payload.message_id])(member, role, guild, payload)

      # ---------- HANDLE RELATED ROLES ----------
        await self.remove_user_reactions(msg = rolesMSG, member = member)

    @commands.Cog.listener()
    async def on_raw_message_delete(self, payload):
        if payload.message_id not in self.cogset['retmsgs'].keys(): return 

        missing_func = self.cogset['retmsgs'][payload.message_id]
        owner = await self.bot._get_owner()

        if missing_func == 'name_color':
            await owner.send("Name colour message has been deleted.")
        
        elif missing_func == 'self_roles':
            await owner.send("Self assignable roles message has been deleted.")

        else:
            await owner.send(f"Function message {missing_func} has been deleted.")

        del self.cogset['retmsgs'][payload.message_id]
        del self.cogset['keys'][payload.message_id]
        return
        


  # -------------------- FUNCTIONS --------------------

    async def remove_user_reactions(self, msg, member = None, all=False):
        '''
        Removes member's reaction from msg

        Parameters
        ------------
        msg :class:`discord.Message`
            The message you want to remove reactions from.
        member :class:`discord.Member`
            Members whose reactions you are removing.
        '''
        
        for reaction in msg.reactions:

            if member is None or all:
                for user in await reaction.users().flatten():
                    if user == self.bot.user and not all: continue

                    await reaction.remove(user)
                    await asyncio.sleep(0.2)  

            else:
                if reaction.count == 1 and reaction.me: continue

                try:
                    await reaction.remove(member)
                    await asyncio.sleep(0.2)

                except discord.errors.NotFound:
                    pass
        return 

    async def post_name_colours_msg(self):
        # ===== VARIABLE SETUP
        guild =         self.bot.get_guild(SelfRoles.config.target_guild_id)
        dest_channel =  discord.utils.get(guild.channels, id=SelfRoles.config.roles_channel_id)
        nc_roles =      [role for role in guild.roles if role.id in SelfRoles.config.name_colors]
        emojin =        [':zero:', ':one:', ':two:', ':three:', ':four:', ':five:', ':six:', ':seven:', ':eight:', ':nine:', ':keycap_ten:', ':arrow_up:', ':arrow_right:', ':arrow_down:', ':arrow_left:']
        emojis =        ['0️⃣', '1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣', '🔟', '⬆️', '➡️', '⬇️', '⬅️']
        desc =          'Add a reaction to set your name colour!\n\n'
        key =           dict()
        rkey=           dict()

        # ===== BUILD THE EMBED DESCRIPTION
        for i, role in enumerate(nc_roles):
            desc = f'{desc}{emojin[i]} - for {role.name}\n'
            key[emojis[i]] = role.id
            rkey[role.id] = emojis[i]

        # ===== BUILD THE EMBED
        e = discord.Embed(
            title=      "Set Name Colour",
            description=desc,
            colour=     RANDOM_DISCORD_COLOR(),
            type=       "rich",
            timestamp=  datetime.datetime.utcnow()
            )

        e.set_footer(       
            icon_url=   GUILD_URL_AS(guild), 
            text=       "{0.name}".format(guild)
            )

        # ===== SEND THE MESSAGE
        msg = await self.bot.send_msg(dest_channel, embed=e)

        # ===== ADD REACTIONS
        for i in nc_roles:
            await msg.add_reaction(rkey[i.id])
            await asyncio.sleep(0.4)

        # ===== SAVE MSG ID AND EMOJI KEY
        self.cogset['keys'][msg.id]     = key
        self.cogset['retmsgs'][msg.id]  = 'name_color'
        
        await cogset.SAVE(self.cogset, cogname=self.qualified_name)

        return

    async def gen_self_roles_msg(self, guild):
        key =           dict()
        rkey=           dict()
        desc =          'Add a reaction to **toggle** your self assinable roles!\n\n'
        self_roles =    [role for role in guild.roles if role.id in self.cogset['selfroles']]
                
        # ===== BUILD THE EMBED DESCRIPTION
        for i, role in enumerate(self_roles):
            desc = f'{desc}{self.emojiname[i]} - for {role.name}\n'
            key[self.emojistring[i]] = role.id
            rkey[role.id] = self.emojistring[i]

        # ===== BUILD THE EMBED
        e = discord.Embed(
            title=          "Set Name Colour", 
            description=    desc, 
            colour=         RANDOM_DISCORD_COLOR(), 
            type=           "rich", 
            timestamp=      datetime.datetime.utcnow()
            )
        e.set_footer(
            icon_url=       GUILD_URL_AS(guild), 
            text=           guild.name
            )

        return (e, key, rkey, self_roles)

    async def update_self_roles_msg(self, guild):
        channel =  discord.utils.get(guild.channels, id=self.bot.config.roles_channel_id)
        msg_id = {v: k for k, v in self.cogset['retmsgs'].items()}['self_roles']
        self_roles_msg = await channel.fetch_message(msg_id)

        e, key, rkey, self_roles = await self.gen_self_roles_msg(guild)

        # ===== Clear all old reactions
        await self.remove_user_reactions(self_roles_msg, all=True)

        # ===== Update the message
        await self_roles_msg.edit(embed=e)

        # ===== ADD REACTIONS
        for i in self_roles:
            await self_roles_msg.add_reaction(rkey[i.id])
            await asyncio.sleep(0.4)

  # -------------------- Commands --------------------
    @checks.HIGHEST_STAFF()
    @commands.command(pass_context=True, hidden=False, name='PostSelfAssign', aliases=[])
    async def cmd_post_self_roles_msg(self, ctx):
        """
        [Administrator] Post the self assignable roles message.
        """
        dest_channel =  discord.utils.get(ctx.guild.channels, id=self.bot.config.roles_channel_id)

        e, key, rkey, self_roles = await self.gen_self_roles_msg(ctx.guild)

        # ===== SEND THE MESSAGE
        msg = await self.bot.send_msg(dest_channel, embed=e)

        # ===== ADD REACTIONS
        for i in self_roles:
            await msg.add_reaction(rkey[i.id])
            await asyncio.sleep(0.4)

        # ===== SAVE MSG ID AND EMOJI KEY
        self.cogset['keys'][msg.id]     =   key
        self.cogset['retmsgs'][msg.id]  =   'self_roles'
        
        await cogset.SAVE(self.cogset, cogname=self.qualified_name)

        return

    @commands.group(pass_context=True, name='selfassign', case_insensitive=True)
    async def cmd_selfassign(self, ctx):
        """Handles the self assignable roles."""

        if ctx.invoked_subcommand is None:
            await ctx.send_help('selfassign')


    @cmd_selfassign.group(pass_context=True, name="allow", aliases=['add'], invoke_without_command=True, case_insensitive=True)
    @checks.HIGHEST_STAFF()
    async def grp_allow(self, ctx, role: discord.Role = None):
        """Add a role to list of self assignable roles."""

        # ===== If no role has been provided.
        if role is None:
            await ctx.send_help('selfassign')
            return
        
        # ===== If role is already self assignable
        if role.id in self.cogset['selfroles']:
            await ctx.send(f"Role <@&{role.id}> is already self assignable.")
            return 
    
        self.cogset['selfroles'].append(role.id)
        await cogset.SAVE(self.cogset, cogname=self.qualified_name)
        await ctx.send(f"Role <@&{role.id}> is now self assignable, please repost/update the self assignable roles message for changes to take effect.")
        return

    @cmd_selfassign.group(pass_context=True, name="remove", aliases=['delete'], invoke_without_command=True, case_insensitive=True)
    @checks.HIGHEST_STAFF()
    async def grp_remove(self, ctx, role: discord.Role = None ):
        """Remove a role from list of self assignable roles."""

        # ===== If no role has been provided.
        if role is None:
            await ctx.send_help('selfassign')
            return

        # ===== If role is already allowed.
        if role.id not in self.cogset['selfroles']:
            await ctx.send(f"Role <@&{role.id}> is wasn't self assignable.")
            return 

        self.cogset['selfroles'].remove(role.id)
        await cogset.SAVE(self.cogset, cogname=self.qualified_name)
        await ctx.send(f"Role <@&{role.id}> is no longer self assignable, please repost/update the self assignable roles message for changes to take effect.")

    @cmd_selfassign.group(pass_context=True, name="list", aliases=[], invoke_without_command=True, case_insensitive=True)
    @checks.HIGHEST_STAFF()
    async def grp_list(self, ctx):
        """List all self assignable roles."""

        self_roles =    [role for role in ctx.guild.roles if role.id in self.cogset['selfroles']]

        desc = "\n".join((f"> {role.name}" for role in self_roles))
        desc += f"\nTotal number of self assignable roles {len(self_roles)}."

        e = discord.Embed(
            title=          "List of Self Assignable Roles", 
            description=    desc, 
            colour=         RANDOM_DISCORD_COLOR(), 
            type=           "rich", 
            timestamp=      datetime.datetime.utcnow()
            )
        e.set_footer(
            icon_url=       GUILD_URL_AS(ctx.guild), 
            text=           ctx.guild.name
            )
        
        await self.bot.send_msg(dest=ctx.channel, embed=e)
        return

  # -------------------- Reaction Functions --------------------
    async def name_color(self, member, role, guild, payload):

        try:
            await member.add_roles(role, reason="Apply new name color.")

        except discord.errors.Forbidden:
            raise exceptions.PostAsWebhook(                
                f'Exception in on_raw_reaction_add\nAdding role {role.name} failed, I do not have permissions to add these roles.', 
                preface=f"```diff\n- An error has occured in {self.qualified_name}\n```") 

        # ===== REMOVE OTHER NAME COLOR ROLES
        for rrole in guild.roles:
            if rrole.id in [i[1] for i in self.cogset['keys'][payload.message_id].items()] and rrole != role:

                try:
                    await member.remove_roles(rrole, reason='Removing old name color.')
                    await asyncio.sleep(0.2)

                except discord.errors.NotFound:
                    pass
        return

    async def self_roles(self, member, role, guild, payload):
        if role.id not in self.cogset['selfroles']:
            return

        if role in member.roles:
            await member.remove_roles(role, reason="Remove self assignable role.")
            msg = f"You've had the role \"{role.name}\" removed on {guild.name}."
        
        else:
            await member.add_roles(role, reason="Apply self assignable role.")
            msg = f"You've been given the role \"{role.name}\" on {guild.name}."

        await member.send(msg)
        return
        




def setup(bot):
    bot.add_cog(SelfRoles(bot))