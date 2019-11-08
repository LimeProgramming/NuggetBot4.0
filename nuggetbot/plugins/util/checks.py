import datetime
from discord import Embed
from functools import wraps
from discord.ext import commands
from nuggetbot.util.chat_formatting import GUILD_URL_AS, AVATAR_URL_AS, RANDOM_DISCORD_COLOR
from nuggetbot.config import Config

config = Config()




##Staff role decor | Bastion or Minister or user with admin perm
def GUILD_OWNER(*args):

    async def pred(ctx):
        if not ctx or not ctx.guild:
            return False   

        if ctx.guild.owner == ctx.author:
            return True

        else:
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

            await ctx.channel.send(embed=embed)
            return False

    return commands.check(pred)


def IS_HIGHEST_STAFF(*args):
    async def pred(ctx):
        if not ctx or not ctx.guild:
            return False   

        if  (   (any(role.id == config.roles["admin"] for role in ctx.author.roles))
            or  (__admin_or_botowner(ctx))
            ):

            return True

        else:
            await ctx.channel.send(content="`You lack the permissions to run this command.`", delete_after=15)
            return False

    return commands.check(pred)


###########################################################################################
###------------------------------ SOME CLEANUP FUNCTIONS -------------------------------###
###########################################################################################
def __admin_or_botowner(ctx):
    return bool(    (ctx.author.guild_permissions.administrator)    
                or  (ctx.author.id == config.owner_id)
    )