import os
import re
import random
import discord
from io import BytesIO
from pathlib import Path
from typing import Union
from PIL import (Image, ImageDraw, ImageFilter, ImageFont)

lvMSGS= ((0, 10), (10, 75), (75, 200), (200, 350), (350, 500), (500, 575), (575, 661), (661, 760), (760, 874), (874, 1005), (1005, 1156), (1156, 1318), (1318, 1503), (1503, 1713), (1713, 1953), (1953, 2226), (2226, 2538), (2538, 2893), (2893, 3298), (3298, 3760), (3760, 4286), (4286, 4843), (4843, 5473), (5473, 6184), (6184, 6988), (6988, 7896), (7896, 8922), (8922, 10082), (10082, 11393), (11393, 12874), (12874, 14548), (14548, 16294), (16294, 18249), (18249, 20439), (20439, 22892), (22892, 25639), (25639, 28716), (28716, 32162), (32162, 36021), (36021, 40344), (40344, 45185), (45185, 50155), (50155, 55672), (55672, 61796), (61796, 68594), (68594, 76139), (76139, 84514), (84514, 93811), (93811, 104130), (104130, 115584), (115584, 128298), (128298, 141769), (141769, 156655), (156655, 173104), (173104, 191280), (191280, 211364), (211364, 233557), (233557, 258080), (258080, 285178), (285178, 315122), (315122, 348210), (348210, 383031), (383031, 421334), (421334, 463467), (463467, 509814), (509814, 560795), (560795, 616874), (616874, 678561), (678561, 746417), (746417, 821059), (821059, 903165), (903165, 988966), (988966, 1082918), (1082918, 1185795), (1185795, 1298446), (1298446, 1421798), (1421798, 1556869), (1556869, 1704772), (1704772, 1866725), (1866725, 2044064), (2044064, 2238250), (2238250, 2439692), (2439692, 2659264), (2659264, 2898598), (2898598, 3159472), (3159472, 3443824), (3443824, 3753768), (3753768, 4091607), (4091607, 4459852), (4459852, 4861239), (4861239, 5298751), (5298751, 5749145), (5749145, 6237822), (6237822, 6768037), (6768037, 7343320), (7343320, 7967502), (7967502, 8644740), (8644740, 9379543), (9379543, 10176804), (10176804, 11041832))
    

# =====================================================================================================
# ------------------------------------- IMAGE GENERATOR FUNCTIONS -------------------------------------
# =====================================================================================================

def GenWelcomeImg(avatar_bytes: bytes, member: Union[discord.User, discord.Member]) -> BytesIO:
    # ===== VARS
    out_image = BytesIO()
    imagedir = Path(__file__).parents[1].joinpath('images')

    # ===== BLUR THE EDGES OF A MEMBERS PFP AND ADD THEIR STATUS
    img =  __square_pfp_blur(avatar_bytes, member.status.__str__(), imagedir, status=False)

    with Image.open(os.path.join(imagedir, "wel", 'welbg.png')).convert('RGBA') as welbg:
        with Image.open(os.path.join(imagedir, "wel", 'c', f'{random.randint(1,123)}.png')).convert('RGBA') as hl:
            
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

def GenGoodbyeImg(avatar_bytes: bytes, member: Union[discord.User, discord.Member]) -> BytesIO:
    # ===== VARS
    out_image = BytesIO()
    imagedir = Path(__file__).parents[1].joinpath('images')

    # ===== BLUR THE EDGES OF A MEMBERS PFP AND ADD THEIR STATUS
    img =  __square_pfp_blur(avatar_bytes, member.status.__str__(), imagedir, status=False)

    with Image.open(os.path.join(imagedir, "wel", 'goodbyebg.png')).convert('RGBA') as welbg:
        with Image.open(os.path.join(imagedir, "wel", 'c', f'{random.randint(1,123)}.png')).convert('RGBA') as hl:
            
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

