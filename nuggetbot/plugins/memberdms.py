from discord.ext import commands
import discord
import asyncio
import datetime
from io import BytesIO
import os
import json

from sebastianbot.plugins.cog_utils import SAVE_COG_CONFIG, LOAD_COG_CONFIG
from sebastianbot.config import Config
from sebastianbot.util.chat_formatting import RANDOM_DISCORD_COLOR, GUILD_URL_AS, AVATAR_URL_AS

class MemberDMS(commands.Cog):
    """Private feedback system."""

    config = None 
    delete_after = 15
    
    def __init__(self, bot):
        self.bot = bot
        MemberDMS.config = Config()
        self.cogset = dict()

  #-------------------- LISTENERS --------------------
    @commands.Cog.listener()
    async def on_ready(self):
        self.cogset = await LOAD_COG_CONFIG(cogname="feedback")
        if not self.cogset:
            self.cogset= dict(
                enablelogging=False
            )

            await SAVE_COG_CONFIG(self.cogset, cogname="feedback")

  #-------------------- LOCAL COG STUFF --------------------
    async def cog_after_invoke(self, ctx):

        if MemberDMS.config.delete_invoking and not isinstance(ctx.channel, discord.abc.PrivateChannel):
            await ctx.message.delete()

        return


  #-------------------- STATIC METHOD --------------------
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


  #-------------------- COG COMMANDS --------------------
    @commands.dm_only()    
    @commands.command(pass_context=True, hidden=True, name='feedback', aliases=[])
    async def cmd_feedback(self, ctx):
        
        guild = self.bot.get_guild(MemberDMS.config.target_guild_id)
        member = guild.get_member(ctx.message.author.id)

        ###===== IF MEMBER IS IN THE SERVER
        if member:
            ###=== IF MEMBER HAS THE MEMBER ROLE
            if bool([role for role in member.roles if role.id == MemberDMS.config.roles["member"]]):
                await self.handle_survey(ctx, ctx.message, guild)

            ###=== IF MEMBER DOES NOT HAVE MEMBER ROLE (IE, IS IN ENTRANCE GATE)
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
        Useage:
            [prefix]findfeedback <msg_id> or <msg_id-ch_id>
        [Bot Owner] Returns user id of who posted anon feedback.
        """

        ###===== CHECK IF THE INPUT IS VALID
        msg_id, ch_id = await MemberDMS.split_msg_ch_id(ctx.message.content)

        if not msg_id:
            await ctx.channel.send("`Useage: [p]findfeedback <msg_id>, [Bot Owner] Returns user id of who posted anon feedback.`")

        ###===== READ THE LOGGED DATA AND RETURN IF NO DATA IS PRESENT
        with open(os.path.join('jsondata','feedback.json'), 'r', encoding='utf-8') as oldfeedback:
            feedback = json.load(oldfeedback)

        if not feedback:
            await ctx.channel.send("`No information found for message`")
            feedback = list()


        ###===== ITERATE THROUGH LOGGED DATA
        valid = False

        for i in feedback:
            if i[0] == msg_id:
                valid = True 

                user_id = i[3]
                present = bool(ctx.message.guild.get_member(user_id))
                guild = ctx.message.guild
                srv_id  = i[2]
                chl_id = i[1]

                break
        
        ###===== IF THERE IS NO DATA, RETURN
        if not valid:
            await ctx.channel.send("No data found for {msg_id}.")
            return 

        embed = discord.Embed(  title=      'Anon Feedback',
                                description=f'User: <@{user_id}> | Still on guild: {present}\n'
                                            f"Posted:\n https://discordapp.com/channels/{srv_id}/{chl_id}/{msg_id}",

                                type=       "rich",
                                timestamp=  datetime.datetime.utcnow(),
                                color=      RANDOM_DISCORD_COLOR()
                                        
                                )

        embed.set_footer(       icon_url=   GUILD_URL_AS(guild),
                                text=       guild.name
                        )
        await ctx.channel.send(embed=embed)
        return

    @commands.is_owner()
    @commands.command(pass_context=True, hidden=True, name="tooglelogfeedback", aliases=([]))
    async def cmd_tooglelogfeedback(self, ctx):
        self.cogset["enablelogging"] = not self.cogset["enablelogging"]

        await SAVE_COG_CONFIG(cogset=self.cogset, cogname="feedback")

        await ctx.channel.send(content=f"Anon Feedback Logging has been set to: {self.cogset['enablelogging']}")
        return


  #-------------------- FUNCTIONS --------------------
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
        feedback_channel = discord.utils.get(guild.channels, id=self.config.channels['servey'])


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

        #===== Tell the user their feedback is sent
        await msg.channel.send(f"Your feedback has been submitted.\nThank you for helping make {guild.name} a better place.")

        #===== LogFeedback
        if self.cogset["enablelogging"]:
            try:
                with open(os.path.join('jsondata','feedback.json'), 'r', encoding='utf-8') as oldfeedback:
                    feedback = json.load(oldfeedback)

                if not feedback:
                    feedback = list()
            except FileNotFoundError:
                feedback = list()

            #sentmsg_id, sendch_id, send_guildid, sender_id, 
            feedback.append([m.id, m.channel.id, m.guild.id, ctx.author.id])

            with open(os.path.join('jsondata','feedback.json'), 'w', encoding='utf-8') as newfeedback:
                json.dump(feedback, newfeedback)


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