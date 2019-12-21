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
import asyncio
import discord
import datetime
from discord.ext import commands

from nuggetbot.util.chat_formatting import RANDOM_DISCORD_COLOR, GUILD_URL_AS, AVATAR_URL_AS, escape
from .util import checks

class Help(commands.Cog):
    '''
    Replacement help commands
    '''
    
    config = None

    def __init__(self, bot):
        self.bot = bot

  #-------------------- LOCAL COG STUFF --------------------      
    async def cog_after_invoke(self, ctx):
        '''THIS IS CALLED AFTER EVERY COG COMMAND, IT DISCONNECTS FROM THE DATABASE AND DELETES INVOKING MESSAGE IF SET TO.'''

        if ctx.message.guild and self.bot.config.delete_invoking:
            await ctx.message.delete()

        return
    
    @asyncio.coroutine
    async def cog_command_error(self, ctx, error):
        print('Ignoring exception in {}'.format(ctx.invoked_with), file=sys.stderr)
        print(error)


  #-------------------- COMMANDS --------------------   
    @checks.BotTester()
    @commands.command(pass_context=True, hidden=False, name='adminhelp', aliases=['bossHelp'])
    async def cmd_adminhelp(self, ctx):
        """
        [Bot Tester] Shows the full list of bot commands.
        """

        command = ctx.message.content[(len(ctx.prefix) + len(ctx.invoked_with)):]

        if command:
            await ctx.send_help(command)

        else:
            await ctx.send_help() 

        return

    @checks.CORE()
    @checks.RECEPTION()
    @commands.command(pass_context=True, hidden=False, name='nuggethelp', aliases=[])
    async def nuggethelp(self, ctx):
        """
        [Core] Prints a help message for the users

        Useage:
            [prefix]NuggetHelp/Help
        """

        embed = discord.Embed(  
            title=      "Self Assignable Roles:",
            description="**SFW Roles:**\n"
                        f"{ctx.prefix}NotifyMe:\tA role that we use to ping people about goings on.\n"
                        f"{ctx.prefix}Book_Wyrm:\tUsed to access <#304365533619421184> text and voice channels.\n"
                        f"{ctx.prefix}RP:\tUsed to access the SFW RP channels.\n"
                        f"{ctx.prefix}Artist:\tArtists who are open to commissions. Plus gain write permissions in <#382167213521633280>\n"
                        "\n"
                        "**NSFW Roles (NSFW Role required):**\n"
                        f"{ctx.prefix}RP_Lewd:\tUsed to access the NSFW RP channels.\n"
                        "\n",
            type=       "rich",
            timestamp=  datetime.datetime.utcnow(),
            colour=     RANDOM_DISCORD_COLOR()
            )

        embed.set_author(   
            name=   "Nugget Help",
            icon_url=AVATAR_URL_AS(self.bot.user)
            )

        embed.add_field(    
            name=   "NSFW Access",
            value=  f"To get access to the NSFW channels just ping staff in <#{self.bot.config.channels['reception_id']}> with your age.",
            inline= False
            )

        embed.add_field(    
            name=   "Private Feedback:",
            value=  f"You can always DM me {self.bot.user.mention} with {self.bot.command_prefix}feedback followed by your feedback for the staff.\nFeedback can be submitted anonymously this way.",
            inline= False
            )
        
        embed.add_field(    
            name=   "Fun Commands:",
            value=  f"{ctx.prefix}RPS <rock/paper/scissors>:\tPlay rock paper scissors with me.\n"
                    f"{ctx.prefix}8ball <question>:\tAsk your question and I shall consult the ball of knowledge.\n"
                    f"{ctx.prefix}Roll <number>:\tRole a dice, you tell me how high I can go.\n"
                    f"{ctx.prefix}Leaderboard:\tTop 10 most popular, I hope I'm on that list.\n",
            inline= False
            )
        
        embed.add_field(    
            name=   "Art and Commissions:",
            value=  
                    f"{ctx.prefix}Commissioner:\tAdds commissioner role, meant for people looking for commissions.\n"
                    f"{ctx.prefix}FindArtists:\tDMs you info about any artist who have registered with us.\n"
                    f"{ctx.prefix}OpenCommissions:\tAdds OpenCommissions role to artists, to show you have slots open.\n"
                    f"{ctx.prefix}ArtistRegister <info>: For artists registering their info with us.\n"
                    f"{ctx.prefix}PingCommissioners: Artists can ping people with the Commissioner role.\n"
                    "[Note: expect more info on this subject soon]",
            inline= False
            )

        embed.add_field(    
            name=   "Need a break?:",
            value=  "If you want to hide the server from yourself for a while; "
                    f"you can post {ctx.prefix}HideServer <xDxHxMxS/seconds> and "
                    "I'll try hide the server from you for a bit. You can re-show the server anytime. \n"
                    "If you're stressed, don't worry: https://www.youtube.com/watch?v=L3HQMbQAWRc,",
            inline= False
            )

        embed.set_footer(   
            text=    ctx.guild.name,
            icon_url=GUILD_URL_AS(ctx.guild)
        )

        await ctx.channel.send(embed=embed, delete_after=90)
        return

def setup(bot):
    bot.add_cog(Help(bot))