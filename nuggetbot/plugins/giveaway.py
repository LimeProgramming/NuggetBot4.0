from discord.ext import commands
import discord
import asyncio
import asyncpg
import datetime
import random

import dblogin 
from nuggetbot.config import Config
from nuggetbot.database import DatabaseLogin
from nuggetbot.database import DatabaseCmds as pgCmds
#from .ctx_decorators import in_channel, is_core, in_channel_name, in_reception, has_role, is_high_staff, is_any_staff
from .cog_utils import in_channel, is_core, in_channel_name, in_reception, has_role, is_high_staff, is_any_staff, SAVE_COG_CONFIG, LOAD_COG_CONFIG
#https://discordpy.readthedocs.io/en/latest/ext/commands/api.html#bot

giveaway_channel_id = int()

class Giveaway(commands.Cog):
    """Lime's Giveaway System."""

    config = None 
    delete_after = 15

    def __init__(self, bot):
        #self.RafEntryActive = False
        #self.RafDatetime = []
        self.bot = bot
        self.cogset = dict()
        #self.config = Config()
        Giveaway.config = Config()
        self.databaselg = DatabaseLogin()
        self.giveaway_role = None

        #self._last_result = None
    
  #-------------------- LISTENERS --------------------
    @commands.Cog.listener()
    async def on_ready(self):
        credentials = {"user": dblogin.user, "password": dblogin.pwrd, "database": dblogin.name, "host": dblogin.host}
        self.db = await asyncpg.create_pool(**credentials)

        ###===== LOAD COG SETTINGS
        self.cogset = await LOAD_COG_CONFIG(cogname="giveaway")

        if not self.cogset:
            self.cogset= dict(
                RafEntryActive=    False,
                RafDatetime=       ""
            )

            await SAVE_COG_CONFIG(self.cogset, cogname="giveaway")

        giveaway_channel_id = Giveaway.config.gvwy_channel_id

    @commands.Cog.listener()
    async def on_member_update(self, before, after):

        if not self.giveaway_role:
            self.giveaway_role = discord.utils.get(after.guild.roles, id=Giveaway.config.gvwy_role_id)
        
        #===== ASSUMING STAFF GIVE A MEMBER THE GIVEAWAY ROLE
        if (self.giveaway_role not in before.roles) and (self.giveaway_role in after.roles):
            past_wins = await self.db.fetchval(pgCmds.GET_GVWY_NUM_WINS, after.id)

            #=== LEVELED ENTRY SYSTEM
            if not past_wins:
                entries=3
            elif past_wins == 1:
                entries=2
            else:
                entries=1
    
            await self.db.execute(pgCmds.ADD_GVWY_ENTRY, after.id, entries, datetime.datetime.utcnow())
            await after.add_roles(self.giveaway_role, reason="Staff added user to giveaway.")

        #===== ASSUMING STAFF REMOVED THE GIVEAWAY ROLE FROM A MEMBER
        elif (self.giveaway_role in before.roles) and (self.giveaway_role not in after.roles):
            await self.db.execute(pgCmds.REM_MEM_GVWY_ENTRIES, after.id)


  #-------------------- LOCAL COG STUFF --------------------
    async def cog_after_invoke(self, ctx):
        if not ctx.message.guild:
            return 
            
        if Giveaway.config.delete_invoking:
            await ctx.message.delete()

        return


  #-------------------- STATIC METHODS --------------------
    @staticmethod
    async def Get_user_id(content):
        try:
            args= content.split(" ")
            if len(args) > 2:
                return False 

            #=== SPLIT, REMOVE MENTION WRAPPER AND CONVERT TO INT
            user_id = args[1]
            user_id = user_id.replace("<", "").replace("@", "").replace("!", "").replace(">", "")
            user_id = int(user_id)
            return user_id

        except (IndexError, ValueError):
            return False

    @staticmethod
    async def Get_user_id_reason(content):
        try:
            args = content.split(" ")
            if len(args) < 2:
                return (False, False)

            #=== SPLIT, REMOVE MENTION WRAPPER AND CONVERT TO INT
            user_id = args[1]
            user_id = user_id.replace("<", "").replace("@", "").replace("!", "").replace(">", "")
            user_id = int(user_id)

            if len(args) > 2:
                reason = " ".join(args[2:])
                reason = reason[:1000]

            else:
                reason = None

            return (user_id, reason)

        except (IndexError, ValueError):
            return (False, False)

    @staticmethod
    async def oneline_valid(content):
        try:
            args = content.split(" ")
            if len(args) > 1:
                return False 

            return True

        except (IndexError, ValueError):
            return False

    @staticmethod
    async def split_list(arr, size=100):
        """Custom function to break a list or string into an array of a certain size"""

        arrs = []

        while len(arr) > size:
            pice = arr[:size]
            arrs.append(pice)
            arr = arr[size:]

        arrs.append(arr)
        return arrs


  #-------------------- COMMANDS --------------------
    ###Users assign themselves the giveaway role
    @is_core()
    @in_channel([giveaway_channel_id])
    @commands.command(pass_context=False, hidden=False, name='giveaway', aliases=["gvwy"])
    async def cmd_giveaway(self, ctx):
        """
        [Core] Users can give themselves the giveaway role

        Useage:
            [prefix]giveaway
        """
        #===== GET RAFLE ROLE
        giveawayRole = discord.utils.get(ctx.guild.roles, id=Giveaway.config.gvwy_role_id)

        ##===== IF RAFFLE IS OPEN
        if self.cogset['RafEntryActive']:

            #=== IF MEMBER IS IN RAFFLE
            if await self.db.fetchval(pgCmds.GET_MEM_EXISTS_GVWY_ENTRIES, ctx.message.author.id):

                #= REM ROLE
                await ctx.message.author.remove_roles(giveawayRole, reason="User left the giveaway.")

                #= REM FROM DATABASE
                await self.db.execute(pgCmds.REM_MEM_GVWY_ENTRIES, ctx.author.id)

                #= RESPOND
                await ctx.channel.send(content="{} has left the giveaway, better luck next time. :negative_squared_cross_mark: ".format(ctx.author.nick or ctx.author.name), delete_after=Giveaway.delete_after)
                return

            #-------------------- ENTRY BLOCKING --------------------
            #=== IF USER HAS BEEN BLACKLISTED FROM GIVEAWAY    
            if Giveaway.config.gvwy_enforce_blacklist:
                if await self.db.fetchval(pgCmds.GET_MEM_EXISTS_GVWY_BLOCKS, ctx.author.id):
                    await ctx.channel.send(content=f"Sorry {ctx.author.mention}, but you have been banned from giveaways on this server.", delete_after=Giveaway.delete_after)
                    return

            #=== IF USER JOINED TOO RECENTLY
            if (datetime.datetime.utcnow() - ctx.author.joined_at).seconds < Giveaway.config.gvwy_min_time_on_srv:
                await ctx.channel.send(content=f"Sorry {ctx.author.mention}, but you have to be on the server for a minimum of 30 days to enter the giveaway.", delete_after=Giveaway.delete_after)
                return

            #=== IF NOT ACTIVE ENOUGH
            if len(await self.db.fetch(pgCmds.GET_MEMBER_MSGS_BETWEEN, ctx.author.id, self.cogset['RafDatetime']["open"], self.cogset['RafDatetime']["past"])) < Giveaway.config.gvwy_min_msgs:
                await ctx.channel.send(content=f"Sorry {ctx.author.mention}, but you have not been active enough on the server to enter the giveaway.", delete_after=Giveaway.delete_after) 
                return

            #-------------------- ENTER MEMBER --------------------
            past_wins = await self.db.fetchval(pgCmds.GET_GVWY_NUM_WINS, ctx.author.id)

            #=== LEVELED ENTRY SYSTEM
            if not past_wins:
                entries=3
            elif past_wins == 1:
                entries=2
            else:
                entries=1

            await self.db.execute(pgCmds.ADD_GVWY_ENTRY, ctx.author.id, entries, ctx.message.created_at)
            await ctx.author.add_roles(giveawayRole, reason="User joined the giveaway")

            await ctx.channel.send(content="{} has entered the giveaway, goodluck :white_check_mark:".format(ctx.author.nick or ctx.author.name), delete_after=Giveaway.delete_after)
            return 
        #===== IF RAFFLE IS CLOSED
        else:
            if await self.db.fetchval(pgCmds.GET_MEM_EXISTS_GVWY_ENTRIES, ctx.author.id):
                #= REM ROLE
                await ctx.author.remove_roles(giveawayRole, reason="User left the giveaway")

                #= REM FROM DATABASE
                await self.db.execute(pgCmds.REM_MEM_GVWY_ENTRIES, ctx.author.id)

                #= RESPOND TO USER
                await ctx.channel.send(content="{} has left the giveaway after entries have been closed. If this was a mistake ask staff to add you back into the giveaway but no promices that you'll be noticed in time. :negative_squared_cross_mark: ".format(ctx.author.nick or ctx.author.name), delete_after=Giveaway.delete_after)
                return

            await ctx.channel.send(content="Sorry {}, but giveaway entries are not open right now. Please check back later.".format(ctx.author.nick or ctx.author.name), delete_after=Giveaway.delete_after)
            return

    ###Adds a user to the blacklist
    @is_high_staff()
    @commands.command(pass_context=True, hidden=False, name='addblacklist', aliases=["gvwy_addblacklist", "gvwy_addblock"])
    async def cmd_addblacklist(self, ctx):
        """
        [Admin/Mod] Adds a user to the blacklist.

        Useage:
            [prefix]addblacklist <userid/mention> <reason>
        """
        user_id, reason = await Giveaway.Get_user_id_reason(ctx.message.content)

        if not user_id:
            await ctx.channel.send(content="`Useage: [p]addblacklist <userid/mention> <reason>, [Admin/Mod] Adds a user to the blacklist.`", delete_after=Giveaway.delete_after)
            return
        
        #===== if a user was already blacklisted
        if await self.db.fetchval(pgCmds.GET_MEM_EXISTS_GVWY_BLOCKS, user_id):
            await ctx.channel.send(content="User already on the raffle blacklist.", delete_after=Giveaway.delete_after)
            return
        
        #===== BLACKLIST THE USER
        else:
            await self.db.execute(pgCmds.ADD_GVWY_BLOCKS_NONTIMED, user_id, ctx.author.id, reason, ctx.message.created_at)
            
            #=== IF MEMBER IS IN THE GIVEAWAY ENTRIES
            if await self.db.fetchval(pgCmds.GET_MEM_EXISTS_GVWY_ENTRIES, user_id):

                #= REMOVE FROM GIVEAWAY ENTRIES
                await self.db.execute(pgCmds.REM_MEM_GVWY_ENTRIES, user_id)
                
                #= REMOVE GIVEAWAY ROLE
                member = ctx.guild.get_member(user_id)
                await member.remove_roles(discord.utils.get(ctx.guild.roles, id=Giveaway.config.gvwy_role_id), reason="User baned from giveaways.")

                await ctx.channel.send(content=f"<@{user_id}> has been added to the raffle blacklist and removed from giveaway entries")
                return

            await ctx.channel.send(content=f"<@{user_id}> has been added to the raffle blacklist.")
            return

    ###Remove a user from the blacklist
    @is_high_staff()
    @commands.command(pass_context=True, hidden=False, name='remblacklist', aliases=["gvwy_remblacklist", "gvwy_remblock"])
    async def cmd_remblacklist(self, ctx):
        """
        [Admin/Mod] Removes a member from the blacklist.

        Useage:
            [prefix]remblacklist <userid/mention>
        """
        user_id = await Giveaway.Get_user_id(ctx.message.content)

        #===== IF THE SUPPILED USERID IS NOT VALID
        if not user_id:
            await ctx.channel.send(content="`Useage: [p]remblacklist <userid/mention>, [Admin/Mod] Removes a member from the blacklist.`", delete_after=Giveaway.delete_after)
            return 
        
        #===== IF USER IS NOT ON BLOCK LIST
        if not await self.db.fetchval(pgCmds.GET_MEM_EXISTS_GVWY_BLOCKS, user_id):
            await ctx.channel.send(content=f"<@{user_id}> was not on the raffle blacklist.", delete_after=Giveaway.delete_after)
            return
        
        #===== ADD USER TO BLOCK LIST 
        await self.db.execute(pgCmds.REM_MEM_GVWY_BLOCK, user_id)
        await ctx.channel.send(content=f"<@{user_id}> has been removed from the raffle blacklist.", delete_after=Giveaway.delete_after)
        return 

    ###Returns a list of users who are blacklisted from the raffle
    @is_any_staff()
    @commands.command(pass_context=True, hidden=False, name='checkblacklist', aliases=["gvwy_checkblacklist", "gvwy_checkblocks"])
    async def cmd_checkblacklist(self, ctx):
        """
        [Any Staff] Returns a list of users who are blacklisted from the raffle

        Useage:
            [prefix]checkblacklist
        """
        if not await Giveaway.oneline_valid(ctx.message.content):
            await ctx.channel.send(content="`Useage: [p]checkblacklist, [Any Staff] Returns a list of users who are blacklisted from the raffle.`", delete_after=Giveaway.delete_after)
            return 

        #===== GET THE DATA FROM THE DATABASE
        blacklistMembers = await self.db.fetch(pgCmds.GET_ALL_GVWY_BLOCKS)

        #===== IF NO-ONE IS BLOCKED
        if not blacklistMembers:
            await ctx.channel.send(content="No blacklisted members.", delete_after=Giveaway.delete_after)
            return
        
        #===== SET THE MESSAGE HEADER
        listedMembers = "```css\nUsers blacklisted from raffle.\n```\n"

        #===== LOOP ALL MEMBERS IN THE SERVER
        for member in ctx.guild.members:

            #=== IF MEMBER IS BLACKLISTED
            if member.id in [i['user_id'] for i in blacklistMembers]:

                for j in blacklistMembers:
                    if member.id == j['user_id']:
                        x = j 
                        break

                listedMembers += "{0.name}#{0.discriminator} | Mention: {0.mention} | Reason: {1} | When: {2}\n".format(member, x["reason"], x["timestamp"].strftime('%b %d, %Y %H:%M:%S'))
            
        #===== SPLIT MAIN MESSAGE STRING INTO AN ARRAY, LIMITING MAX NUM OF CHARS TO 2000
        listedMembers = await Giveaway.split_list(listedMembers, size=2000)
        
        #===== MESSAGE OUT THE BLACKLISTED MEMBERS
        for i in range(len(listedMembers)):
            await ctx.send(listedMembers[i])

        #===== DONE
        return

    ###Adds a user to the previous winners list
    @is_high_staff()
    @commands.command(pass_context=True, hidden=True, name='makeprewinner', aliases=["gvwy_makeprewinner"])
    async def cmd_makeprewinner(self, ctx):
        """
        [Admin/Mod] Adds a user to the list of previous winners.

        Useage:
            [prefix]makeprewinner <userid/mention>
        """
        user_id = await Giveaway.Get_user_id(ctx.message.content)

        #===== IF THE SUPPILED USERID IS NOT VALID
        if not user_id:
            await ctx.channel.send(content="`Useage: [p]makeprewinner <userid/mention>,\n[Admin/Mod] Adds a user to the list of previous winners.`", delete_after=Giveaway.delete_after)
            return 
        
        #===== ADD USER TO WINNERS LIST 
        await self.db.execute(pgCmds.ADD_GVWY_PRE_WINS, user_id, datetime.datetime.utcnow())

        await ctx.channel.send(content=f"<@{user_id}> has been added to the giveaway winner list.", delete_after=Giveaway.delete_after)
        return

    ###Remove a user to the previous winners list
    @is_high_staff()
    @commands.command(pass_context=True, hidden=True, name='remprewinner', aliases=["gvwy_remprewinner"])
    async def cmd_remprewinner(self, ctx):
        """
        [Admin/Mod] Removes a member from the previous winners list.

        Useage:
            [prefix]remprewinner <userid/mention>
        """
        user_id = await Giveaway.Get_user_id(ctx.message.content)

        #===== IF THE SUPPILED USERID IS NOT VALID
        if not user_id:
            await ctx.channel.send(content="`Useage: [p]remprewinner <userid/mention>, [Admin/Mod] Removes a member from the previous winners list.`", delete_after=Giveaway.delete_after)
            return 

        #===== GET DATA FROM DATABASE
        prewindata = await self.db.fetchrow(pgCmds.GET_MEM_GVWY_PRE_WIN, user_id)

        #===== IF USER IS NOT ON BLOCK LIST
        if not prewindata:
            await ctx.channel.send(content=f"<@{user_id}> has never won before.", delete_after=Giveaway.delete_after)
            return
        
        pastwins = int(prewindata['num_wins'])

        #===== DEINCREMENT THE USERS NUMBER OF WINS IF NEEDED
        if pastwins > 1:
            await self.db.execute(pgCmds.SET_GVWY_NUM_WINS, (prewindata['num_wins'] - 1), user_id)
            await ctx.channel.send(content=f"<@{user_id}> has had their number of previous wins set to {(pastwins - 1)}.", delete_after=Giveaway.delete_after)
            return
        
        #===== OTHERWISE JUST REMOVE THEM FROM THE PREVIOUS WINNERS LIST
        await self.db.execute(pgCmds.REM_MEM_GVWY_PRE_WINS, user_id)
        await ctx.channel.send(content=f"<@{user_id}> has been removed from the previous winners list.", delete_after=Giveaway.delete_after)
        return
        
    ###Returns a list of users who have won the raffle before
    @is_any_staff()
    @commands.command(pass_context=True, hidden=True, name='checkprewinners', aliases=["gvwy_checkprewinners"])
    async def cmd_checkprewinners(self, ctx):
        """
        [Any Staff] Returns a list of users who have won the raffle before.

        Useage
            [prefix]checkprewinners
        """
        #===== IS THE INPUT VALID
        if not await Giveaway.oneline_valid(ctx.message.content):
            await ctx.channel.send(content="`Useage: [p]checkprewinners, [Any Staff] Returns a list of users who have won the raffle before.`", delete_after=Giveaway.delete_after)
            return 

        #===== GET THE DATA FROM THE DATABASE
        preWinners = await self.db.fetch(pgCmds.GET_ALL_GVWY_PRE_WINS)
        
        #===== IF NO-ONE WON BEFORE
        if not preWinners:
            await ctx.channel.send(content="No-one ever won before.", delete_after=Giveaway.delete_after)
            return

        #===== MAKE MESSAGE HEADER
        listedMembers = "```css\nUsers who have won the raffle before.\n```\n"

        #===== LOOP ALL MEMBERS IN THE SERVER
        for member in ctx.guild.members:

            #=== IF MEMBER WON BEFORE
            if member.id in [i['user_id'] for i in preWinners]:

                for j in preWinners:
                    if member.id == j['user_id']:
                        x = j 
                        break

                listedMembers += "{0.name}#{0.discriminator} | Mention: {0.mention} | Number Wins: {1} | Last Win: {2}\n".format(member, x["num_wins"], x["last_win"].strftime('%b %d, %Y %H:%M:%S'))
            
        #===== SPLIT MAIN MESSAGE STRING INTO AN ARRAY, LIMITING MAX NUM OF CHARS TO 2000
        listedMembers = await Giveaway.split_list(listedMembers, size=2000)
        
        #===== MESSAGE OUT THE PREVIOUS WINNERS MEMBERS
        for i in range(len(listedMembers)):
            await ctx.send(listedMembers[i])

        #===== DONE
        return
        
    ###Support or above calls a winner of the raffle 
    @is_any_staff()
    @commands.command(pass_context=True, hidden=False, name='callgiveawaywinner', aliases=["gvwy_callwinner"])
    async def cmd_callgiveawaywinner(self, ctx):
        """
        [Any Staff] Returns a random user who has entered the Giveaway. Base Stats: 3 entries if never won, 2 entries if won once, 1 entry if won more twice or more.

        Useage:
            [prefix]callgiveawaywinner
        """
        async with ctx.typing():
            dbGvwyEntries = await self.db.fetch(pgCmds.GET_ALL_GVWY_ENTRIES)
            draw = list()

            #===== IF NO-ONE IS IN THE GIVEAWAY
            if not dbGvwyEntries:
                await ctx.channel.send(content="No entries in the giveaway.")
                return 
            
            #===== BUILD A LIST OF USER ID'S TO DRAW
            for entry in dbGvwyEntries:
                #=== i = LIST WITH USER_ID MULTIPLED BY THE AMOUNT OF ENTRIES THEY HAVE
                i = [entry["user_id"]] * entry['entries']
                draw = draw + i
            
            #===== SHUFFLE THE LIST OF USER ID'S
            random.shuffle(draw)
            
            #===== PICK A WINNER
            winnerid = random.choice(draw)
            
            #===== WRITE WINNER TO DATABASE
            await self.db.execute(pgCmds.ADD_GVWY_PRE_WINS, winnerid, datetime.datetime.utcnow())
            
            #===== GET MEMBER FROM GUILD AND REMOVE GIVEAWAY ROLE
            winner = ctx.guild.get_member(winnerid)
            await winner.remove_roles(discord.utils.get(ctx.guild.roles, id=Giveaway.config.gvwy_role_id), reason="User won giveaway.")
            
            #===== ANNOUNCE WINNER
            await ctx.channel.send(content=f"Congratulations {winner.mention}! You've won a prize in the giveaway.")
            return

    ###Bastion or above close raffle
    @is_high_staff()
    @commands.command(pass_context=True, hidden=False, name='endraffle', aliases=["gvwy_end"])
    async def cmd_endraffle(self, ctx):
        """
        [Admin/Mod] Closes the raffle.

        Useage:
            [prefix]endraffle
        """
        #===== CLOSE RAFFLE ENTRY
        self.cogset['RafEntryActive']
        await SAVE_COG_CONFIG(self.cogset, cogname="giveaway")

        #===== GET GIVEAWAY ROLE AND MEMBERS
        giveawayRole = discord.utils.get(ctx.guild.roles, id=Giveaway.config.gvwy_role_id)
        giveawayMembers = [member for member in ctx.guild.members if giveawayRole in member.roles]

        #===== REM GIVEAWAY ROLE FROM EVERYONE
        for member in giveawayMembers:
            await member.remove_roles(giveawayRole, reason="Giveaway ended.")
            await asyncio.sleep(0.1)
        
        #==== CLEAR GIVEAWAY ENTRIES FROM THE DATABASE
        await self.db.execute(pgCmds.REM_ALL_GVWY_ENTRIES)
        
        #==== ANNOUNCE GIVEAWAY CLOSURE
        await ctx.channel.send(content=Giveaway.config.gvwy_end_message.replace("(newline)", "\n"))
        return

    ###Support or above can allow raffle entries
    @is_any_staff()
    @commands.command(pass_context=True, hidden=False, name='allowentries', aliases=["gvwy_allow"])
    async def cmd_allowentries(self, ctx):
        """
        [Any Staff] Turns on raffle entries

        Useage:
            [prefix]allowentries
        """

        if not self.cogset['RafEntryActive']:
            self.cogset['RafEntryActive'] = True
            self.cogset['RafDatetime'] = {'open':datetime.datetime.utcnow(), 'past':datetime.datetime.utcnow() + datetime.timedelta(days = -15)}

            await SAVE_COG_CONFIG(self.cogset, cogname="giveaway")

            await ctx.channel.send(content="Entries now allowed :thumbsup:")
            return
        
        await ctx.channel.send(content="Entries already allowed :thumbsup:")
        return

    ###Support or above can close raffle entries
    @is_any_staff()
    @commands.command(pass_context=True, hidden=False, name='stopentries', aliases=["gvwy_stop"])
    async def cmd_stopentries(self, ctx):
        """
        [Any Staff] Turns off raffle entries

        Useage:
            [prefix]stopentries
        """

        if self.cogset['RafEntryActive']:
            self.cogset['RafEntryActive'] = False

            await SAVE_COG_CONFIG(self.cogset, cogname="giveaway")

            await ctx.channel.send(content="Entries now turned off :thumbsup:")
            return

        await ctx.channel.send(content="Entries already turned off :thumbsup:")
        return

    ###Support or above can post list of raffle entries
    @in_channel([giveaway_channel_id])
    @is_core()
    @commands.command(pass_context=True, hidden=False, name='giveawayentries', aliases=["gvwy_giveawayentries"])
    async def cmd_giveawayentries(self, ctx):
        """
        [Core/GiveawayChannel] Posts a list of raffle entries

        Useage:
            [prefix]giveawayentries
        """
        #===== GET DATA FROM DATABASE
        gvwyEntries = await self.db.fetch(pgCmds.GET_ALL_GVWY_ENTRIES)

        #===== IF NO-ONE IS IN THE RAFFLE
        if not gvwyEntries:
            await ctx.channel.send(content="There are no entries in the giveaway.", delete_after=20)
            return
        
        entriesMsg = "A total of {} member/s have entered the giveaway.\n".format(len(gvwyEntries))

        for i, entry in enumerate(gvwyEntries, 1):
            member = ctx.guild.get_member(entry['user_id'])
            entriesMsg += "No.{}: {}\n".format(i, member.nick or member.name)

        entriesMsg += "Best of luck everyone."

        #===== SPLIT THE MESSAGE ITNO AN ARRAY TO CONFORM WITH THE 2000 CHARACTER LIMIT
        entriesMsg = await Giveaway.split_list(entriesMsg, size=2000)

        #===== MESSAGE OUT THE LIST OF RAFFLE ENTRIES
        for i in range(len(entriesMsg)):
            await ctx.send(entriesMsg[i])
        
        return

    @is_any_staff()
    @commands.command(pass_context=True, hidden=True, name='giveawayoverride', aliases=["gvwy_giveawayoverride"])
    async def cmd_giveawayoverride(self, ctx):
        """
        [Admin/Mod] Adds a user to a giveaway regardless of qualifcations.

        Useage:
            [prefix]giveawayoverride <userid/mention>
        """
        user_id = await Giveaway.Get_user_id(ctx.message.content)

        #===== IF THE SUPPILED USERID IS NOT VALID
        if not user_id:
            await ctx.channel.send(content="`Useage: [p]giveawayoverride <userid/mention>,\n[Admin/Mod] Adds a user to a giveaway regardless of qualifcations.`", delete_after=Giveaway.delete_after)
            return 

        #===== IF USER DOESN'T EXIST
        member = ctx.guild.get_member(user_id)
        if not member:
            await ctx.channel.send(content=f"User does not exist or is not a member of {ctx.guild.name}", delete_after=Giveaway.delete_after)
            return

        #-------------------- ENTER MEMBER --------------------
        past_wins = await self.db.fetchval(pgCmds.GET_GVWY_NUM_WINS, user_id)

        #=== LEVELED ENTRY SYSTEM
        if not past_wins:
            entries=3
        elif past_wins == 1:
            entries=2
        else:
            entries=1

        await self.db.execute(pgCmds.ADD_GVWY_ENTRY, user_id, entries, ctx.message.created_at)
        await member.add_roles(discord.utils.get(ctx.guild.roles, id=Giveaway.config.gvwy_role_id), reason="Staff member added user to giveaway")

        await ctx.channel.send(content=f"<@{user_id}> has been entered to the giveaway by {ctx.author.mention}", delete_after=Giveaway.delete_after)
        return



def setup(bot):
    bot.add_cog(Giveaway(bot))