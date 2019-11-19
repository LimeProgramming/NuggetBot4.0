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

@asyncio.coroutine
async def SAVE(cogset, cogname:str):
    '''
    Used by the cogs to save their settings so nothing is lost in a shutdown.
    Saves these settings to a yml file in order to allow for a wide range of data types to be stored.

    Parameters
    ------------
    cogset
        Data to be stored, this data can be anything.
    cogname :class:`str`  
        Name of the cog so the data can retrived later.
    '''

    try:
        with open(os.path.join('data','cogSettings.yml'), 'r') as cogSettings:
            existing = yaml.load(cogSettings, Loader=yaml.FullLoader)

    except FileNotFoundError:
        existing = dict()

    existing[cogname] = cogset

    with open(os.path.join('data','cogSettings.yml'), 'w') as cogSettings:
        yaml.dump(existing, cogSettings, sort_keys=True)

@asyncio.coroutine
async def LOAD(cogname : str):
    '''
    Used by the cogs to retrived their settings at startup.

    Parameters
    ------------
    cogname :class:`str`  
        Name of the cog whose data will be retrieved.

    Returns
    ------------
    cogset 
        Data which was stored, can be any data type. Is None is no data is found.
    '''

    try:
        with open(os.path.join('data','cogSettings.yml'), 'r') as cogSettings:
            existing = yaml.load(cogSettings, Loader=yaml.FullLoader)
        
        cogset = existing[cogname]

    except (FileNotFoundError, KeyError):
        cogset = None

    return cogset
