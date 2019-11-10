from discord.ext import commands
import discord
import asyncio
import datetime
from random import choice, randint
import random
from enum import Enum

from .util import checks
from nuggetbot.config import Config
from nuggetbot.util.chat_formatting import AVATAR_URL_AS, GUILD_URL_AS, RANDOM_DISCORD_COLOR

class RPS(Enum):
    rock     = "\N{MOYAI}"
    paper    = "\N{PAGE FACING UP}"
    scissors = "\N{BLACK SCISSORS}"


class Fun(commands.Cog):
    """Fun commands."""

    config = None 
    ball = ["As I see it, yes", "It is certain", "It is decidedly so", "Most likely", "Outlook good",
            "Signs point to yes", "Without a doubt", "Yes", "Yes – definitely", "You may rely on it", "Reply hazy, try again",
            "Ask again later", "Better not tell you now", "Cannot predict now", "Concentrate and ask again",
            "Don't count on it", "My reply is no", "My sources say no", "Outlook not so good", "Very doubtful"]

    def __init__(self, bot):
        self.bot = bot
        Fun.config = Config()

  #-------------------- LOCAL COG STUFF --------------------
    async def cog_after_invoke(self, ctx):
        if Fun.config.delete_invoking:
            await ctx.message.delete()

        return

  #-------------------- COG COMMANDS --------------------

    #@in_channel([ChnlID.reception, ChnlID.blessrng])
    @checks.CORE()
    @commands.command(pass_context=True, hidden=False, name='rps', aliases=[])
    async def cmd_rps(self, ctx):
        """
        Useage:
            [prefix]rps rock/paper/scissors
        [Core] Plays Rock Paper Scissors.

        Play rock paper scissors.
        """

        try:
            choice = (ctx.message.content.split(" ")[1]).lower()
            if choice not in ["rock", "paper", "scissors"]:
                raise ValueError()

            player_choice = RPS.rock if choice == "rock" else RPS.paper if choice == "paper" else RPS.scissors if choice == "scissors" else None

            if player_choice is None:
                raise ValueError()

        except (IndexError, ValueError):
            await ctx.channel.send(content="`Useage: [p]rps rock/paper/scissors, [Core] Plays Rock Paper Scissors.`")
            return

        bot_choice = random.choice((RPS.rock, RPS.paper, RPS.scissors))

        cond = {
                (RPS.rock,     RPS.paper)    : False,
                (RPS.rock,     RPS.scissors) : True,
                (RPS.paper,    RPS.rock)     : True,
                (RPS.paper,    RPS.scissors) : False,
                (RPS.scissors, RPS.rock)     : False,
                (RPS.scissors, RPS.paper)    : True
               }

        if bot_choice == player_choice:
            outcome = None # Tie
        else:
            outcome = cond[(player_choice, bot_choice)]

        if outcome is True: 
            await ctx.channel.send(content=f"{bot_choice.value} You win {ctx.author.mention}!")

        elif outcome is False:
            await ctx.channel.send(content=f"{bot_choice.value} You lose {ctx.author.mention}!")

        else:
            await ctx.channel.send(content=f"{bot_choice.value} We're square {ctx.author.mention}!")

        return

    #@in_channel([ChnlID.reception, ChnlID.blessrng])
    @checks.CORE()
    @commands.command(pass_context=True, hidden=False, name='8ball', aliases=[])
    async def cmd_8ball(self, ctx):
        """
        Useage:
            [prefix]8ball <question>
        [Core] Rolls an 8ball

        Ask 8 ball a question
        Question must end with a question mark.
        """
        
        question = ctx.message.content[(len(ctx.prefix) + len(ctx.invoked_with)):].strip()

        if len(question) == 0:

            await ctx.channel.send(content="`Useage: [p]8ball <question> [Core] Rolls an 8ball.`")
            return

        if question.endswith("?") and question != "?":
            e = discord.Embed(
                            title=          "Question",
                            type=           "rich",
                            color=          RANDOM_DISCORD_COLOR(),
                            description=    question,
                            timestamp=      datetime.datetime.utcnow()
                            )
            e.add_field(    name=       "Answer",
                            value=      choice(Fun.ball),
                            inline=     False
                        )
            e.set_author(   name=       "8Ball | {0.name}#{0.discriminator}".format(ctx.author),
                            icon_url=   AVATAR_URL_AS(user=ctx.author)
                        )
            e.set_footer(   icon_url=   GUILD_URL_AS(ctx.guild), 
                            text=       f"{ctx.guild.name}"
                        )

            await ctx.channel.send(embed=e)

        else:
            await ctx.channel.send(content="That doesn't look like a question.")

        return

    #@in_channel([ChnlID.reception, ChnlID.blessrng])
    @checks.CORE()
    @commands.command(pass_context=True, hidden=False, name='roll', aliases=[])
    async def cmd_roll(self, ctx):
        """
        Useage:
            [prefix]roll <number>
        [Core] Rolls a dice

        Rolls random number (between 1 and user choice)
        Defaults to 100.
        """
        try:
            number = int(ctx.message.content.split(" ")[1])

            if number <= 1:
                raise ValueError()      

        except (ValueError, IndexError):
            await ctx.channel.send(content="`Useage: [p]roll <number higher than 1> [Core] Rolls a dice.`")
            return

        n = randint(1, number)
        await ctx.channel.send(content=f"{ctx.author.mention} :game_die: {n} :game_die:")
        return


def setup(bot):
    bot.add_cog(Fun(bot))