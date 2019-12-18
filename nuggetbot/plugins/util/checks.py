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

import discord
import datetime
from functools import wraps
from discord.ext import commands
from collections.abc import Iterable
from nuggetbot.util.chat_formatting import GUILD_URL_AS, AVATAR_URL_AS, RANDOM_DISCORD_COLOR
from nuggetbot.config import Config

config = Config()


###########################################################################################
###-------------------------------- COMMAND DECORATORS ---------------------------------###
###########################################################################################

def CHANNEL(ch_id_names):
    """
    Decorator for bot commands. Invoking msg must be sent in the channel/s provided
    Channel Limitations are overwritten if author is Staff | Admin | Guild Owner | Bot Owner 

    Args:
        (str)       Channel name
        (int)       Channel ID
        (Iterable)  Can be a mix of names and ids

    Returns:
        (bool)
    """
    def inner(func):
        
        @wraps(func)
        async def pred(ctx):
            ### ---------- BLOCK DM'S OR ERRORS ---------- ###
            if not ctx or not ctx.guild:
                return False 

            ### ---------- SOME HALF BAKED RESOLVER ---------- ###
            res = False 

            if not isinstance(ch_id_names, Iterable):
                ch_id_names = [ch_id_names]

            for i in ch_id_names:
                #-  IF CHANNEL ID WAS SUPPLIED 
                if isinstance(i, int):
                    res = bool(ctx.channel.id == i or res)

                #-  IF CHANNEL NAME WAS SUPPLIED   
                elif  isinstance(i, str):
                    res = bool(ctx.channel.name == i or res)  

                #-  EXIT LOOP IF RET IS TRUE
                if res:
                    break

            ### ---------- SOME IF STATEMENTS ---------- ###
            return bool (   (res) 
                        or  (any(role.id in config.roles["any_staff"] for role in ctx.author.roles))
                        or __admin_or_bgowner(ctx)
                        )
        return pred

    return commands.check(inner)

#MSG author must have a certain role or user with admin perm
def HAS_ROLE(role_id_names):
    """
    Decorator for bot commands. MSG author must have one or more of the role/s provided.
    Role Limitations are overwritten if author is Staff | Admin | Guild Owner | Bot Owner 

    Args:
        (str)       Role name
        (int)       Role ID
        (Iterable)  Can be a mix of names and ids

    Returns:
        (bool)
    """
    def inner(func):

        @wraps(func)
        async def pred(ctx):
            ### ---------- BLOCK DM'S OR ERRORS ---------- ###
            if not ctx or not ctx.guild:
                return False 

            ### ---------- SOME HALF BAKED RESOLVER ---------- ###
            res = False 

            if not isinstance(role_id_names, Iterable):
                role_id_names = [role_id_names]

            for i in role_id_names:
                #-  IF Role ID WAS SUPPLIED 
                if isinstance(i, int):
                    res = bool(any(role.id == i for role in ctx.author.roles) or res)

                #-  IF Role NAME WAS SUPPLIED   
                elif  isinstance(i, str):
                    res = bool(any(role.name == i for role in ctx.author.roles) or res)

                #-  EXIT LOOP IF RET IS TRUE
                if res:
                    break

            ### ---------- SOME IF STATEMENTS ---------- ###
            return bool (   (res)
                        or  (any(role.id in config.roles["any_staff"] for role in ctx.author.roles))
                        or __admin_or_bgowner(ctx)
                        )
        
        return pred

    return commands.check(inner)

### LOCK COMMANDS TO THE RECEPTION CHANNEL
def RECEPTION(*args):
    
    async def pred(ctx):
        if not ctx or not ctx.guild:
            return False 

        if  (  (ctx.channel.id == config.channels["reception_id"]) 
            or (any(role.id in config.roles["any_staff"] for role in ctx.author.roles))
            or (__admin_or_bgowner(ctx))
            ):
            return True

        else:
            await ctx.author.send(embed=await __gen_recep_embed(ctx, config.channels["reception_id"]), delete_after=30)
            return False

    return commands.check(pred)

### IF USER HAS CORE ROLE OR STAFF OR ADMIN 
def CORE(*args):
    async def pred(ctx):
        if not ctx or not ctx.guild:
            return False 

        if  (   (any(role.id in config.roles["user_staff"] for role in ctx.author.roles)) 
            or  (__admin_or_bgowner(ctx))
            ):
            return True 
        
        else:
            await ctx.channel.send(embed=await __gen_nocore_embed(ctx), delete_after=30)
            return False

    return commands.check(pred)