def GenLevelUPImage(avatar_bytes: bytes, member: Union[discord.User, discord.Member], level: int, rank: int, gems: int, reward:int) -> BytesIO:
    # ===== VARS
    out_image = BytesIO()
    imagedir = Path(__file__).parents[1].joinpath('images')

    # ===== BLUR THE EDGES OF A MEMBERS PFP AND ADD THEIR STATUS
    img = __square_pfp_blur(avatar_bytes, member.status.__str__(), imagedir)

    # ===== OPEN THE MAIN BACKGROUND IMAGE FOR THE LEVELUP IMAGE
    with Image.open(os.path.join(imagedir, "levelupbg2.png")) as background:

        # =====    ADD THE PROFILE IMAGE
        background.paste(img, (10, 10), mask=img)

        # =====    ADD THE GEM IMAGES
        gem1 = Image.open(os.path.join(imagedir, "gem1.png")).convert('RGBA')
        gem2 = Image.open(os.path.join(imagedir, "gem2.png")).convert('RGBA')
        gem3 = Image.open(os.path.join(imagedir, "gem3.png")).convert('RGBA')

        background.paste(gem2, (550, 109), mask=gem2)
        background.paste(gem1, (577, 109), mask=gem1)
        background.paste(gem3, (608, 109), mask=gem3)


        background.paste(gem1, (187, 64), mask=gem1)

        # =====    ADD THE TEXT
        #-------    FONTS
        lfont = ImageFont.truetype(os.path.join(imagedir, "OpenSans-Semibold.ttf"), 42)
        zfont = ImageFont.truetype(os.path.join(imagedir, "OpenSans-Regular.ttf"), 38)
        sfont = ImageFont.truetype(os.path.join(imagedir, "OpenSans-Light.ttf"), 32)

        draw = ImageDraw.Draw(background)

        #= username
        draw.text((160, 105), __get_clean_name(member), fill=(230, 230, 230, 255), font=sfont)
        #= Level up
        draw.text((259, 0), "Level Up", fill=(230, 230, 230, 255), font=lfont)
        #= Reward
        draw.text((222, 50), f"Reward: {reward}", fill=(230, 230, 230, 255), font=zfont)
        #= Level
        draw.text((550, 0), "LV:", fill=(230, 230, 230, 255), font=zfont)
        draw.text((650, 0), f"{level}", fill=(230, 230, 230, 255), font=lfont)
        #= Rank
        draw.text((550, 46), f"Rank:", fill=(230, 230, 230, 255), font=zfont)
        draw.text((650, 46), f"{rank}", fill=(230, 230, 230, 255), font=lfont)
        #= Gems
        draw.text((650, 92), f"{gems}", fill=(230, 230, 230, 255), font=lfont)

        background.save(out_image, "png")

    out_image.seek(0)

    return out_image

def GenProfileImage(avatar_bytes: bytes, member: Union[discord.User, discord.Member], level: int, rank: int, gems: int, nummsgs:int) -> BytesIO:
    # ===== VARS
    out_image = BytesIO()
    imagedir = Path(__file__).parents[1].joinpath('images')

    # ===== BLUR THE EDGES OF A MEMBERS PFP AND ADD THEIR STATUS
    img = __square_pfp_blur(avatar_bytes, member.status.__str__(), imagedir)
    
    with Image.open(os.path.join(imagedir, "profilebg.png")) as background:
        # =====    ADD THE PROFILE IMAGE
        background.paste(img, (10, 10), mask=img)

        # =====    ADD THE GEM IMAGES
        gem1 = Image.open(os.path.join(imagedir, "gem1.png")).convert('RGBA')
        gem2 = Image.open(os.path.join(imagedir, "gem2.png")).convert('RGBA')
        gem3 = Image.open(os.path.join(imagedir, "gem3.png")).convert('RGBA')

        background.paste(gem2, (550, 109), mask=gem2)
        background.paste(gem1, (577, 109), mask=gem1)
        background.paste(gem3, (608, 109), mask=gem3)

        # =====    ADD THE PROGRESS BAR
        background.paste(Image.new("RGBA", (776, 30), (0, 85, 183, 255)), (12, 152), mask=None)

        if level < 100:
            a, b = lvMSGS[level]
            x = int(((nummsgs - a) / (b - a)) * 776)

            if x < 1:
                x = 1
            elif x > 776:
                x = 775
        else:
            x = 776

        background.paste(Image.new("RGBA", (x, 30), (0, 175, 96, 255)), (12, 152), mask=None)

        # =====    ADD THE TEXT
        #-------    FONTS
        lfont = ImageFont.truetype(os.path.join(imagedir, "OpenSans-Semibold.ttf"), 42)
        zfont = ImageFont.truetype(os.path.join(imagedir, "OpenSans-Regular.ttf"), 38)
        sfont = ImageFont.truetype(os.path.join(imagedir, "OpenSans-Light.ttf"), 32)

        draw = ImageDraw.Draw(background)

        #= username
        draw.text((160, 105), __get_clean_name(member), fill=(230, 230, 230, 255), font=sfont)
        #= Level
        draw.text((550, 0), "LV:", fill=(230, 230, 230, 255), font=zfont)
        draw.text((650, 0), f"{level}", fill=(230, 230, 230, 255), font=lfont)
        #= Rank
        draw.text((550, 46), f"Rank:", fill=(230, 230, 230, 255), font=zfont)
        draw.text((650, 46), f"{rank}", fill=(230, 230, 230, 255), font=lfont)
        #= Gems
        draw.text((650, 92), f"{gems}", fill=(230, 230, 230, 255), font=lfont)

        background.save(out_image, "png")

    out_image.seek(0)

    return out_image

