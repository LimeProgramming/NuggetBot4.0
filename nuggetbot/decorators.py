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
            or (any(role.name in config.roles["any_staff"] for role in og_msg.author.roles))
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
            or (any(role.name in config.roles["any_staff"] for role in og_msg.author.roles))
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
        or (any(role.name in config.roles["any_staff"] for role in og_msg.author.roles))
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
        or (any(role.name in config.roles["user_staff"] for role in og_msg.author.roles))
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
            or (any(role.name in config.roles["any_staff"] for role in og_msg.author.roles))
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
        or (any(role.name in config.roles["high_staff"] for role in og_msg.author.roles))
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
        or (any(role.name in config.roles["any_staff"] for role in og_msg.author.roles))
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



def command(pattern=None, db_check=False, user_check=None, db_name=None,
            require_role="", require_one_of_roles="", banned_role="",
            banned_roles="", cooldown=0, global_cooldown=0,
            description="", usage=None):

    def actual_decorator(func):
        name = func.__name__
        cmd_name = "!" + name
        prog = re.compile(pattern or cmd_name)
        
        @wraps(func)
        async def wrapper(self, message):

            # Is it matching?
            match = prog.match(message.content)
            if not match:
                return False

            args = match.groups()
            server = message.server
            author = message.author
            author_role_ids = [role.id for role in author.roles]
            storage = await self.get_storage(server)

            is_owner = author.server.owner.id == author.id

            perms = author.guild_permissions
            is_admin = perms.manage_server or perms.administrator or is_owner

            # Checking if the command is enabled
            if db_check:
                check = await storage.get(db_name or name)
                if not check:
                    return

            # Cooldown
            if isinstance(cooldown, str):
                cooldown_dur = int(await storage.get(cooldown) or 0)
            else:
                cooldown_dur = cooldown

            if isinstance(global_cooldown, str):
                global_cooldown_dur = int(await storage.get(global_cooldown) or
                                          0)
            else:
                global_cooldown_dur = global_cooldown

            if global_cooldown_dur != 0:
                check = await storage.get("cooldown:" + name)
                if check:
                    return

            if cooldown_dur != 0:
                check = await storage.get("cooldown:" + name + ":" + author.id)
                if check:
                    return

            # Checking the member with the predicate
            if user_check and not is_admin:
                authorized = await user_check(message.author)
                if not authorized:
                    return

            # Checking roles
            if require_role and not is_admin:
                role_id = await storage.get(require_role)
                if role_id not in author_role_ids:
                    return

            if require_one_of_roles and not is_admin:
                role_ids = await storage.smembers(require_one_of_roles)
                authorized = False
                for role in author.roles:
                    if role.id in role_ids:
                        authorized = True
                        break

                if not authorized:
                    return

            if banned_role:
                role_id = await storage.get(banned_role)
                if role_id in author_role_ids:
                    return

            if banned_roles:
                role_ids = await storage.smembers(banned_roles)
                if any([role_id in author_role_ids
                        for role_id in role_ids]):
                    return

            log.info("{}#{}@{} >> {}".format(message.author.name,
                                             message.author.discriminator,
                                             message.server.name,
                                             message.clean_content))
            if global_cooldown_dur != 0:
                await storage.set("cooldown:" + name, "1")
                await storage.expire("cooldown:" + name, global_cooldown_dur)

            if cooldown_dur != 0:
                await storage.set("cooldown:" + name + ":" + author.id, "1")
                await storage.expire("cooldown:" + name + ":" + author.id,
                                     global_cooldown_dur)

            await func(self, message, args)
        wrapper._db_check = db_check
        wrapper._db_name = db_name or func.__name__
        wrapper._is_command = True
        if usage:
            command_name = usage
        else:
            command_name = "!" + func.__name__
        wrapper.info = {"name": command_name,
                        "description": description}
        return wrapper
    return actual_decorator