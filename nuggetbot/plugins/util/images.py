import os
import re
import random
import discord
from io import BytesIO
from typing import Union
from PIL import (Image, ImageDraw, ImageFilter, ImageFont)




def GenWelcomeImg(avatar_bytes: bytes, member: Union[discord.User, discord.Member]) -> BytesIO:
    print(os.path.split(os.path.realpath(__file__))[0])


    # ===== VARS
    out_image = BytesIO()
    imagedir = os.path.join(os.path.split(os.path.split(os.path.realpath(__file__))[0])[0], "images")
    highLight = os.path.join(imagedir, "wel", 'c', f'{random.randint(1,61)}.png')

    # ===== BLUR THE EDGES OF A MEMBERS PFP AND ADD THEIR STATUS
    img =  __square_pfp_blur(avatar_bytes, member.status.__str__(), imagedir, status=False)

    with Image.open(os.path.join(imagedir, "wel", 'welbg.png')).convert('RGBA') as welbg:
        with Image.open(highLight).convert('RGBA') as hl:
            
            # = ADD THE HIGHLIGHT TO THE IMAGE
            workingImg = Image.alpha_composite(welbg, hl)

            # = ADD THE PFP TO THE IMAGE
            workingImg.paste(img, (44, 29), mask=img)

            # = MAKE OUR FONT
            font = ImageFont.truetype(os.path.join(imagedir, "OpenSans-Regular.ttf"), 24)

            draw = ImageDraw.Draw(workingImg)
            draw.text((188, 98), __get_clean_name(member, 30, at=True), fill=(135, 134, 142, 255), font=font)

            workingImg.save(out_image, "png")

    out_image.seek(0)

    return out_image






def __square_pfp_blur(avatar_bytes, mstat, imgdir, *, RADIUS=2, status=True):
    """
    This just blurs the edges of a members pfp
    """

    diam = 2*RADIUS

    ###===== OPEN THE MEMBERS STATUS IMAGE
    if status:
        status = Image.open(os.path.join(imgdir, f"{mstat if mstat in ['offline', 'online', 'dnd', 'idle'] else 'online'}.png")).convert('RGBA')

    ###===== WITH OPEN THE MEMBERS PFP
    with Image.open(BytesIO(avatar_bytes)).convert('RGBA') as rgba_avatar:
        canvas = Image.new('RGBA', (rgba_avatar.size[0]+diam, rgba_avatar.size[1]+diam), (35,39,42,0))
        canvas.paste(rgba_avatar, (RADIUS, RADIUS))

    ###===== GENERATE OUR BLUR MASK
    with Image.new('L', canvas.size, 0) as mask:
        draw = ImageDraw.Draw(mask)
        x0, y0 = 0, 0
        x1, y1 = canvas.size
        for d in range(diam+RADIUS):
            x1, y1 = x1-1, y1-1
            alpha = 255 if d<RADIUS else int(255*(diam+RADIUS-d)/diam)
            draw.rectangle([x0, y0, x1, y1], outline=alpha)
            x0, y0 = x0+1, y0+1

        blur = canvas.filter(ImageFilter.GaussianBlur(RADIUS/2))
        canvas.paste(blur, mask=mask)
        
    ###===== RETURN OUR COMPOSITED IMAGE
    # order of layers: new image, blured member pfp, member status image
    if status:
        return Image.alpha_composite(Image.new('RGBA', canvas.size, (35,39,42,255)), Image.alpha_composite(canvas, status))
    else:
        return Image.alpha_composite(Image.new('RGBA', canvas.size, (35,39,42,255)), canvas)

def __get_clean_name(member, maxlen=22, *, at=False):

    # ===== IF THE MEMBER HAS A NICKNAME, USE THAT AND IGNORE THE DISCRIMINATOR
    if member.nick:
        name = f'@{member.nick}' if at else member.nick
        re.sub(r'[^\x00-\x7f]',r'', name).strip()

        if len(name) > maxlen: 
            name = f"{name[:maxlen]}..."
    
    # ===== IF MEMBER ONLY HAS THEIR USERNAME, USE THAT AND INCLUDE DISCRIMINATOR      
    else:
        mname = f'@{member.name}' if at else member.name
        re.sub(r'[^\x00-\x7f]',r'', mname).strip()

        if len(f"{mname}#{member.discriminator}") <= maxlen:
            name = f"{mname}#{member.discriminator}"

        elif len(mname) <= maxlen:
            name = mname

        else:
            name = f"{mname[:maxlen]}..."
        
    return name 




