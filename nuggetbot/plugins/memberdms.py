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
import sys
import json
import dblogin 
import discord
import asyncio
import asyncpg
import datetime
from io import BytesIO
from discord.ext import commands

from nuggetbot.config import Config
from nuggetbot.util import gen_embed as GenEmbed
from nuggetbot.database import DatabaseCmds as pgCmds
from nuggetbot.util.chat_formatting import RANDOM_DISCORD_COLOR, GUILD_URL_AS, AVATAR_URL_AS

#from .cog_utils import SAVE_COG_CONFIG, LOAD_COG_CONFIG
from .util import cogset

class MemberDMS(commands.Cog):
    """Private feedback system."""

    config = None 
    delete_after = 15
    
    def __init__(self, bot):
        self.bot = bot
        MemberDMS.config = Config()
        self.cogset = dict()
        self.db = None

  # -------------------- LISTENERS --------------------
    @commands.Cog.listener()
    async def on_ready(self):
        self.cogset = await cogset.LOAD(cogname=self.qualified_name)
        if not self.cogset:
            self.cogset= dict(
                enablelogging=True
            )

            await cogset.SAVE(self.cogset, cogname=self.qualified_name)


  # -------------------- LOCAL COG STUFF --------------------
    async def cog_before_invoke(self, ctx):
        '''THIS IS CALLED BEFORE EVERY COG COMMAND, IT'S SOLE PURPOSE IS TO CONNECT TO THE DATABASE'''

        credentials = {"user": dblogin.user, "password": dblogin.pwrd, "database": dblogin.name, "host": dblogin.host}
        self.db = await asyncpg.create_pool(**credentials)

        return

    async def cog_after_invoke(self, ctx):
        
        await self.db.close()

        if MemberDMS.config.delete_invoking and not isinstance(ctx.channel, discord.abc.PrivateChannel):
            await ctx.message.delete()

        return

    @asyncio.coroutine
    async def cog_command_error(self, ctx, error):
        print('Ignoring exception in {}'.format(ctx.invoked_with), file=sys.stderr)
        print(error)

  # -------------------- STATIC METHOD --------------------
    @staticmethod
    async def split_msg_ch_id(content):
        try:
            args= content.split(" ")

            if len(args) > 2:
                return [False, False]

            #=== SPLIT, REMOVE MENTION WRAPPER AND CONVERT TO INT
            msg_id = args[1]
            if len(msg_id) > 18:
                msg_id, ch_id = msg_id.split('-')

                if len(msg_id) >= 18 and len(ch_id) >= 18:
                    msg_id = int(msg_id)
                    ch_id = int(ch_id)
                    return [msg_id, ch_id]

                else:
                    return [False, False]

            else:
                msg_id = int(msg_id)
                ch_id = None

                return [msg_id, ch_id]

        except (IndexError, ValueError):
            return [False, False]


  # -------------------- COG COMMANDS --------------------
    @commands.dm_only()    
    @commands.command(pass_context=True, hidden=True, name='feedback', aliases=[])
    async def cmd_feedback(self, ctx):
        
        guild = self.bot.get_guild(MemberDMS.config.target_guild_id)
        member = guild.get_member(ctx.message.author.id)

        # ===== IF MEMBER IS IN THE SERVER
        if member:
            # === IF MEMBER HAS THE MEMBER ROLE
            if bool([role for role in member.roles if role.id == MemberDMS.config.roles["member"]]):
                await self.handle_survey(ctx, ctx.message, guild)

            # === IF MEMBER DOES NOT HAVE MEMBER ROLE (IE, IS IN ENTRANCE GATE)
            else:
                await ctx.channel.send( "Not much point in messaging me. \n"
                                        f"I suggest pinging the staff in <#{self.config.channels['gate']}> to be let in to the rest of the server first."
                                        )

        #IF USER IN NOT IN THE SERVER
        else:
            await ctx.channel.send("It seems you're not a member of {0}.\nI suggest joining {0}.".format(guild.name))
    
        return

    @commands.guild_only()
    @commands.is_owner()
    @commands.command(pass_context=True, hidden=True, name="findfeedback", aliases=([]))
    async def cmd_findfeedback(self, ctx):
        """
        [Bot Owner] Returns user id of who posted anon feedback.

        Useage:
            [prefix]findfeedback <msg_id> or <msg_id-ch_id>
        """
        try:
            args= ctx.message.content.split(" ")

            if len(args) > 2:
                raise ValueError

            # === SPLIT, REMOVE MENTION WRAPPER AND CONVERT TO INT
            msg_id = args[1]
            if len(msg_id) > 18:
                msg_id, ch_id = msg_id.split('-')

                if len(msg_id) >= 18 and len(ch_id) >= 18:
                    msg_id = int(msg_id)
                    ch_id = int(ch_id)

                else:
                    await ctx.send_help('findfeedback', delete_after=15)
                    return

            else:
                msg_id = int(msg_id)
                ch_id = None

        except (IndexError, ValueError):
            await ctx.send_help('findfeedback', delete_after=15)
            return
        
        # IF NO CHANNEL ID WAS PROVIDED
        if not ch_id:
            data = await self.db.fetchrow(pgCmds.GET_MEM_DM_FEEDBACK, msg_id, ctx.guild.id)

        else:
            data = await self.db.fetchrow(pgCmds.GET_MEM_CH_DM_FEEDBACK, msg_id, ch_id, ctx.guild.id)

        #===== IF NO RECORD IN THE DATABASE
        if not data:
            await ctx.channel.send(content=f"No record matching id {msg_id} found.", delete_after=15)
            return

        present = bool(ctx.guild.get_member(data['user_id']))
        
        embed = await GenEmbed.genFeedbackSnooping(data['user_id'], data['sent_msg_id'], data['sent_chl_id'], data['sent_srv_id'], present, data['timestamp'], ctx.guild)
 
        await ctx.channel.send(embed=embed)
        return


  # -------------------- FUNCTIONS --------------------
    async def handle_survey(self, ctx, msg, guild): #updated
        """Custom function to handle the private feedback system"""

        react = await self.ask_yn(msg,
                             "Are you sure you want to submit this feedback anonymously?\n"
                             "You must add a reaction for feedback to be submitted!",
                             timeout=120)

        #===== if user says yes
        if react:
            header = "```css\nAnonymous User Feedback\n```"

        #===== Time out handing
        elif react == None:
            await msg.channel.send("You took too long respond. Cancelling action, feedback **not** sent.")
            return

        #===== if user says no
        else:
            header = "```css\nUser Feedback\n```User: " + msg.author.mention + "\nMessage:"

        msg_content = msg.content.strip()[(len(ctx.prefix) + len(ctx.invoked_with)):]
        msg_attach = []
        feedback_channel = discord.utils.get(guild.channels, id=self.config.channels['feedback_id'])


        async with feedback_channel.typing():
            #=== if msg has an attachment
            if msg.attachments:
                for attach in msg.attachments:
                    fb = await attach.read()
                    filename = attach.filename

                    msg_attach.append(discord.File(BytesIO(fb), filename=filename, spoiler=False))

            #=== if feedback cannot be sent as one message
            if len(msg_content) > ((2000 - len(header))):
                m = await feedback_channel.send(header)
                await feedback_channel.send(msg_content)

                if msg_attach is not None:
                    await feedback_channel.send(files=msg_attach)

            else:
                m = await feedback_channel.send(f"{header} {msg_content}", files=msg_attach)

        #===== Log info to database
        await self.db.execute(pgCmds.ADD_DM_FEEDBACK, msg.author.id, msg.channel.id, m.id, m.channel.id, m.guild.id, m.created_at)

        #===== Tell the user their feedback is sent
        await msg.channel.send(f"Your feedback has been submitted.\nThank you for helping make {guild.name} a better place.")

        return

    #updated
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
            if not isinstance(message.channel, discord.abc.PrivateChannel):
                await message.delete()

            await msg.channel.send(error)
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

    async def _del_msg_later(self, message, after):
        """Custom function to delete messages after a period of time"""

        await asyncio.sleep(after)
        await message.delete()
        return

def setup(bot):
    bot.add_cog(MemberDMS(bot))