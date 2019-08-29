from discord.ext import commands
import discord
import asyncio
import asyncpg
import datetime

from nuggetbot.config import Config
from nuggetbot.database import DatabaseLogin
from nuggetbot.database import DatabaseCmds as pgCmds
from nuggetbot.decorators import in_channel_name, in_reception, has_role, is_high_staff, is_any_staff, turned_off, owner_only
from .ctx_decorators import in_channel, is_core
#https://discordpy.readthedocs.io/en/latest/ext/commands/api.html#bot

class Giveaway(commands.Cog):
    """Poll voting system."""


    def __init__(self, bot):
        self.RafEntryActive = False
        self.RafDatetime = []
        self.bot = bot
        self.config = Config()
        self.databaselg = DatabaseLogin()

        #self._last_result = None
    @commands.Cog.listener()
    async def on_ready(self):
        credentials = {"user": self.databaselg.user, "password": self.databaselg.pwrd, "database": self.databaselg.name, "host": self.databaselg.host}
        self.db = await asyncpg.create_pool(**credentials)


    async def Response(self, ctx, content="", reply=True, delete_after=None, embed=None, tts=False):
        if reply:
            await ctx.message.channel.send(content=content, tts=tts, embed=embed, delete_after=delete_after, nonce=None)

        await ctx.message.delete()


    #@commands.command(hidden=False, pass_context=True)
   # @commands.guild_only()
   # @commands.command(pass_context=True, hidden=True, name='eval')
   # async def testgiveaway(self, ctx, *, body: str):
   #     print(1)
   #     print(body)



    ###Users assign themselves the giveaway role
    #
    @is_core()
    @in_channel([607424940177883148])
    @commands.guild_only()
    @commands.command(pass_context=False, hidden=False, name='giveaway', aliases=["gvwy"])
    async def cmd_giveaway(self, msg):
        """
        Useage:
            [prefix]giveaway
        [Core] Users can give themselves the giveaway role
        """
        #===== GET RAFLE ROLE
        giveawayRole = discord.utils.get(msg.guild.roles, name=self.config.gvwy_role_name)

        ##===== IF RAFFLE IS OPEN
        if self.RafEntryActive:

            #=== IF MEMBER IS IN RAFFLE
            if await self.db.fetchval(pgCmds.GET_MEM_EXISTS_GVWY_ENTRIES, msg.author.id):
                #= REM ROLE
                await msg.author.remove_roles(giveawayRole, reason="User left the giveaway.")
                #= REM FROM DATABASE
                await self.db.execute(pgCmds.REM_MEM_GVWY_ENTRIES, msg.author.id)
                #= RESPOND
                await self.Response(ctx=msg, content="{} has left the giveaway, better luck next time. :negative_squared_cross_mark: ".format(msg.author.nick or msg.author.name), delete_after=10)
                return

            #-------------------- ENTRY BLOCKING --------------------
            #=== IF USER HAS BEEN BLACKLISTED FROM GIVEAWAY    
            if self.config.gvwy_enforce_blacklist:
                if await self.db.fetchval(pgCmds.GET_MEM_EXISTS_GVWY_BLOCKS, msg.author.id):
                    await self.Response(ctx=msg, content=F"Sorry {msg.author.mention}, but you have been barred from giveaways on this server.", delete_after=10)
                    return
            #=== IF USER JOINED TOO RECENTLY
            if (datetime.datetime.utcnow() - msg.author.joined_at).seconds < self.config.gvwy_min_time_on_srv:
                await self.Response(ctx=msg, content=F"Sorry {msg.author.mention}, but you have to be on the server for a minimum of 30 days to enter the giveaway.", delete_after=10)
                return
            #=== IF NOT ACTIVE ENOUGH
            if len(await self.db.fetch(pgCmds.GET_MEMBER_MSGS_BETWEEN, msg.author.id, self.RafDatetime["open"], self.RafDatetime["past"])) < self.config.gvwy_min_msgs:
                await self.Response(ctx=msg, content=F"Sorry {msg.author.mention}, but you have not been active enough on the server to enter the giveaway.", delete_after=10)   
                return
            #-------------------- ENTER MEMBER --------------------
            past_wins = await self.db.fetchval(pgCmds.GET_GVWY_NUM_WINS, msg.author.id)

            #=== LEVELED ENTRY SYSTEM
            if not past_wins:
                entries=3
            elif past_wins == 1:
                entries=2
            else:
                entries=1

            await self.db.execute(pgCmds.ADD_GVWY_ENTRY, msg.author.id, entries, msg.created_at)
            await msg.author.add_roles(giveawayRole, reason="User joined the giveaway")

            await self.Response(ctx=msg, content="{} has entered the giveaway, goodluck :white_check_mark:".format(msg.author.nick or msg.author.name), delete_after=10)
            return 
        #===== IF RAFFLE IS CLOSED
        else:
            if await self.db.fetchval(pgCmds.GET_MEM_EXISTS_GVWY_ENTRIES, msg.author.id):
                #= REM ROLE
                await msg.author.remove_roles(giveawayRole, reason="User left the giveaway")
                #= REM FROM DATABASE
                await self.db.execute(pgCmds.REM_MEM_GVWY_ENTRIES, msg.author.id)
                #= RESPOND TO USER
                await self.Response(ctx=msg, content="{} has left the giveaway after entries have been closed. If this was a mistake ask staff to add you back into the giveaway but no promices that you'll be noticed in time. :negative_squared_cross_mark: ".format(msg.author.nick or msg.author.name), delete_after=15)
                return

            await self.Response(ctx=msg, content="Sorry {}, but giveaway entries are not open right now. Please check back later.".format(msg.author.nick or msg.author.name), delete_after=10)
            return

    ###Adds a user to the blacklist
    @is_high_staff 
    @commands.guild_only()
    @commands.command(pass_context=True, hidden=False, name='addblacklist', aliases=["gvwy_addblacklist"])
    async def cmd_addblacklist(self, msg):
        """
        Useage:
            [prefix]addblacklist <userid/mention> <reason>
        [Admin/Mod] Adds a user to the blacklist.
        """
        try:
            args = msg.content.split(" ")
            if len(args) > 3:
                return Response(content="`Useage: [p]addblacklist <userid/mention> <reason>, [Admin/Mod] Adds a user to the blacklist.`")

            #=== SPLIT, REMOVE MENTION WRAPPER AND CONVERT TO INT
            user_id = args[1]
            user_id = user_id.replace("<", "").replace("@", "").replace("!", "").replace(">", "")
            user_id = int(user_id)

            if len(args) == 3:
                reason = args[2]
                reason = reason[:1000]
            else:
                reason = None

        except (IndexError, ValueError):
            return Response(content="`Useage: [p]addblacklist <userid/mention> <reason>, [Admin/Mod] Adds a user to the blacklist.`")

        #===== IF USER IS NOT ON GUILD
        #if not msg.guild.get_member(user_id):
        #    return Response(content=f"User does not exist or is not a member of {msg.guild.name}")
        
        #===== if a user was already blacklisted
        if await self.db.fetchval(pgCmds.GET_MEM_EXISTS_GVWY_BLOCKS, user_id):
            return Response(content="User already on the raffle blacklist.")
        
        #===== BLACKLIST THE USER
        else:
            await self.db.execute(pgCmds.ADD_GVWY_BLOCKS_NONTIMED, user_id, msg.author.id, reason, msg.author.created_at)
            
            #=== IF MEMBER IS IN THE GIVEAWAY ENTRIES
            if await self.db.fetchval(pgCmds.GET_MEM_EXISTS_GVWY_ENTRIES, user_id):
                #= REMOVE FROM GIVEAWAY ENTRIES
                await self.db.execute(pgCmds.REM_MEM_GVWY_ENTRIES, user_id)
                
                #= REMOVE GIVEAWAY ROLE
                member = msg.guild.get_member(user_id)
                await member.remove_roles(discord.utils.get(msg.guild.roles, name=self.config.gvwy_role_name), reason="User baned from giveaways.")

                return Response(content=f"<@{user_id}> has been added to the raffle blacklist and removed from giveaway entries")

            return Response(content=f"<@{user_id}> has been added to the raffle blacklist.")

    ###Remove a user from the blacklist
    @is_high_staff
    @commands.guild_only()
    @commands.command(pass_context=True, hidden=False, name='remblacklist', aliases=["gvwy_remblacklist"])
    async def cmd_remblacklist(self, msg):
        """
        Useage:
            [prefix]remblacklist <userid/mention>
        [Admin/Mod] Removes a member from the blacklist.
        """
        try:
            args= msg.content.split(" ")
            if len(args) > 2:
                return Response(content="`Useage: [p]remblacklist <userid/mention>, [Admin/Mod] Removes a member from the blacklist.`")

            #=== SPLIT, REMOVE MENTION WRAPPER AND CONVERT TO INT
            user_id = args[1]
            user_id = user_id.replace("<", "").replace("@", "").replace("!", "").replace(">", "")
            user_id = int(user_id)

        except (IndexError, ValueError):
            return Response(content="`Useage: [p]remblacklist <userid/mention>, [Admin/Mod] Removes a member from the blacklist.`")
        
        #===== IF USER IS NOT ON BLOCK LIST
        if not await self.db.fetchval(pgCmds.GET_MEM_EXISTS_GVWY_BLOCKS, user_id):
            return Response(content=f"<@{user_id}> was not on the raffle blacklist.")
        
        #===== ADD USER TO BLOCK LIST 
        await self.db.execute(pgCmds.REM_MEM_GVWY_BLOCK, user_id)
        return Response(content=f"<@{user_id}> has been removed from the raffle blacklist.")

    ###Returns a list of users who are blacklisted from the raffle
    @is_any_staff
    @commands.guild_only()
    @commands.command(pass_context=True, hidden=False, name='checkblacklist', aliases=["gvwy_checkblacklist"])
    async def cmd_checkblacklist(self, msg):
        """
        Useage:
            [prefix]checkblacklist
        [Any Staff] Returns a list of users who are blacklisted from the raffle
        """
        try:
            args= msg.content.split(" ")
            if len(args) > 1:
                return Response(content="`Useage: [p]checkblacklist, [Any Staff] Returns a list of users who are blacklisted from the raffle.`")

        except (IndexError, ValueError):
            return Response(content="`Useage: [p]checkblacklist, [Any Staff] Returns a list of users who are blacklisted from the raffle.`")

        blacklistMembers = await self.db.fetch(pgCmds.GET_ALL_GVWY_BLOCKS)

        #===== IF NO-ONE IS BLOCKED
        if not blacklistMembers:
            return Response(content="No blacklisted members.", reply=True)
        
        listedMembers = ""

        #===== LOOP ALL MEMBERS IN THE SERVER
        for member in msg.guild.members:

            #=== IF MEMBER IS BLACKLISTED
            if member.id in [i['user_id'] for i in blacklistMembers]:

                for j in blacklistMembers:
                    if member.id == j['user_id']:
                        x = j 
                        break

                listedMembers += "{0.name}#{0.discriminator} | Mention: {0.mention} | Reason: {1} | When: {2}\n".format(member, x["reason"], x["timestamp"].strftime('%b %d, %Y %H:%M:%S'))

        #===== SEND HEADER MESSAGE
        await self.safe_send_message(msg.channel, "```css\nUsers blacklisted from raffle.\n```")
            
        #===== SPLIT MAIN MESSAGE STRING INTO AN ARRAY, LIMITING MAX NUM OF CHARS TO 2000
        listedMembers = await self.split_list(listedMembers, size=2000)
        
        #===== MESSAGE OUT THE BLACKLISTED MEMBERS
        for i in range(len(listedMembers)):
            await self.safe_send_message(msg.channel, listedMembers[i])

        #===== DONE
        return Response(reply=False)

    ###Adds a user to the previous winners list
    @is_high_staff
    @commands.guild_only()
    @commands.command(pass_context=True, hidden=False, name='makeprewinner', aliases=["gvwy_makeprewinner"])
    async def cmd_makeprewinner(self, msg):
        """
        Useage:
            [prefix]makeprewinner <userid/mention>
        [Admin/Mod] Adds a user to the list of previous winners.
        """
        try:
            args = msg.content.split(" ")
            if len(args) > 2:
                return Response(content="`Useage: [p]makeprewinner <userid/mention>,\n[Admin/Mod] Adds a user to the list of previous winners.`")

            #=== SPLIT, REMOVE MENTION WRAPPER AND CONVERT TO INT
            user_id = args[1]
            user_id = user_id.replace("<", "").replace("@", "").replace("!", "").replace(">", "")
            user_id = int(user_id)

        except (IndexError, ValueError):
            return Response(content="`Useage: [p]makeprewinner <userid/mention>,\n[Admin/Mod] Adds a user to the list of previous winners.`")

        #===== IF USER IS NOT ON GUILD
        #if not msg.guild.get_member(user_id):
        #    return Response(content=f"User does not exist or is not a member of {msg.guild.name}")
        
        #===== ADD USER TO WINNERS LIST 
        await self.db.execute(pgCmds.ADD_GVWY_PRE_WINS, user_id, datetime.datetime.utcnow())

        return Response(content=f"<@{user_id}> has been added to the giveaway winner list.")

    ###Remove a user to the previous winners list
    @is_high_staff
    @commands.guild_only()
    @commands.command(pass_context=True, hidden=False, name='remprewinner', aliases=["gvwy_remprewinner"])
    async def cmd_remprewinner(self, msg):
        """
        Useage:
            [prefix]remprewinner <userid/mention>
        [Admin/Mod] Removes a member from the previous winners list.
        """
        try:
            args= msg.content.split(" ")
            if len(args) > 2:
                return Response(content="`Useage: [p]remprewinner <userid/mention>, [Admin/Mod] Removes a member from the previous winners list.`")

            #=== SPLIT, REMOVE MENTION WRAPPER AND CONVERT TO INT
            user_id = args[1]
            user_id = user_id.replace("<", "").replace("@", "").replace("!", "").replace(">", "")
            user_id = int(user_id)

        except (IndexError, ValueError):
            return Response(content="`Useage: [p]remprewinner <userid/mention>, [Admin/Mod] Removes a member from the previous winners list.`")
        
        #===== GET DATA FROM DATABASE
        prewindata = await self.db.fetchrow(pgCmds.GET_MEM_GVWY_PRE_WIN, user_id)
        

        #===== IF USER IS NOT ON BLOCK LIST
        if not prewindata:
            return Response(content=f"<@{user_id}> was not on the raffle blacklist.")
        
        pastwins = int(prewindata['num_wins'])

        #===== DEINCREMENT THE USERS NUMBER OF WINS IF NEEDED
        if pastwins > 1:
            await self.db.execute(pgCmds.SET_GVWY_NUM_WINS, (prewindata['num_wins'] - 1), user_id)
            return Response(content=f"<@{user_id}> has had their number of previous wins set to {(pastwins - 1)}.")
        
        #===== OTHERWISE JUST REMOVE THEM FROM THE PREVIOUS WINNERS LIST
        await self.db.execute(pgCmds.REM_MEM_GVWY_PRE_WINS, user_id)
        return Response(content=f"<@{user_id}> has been removed from the previous winners list.")
        
    ###Returns a list of users who have won the raffle before
    @commands.guild_only()
    @is_any_staff
    @commands.command(pass_context=True, hidden=False, name='checkprewinners', aliases=["gvwy_checkprewinners"])
    async def cmd_checkprewinners(self, msg):
        """
        Useage
            [prefix]checkprewinners
        [Any Staff] Returns a list of users who have won the raffle before.
        """
        try:
            args= msg.content.split(" ")
            if len(args) > 1:
                return Response(content="`Useage: [p]checkprewinners, [Any Staff] Returns a list of users who have won the raffle before.`")

        except (IndexError, ValueError):
            return Response(content="`Useage: [p]checkprewinners, [Any Staff] Returns a list of users who have won the raffle before.`")
    
        preWinners = await self.db.fetch(pgCmds.GET_ALL_GVWY_PRE_WINS)
        
        #===== IF NO-ONE WON BEFORE
        if not preWinners:
            return Response(content="No-one ever won before.")

        listedMembers = ""

        #===== LOOP ALL MEMBERS IN THE SERVER
        for member in msg.guild.members:

            #=== IF MEMBER WON BEFORE
            if member.id in [i['user_id'] for i in preWinners]:

                for j in preWinners:
                    if member.id == j['user_id']:
                        x = j 
                        break

                listedMembers += "{0.name}#{0.discriminator} | Mention: {0.mention} | Number Wins: {1} | Last Win: {2}\n".format(member, x["num_wins"], x["last_win"].strftime('%b %d, %Y %H:%M:%S'))

        #===== SEND HEADER MESSAGE
        await self.safe_send_message(msg.channel, "```css\nUsers who have won the raffle before.\n```")
            
        #===== SPLIT MAIN MESSAGE STRING INTO AN ARRAY, LIMITING MAX NUM OF CHARS TO 2000
        listedMembers = await self.split_list(listedMembers, size=2000)
        
        #===== MESSAGE OUT THE PREVIOUS WINNERS MEMBERS
        for i in range(len(listedMembers)):
            await self.safe_send_message(msg.channel, listedMembers[i])

        #===== DONE
        return Response(reply=False)
        
    ###Support or above calls a winner of the raffle 
    @commands.guild_only()
    @is_any_staff
    @commands.command(pass_context=True, hidden=False, name='callgiveawaywinner', aliases=["gvwy_callgiveawaywinner"])
    async def cmd_callgiveawaywinner(self, msg):
        """
        Useage:
            [prefix]callgiveawaywinner
        [Any Staff] Returns a random user who has entered the Giveaway. Base Stats: 3 entries if never won, 2 entries if won once, 1 entry if won more twice or more.
        """
        dbGvwyEntries = await self.db.fetch(pgCmds.GET_ALL_GVWY_ENTRIES)
        draw = list()

        #===== IF NO-ONE IS IN THE GIVEAWAY
        if not dbGvwyEntries:
            return Response(content="No entries in the giveaway.")
        
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
        winner = msg.guild.get_member(winnerid)
        await winner.remove_roles(discord.utils.get(msg.guild.roles, name=self.config.gvwy_role_name), reason="User won giveaway.")
        
        #===== ANNOUNCE WINNER
        return Response(content=f"Congratulations {winner.mention}! You've won a prize in the giveaway.")

    ###Bastion or above close raffle
    @commands.guild_only()
    @is_high_staff
    @commands.command(pass_context=True, hidden=False, name='endraffle', aliases=["gvwy_endraffle"])
    async def cmd_endraffle(self, msg):
        """
        Useage:
            [prefix]endraffle
        [Admin/Mod] Closes the raffle.
        """
        #===== CLOSE RAFFLE ENTRY
        self.RafEntryActive = False

        #===== GET GIVEAWAY ROLE AND MEMBERS
        giveawayRole = discord.utils.get(msg.guild.roles, name=self.config.gvwy_role_name)
        giveawayMembers = [member for member in msg.guild.members if giveawayRole in member.roles]

        #===== REM GIVEAWAY ROLE FROM EVERYONE
        for member in giveawayMembers:
            await member.remove_roles(giveawayRole, reason="Giveaway ended.")
            await asyncio.sleep(0.1)
        
        #==== CLEAR GIVEAWAY ENTRIES FROM THE DATABASE
        await self.db.execute(pgCmds.REM_ALL_GVWY_ENTRIES)
        
        #==== ANNOUNCE GIVEAWAY CLOSURE
        return Response(content=self.config.gvwy_end_message)

    ###Support or above can allow raffle entries
    @commands.guild_only()
    @is_any_staff
    @commands.command(pass_context=True, hidden=False, name='allowentries', aliases=["gvwy_allowentries"])
    async def cmd_allowentries(self, msg):
        """
        Useage:
            [prefix]allowentries
        [Any Staff] Turns on raffle entries
        """

        if not self.RafEntryActive:
            self.RafEntryActive = True
            self.RafDatetime = {'open':datetime.datetime.utcnow(), 'past':datetime.datetime.utcnow() + datetime.timedelta(days = -15)}

            return Response(content="Entries now allowed :thumbsup:")
        
        else:
            return Response(content="Entries already allowed :thumbsup:")

    ###Support or above can close raffle entries
    @commands.guild_only()
    @is_any_staff
    @commands.command(pass_context=True, hidden=False, name='stopentries', aliases=["gvwy_stopentries"])
    async def cmd_stopentries(self, msg):
        """
        Useage:
            [prefix]stopentries
        [Any Staff] Turns off raffle entries
        """

        if self.RafEntryActive:
            self.RafEntryActive = False

            return Response(content="Entries now turned off :thumbsup:")

        return Response(content="Entries already turned off :thumbsup:")

    ###Support or above can post list of raffle entries
    @commands.guild_only()
    #@in_channel([ChnlID.giveaway])
    @is_core
    @commands.command(pass_context=True, hidden=False, name='giveawayentries', aliases=["gvwy_giveawayentries"])
    async def cmd_giveawayentries(self, msg):
        """
        Useage:
            [prefix]giveawayentries
        [Core/GiveawayChannel] Posts a list of raffle entries
        """
        #===== GET DATA FROM DATABASE
        gvwyEntries = await self.db.fetch(pgCmds.GET_ALL_GVWY_ENTRIES)

        #===== IF NO-ONE IS IN THE RAFFLE
        if not gvwyEntries:
            return Response(content="There are no entries in the giveaway.", delete_after=20)
        
        entriesMsg = "A total of {} member/s have entered the giveaway.\n".format(len(gvwyEntries))

        for i, entry in enumerate(gvwyEntries, 1):
            member = msg.guild.get_member(entry['user_id'])
            entriesMsg += "No.{}: {}\n".format(i, member.nick or member.name)

        entriesMsg += "Best of luck everyone."

        #===== SPLIT THE MESSAGE ITNO AN ARRAY TO CONFORM WITH THE 2000 CHARACTER LIMIT
        entriesMsg = await self.split_list(entriesMsg, size=2000)

        #===== MESSAGE OUT THE LIST OF RAFFLE ENTRIES
        for i in range(len(entriesMsg)):
            await self.safe_send_message(msg.channel, entriesMsg[i])
        
        return Response(reply=False)

    @commands.guild_only()
    @is_any_staff
    @commands.command(pass_context=True, hidden=True, name='giveawayoverride', aliases=["gvwy_giveawayoverride"])
    async def cmd_giveawayoverride(self, msg):
        """
        Useage:
            [prefix]giveawayoverride <userid/mention>
        [Admin/Mod] Adds a user to a giveaway regardless of qualifcations.
        """
        try:
            args = msg.content.split(" ")
            if len(args) > 2:
                return Response(content="`Useage: [p]giveawayoverride <userid/mention>,\n[Admin/Mod] Adds a user to a giveaway regardless of qualifcations.`")

            #=== SPLIT, REMOVE MENTION WRAPPER AND CONVERT TO INT
            user_id = args[1]
            user_id = user_id.replace("<", "").replace("@", "").replace("!", "").replace(">", "")
            user_id = int(user_id)

        except (IndexError, ValueError):
            return Response(content="`Useage: [p]giveawayoverride <userid/mention>,\n[Admin/Mod] Adds a user to a giveaway regardless of qualifcations.`")

        #===== IF USER DOESN'T EXIST
        if not msg.guild.get_member(user_id):
            return Response(content="User does not exist or is not a member of {}".format(msg.guild.name))

        #-------------------- ENTER MEMBER --------------------
        past_wins = await self.db.fetchval(pgCmds.GET_GVWY_NUM_WINS, user_id)

        #=== LEVELED ENTRY SYSTEM
        if not past_wins:
            entries=3
        elif past_wins == 1:
            entries=2
        else:
            entries=1

        await self.db.execute(pgCmds.ADD_GVWY_ENTRY, user_id, entries, msg.created_at)
        await msg.author.add_roles(discord.utils.get(msg.guild.roles, name=self.config.gvwy_role_name), reason="Staff member added user to giveaway")

        return Response(content=f"<@{user_id}> has been entered to the giveaway by {msg.author.mention}", delete_after=10)



def setup(bot):
    bot.add_cog(Giveaway(bot))