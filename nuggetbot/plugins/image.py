# basic dependencies
import discord
from discord.ext import commands
from discord.utils import _bytes_to_base64_data
import os

# aiohttp should be installed if discord.py is
import aiohttp

# PIL can be installed through
# `pip install -U Pillow`
from PIL import Image, ImageDraw, ImageFont

# partial lets us prepare a new function with args for run_in_executor
from functools import partial

# BytesIO allows us to convert bytes into a file-like byte stream.
from io import BytesIO

# this just allows for nice function annotation, and stops my IDE from complaining.
from typing import Union

from nuggetbot.util.chat_formatting import AVATAR_URL_AS

class ImageCog(commands.Cog):
    def __init__(self, bot: commands.Bot):

        # we need to include a reference to the bot here so we can access its loop later.
        self.bot = bot

        # create a ClientSession to be used for downloading avatars
        self.session = aiohttp.ClientSession(loop=bot.loop)


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
    def processing3(avatar_bytes: bytes, colour: tuple) -> BytesIO:
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

                        background.paste(img, (0, 0), mask=None)

                        #img.save(out_avatar, "png")

                        #with Image.open(out_avatar) as img2:

                        img = Image.alpha_composite(background, status)

                        #img.save(ava_status, "png")

        print(1)
        #with Image.open(ava_status).convert('RGB') as ava:
            
        #base image is 132
        with Image.new("RGBA", (700, 148), (0, 0, 0)) as background:

            #img.paste(background, (8, 8), mask=None)

            background.paste(img, (8, 8), mask=None)


            font = ImageFont.truetype(os.path.join(imagedir, "OpenSans-Light.ttf"), 16)

            draw = ImageDraw.Draw(background)

            # font = ImageFont.truetype(<font-file>, <font-size>)
            #font = ImageFont.truetype("sans-serif.ttf", 16)

            # draw.text((x, y),"Sample Text",(r,g,b))
            draw.text((160, 20),"Sample Text", fill=(255, 0, 0, 255), font=font)

            #img.save(ava_status, "png")
            print(2)
            background.save(ava_status, "png")

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

            if isinstance(member, discord.Member):
                # get the user's colour, pretty self explanatory
                member_colour = member.colour.to_rgb()
            else:
                # if this is in a DM or something went seriously wrong
                member_colour = (0, 0, 0)

            # grab the user's avatar as bytes
            #avatar_bytes = await self.get_avatar(member)

            avatar_bytes = await member.avatar_url_as(format='png', static_format='webp', size=128).read()

            # create partial function so we don't have to stack the args in run_in_executor
            fn = partial(self.processing3, avatar_bytes, member_colour)

            # this runs our processing in an executor, stopping it from blocking the thread loop.
            # as we already seeked back the buffer in the other thread, we're good to go
            final_buffer = await self.bot.loop.run_in_executor(None, fn)

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