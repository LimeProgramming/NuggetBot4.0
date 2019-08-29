import discord
import colorsys
import random

def error(text):
    return "\N{NO ENTRY SIGN} {}".format(text)

def warning(text):
    return "\N{WARNING SIGN} {}".format(text)

def info(text):
    return "\N{INFORMATION SOURCE} {}".format(text)

def question(text):
    return "\N{BLACK QUESTION MARK ORNAMENT} {}".format(text)

def bold(text):
    return "**{}**".format(text)

def box(text, lang=""):
    ret = "```{}\n{}\n```".format(lang, text)
    return ret

def inline(text):
    return "`{}`".format(text)

def italics(text):
    return "*{}*".format(text)

def strikethrough(text):
    return "~~{}~~".format(text)

def underline(text):
    return "__{}__".format(text)

def escape(text, *, mass_mentions=False, formatting=False):
    if mass_mentions:
        text = text.replace("@everyone", "@\u200beveryone")
        text = text.replace("@here", "@\u200bhere")
    if formatting:
        text = (text.replace("`", "\\`")
                    .replace("*", "\\*")
                    .replace("_", "\\_")
                    .replace("~", "\\~"))
    return text

def escape_mass_mentions(text):
    return escape(text, mass_mentions=True)

def AVATAR_URL_AS(user, format=None, static_format='webp', size=256):
    if not isinstance(user, discord.abc.User):
        return 'https://cdn.discordapp.com/embed/avatars/0.png'

    if user.avatar is None:
        # Default is always blurple apparently
        #return user.default_avatar_url
        return 'https://cdn.discordapp.com/embed/avatars/{}.png'.format(user.default_avatar.value)

    format = format or 'png'

    return 'https://cdn.discordapp.com/avatars/{0.id}/{0.avatar}.{1}?size={2}'.format(user, format, size)


def GUILD_URL_AS(guild, format=None, static_format='webp', size=256):
    if not isinstance(guild, discord.Guild):
        return 'https://cdn.discordapp.com/embed/avatars/0.png'
    
    if format is None:
        format = 'gif' if guild.is_icon_animated() else static_format

    return 'https://cdn.discordapp.com/icons/{0.id}/{0.icon}.{1}?size={2}'.format(guild, format, size)

def RANDOM_DISCORD_COLOR():
    choice = random.choice([1]*10 + [2]*20 + [3]*20)

    if choice == 1:
        values = [int(x * 255) for x in colorsys.hsv_to_rgb(random.random(), 1, 1)]
    elif choice == 2: 
        values = [int(x * 255) for x in colorsys.hsv_to_rgb(random.random(), random.random(), 1)]
    else:
        values = [int(x * 255) for x in colorsys.hsv_to_rgb(random.random(), random.random(), random.random())]

    color = discord.Color.from_rgb(*values)

    return color