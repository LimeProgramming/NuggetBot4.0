import datetime
from discord import Embed
from functools import wraps
from discord.ext import commands
from nuggetbot.util.chat_formatting import GUILD_URL_AS, AVATAR_URL_AS, RANDOM_DISCORD_COLOR
from nuggetbot.config import Config

config = Config()


###########################################################################################
###-------------------------------- COMMAND DECORATORS ---------------------------------###
###########################################################################################

##Permissions decor | guild owner only
def GUILD_OWNER(*args):
    async def pred(ctx):
        if not ctx or not ctx.guild:
            return False   

        if ctx.guild.owner == ctx.author:
            return True

        else:
            await ctx.channel.send(embed=await __gen_guildowner_embed(ctx))
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


###########################################################################################
###------------------------------ SOME CLEANUP FUNCTIONS -------------------------------###
###########################################################################################

async def __gen_guildowner_embed(ctx):
    embed = Embed(  
        title=      ':warning: You do not own this guild',
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
        value=      f"```\nYou are not the owner of this guild, contact {ctx.guild.owner.name}#{ctx.guild.owner.discriminator} if a command needs to be preformed.\n```",
        inline=     False
        )
    
    return embed

async def __gen_guildstaff_embed(ctx, roles):
    if isinstance(roles, list):
        rroles = " ".join(roles)
    else:
        rroles = roles 

    embed = Embed(  
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