"""
    rgba_avatar = ImageOps.fit(rgba_avatar, mask.size, centering=(0.5, 0.5))
    rgba_avatar.putalpha(mask)



with Image.open('pfp2.png').convert('RGBA') as rgba_avatar:
    with Image.new('L', rgba_avatar.size, 255).convert('RGBA') as mask:
        draw = ImageDraw.Draw(mask)
        draw.ellipse([(0,0), rgba_avatar.size], fill=0)
        with Image.new('RGBA', rgba_avatar.size, (0,0,0,0)) as crop_avatar:
            crop_avatar.paste(rgba_avatar, mask=mask)
    canvas = Image.new('RGBA', (crop_avatar.size[0]+diam, crop_avatar.size[1]+diam), (35,39,42,0))
    canvas.paste(crop_avatar, (RADIUS, RADIUS))
        
import numpy as np


with Image.open('pfp2.png').convert('RGBA') as rgba_avatar:
    with Image.new('L', rgba_avatar.size, 0) as mask:
        draw = ImageDraw.Draw(mask)
        draw.ellipse([(0,0), rgba_avatar.size], fill=255)
        npImage=np.dstack((np.array(rgba_avatar), np.array(mask)))
    canvas = Image.new('RGBA', (rgba_avatar.size[0]+diam, rgba_avatar.size[1]+diam), (35,39,42,0))
    canvas.paste(Image.fromarray(npImage), (RADIUS, RADIUS))



with Image.open('pfp2.png').convert('RGBA') as rgba_avatar:
    with Image.new('L', rgba_avatar.size, 255) as mask:
        draw = ImageDraw.Draw(mask)
        rgba_avatar.putalpha(mask)

    canvas = Image.new('RGBA', (rgba_avatar.size[0]+diam, rgba_avatar.size[1]+diam), (35,39,42,0))
    canvas.paste(rgba_avatar, (RADIUS, RADIUS))


@working

offset = 0
blur_radius = 2
offset = blur_radius * 2 + offset
with Image.open('pfp2.png').convert('RGBA') as rgba_avatar:
    canvas = Image.alpha_composite(Image.new('RGBA', rgba_avatar.size, (35,39,42, 255)), rgba_avatar)

    with Image.new('L', rgba_avatar.size, 0) as mask:
        draw = ImageDraw.Draw(mask)
        draw.ellipse((offset, offset, canvas.size[0] - offset, canvas.size[1] - offset), fill=255)
        mask = mask.filter(ImageFilter.GaussianBlur(blur_radius))
        canvas.putalpha(mask)

return canvas

@working

####    THIS CROPS AN IMAGE TO A CIRCLE AND KEEPS TRANSPEARANCY 

with Image.open('pfp2.png').convert('RGBA') as rgba_avatar:
    with Image.new('L', rgba_avatar.size, 0) as mask:
        draw = ImageDraw.Draw(mask)
        draw.ellipse([(0,0), rgba_avatar.size], fill=255)
        im = Image.composite(rgba_avatar, Image.new('RGBA', rgba_avatar.size, (0,0,0,0)), mask)

@working

####    THIS CROPS AN IMAGE TO A CIRCLE AND KEEPS TRANSPEARANCY PLUS BLURS EDGES

offset = 0
blur_radius = 20
offset = blur_radius * 2 + offset
with Image.open('pfp2.png').convert('RGBA') as rgba_avatar:
    with Image.new('L', rgba_avatar.size, 0) as mask:
        draw = ImageDraw.Draw(mask)
        draw.ellipse((offset, offset, rgba_avatar.size[0] - offset, rgba_avatar.size[1] - offset), fill=255)
        mask = mask.filter(ImageFilter.GaussianBlur(blur_radius))
        im = Image.composite(rgba_avatar, Image.new('RGBA', rgba_avatar.size, (0,0,0,0)), mask)

@working


with Image.new('L', canvas.size, 255) as mask:
    draw = ImageDraw.Draw(mask)
    x0, y0 = 0, 0
    x1, y1 = canvas.size
    for d in range(diam+RADIUS):
        alpha = 255 if d<RADIUS else int(255*(diam+RADIUS-d)/diam)
        draw.ellipse([x0, y0, x1, y1], outline=alpha)
        x1, y1 = x1-1, y1-1
        x0, y0 = x0+1, y0+1
    alpha = 0
    draw.ellipse([x0, y0, x1, y1], fill=alpha, outline=alpha)
    blur = canvas.filter(ImageFilter.GaussianBlur(RADIUS/2))
    canvas.paste(blur, mask=mask)


out = Image.alpha_composite(Image.new('RGBA', canvas.size, (35,39,42,255)), canvas)


with Image.new('L', (136,136), 255) as mask:
    draw = ImageDraw.Draw(mask)
    x0, y0 = 0, 0
    x1, y1 = (136,136)
    for d in range(diam+RADIUS):
        alpha = 255 if d<RADIUS else int(255*(diam+RADIUS-d)/diam)
        draw.ellipse([x0, y0, x1, y1], fill=alpha, outline=alpha)
        x1, y1 = x1-1, y1-1
        x0, y0 = x0+1, y0+1
    
    alpha = 0
    draw.ellipse([x0, y0, x1, y1], fill=alpha, outline=alpha)


mask = Image.new('L', (136,136), 0)

"""