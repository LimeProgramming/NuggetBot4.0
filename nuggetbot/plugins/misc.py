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

import qrcode
import random
import discord
import asyncio
import pathlib
import datetime

from io import BytesIO
from PIL import Image
from discord.ext import commands

description = """
A Collection of commands that don't really fit in anywhere else.
"""

class Misc(commands.Cog):

    def __init__(self, bot: commands.Bot):

        # we need to include a reference to the bot here so we can access its loop later.
        self.bot = bot

  # -------------------- LISTENERS --------------------


  # -------------------- COG COMMANDS --------------------
    @commands.dm_only()
    @commands.command(pass_context=True, hidden=True, name='getcrypto', aliases=[])
    async def cmd_getcrypto(self, ctx, coin = None):
        """
        [DM Only] Gets cryptocurrency wallet address and QRCode for all or specifed wallets defined in bot config.

        Usage:
            [p]getcrypto 
                Lists all cryptocurrency coins and wallet addresses.

            [p]getcrypto list 
                Lists all cryptocurrency coins and wallet addresses.
            
            [p]getcrypto <coin abbreviation>
                Returns wallet address as string and QR image.

            [p]getcrypto random
                Returns random wallet address as string and QR image.     
        """

        if coin is None or coin.lower() == "list":
            r = "__**All Guild Wallets**__"

            for i in self.bot.config.wallets.keys():
                r += f"\n{i}: {self.bot.config.wallets[i][1]}"

            await ctx.send(r)

        elif coin.upper() in self.bot.config.wallets.keys():
            async with ctx.typing():
                coin = coin.upper()

                r = f"__**{self.bot.config.wallets[coin][0]}/{coin}**__\n"
                r += f"Address: {self.bot.config.wallets[coin][1]}"

                qr = await self.getWalletQR(self.bot.config.wallets[coin])

                await ctx.send(r, file=discord.File(filename=f"{self.bot.config.wallets[coin][0]}.png", fp=qr))
        
        elif coin.lower() == "random":
            coin = random.choice(tuple(self.bot.config.wallets.keys()))

            async with ctx.typing():
                r = f"__**{self.bot.config.wallets[coin][0]}/{coin}**__\n"
                r += f"Address: {self.bot.config.wallets[coin][1]}"

                qr = await self.getWalletQR(self.bot.config.wallets[coin])

                await ctx.send(r, file=discord.File(filename=f"{self.bot.config.wallets[coin][0]}.png", fp=qr))

        else:
            await ctx.send_help()

        return 




  # -------------------- FUNCTIONS --------------------
    
    async def getWalletQR(self, coin):
        """
        Generates a wallet QR code from the coin variable provided.
        This will read the QR code from data cache if it exists, if not then it will generate the QR code and store it.
        
        Returns
        --------
        :class:`bytes`
            QR code image.
        """

        out_image = BytesIO()
        p = pathlib.Path.cwd() / "data" / "cache" / "wallets"

        if not p.exists():
            p.mkdir()

        p = p / f"{coin[0]}_{coin[1]}.png"

        if not p.exists():
            
            # === GENERATE THE QRCODE IF IT DOES NOT EXIST
            qr = qrcode.QRCode(
                error_correction=qrcode.constants.ERROR_CORRECT_M,
                box_size=6,
                border=1
                )
            qr.add_data(coin[1])
            qr.make(fit=True)

            img = qr.make_image(fill_color="black", back_color="white").get_image()

            with open(p, 'wb') as f:
                img.save(f)
        
        # ===== OPEN THE FILE AND SAVE IT BYTES.IO
        with Image.open(p) as f:
            f.save(out_image, "png")

        out_image.seek(0)

        return out_image


def setup(bot: commands.Bot):
    bot.add_cog(Misc(bot))