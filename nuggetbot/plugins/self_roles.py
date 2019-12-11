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
        self.bot = bot
        self.cogset = dict()
        SelfRoles.config = Config()

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
        print('Ignoring exception in {}'.format(ctx.invoked_with), file=sys.stderr)
        print(error)

  # -------------------- LISTENERS --------------------
    @commands.Cog.listener()
    async def on_ready(self): 
      # ---------- LOADS THE COGSET ----------
        self.cogset = await cogset.LOAD(self.qualified_name)
        if not self.cogset:
            self.cogset= dict(
                keys = dict(),
                retmsgs = dict()
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
            

      # ---------- CHECK FOR CHANGES IN MESSAGES ----------
        # === GET NUGGETBOT AS A MEMBER
        #selfmember =  guild.get_member(self.bot.user.id)
        #if not selfmember:
        #    raise exceptions.Note(f'Could not find myself in {guild.name}')

        # === CHECK IF BOT CAN ACTUALLY GRANT THE ROLE
        #if selfmember.top_role.position <= role.position:
        #    raise exceptions.Note(f'Role {role.name} is higher or equal to my top_role so I cannot apply it anyone.')


    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        """
        This function will take care of self assign roles via reactions.
        We are using the "raw" variant of the reaction add event because the self assign roles message may not be cached in the bots memory.


        Since this is one of the critical functions of the bot I'm reporting all the possible errors so that they can be addressed.
        """

      # ---------- IGNORE ----------
        # ===== REACTIONS FROM DM'S
        if not payload.guild_id: return 

        # ===== IRRELIVANT MESSAGES
        if payload.message_id not in self.cogset['retmsgs'].keys(): return

        # ===== REACTIONS FROM BOT
        if payload.user_id == self.bot.user.id: return

      # ---------- GET NEEDED VARIABLES ----------
        # ===== THE GUILD
        guild = self.bot.get_guild(payload.guild_id)

        # ===== THE CHANNEL
        rolesCHL = guild.get_channel(payload.channel_id)

        # ===== THE MESSAGE
        rolesMSG = await rolesCHL.fetch_message(payload.message_id)

        # ===== THE REACTOR AS A MEMBER
        member = guild.get_member(payload.user_id)
        if not member:
            # === IF MEMBER SOMEHOW LEFT IMMIDATELY AFTER REACTING
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


        


  # -------------------- FUNCTIONS --------------------

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


    async def remove_user_reactions(self, msg, member = None):
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

            if member is None:
                for user in await reaction.users().flatten():
                    if user == self.bot.user: continue

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

def setup(bot):
    bot.add_cog(SelfRoles(bot))