def GATED(*args):
    async def pred(ctx):
        if not ctx or not ctx.guild:
            return False 

        return bool (   (any(role.id == config.roles['gated'] for role in ctx.author.roles)) 
                    or  (__admin_or_bgowner(ctx))
                    )

    return commands.check(pred)

# -------------------- STAFF DECORS --------------------
##Permissions decor | guild owner only
def GUILD_OWNER(*args):
    async def pred(ctx):
        if not ctx or not ctx.guild:
            return False   

        if ctx.guild.owner == ctx.author:
            return True

        else:
            await ctx.channel.send(embed=await __gen_guildowner_embed(ctx), delete_after=30)
            return False

    return commands.check(pred)

##Staff role decor | Minister or user with admin perm
def HIGHEST_STAFF(*args):
    async def pred(ctx):
        if not ctx or not ctx.guild:
            return False   

        if  (   (any(role.id == config.roles["admin"] for role in ctx.author.roles))
            or  (__admin_or_bgowner(ctx))
            ):

            return True

        else:
            await ctx.channel.send(embed = __gen_guildstaff_embed(ctx, config.roles["admin"]), delete_after=30)
            return False

    return commands.check(pred)

##Staff role decor | Bastion or Minister or user with admin perm
def HIGH_STAFF(*args):

    async def pred(ctx):
        if not ctx or not ctx.guild:
            return False   

        if  (   (any(role.id in config.roles["high_staff"] for role in ctx.author.roles))
            or __admin_or_bgowner(ctx)
            ):

            return True

        else:
            await ctx.channel.send(embed = await __gen_guildstaff_embed(ctx, config.roles["high_staff"]), delete_after=30)
            return False

    return commands.check(pred)

##Staff role decor | Support or Bastion or Minister or user with admin perm
def ANY_STAFF(*args):
    async def pred(ctx):
        if not ctx or not ctx.guild:
            return False   

        if  (   (any(role.id in config.roles["any_staff"] for role in ctx.author.roles))
            or __admin_or_bgowner(ctx)
            ):

            return True

        else:
            await ctx.channel.send(embed = await __gen_guildstaff_embed(ctx, config.roles["any_staff"]), delete_after=30)
            return False

    return commands.check(pred)

##Disables a bot command
def DISABLED(*args):
    return commands.check(False)

# -------------------- BOT OWNER DECORS --------------------
def BOT_OWNER(*args):
    async def pred(ctx):
        if not ctx or not ctx.guild:
            return False   

        if await ctx.bot.is_owner(ctx.author):
            return True

        else:
            await ctx.channel.send(embed=await __gen_botowner_embed(ctx), delete_after=30)
            return False

    return commands.check(pred)
    
##########################################################################################################
###-------------------------- COMMANDS.COMMAND WRAPPERS, DM CHANNELS ALLOWED --------------------------###
##########################################################################################################

#if user has core_role  or user with admin perm
def CORE_DM(*args):

    async def pred(ctx):
        if not ctx:
            return False 

        guild, invoker = __get_guild_and_invoker(ctx)

        return bool (   (any(role.id in config.roles["user_staff"] for role in invoker.roles))
                    or  (__admin_or_bgowner(ctx))
                    )

    return commands.check(pred)

def HIGHEST_STAFF_DM(*args):
    async def pred(ctx):
        if not ctx:
            return False   

        guild, invoker = __get_guild_and_invoker(ctx)

        if  (   (any(role.id in config.roles["admins"] for role in invoker.roles))
            or  (__admin_or_bgowner(ctx))
            ):

            return True

        else:    
            await ctx.channel.send(content="`You lack the permissions to run this command.`")
            return False

    return commands.check(pred)

##Staff role decor | Bastion or Minister or user with admin perm
def HIGH_STAFF_DM(*args):

    async def pred(ctx):
        if not ctx:
            return False   

        guild, invoker = __get_guild_and_invoker(ctx)

        if  (   (any(role.id in config.roles["high_staff"] for role in invoker.roles))
            or  (__admin_or_bgowner(ctx))
            ):

            return True

        else:
            await ctx.channel.send(content="`You lack the permissions to run this command.`")
            return False

    return commands.check(pred)

