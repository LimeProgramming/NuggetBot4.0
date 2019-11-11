import re 
import logging
from functools import wraps
#from discord.ext.commands.bot import _get_variable
from .config import Config
from .utils import Response, _get_variable

config = Config()
log = logging.getLogger('discord')

#Msg must be in specified channel or command be posted by staff or user with admin perm
def in_channel(channel_ids):

    def inner(func):

        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            og_msg = _get_variable('message')

            if ((not og_msg)
            or (og_msg.channel.id in channel_ids) 
            or (any(role.id in config.roles["any_staff"] for role in og_msg.author.roles))
            or (og_msg.author.guild_permissions.administrator)
            or (og_msg.author.id == config.owner_id)):
                return await func(self, msg=og_msg)

            else:
                return

        return wrapper

    return inner

#Msg must be in specified channel or command be posted by staff or user with admin perm
def in_channel_name(channel_names):
    def inner(func):

        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            og_msg = _get_variable('message')

            if ((not og_msg)
            or (og_msg.channel.name in channel_names)
            or (any(role.id in config.roles["any_staff"] for role in og_msg.author.roles))
            or (og_msg.author.guild_permissions.administrator)
            or (og_msg.author.id == config.owner_id)):
                return await func(self, msg=og_msg)

            else:
                return

        return wrapper

    return inner

#Msg must be in reception_channel (setup.ini) or command be posted by staff or user with admin perm
def in_reception(func):
    @wraps(func)
    async def wrapper(self, *args, **kwargs):
        og_msg = _get_variable('message')

        if ((not og_msg)
        or (og_msg.channel.id == config.channels["reception_id"]) 
        or (any(role.id in config.roles["any_staff"] for role in og_msg.author.roles))
        or (og_msg.author.guild_permissions.administrator)
        or (og_msg.author.id == config.owner_id)):
            return await func(self, msg=og_msg)

        else:
            return

    return wrapper

#if user has core_role  or user with admin perm
def is_core(func):
    @wraps(func)

    async def wrapper(self, *args, **kwargs):
        og_msg = _get_variable('message')

        if ((not og_msg)
        or (any(role.id in config.roles["user_staff"] for role in og_msg.author.roles))
        or (og_msg.author.guild_permissions.administrator)
        or (og_msg.author.id == config.owner_id)):
            return await func(self, msg=og_msg)

        else:
            return await _responce_generator(self, content="`You do not have the permission to run this command.`", reply=True)

    return wrapper

#MSG author must have a certain role or user with admin perm
def has_role(role_name):
    def inner(func):

        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            og_msg = _get_variable('message')

            if ((not og_msg)
            or (any(role.name in role_name for role in og_msg.author.roles))
            or (any(role.id in config.roles["any_staff"] for role in og_msg.author.roles))
            or (og_msg.author.guild_permissions.administrator)
            or (og_msg.author.id == config.owner_id)):
                return await func(self, msg=og_msg)

            else:
                return await _responce_generator(self, content="`You do not have the permission to run this command.`", reply=True)

        return wrapper

    return inner

##Staff role decor | Bastion or Minister or user with admin perm
def is_high_staff(func):
    @wraps(func)

    async def wrapper(self, *args, **kwargs):
        og_msg = _get_variable('message')

        if ((not og_msg)
        or (any(role.id in config.roles["high_staff"] for role in og_msg.author.roles))
        or (og_msg.author.guild_permissions.administrator)
        or (og_msg.author.id == config.owner_id)):
            return await func(self, msg=og_msg)

        else:
            return await _responce_generator(self, content="`You lack the permissions to run this command.`")

    return wrapper

##Staff role decor | Support orBastion or Minister or user with admin perm
def is_any_staff(func):
    @wraps(func)

    async def wrapper(self, *args, **kwargs):
        og_msg = _get_variable('message')

        if ((not og_msg)
        or (any(role.id in config.roles["any_staff"] for role in og_msg.author.roles))
        or (og_msg.author.guild_permissions.administrator)
        or (og_msg.author.id == config.owner_id)):
            return await func(self, msg=og_msg)

        else:
            return await _responce_generator(self, content="`You lack the permissions to run this command.`")

    return wrapper

### Disables a bot command
def turned_off(func):
    @wraps(func)
    async def wrapper(self, *args, **kwargs):
        return

    return wrapper

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



async def _responce_generator(self, content="", embed=None, reply=True, delete_after=None):
    return Response(content=content, embed=embed, reply=reply, delete_after=delete_after)
