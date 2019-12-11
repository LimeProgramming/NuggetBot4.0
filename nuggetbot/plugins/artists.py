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
import discord
import asyncio
import asyncpg
import datetime
from discord.ext import commands

from .util import checks
from nuggetbot.config import Config
from nuggetbot.database import DatabaseCmds as pgCmds
from nuggetbot.util.chat_formatting import AVATAR_URL_AS, GUILD_URL_AS, RANDOM_DISCORD_COLOR

import dblogin 


class Artists(commands.Cog):
    """Some Commands for artists"""

    config = None 

    def __init__(self, bot):
        self.bot = bot
        Artists.config = Config()

    async def Response(self, ctx, content="", reply=True, delete_after=None, embed=None, tts=False):
        '''A Response handler, it's a lazy hold over from a much older version of NuggetBot'''

        if reply:
            await ctx.message.channel.send(content=content, tts=tts, embed=embed, delete_after=delete_after, nonce=None)

        await ctx.message.delete()

  #-------------------- STATIC METHODS --------------------
    @staticmethod
    async def _toggle_role(ctx, baseRoleID, delete_after=15, reason=None):
        '''Handler to toggle a guild members role'''

        baseRole = discord.utils.get(ctx.author.roles, id=baseRoleID)
        toggleAdd = not bool(baseRole)

        if toggleAdd:
            baseRole = discord.utils.get(ctx.guild.roles, id=baseRoleID)
            await ctx.author.add_roles(baseRole, reason=reason)

        else:
            await ctx.author.remove_roles(baseRole, reason=reason)

        await Artists._report_edited_roles(ctx, nsfwRole="N/A", isRoleAdded=toggleAdd, changedRoles=[baseRole.name], delete_after=delete_after, Archive=True)
        return

    @staticmethod
    async def _report_edited_roles(ctx, nsfwRole, isRoleAdded, changedRoles, delete_after=15, Archive=True):
        '''Reports edited roles to the user and to staff.'''

        embed = discord.Embed(  description=f"Mention: {ctx.author.mention}\n"
                                            f"Has NSFW Role: {nsfwRole}\n",
                                type=       "rich",
                                timestamp=  datetime.datetime.utcnow(),
                                colour=     (0x51B5CC if isRoleAdded else 0xCC1234)
                            )
        embed.set_author(       name=       "Roles updated",
                                icon_url=   AVATAR_URL_AS(ctx.author)
                        )

        log = ""
        logPrefix = ("+" if isRoleAdded else "-")

        for i, changedRole in enumerate(changedRoles):
            if i == 0:
                log += f"{logPrefix}{changedRole}"
            else:
                log += f"\n{logPrefix}{changedRole}"

        embed.add_field(        name=       ("Assigned Roles" if isRoleAdded else "Removed Roles"),
                                value=      log,
                                inline=     False
                        )
        embed.set_footer(       icon_url=   GUILD_URL_AS(ctx.guild), 
                                text=       ctx.guild.name
                        )

        await ctx.channel.send(content=None, embed=embed, delete_after=delete_after)

        if Archive:
            ch = discord.utils.get(ctx.guild.channels, id=Artists.config.channels['bot_log'])

            await ch.send(content=None, embed=embed)

        return

    @classmethod
    async def store_artist_info(cls, artist, info="Artist provided no info."):
        credentials = {"user": dblogin.user, "password": dblogin.pwrd, "database": dblogin.name, "host": dblogin.host}
        database = await asyncpg.create_pool(**credentials)
        await database.execute(pgCmds.UPDATE_ARTIST_INFO, int(artist.id), info)

        await database.close()

        return

    @classmethod
    async def get_artist_info(cls, list_of_artists):
        #===== Connect to the database and get the info from the artist_info table
        credentials = {"user": dblogin.user, "password": dblogin.pwrd, "database": dblogin.name, "host": dblogin.host}
        database = await asyncpg.create_pool(**credentials)
        artists_info = await database.fetch(pgCmds.GET_ALL_ARTIST_INFO)
        await database.close()

        embeds = list() 

        #===== Make the embeds to return
        for row in artists_info:
            for artist in list_of_artists:
                if row["user_id"] == artist.id:

                    embed = discord.Embed(  description=artist.mention,
                                            colour=     RANDOM_DISCORD_COLOR(),
                                            timestamp=  datetime.datetime.utcnow(),
                                            type=       "rich"
                                        )

                    embed.set_thumbnail(    url=        AVATAR_URL_AS(user=artist)
                                        )

                    embed.set_author(       name=       "{0.name}#{0.discriminator}".format(artist),
                                            icon_url=   AVATAR_URL_AS(user=artist)
                                    )

                    embed.set_footer(       icon_url=   GUILD_URL_AS(artist.guild), 
                                            text=       "{}".format(artist.guild.name)
                                    )

                    embed.add_field(        name=       "Infomation",
                                            value=      row["info"]
                                    )

                    embeds.append(embed)
        
        #===== if no artists found
        if len(embeds) == 0:

            embed = discord.Embed(  title="No artists available.",
                                    description="Sorry",
                                    colour=     RANDOM_DISCORD_COLOR(),
                                    timestamp=  datetime.datetime.utcnow(),
                                    type=       "rich"
                                )

            embeds.append(embed)

        return embeds


  #-------------------- COMMANDS --------------------
    #@has_role(["Artist"])
    #@in_channel([ChnlID.artistcorner, ChnlID.reception])
    @commands.command(pass_context=False, hidden=False, name='opencommissions', aliases=[])
    async def cmd_opencommissions(self, ctx):
        """
        [Artist] Artists can toggle the opencommissions role
        """
        await Artists._toggle_role(ctx=ctx, baseRoleID=Artists.config.art_roles['opencoms'], reason=Artists.config.art_reasons["Toggle Open Commissions"])
        await self.Response(ctx=ctx, reply=False)
        return

    #@has_role(["Artist"])
    #@in_channel([ChnlID.commissions, ChnlID.advertself, ChnlID.nsfwadvertself])
    @commands.command(pass_context=True, hidden=False, name='pingcommissioners', aliases=[])
    async def cmd_pingcommissioners(self, ctx):
        """
        [Artist] Artists can ping people with the commissioners role
        """

        commissionerRole = discord.utils.get(ctx.guild.roles, id=Artists.config.art_roles['commer'])

        await commissionerRole.edit(mentionable=True, reason=Artists.config.art_reasons["Commissioner_mentionable"])
        await ctx.channel.send(f"{commissionerRole.mention}")
        await asyncio.sleep(5)
        await commissionerRole.edit(mentionable=False, reason=Artists.config.art_reasons["Commissioner_mentionable"])

        await self.Response(ctx=ctx, reply=False)
        return 
    
    #@has_role(["Artist"])
    #@in_channel([ChnlID.reception, ChnlID.artistcorner])
    @commands.command(pass_context=True, hidden=False, name='artistregister', aliases=[])
    async def cmd_artistregister(self, ctx):
        """
        [Artist] <info> Allows an artist to register information about them for the find artists role
        """

        info = ctx.message.content[(len(Artists.config.command_prefix) + 14):].strip()

        if len(info) == 0:
            await self.Response(ctx=ctx, content="`Useage: [p]artistregister <information> [Artist] Artists can register their information.`", reply=True)
            return

        await Artists.store_artist_info(ctx.message.author, info)

        await self.Response(ctx=ctx, content="Your information has been added, thank you and goodluck.")     
        return

    #@is_core
    #@in_reception
    @commands.dm_only()
    @commands.command(pass_context=False, hidden=False, name='findartists', aliases=[])
    async def cmd_findartists(self, ctx):
        """
        [Core] DMs people info artists who have the open commissions role and registered if with bot.
        """

        guild = self.bot.get_guild(Artists.config.target_guild_id)
        commissionerRole = discord.utils.get(guild.roles, id=Artists.config.art_roles['opencoms'])
        openComs = [member for member in guild.members if commissionerRole in member.roles]

        embeds = await Artists.get_artist_info(openComs)

        for embed in embeds:
            await ctx.author.send(embed=embed)
            #await self.safe_send_message(msg.author, embed=embed)
            await asyncio.sleep(0.5)

        return



def setup(bot):
    bot.add_cog(Artists(bot))