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
import yaml
import asyncio
import datetime
from io import BytesIO
from PIL import Image
from typing import Union
from discord import User, Member

@asyncio.coroutine
async def GET_AVATAR_BYTES(user: Union[User, Member], size: int, *, fmt='png', max_age = 1) -> bytes:
    '''
    Retrives a members avatar image in bytes from either discord servers or local cache.
    Cached images are stored in //data/cache/avatars/

    Parameters
    ------------
    user :class:`discord.User, discord.Member`
        Discord User whose avatar is being retrieved.
    size :class:`int`  
        Height and Width of the avatar to be retrieved. All user avatars are square.
    fmt :class:`str`
        Desired format of the returned image. Png is the default but webp, gif and jpg are also supported.
    max_age :class:`int`
        Max allowable age of the cached image if the member has since changed their pfp.

    Returns    
    ------------
    avatar_bytes :class:`bytes`
        Avatar of the member in bytes.
    '''

    failed = False
    path = None
    stored = dict()

    # ---------------- MANAGE DEFAULT AVATAR ---------------
    if not user.avatar:
        with open(os.path.join('nuggetbot', 'plugins', 'images', 'defaultavatar', f'{size}', f'{user.default_avatar.value}.{fmt}'), 'rb') as image:
            avatar_bytes = image.read()
                
        return avatar_bytes

    # ---------------- MANAGE CUSTOM AVATAR ----------------
    try:
        # === LOAD THE EXISTING YML FILE
        with open(os.path.join('data','storedAvatars.yml'), 'r') as storedAvatars:
            stored = yaml.load(storedAvatars, Loader=yaml.FullLoader)

        # === ENUMERATE AND CYCLE THROUGH THE LIST OF STORED IMAGES FOR THE MEMBER
        for i, img in  enumerate(stored[user.id]):

            # = IF A MATCH HAS BEEN FOUND
            if img['size'] == size and img['mime'] == fmt:
                
                # = CHECK IF USER HAS CHANGED THEIR AVATAR
                if img['avatar'] == str(user.avatar):
                    path = img['path']
                
                # = IF USER CHNAGED THEIR AVATAR BUT STORED FILE IS STILL NEW
                elif (datetime.datetime.utcnow() - img['timestamp'] ).days < max_age:
                    path = img['path']
                
                # = IF A MATCH WAS FOUND BUT IT'S TOO OUTDATED. 
                # --- THIS THEN JUST STORES THE INDEX OF THE OUTDATED ENTRY.
                else:
                    failed = i

                #= EXIT LOOP
                break
        
        # === IF A PATH HAS BEEN FOUND
        if path:
            # = CHECK IF FILE ACTUALLY EXISTS AND RETURN THE BYTES
            if os.path.exists(path):
                with open(path, 'rb') as image:
                    avatar_bytes = image.read()
                
                return avatar_bytes

            # = IF FILE WAS NOT FOUND, SET FAILED TO ENTRY INDEX
            else:
                failed = i
    
    # ========================
    # ===== IF THERE'S AN ERROR SET FAILED TO TRUE AND RUN THE CODE BELOW
    except (FileNotFoundError, KeyError):
        failed = True

    # ===== IF WE HIT THIS POINT, ASSUME THE ABOVE FAILED
    avatar_bytes = await user.avatar_url_as(format=fmt, static_format='webp', size=size).read()
    
    # ===== DOUBLE CHECK IMAGE SIZE BECAUSE DISCORD IS SHIT
    with Image.open(BytesIO(avatar_bytes)).convert('RGBA') as im:
        if (size, size) == im.size:
            im.close()
        
        else:
            avatar_bytes = BytesIO()
            im.thumbnail((size,size), Image.LANCZOS)
            im.save(avatar_bytes, "webp")
            avatar_bytes.seek(0)
            avatar_bytes = avatar_bytes.read()

    path = os.path.join('data', 'cache', 'avatars', f'{str(user.id)}_{str(size)}.{fmt}')
    
    # ===== SAVE THE IMAGE TO FILE
    with open(path, 'wb') as image:
        image.write(avatar_bytes)

    data={ 
        'avatar':       str(user.avatar),           'path': path,
        'size':         size,                       'mime': fmt,
        'timestamp':    datetime.datetime.utcnow()
    }

    # ===== THIS REPLACES AN EXISTING ENTRY IN OUR YML FILE
    if not isinstance(failed, bool):
        stored[user.id][failed] = data

    # ===== THIS MAKES AN ENTRY IN OUR YML FILE IF NO EXISTING ENTRY WAS FOUND
    else:
        if user.id in stored.keys():
            stored[user.id].append(data)
        else:
            stored[user.id] = [data]

    # ===== WRITE THE UPDATED STORE TO THE YML FILE
    with open(os.path.join('data','storedAvatars.yml'), 'w') as storedAvatars:
        yaml.dump(stored, storedAvatars, sort_keys=True)

    return avatar_bytes


