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
import re
import json 
import yaml
import discord
import asyncio
import datetime
from typing import Union
from functools import wraps
from discord.ext import commands
from collections.abc import Iterable
from nuggetbot.config import Config

config = Config()

###########################################################################################
###-------------------------- JUST SOME REGULAR OLD FUNCTIONS --------------------------###
###########################################################################################

def __get_guild_and_invoker(ctx):
    guild = ctx.bot.get_guild(config.target_guild_id)
    invoker = guild.get_member(ctx.author.id)

    return guild, invoker

def __admin_or_owner(ctx, invoker):
    return bool(    (invoker.guild_permissions.administrator)    
                or  (ctx.author.id == config.owner_id)
    )

####################################################################################################
###-------------------------- COMMANDS.COMMAND WRAPPERS, IN GUILD ONLY --------------------------###
####################################################################################################


#Msg must be in specified channel or command be posted by staff or user with admin perm
def in_channel(channel_ids):

    def inner(func):
        
        @wraps(func)
        async def pred(ctx):
            if not ctx or not ctx.guild:
                return False 

            return bool (   (ctx.channel.id in channel_ids) 
                        or  (any(role.id in config.roles["any_staff"] for role in channel_ids.author.roles))
                        or __admin_or_owner(ctx, ctx.author)
                        )
        return pred

    return commands.check(inner)

#Msg must be in specified channel or command be posted by staff or user with admin perm
def in_channel_name(channel_names):

    def inner(func):

        @wraps(func)
        async def pred(ctx):
            if not ctx or not ctx.guild:
                return False 

            if  (   (ctx.channel.name in channel_names)
                or  (any(role.id in config.roles["any_staff"] for role in ctx.author.roles))
                or __admin_or_owner(ctx, ctx.author)
                ):

                return True

            return False 

        return pred

    return commands.check(inner)

#MSG author must have a certain role or user with admin perm
def has_role(role_name):

    def inner(func):

        @wraps
        async def pred(ctx):
            if not ctx or not ctx.guild:
                return False 

            if  (   (any(role.name in role_name for role in ctx.author.roles))
                or  (any(role.id in config.roles["any_staff"] for role in ctx.author.roles))
                or __admin_or_owner(ctx, ctx.author)
                ):

                return True

            else:
                return False
        
        return pred

    return commands.check(inner)

#Msg must be in reception_channel (setup.ini) or command be posted by staff or user with admin perm
def IN_RECEPTION(*args):
    
    async def pred(ctx):
        if not ctx or not ctx.guild:
            return False 

        return bool (  (ctx.channel.id == config.channels["reception_id"]) 
                    or (any(role.name in config.roles["any_staff"] for role in ctx.author.roles))
                    or __admin_or_owner(ctx, ctx.author)
                    )

    return commands.check(pred)

#if user has core_role  or user with admin perm
def IS_CORE(*args):
    async def pred(ctx):
        if not ctx or not ctx.guild:
            return False 

        return bool (   (any(role.id in config.roles["user_staff"] for role in ctx.author.roles))
                    or __admin_or_owner(ctx, ctx.author)
                    )

    return commands.check(pred)

def IS_HIGHEST_STAFF(*args):
    async def pred(ctx):
        if not ctx or not ctx.guild:
            return False   

        if  (   (any(role.id == config.roles["admin"] for role in ctx.author.roles))
            or __admin_or_owner(ctx, ctx.author)
            ):

            return True

        else:
            await ctx.channel.send(content="`You lack the permissions to run this command.`", delete_after=15)
            return False

    return commands.check(pred)

##Staff role decor | Bastion or Minister or user with admin perm
def IS_HIGH_STAFF(*args):

    async def pred(ctx):
        if not ctx or not ctx.guild:
            return False   

        if  (   (any(role.id in config.roles["high_staff"] for role in ctx.author.roles))
            or __admin_or_owner(ctx, ctx.author)
            ):

            return True

        else:
            await ctx.channel.send(content="`You lack the permissions to run this command.`", delete_after=15)
            return False

    return commands.check(pred)

##Staff role decor | Support orBastion or Minister or user with admin perm
def IS_ANY_STAFF(*args):
    async def pred(ctx):
        if not ctx or not ctx.guild:
            return False   

        if  (   (any(role.id in config.roles["any_staff"] for role in ctx.author.roles))
            or __admin_or_owner(ctx, ctx.author)
            ):

            return True

        else:
            await ctx.channel.send(content="`You lack the permissions to run this command.`", delete_after=15)
            return False

    return commands.check(pred)


### Disables a bot command
def turned_off(*args):
    async def pred(ctx):
        await ctx.channel.send(content="`This command is disabled`")
        return False

    return commands.check(pred)


###Bot owner only commands
def owner_only(func):

    async def wrapper(ctx):
        if not ctx:
            return False

        if ctx.author.id == config.owner_id:
            return True

        else:
            await ctx.channel.send(content="`You are not the bot owner.`", delete_after=15)
            return False

    return commands.check(wrapper)

