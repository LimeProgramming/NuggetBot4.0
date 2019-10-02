# basic dependencies
import discord
from discord.ext import commands
from discord.utils import _bytes_to_base64_data
import os

# aiohttp should be installed if discord.py is
import aiohttp

# PIL can be installed through
# `pip install -U Pillow`
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# partial lets us prepare a new function with args for run_in_executor
from functools import partial

# BytesIO allows us to convert bytes into a file-like byte stream.
from io import BytesIO

# this just allows for nice function annotation, and stops my IDE from complaining.
from typing import Union

from nuggetbot.util.chat_formatting import AVATAR_URL_AS

import asyncpg
import dblogin 

class ImageCog(commands.Cog):
    lvMSGS= ((0, 10), (10, 75), (75, 200), (200, 350), (350, 500), (500, 575), (575, 661), (661, 760), (760, 874), (874, 1005), (1005, 1156), (1156, 1318), (1318, 1503), (1503, 1713), (1713, 1953), (1953, 2226), (2226, 2538), (2538, 2893), (2893, 3298), (3298, 3760), (3760, 4286), (4286, 4843), (4843, 5473), (5473, 6184), (6184, 6988), (6988, 7896), (7896, 8922), (8922, 10082), (10082, 11393), (11393, 12874), (12874, 14548), (14548, 16294), (16294, 18249), (18249, 20439), (20439, 22892), (22892, 25639), (25639, 28716), (28716, 32162), (32162, 36021), (36021, 40344), (40344, 45185), (45185, 50155), (50155, 55672), (55672, 61796), (61796, 68594), (68594, 76139), (76139, 84514), (84514, 93811), (93811, 104130), (104130, 115584), (115584, 128298), (128298, 141769), (141769, 156655), (156655, 173104), (173104, 191280), (191280, 211364), (211364, 233557), (233557, 258080), (258080, 285178), (285178, 315122), (315122, 348210), (348210, 383031), (383031, 421334), (421334, 463467), (463467, 509814), (509814, 560795), (560795, 616874), (616874, 678561), (678561, 746417), (746417, 821059), (821059, 903165), (903165, 988966), (988966, 1082918), (1082918, 1185795), (1185795, 1298446), (1298446, 1421798), (1421798, 1556869), (1556869, 1704772), (1704772, 1866725), (1866725, 2044064), (2044064, 2238250), (2238250, 2439692), (2439692, 2659264), (2659264, 2898598), (2898598, 3159472), (3159472, 3443824), (3443824, 3753768), (3753768, 4091607), (4091607, 4459852), (4459852, 4861239), (4861239, 5298751), (5298751, 5749145), (5749145, 6237822), (6237822, 6768037), (6768037, 7343320), (7343320, 7967502), (7967502, 8644740), (8644740, 9379543), (9379543, 10176804), (10176804, 11041832))
    
    #lvlMSGS = (10, 75, 200, 350, 500, 575, 661, 760, 874, 1005, 1156, 1318, 1503, 1713, 1953, 2226, 2538, 2893, 3298, 3760, 4286, 4843, 5473, 6184, 6988, 7896, 8922, 10082, 11393, 12874, 14548, 16294, 18249, 20439, 22892, 25639, 28716, 32162, 36021, 40344, 45185, 50155, 55672, 61796, 68594, 76139, 84514, 93811, 104130, 115584, 128298, 141769, 156655, 173104, 191280, 211364, 233557, 258080, 285178, 315122, 348210, 383031, 421334, 463467, 509814, 560795, 616874, 678561, 746417, 821059, 903165, 988966, 1082918, 1185795, 1298446, 1421798, 1556869, 1704772, 1866725, 2044064, 2238250, 2439692, 2659264, 2898598, 3159472, 3443824, 3753768, 4091607, 4459852, 4861239, 5298751, 5749145, 6237822, 6768037, 7343320, 7967502, 8644740, 9379543, 10176804, 11041832)
    
    def __init__(self, bot: commands.Bot):

        # we need to include a reference to the bot here so we can access its loop later.
        self.bot = bot

        # create a ClientSession to be used for downloading avatars
        self.session = aiohttp.ClientSession(loop=bot.loop)

  #-------------------- LOCAL COG STUFF -------------------- 
    async def cog_before_invoke(self, ctx):
        '''THIS IS CALLED BEFORE EVERY COG COMMAND, IT'S SOLE PURPOSE IS TO CONNECT TO THE DATABASE'''

        credentials = {"user": dblogin.user, "password": dblogin.pwrd, "database": dblogin.name, "host": dblogin.host}
        self.db = await asyncpg.create_pool(**credentials)

        return

    async def cog_after_invoke(self, ctx):
        await self.db.close()

        return


    async def get_avatar(self, user: Union[discord.User, discord.Member]) -> bytes:

        # generally an avatar will be 1024x1024, but we shouldn't rely on this
        avatar_url = AVATAR_URL_AS(user, format="png", size=128)

        async with self.session.get(avatar_url) as response:
            avatar_bytes = await response.read()

        return avatar_bytes

    @staticmethod
    def processing(avatar_bytes: bytes, colour: tuple) -> BytesIO:

        head, tail = os.path.split(os.path.realpath(__file__))
        bg = os.path.join(head, "images", "testbg.png")

        # we must use BytesIO to load the image here as PIL expects a stream instead of
        # just raw bytes.
        with Image.open(BytesIO(avatar_bytes)).convert('RGBA') as im:

            # this creates a new image the same size as the user's avatar, with the
            # background colour being the user's colour.
            #with Image.new("RGBA", im.size, colour) as background:
            with Image.open(bg).convert('RGBA') as background:
                # this ensures that the user's avatar lacks an alpha channel, as we're
                # going to be substituting our own here.
                rgb_avatar = im.convert("RGBA")

                # this is the mask image we will be using to create the circle cutout
                # effect on the avatar.
                with Image.new("L", im.size, 0) as mask:

                    # ImageDraw lets us draw on the image, in this instance, we will be
                    # using it to draw a white circle on the mask image.
                    mask_draw = ImageDraw.Draw(mask)

                    # draw the white circle from 0, 0 to the bottom right corner of the image
                    #mask_draw.ellipse([(0, 0), im.size], fill=255)
                    mask_draw.rectangle([(0, 0), im.size], fill=255)

                    # paste the alpha-less avatar on the background using the new circle mask
                    # we just created.
                    background.paste(rgb_avatar, (472, 0), mask=rgb_avatar)

                #Canvas = Image.new("RGBA", (600, 128), color=0):
                #Canvas.paste(rgb_avatar, (472, 0), mask=None)


                #Image.alpha_composite(im1, im2)
                #background.paste(rgb_avatar, (472, 0), mask=None) #test

                # prepare the stream to save this image into
                final_buffer = BytesIO()

                # save into the stream, using png format.
                background.save(final_buffer, "png")

        # seek back to the start of the stream
        final_buffer.seek(0)

        return final_buffer

    @staticmethod
    def processing2(avatar_bytes: bytes, colour: tuple) -> BytesIO:

        #===== VARS
        out_avatar = BytesIO()
        ava_status = BytesIO()

        head, tail = os.path.split(os.path.realpath(__file__))
        imagedir = os.path.join(head, "images")


        #rgba_avatar = Image.open(BytesIO(avatar_bytes)).convert('RGBA')

        with Image.open(BytesIO(avatar_bytes)).convert('RGBA') as rgba_avatar:
            
            with Image.new("RGBA", (130, 130), (0, 0, 0)) as background:

                with Image.new("L", rgba_avatar.size, 0) as avatar_mask:
                
                    mask_draw = ImageDraw.Draw(avatar_mask)

                    mask_draw.ellipse([(0, 0), rgba_avatar.size], fill=255)

                    background.paste(rgba_avatar, (0, 0), mask=avatar_mask)

                # save into the stream, using png format.
                background.save(out_avatar, "png")

        #================================

        #imagedir

        with Image.open(os.path.join(imagedir, "online.png")) as status:
            status.convert('RGBA') 

            with Image.open(out_avatar) as img:
                img2 = Image.alpha_composite(img, status)

                img2.save(ava_status, "png")

        ava_status.seek(0)

        return ava_status

    @staticmethod
    def processing3(avatar_bytes: bytes, member: Union[discord.User, discord.Member]) -> BytesIO:
        #===== VARS
        out_avatar = BytesIO()
        ava_status = BytesIO()

        head, tail = os.path.split(os.path.realpath(__file__))
        imagedir = os.path.join(head, "images")

        #print(avatar_bytes)

        with Image.open(BytesIO(avatar_bytes)).convert('RGBA') as rgba_avatar:

            with Image.new("RGBA", (132, 132), (0, 0, 0)) as background:
                
                with Image.open(os.path.join(imagedir, "ava_mask.png")) as avatar_mask:

                    with Image.open(os.path.join(imagedir, "online.png")) as status:
                        status.convert('RGBA') 

                        #foreground = Image.new("RGBA", rgba_avatar.size, (54, 57, 63, 255))

                        #rgba_avatar.paste(foreground, (0,0))

                        #rgba_avatar.paste(foreground, (0,0), mask=rgba_avatar)

                        img = Image.alpha_composite((Image.alpha_composite(Image.new("RGBA", rgba_avatar.size, (54, 57, 63, 255)), rgba_avatar)), avatar_mask)

                        #background.paste(img, (0, 0), mask=None)

                        #img.save(out_avatar, "png")

                        #with Image.open(out_avatar) as img2:

                        img = Image.alpha_composite(img, status)

                        #img.save(ava_status, "png")

        #print(1)
        #with Image.open(ava_status).convert('RGB') as ava:
            
        #base image is 132
        #with Image.new("RGBA", (700, 148), (0, 0, 0, 0)) as background:
        #800 x 152
        with Image.open(os.path.join(imagedir, "mbg.png")) as background:
            #img.paste(background, (8, 8), mask=None)

            background.paste(img, (10, 10), mask=None)


            font = ImageFont.truetype(os.path.join(imagedir, "OpenSans-Light.ttf"), 32)

            draw = ImageDraw.Draw(background)

            # font = ImageFont.truetype(<font-file>, <font-size>)
            #font = ImageFont.truetype("sans-serif.ttf", 16)

            # draw.text((x, y),"Sample Text",(r,g,b))
            draw.text((160, 20),f"{member.name}#{member.discriminator}", fill=(230, 230, 230, 255), font=font)

            #img.save(ava_status, "png")
            #print(2)
            background.save(ava_status, "png")

        ava_status.seek(0)

        return ava_status

    @staticmethod
    def processing4(avatar_bytes: bytes, member: Union[discord.User, discord.Member], level: int, rank: int, gems: int, nummsgs:int) -> BytesIO:
        #===== VARS
        out_avatar = BytesIO()
        ava_status = BytesIO()

        head, tail = os.path.split(os.path.realpath(__file__))
        imagedir = os.path.join(head, "images")

        mstat = member.status.__str__()
        if mstat not in ["offline", "online", "dnd", "idle"]:
            mstat = "online"

        with Image.open(BytesIO(avatar_bytes)).convert('RGBA') as rgba_avatar:
            with Image.open(os.path.join(imagedir, f"{mstat}.png")).convert('RGBA') as status:

                RADIUS = 2
                diam = 2*RADIUS
        
                background = Image.new('RGBA', (rgba_avatar.size[0]+diam, rgba_avatar.size[1]+diam), (0,0,0,0))
                background.paste(rgba_avatar, (RADIUS, RADIUS))

                # Create paste mask
                mask = Image.new('L', background.size, 0)
                draw = ImageDraw.Draw(mask)
                x0, y0 = 0, 0
                x1, y1 = background.size
                for d in range(diam+RADIUS):
                    x1, y1 = x1-1, y1-1
                    alpha = 255 if d<RADIUS else int(255*(diam+RADIUS-d)/diam)
                    draw.rectangle([x0, y0, x1, y1], outline=alpha)
                    x0, y0 = x0+1, y0+1

                blur = background.filter(ImageFilter.GaussianBlur(RADIUS/2))
                background.paste(blur, mask=mask)
                
                img = Image.alpha_composite(background, status)
        
        with Image.open(os.path.join(imagedir, "Untitle2d.png")) as background:
            try:
                ###=====    ADD THE PROFILE IMAGE
                background.paste(img, (10, 10), mask=img)

                ###=====    ADD THE GEM IMAGES
                gem1 = Image.open(os.path.join(imagedir, "gem1.png")).convert('RGBA')
                gem2 = Image.open(os.path.join(imagedir, "gem2.png")).convert('RGBA')
                gem3 = Image.open(os.path.join(imagedir, "gem3.png")).convert('RGBA')

                background.paste(gem2, (550, 109), mask=gem2)
                background.paste(gem1, (577, 109), mask=gem1)
                background.paste(gem3, (608, 109), mask=gem3)

                ###=====    ADD THE PROGRESS BAR
                background.paste(Image.new("RGBA", (776, 30), (0, 85, 183, 255)), (12, 152), mask=None)

                if level < 100:
                    a, b = ImageCog.lvMSGS[level]
                    x = int(((nummsgs - a) / (b - a)) * 776)

                    if x < 1:
                        x = 1
                    elif x > 776:
                        x = 775
                else:
                    x = 776

                background.paste(Image.new("RGBA", (x, 30), (0, 175, 96, 255)), (12, 152), mask=None)

                ###=====    ADD THE TEXT
                #-------    FONTS
                lfont = ImageFont.truetype(os.path.join(imagedir, "OpenSans-Semibold.ttf"), 42)
                zfont = ImageFont.truetype(os.path.join(imagedir, "OpenSans-Regular.ttf"), 38)
                sfont = ImageFont.truetype(os.path.join(imagedir, "OpenSans-Light.ttf"), 32)

                draw = ImageDraw.Draw(background)

                #= username
                draw.text((160, 105), f"{member.name}#{member.discriminator}", fill=(230, 230, 230, 255), font=sfont)
                #= Level
                draw.text((550, 0), "LV:", fill=(230, 230, 230, 255), font=zfont)
                draw.text((650, 0), f"{level}", fill=(230, 230, 230, 255), font=lfont)
                #= Rank
                draw.text((550, 46), f"Rank:", fill=(230, 230, 230, 255), font=zfont)
                draw.text((650, 46), f"{rank}", fill=(230, 230, 230, 255), font=lfont)
                #= Gems
                draw.text((650, 92), f"{gems}", fill=(230, 230, 230, 255), font=lfont)

                background.save(ava_status, "png")
            except Exception as e:
                print(e)
                raise TypeError

        ava_status.seek(0)

        return ava_status

    @commands.command()
    async def imagetest(self, ctx, *, member: discord.Member = None):
        """Display the user's avatar on their colour."""

        # this means that if the user does not supply a member, it will default to the
        # author of the message.
        member = member or ctx.author

        async with ctx.typing():
            # this means the bot will type while it is processing and uploading the image


            # grab the user's avatar as bytes
            avatar_bytes = await member.avatar_url_as(format='png', static_format='webp', size=128).read()

            try:
                rank = await self.db.fetchval('Select Count(user_id) from public.members where nummsgs > (Select nummsgs from public.members where user_id = CAST($1 AS BIGINT))', member.id)
                rank = rank + 1 

                level, nummsgs, gems = await self.db.fetchrow('Select level, nummsgs, gems from public.members where user_id = CAST($1 AS BIGINT)', member.id)

                # create partial function so we don't have to stack the args in run_in_executor
                fn = partial(self.processing4, avatar_bytes, member, level, rank, gems, nummsgs)

                # this runs our processing in an executor, stopping it from blocking the thread loop.
                # as we already seeked back the buffer in the other thread, we're good to go
                final_buffer = await self.bot.loop.run_in_executor(None, fn)
            except Exception as e:
                print(e)
                raise TypeError
            # prepare the file
            file = discord.File(filename="circle.png", fp=final_buffer)

            # send it
            await ctx.send(file=file)

    @commands.command()
    async def circle(self, ctx, *, member: discord.Member = None):
        """Display the user's avatar on their colour."""

        # this means that if the user does not supply a member, it will default to the
        # author of the message.
        member = member or ctx.author

        async with ctx.typing():
            # this means the bot will type while it is processing and uploading the image

            if isinstance(member, discord.Member):
                # get the user's colour, pretty self explanatory
                member_colour = member.colour.to_rgb()
            else:
                # if this is in a DM or something went seriously wrong
                member_colour = (0, 0, 0)

            # grab the user's avatar as bytes
            avatar_bytes = await self.get_avatar(member)

            # create partial function so we don't have to stack the args in run_in_executor
            fn = partial(self.processing, avatar_bytes, member_colour)

            # this runs our processing in an executor, stopping it from blocking the thread loop.
            # as we already seeked back the buffer in the other thread, we're good to go
            final_buffer = await self.bot.loop.run_in_executor(None, fn)

            # prepare the file
            file = discord.File(filename="circle.png", fp=final_buffer)

            # send it
            await ctx.send(file=file)


# setup function so this can be loaded as an extension
def setup(bot: commands.Bot):
    bot.add_cog(ImageCog(bot))