def GenGiftedGemsImage(avatar_bytes: bytes, member: Union[discord.User, discord.Member], ggems: int) -> BytesIO:
    # ===== VARS
    out_image = BytesIO()
    imagedir = Path(__file__).parents[1].joinpath('images')

    # ===== BLUR THE EDGES OF A MEMBERS PFP AND ADD THEIR STATUS
    img = __square_pfp_blur(avatar_bytes, member.status.__str__(), imagedir)

    # ===== OPEN THE MAIN BACKGROUND IMAGE FOR THE LEVELUP IMAGE
    with Image.open(os.path.join(imagedir, "levelupbg2.png")) as background:

        # =====    ADD THE PROFILE IMAGE
        background.paste(img, (10, 10), mask=img)

        # =====    ADD THE GEM IMAGES
        gem1 = Image.open(os.path.join(imagedir, "gem1.png")).convert('RGBA')
        gem2 = Image.open(os.path.join(imagedir, "gem2.png")).convert('RGBA')
        gem3 = Image.open(os.path.join(imagedir, "gem3.png")).convert('RGBA')

        background.paste(gem2, (167, 64), mask=gem2)
        background.paste(gem1, (194, 64), mask=gem1)
        background.paste(gem3, (225, 64), mask=gem3)

        # =====    ADD THE TEXT
        #-------    FONTS
        lfont = ImageFont.truetype(os.path.join(imagedir, "OpenSans-Semibold.ttf"), 42)
        zfont = ImageFont.truetype(os.path.join(imagedir, "OpenSans-Regular.ttf"), 38)
        sfont = ImageFont.truetype(os.path.join(imagedir, "OpenSans-Light.ttf"), 32)

        draw = ImageDraw.Draw(background)

        #= username
        draw.text((160, 105), __get_clean_name(member, 40), fill=(230, 230, 230, 255), font=sfont)
        #= Level up
        draw.text((259, 0), "Received", fill=(230, 230, 230, 255), font=lfont)
        #= Reward
        draw.text((260, 50), f"Gems: {ggems}", fill=(230, 230, 230, 255), font=zfont)

        background.save(out_image, "png")

    out_image.seek(0)

    return out_image



# =====================================================================================================
# ------------------------------- FUNCS USED BY THE GEN FUNCTIONS ABOVE -------------------------------
# =====================================================================================================

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


def __round_pfp_blur(avatar_bytes, mstat, imgdir, *, RADIUS=2, status=True, basecolour=(35,39,42,255)):
    
    if isinstance(avatar_bytes, BytesIO):
        avatar_bytes = avatar_bytes.getvalue()

    diam = 2*RADIUS

    with Image.open(BytesIO(avatar_bytes)).convert('RGBA') as ava:
        with Image.new('L', ava.size, 0) as mask:
            draw = ImageDraw.Draw(mask)
            draw.ellipse([(diam, diam), (ava.size[0] - diam, ava.size[1] - diam)], fill=255)
            mask = mask.filter(ImageFilter.GaussianBlur(RADIUS))
            im = Image.alpha_composite(Image.new('RGBA', ava.size, basecolour), Image.composite(ava, Image.new('RGBA', ava.size, (0,0,0,0)), mask))

    return im


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