##Staff role decor | Support orBastion or Minister or user with admin perm
def ANY_STAFF_DM(*args):
    async def pred(ctx):
        if not ctx:
            return False   

        guild, invoker = __get_guild_and_invoker(ctx)

        if  (   (any(role.id in config.roles["any_staff"] for role in invoker.roles))
            or  (__admin_or_bgowner(ctx))
            ):

            return True

        else:
            await ctx.channel.send(content="`You lack the permissions to run this command.`")
            return False

    return commands.check(pred)


###########################################################################################
###------------------------------ SOME CLEANUP FUNCTIONS -------------------------------###
###########################################################################################

def __admin_or_botowner(ctx):
    return bool(    (ctx.author.guild_permissions.administrator)    
                or  (ctx.author.id == config.owner_id)
    )

def __admin_or_bgowner(ctx):
    return bool(    (ctx.author.guild_permissions.administrator)    
                or  (ctx.author == ctx.guild.owner)
                or  (ctx.author.id == config.owner_id)
    )

def __get_guild_and_invoker(ctx):
    guild = ctx.bot.get_guild(config.target_guild_id)
    invoker = guild.get_member(ctx.author.id)

    return guild, invoker


###########################################################################################
###--------------------------------- EMBED GENERATORS ----------------------------------###
###########################################################################################
async def __gen_recep_embed(ctx, ch_id):
    embed = discord.Embed(
        title=      ":exclamation: Unauthorized use of bot commands. :exclamation: ",
        description=f"Please keep use of bot commands within <#{ch_id}>\nThank You.",
        type=       'rich',
        timestamp=  datetime.datetime.utcnow(),
        color=      RANDOM_DISCORD_COLOR()
        )

    embed.set_footer(       
        icon_url=   GUILD_URL_AS(ctx.guild),
        text=       ctx.guild.name
        )
    
    return embed

async def __gen_nocore_embed(ctx):
    embed = discord.Embed(
        title=      ':wave: Welcome Newbie!',
        description="",
        type=       'rich',
        timestamp=  datetime.datetime.utcnow(),
        color=      RANDOM_DISCORD_COLOR()
        )
        
    embed.set_footer(       
        icon_url=   GUILD_URL_AS(ctx.guild),
        text=       ctx.guild.name
        )

    embed.add_field(    
        name=       "You can not use this command yet.",
        value=      f"You'll need to join the rest of our great guild first.",
        inline=     False
        )
    
    return embed

async def __gen_guildowner_embed(ctx):
    embed = discord.Embed(  
        title=      ':warning: You do not own this guild',
        description="",
        type=       'rich',
        timestamp=  datetime.datetime.utcnow(),
        color=      RANDOM_DISCORD_COLOR()
        )

    embed.set_footer(       
        icon_url=   GUILD_URL_AS(ctx.guild),
        text=       ctx.guild.name
        )
        
    embed.add_field(    
        name=       "Error:",
        value=      f"```\nYou are not the owner of this guild, contact {ctx.guild.owner.name}#{ctx.guild.owner.discriminator} if a command needs to be preformed.\n```",
        inline=     False
        )
    
    return embed

async def __gen_botowner_embed(ctx):
    embed = discord.Embed(  
        title=      ':warning: You do not own me.',
        description="",
        type=       'rich',
        timestamp=  datetime.datetime.utcnow(),
        color=      RANDOM_DISCORD_COLOR()
        )

    embed.set_footer(       
        icon_url=   GUILD_URL_AS(ctx.guild),
        text=       ctx.guild.name
        )
        
    embed.add_field(    
        name=       "Error:",
        value=      f"```\nOnly the bot owner can run {ctx.invoked_with}\n```",
        inline=     False
        )
    
    return embed


async def __gen_guildstaff_embed(ctx, roles):
    if isinstance(roles, list):
        rroles = " ".join(roles)
    else:
        rroles = roles 

    embed = discord.Embed(  
        title=      ':octagonal_sign: You lack the required permissions to preform this command :octagonal_sign:',
        description="",
        type=       'False',
        timestamp=  datetime.datetime.utcnow(),
        color=      RANDOM_DISCORD_COLOR()
        )

    embed.set_footer(       
        icon_url=   GUILD_URL_AS(ctx.guild),
        text=       ctx.guild.name
        )
        
    embed.add_field(    
        name=       "Error:",
        value=      "```\n"
                    "Suffcient permissions required for this command.\n"
                    f"You need one of the following roles: {rroles} **or** administrator permissions.\n"
                    f"If you require the use of this command to preform your duties, then contact {ctx.guild.owner.name}#{ctx.guild.owner.discriminator} for assistance.\n"
                    "```",
        inline=     False
        )
    
    return embed

