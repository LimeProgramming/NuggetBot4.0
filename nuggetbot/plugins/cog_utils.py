import os 
import re
import json 
import asyncio
import datetime
from functools import wraps
from discord.ext import commands
from collections.abc import Iterable
from nuggetbot.config import Config

config = Config()

#Msg must be in specified channel or command be posted by staff or user with admin perm
def in_channel(channel_ids):

    def inner(func):
        
        @wraps(func)
        async def pred(ctx):
            if not ctx or not ctx.guild:
                return False 

            return bool (   (ctx.channel.id in channel_ids) 
                        or  (any(role.name in config.roles["any_staff"] for role in channel_ids.author.roles))
                        or  (channel_ids.author.guild_permissions.administrator)
                        or  (channel_ids.author.id == config.owner_id)
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
                or  (any(role.name in config.roles["any_staff"] for role in ctx.author.roles))
                or  (ctx.author.guild_permissions.administrator)
                or  (ctx.author.id == config.owner_id)
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
                or  (any(role.name in config.roles["any_staff"] for role in ctx.author.roles))
                or  (ctx.author.guild_permissions.administrator)
                or  (ctx.author.id == config.owner_id)
                ):

                return True

            else:
                return False
        
        return pred

    return commands.check(inner)

#Msg must be in reception_channel (setup.ini) or command be posted by staff or user with admin perm
def in_reception(*args):
    
    async def pred(ctx):
        if not ctx or not ctx.guild:
            return False 

        return bool (  (ctx.channel.id == config.channels["reception_id"]) 
                    or (any(role.name in config.roles["any_staff"] for role in ctx.author.roles))
                    or (ctx.author.guild_permissions.administrator)
                    or (ctx.author.id == config.owner_id)
                    )

    return commands.check(pred)

#if user has core_role  or user with admin perm
def is_core(*args):

    async def pred(ctx):
        if not ctx or not ctx.guild:
            return False 

        return bool (   (any(role.name in config.roles["user_staff"] for role in ctx.author.roles))
                    or  (ctx.author.guild_permissions.administrator)
                    or  (ctx.author.id == config.owner_id)
                    )

    return commands.check(pred)

##Staff role decor | Bastion or Minister or user with admin perm
def is_high_staff(*args):

    async def pred(ctx):
        if not ctx or not ctx.guild:
            return False   

        if  (   (any(role.name in config.roles["high_staff"] for role in ctx.author.roles))
            or  (ctx.author.guild_permissions.administrator)
            or  (ctx.author.id == config.owner_id)
            ):

            return True

        else:
            return False
            #return await _responce_generator(self, content="`You lack the permissions to run this command.`")

    return commands.check(pred)

##Staff role decor | Support orBastion or Minister or user with admin perm
def is_any_staff(*args):
    async def pred(ctx):
        if not ctx or not ctx.guild:
            return False   

        if  (   (any(role.name in config.roles["any_staff"] for role in ctx.author.roles))
            or  (ctx.author.guild_permissions.administrator)
            or  (ctx.author.id == config.owner_id)
            ):

            return True

        else:
            return False
            #return await _responce_generator(self, content="`You lack the permissions to run this command.`")

    return commands.check(pred)

### Disables a bot command
def turned_off(*args):
    #@wraps(func)
    #async def wrapper(self, *args, **kwargs):
    #    return

    #return wrapper
    return commands.check(False)


###Bot owner only commands
def owner_only(func):
    @wraps(func)

    async def wrapper(self, *args, **kwargs):
        og_msg = _get_variable('message')

        if ((not og_msg)
        or (og_msg.author.id == config.owner_id)):
            return await func(self, msg=og_msg)

        else:
            return await _responce_generator(self, content="`You are not the bot owner.`")

    return wrapper



@asyncio.coroutine
async def SAVE_COG_CONFIG(cogset, cogname:str):

    with open(os.path.join('jsondata','cogSettings.json'), 'r', encoding='utf-8') as cogSettings:
        existing = json.load(cogSettings)
    
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

    with open(os.path.join('jsondata','cogSettings.json'), 'w', encoding='utf-8') as cogSettings:
        json.dump(existing, cogSettings, skipkeys=True, sort_keys=True)

    return

@asyncio.coroutine
async def LOAD_COG_CONFIG(cogname : str):
    with open(os.path.join('jsondata','cogSettings.json'), 'r', encoding='utf-8') as cogSettings:
        existing = json.load(cogSettings)

    ###===== TRY TO USE THE COGNAME AS A KEY, IF COGNAME IS NOT A KEY, COGSET WILL BE NONE
    try:
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

    except KeyError:
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

    if isinstance(val, str) and bool(re.match(r'^ ([0-9]{4}\-[0-9]{2}\-[0-9]{2} \d\d\:\d\d\:\d\d\.\d+) $', val)):
        val = datetime.datetime.fromisoformat(val)

    return val