###Bot owner only commands
def is_owner(*args):

    async def wrapper(ctx):
        if not ctx:
            return False

        if ctx.author.id == config.owner_id:
            return True

        else:
            await ctx.channel.send(content="`You are not the bot owner.`", delete_after=15)
            return False

    return commands.check(wrapper)


##########################################################################################################
###-------------------------- COMMANDS.COMMAND WRAPPERS, DM CHANNELS ALLOWED --------------------------###
##########################################################################################################

#if user has core_role  or user with admin perm
def IS_CORE_DM(*args):

    async def pred(ctx):
        if not ctx:
            return False 

        guild, invoker = __get_guild_and_invoker(ctx)

        return bool (   (any(role.id in config.roles["user_staff"] for role in invoker.roles))
                    or  (__admin_or_owner(ctx, invoker))
                    )

    return commands.check(pred)

def IS_HIGHEST_STAFF_DM(*args):
    async def pred(ctx):
        if not ctx:
            return False   

        guild, invoker = __get_guild_and_invoker(ctx)

        if  (   (any(role.id in config.roles["admins"] for role in invoker.roles))
            or  (__admin_or_owner(ctx, invoker))
            ):

            return True

        else:    
            await ctx.channel.send(content="`You lack the permissions to run this command.`")
            return False

    return commands.check(pred)

##Staff role decor | Bastion or Minister or user with admin perm
def IS_HIGH_STAFF_DM(*args):

    async def pred(ctx):
        if not ctx:
            return False   

        guild, invoker = __get_guild_and_invoker(ctx)

        if  (   (any(role.id in config.roles["high_staff"] for role in invoker.roles))
            or  (__admin_or_owner(ctx, invoker))
            ):

            return True

        else:
            await ctx.channel.send(content="`You lack the permissions to run this command.`")
            return False

    return commands.check(pred)

##Staff role decor | Support orBastion or Minister or user with admin perm
def IS_ANY_STAFF_DM(*args):
    async def pred(ctx):
        if not ctx:
            return False   

        guild, invoker = __get_guild_and_invoker(ctx)

        if  (   (any(role.id in config.roles["any_staff"] for role in invoker.roles))
            or  (__admin_or_owner(ctx, invoker))
            ):

            return True

        else:
            await ctx.channel.send(content="`You lack the permissions to run this command.`")
            return False

    return commands.check(pred)


###########################################################################################################
###------------------------------ COG SETTING SAVING AND LOADING COMMANDS ------------------------------###
###########################################################################################################

@asyncio.coroutine
async def SAVE_COG_CONFIG(cogset, cogname:str):

    try:
        with open(os.path.join('data','cogSettings.json'), 'r', encoding='utf-8') as cogSettings:
            existing = json.load(cogSettings)
    except FileNotFoundError:
        existing = dict()
    
    ###===== Convert Datetime.datetime to string to allow for serialization
    for key in cogset.keys():
        cogset[key] = await __convert_dd_str(cogset[key])

        ###=== IF THE ITEM IS A DICT
        if isinstance(cogset[key], dict):
            for i in cogset[key].keys():
                cogset[key][i] = await __convert_dd_str(cogset[key][i])

        ###=== IF THE ITEM IN THE DICT CAN BE ITERATED (IE, LISTS, TUPLES, SETS)
        elif isinstance(cogset[key], Iterable):
            for j, i in enumerate(cogset[key]):
                cogset[key][j] = await __convert_dd_str(i)

    existing[cogname] = cogset

    with open(os.path.join('data','cogSettings.json'), 'w', encoding='utf-8') as cogSettings:
        json.dump(existing, cogSettings, skipkeys=True, sort_keys=True)

    return

@asyncio.coroutine
async def LOAD_COG_CONFIG(cogname : str):
    ###===== TRY TO USE THE COGNAME AS A KEY, IF COGNAME IS NOT A KEY, COGSET WILL BE NONE
    # ALSO IF NO COG SETTINGS HAVE BEEN SET, THEN IT'LL THROW A FILENOTFOUNDERROR
    try:
        with open(os.path.join('data','cogSettings.json'), 'r', encoding='utf-8') as cogSettings:
            existing = json.load(cogSettings)

        cogset = existing[cogname]

        ###=== CONVERT DATETIME ITEMS BACK TO THE CORRECT FORMAT
        for key in cogset.keys():
            cogset[key] = await __convert_str_dd(cogset[key])

            ###= IF THE ITEM IS A DICT
            if isinstance(cogset[key], dict):
                for i in cogset[key].keys():
                    cogset[key][i] = await __convert_str_dd(cogset[key][i])

            ###= IF THE ITEM IN THE DICT CAN BE ITERATED (IE, LISTS, TUPLES, SETS)
            elif isinstance(cogset[key], Iterable):
                for j, i in enumerate(cogset[key]):
                    cogset[key][j] = await __convert_str_dd(i)

    except (FileNotFoundError, KeyError):
        cogset = None

    return cogset

@asyncio.coroutine
async def __convert_dd_str(val):
    """
    Converts a datetime object to a string
    """

    if isinstance(val, datetime.datetime):
        val = val.__str__()

    return val

@asyncio.coroutine
async def __convert_str_dd(val):
    """
    Converts a str of datetime patter to a real datetime object
    """

    #if isinstance(val, str) and bool(re.match(r'^ ([0-9]{4}\-[0-9]{2}\-[0-9]{2} \d\d\:\d\d\:\d\d\.\d+) $', val)):
    if isinstance(val, str):
        try:
            val = datetime.datetime.fromisoformat(val)
        except ValueError:
            pass

    return val


###########################################################################################################
###------------------------------------ CACHE MEMBER AVATAR IMAGES -------------------------------------###
###########################################################################################################

"""
{12345: [{  'avatar':       varchar
            'size':         int,
            'timestamp':    datetime.datetime.utcnow(),
            'image':        "path"
            }]
                    
}
"""

@asyncio.coroutine
async def GET_AVATAR_BYTES(user: Union[discord.User, discord.Member], size: int, fmt='png', max_age = 1) -> bytes:
    failed = False
    path = None
    stored = dict()

    ###---------------- MANAGE DEFAULT AVATAR ---------------###
    if not user.avatar:
        with open(os.path.join('nuggetbot', 'plugins', 'images', 'defaultavatar', f'{size}', f'{user.default_avatar.value}.{fmt}'), 'rb') as image:
            avatar_bytes = image.read()
                
        return avatar_bytes

    ###---------------- MANAGE CUSTOM AVATAR ----------------###
    try:
        ###=== LOAD THE EXISTING YML FILE
        with open(os.path.join('data','storedAvatars.yml'), 'r') as storedAvatars:
            stored = yaml.load(storedAvatars, Loader=yaml.FullLoader)

        ###=== ENUMERATE AND CYCLE THROUGH THE LIST OF STORED IMAGES FOR THE MEMBER
        for i, img in  enumerate(stored[user.id]):

            ###= IF A MATCH HAS BEEN FOUND
            if img['size'] == size and img['mime'] == fmt:
                
                #= CHECK IF USER HAS CHANGED THEIR AVATAR
                if img['avatar'] == str(user.avatar):
                    path = img['path']
                
                #= IF USER CHNAGED THEIR AVATAR BUT STORED FILE IS STILL NEW
                elif (datetime.datetime.utcnow() - img['timestamp'] ).days < max_age:
                    path = img['path']
                
                #= IF A MATCH WAS FOUND BUT IT'S TOO OUTDATED. 
                #--- THIS THEN JUST STORES THE INDEX OF THE OUTDATED ENTRY.
                else:
                    failed = i

                #= EXIT LOOP
                break
        
        ###=== IF A PATH HAS BEEN FOUND
        if path:
            ###= CHECK IF FILE ACTUALLY EXISTS AND RETURN THE BYTES
            if os.path.exists(path):
                with open(path, 'rb') as image:
                    avatar_bytes = image.read()
                
                return avatar_bytes

            ###= IF FILE WAS NOT FOUND, SET FAILED TO ENTRY INDEX
            else:
                failed = i
    
    ###========================
    ###===== IF THERE'S AN ERROR SET FAILED TO TRUE AND RUN THE CODE BELOW
    except (FileNotFoundError, KeyError):
        failed = True

    ###===== IF WE HIT THIS POINT, ASSUME THE ABOVE FAILED
    avatar_bytes = await user.avatar_url_as(format=fmt, static_format='webp', size=size).read()
    path = os.path.join('data','cache', 'avatars', f'{str(user.id)}_{str(size)}.{fmt}')
    
    ###===== SAVE THE IMAGE TO FILE
    with open(path, 'wb') as image:
        image.write(avatar_bytes)

    data={ 
        'avatar':       str(user.avatar),           'path': path,
        'size':         size,                       'mime': fmt,
        'timestamp':    datetime.datetime.utcnow()
    }

    ###===== THIS REPLACES AN EXISTING ENTRY IN OUR YML FILE
    if not isinstance(failed, bool):
        stored[user.id][failed] = data

    ###===== THIS MAKES AN ENTRY IN OUR YML FILE IF NO EXISTING ENTRY WAS FOUND
    else:
        if user.id in stored.keys():
            stored[user.id].append(data)
        else:
            stored[user.id] = [data]

    ###===== WRITE THE UPDATED STORE TO THE YML FILE
    with open(os.path.join('data','storedAvatars.yml'), 'w') as storedAvatars:
        yaml.dump(stored, storedAvatars, sort_keys=True)

    return avatar_bytes


