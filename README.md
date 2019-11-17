# NuggetBot4.0
 Made again because GitHub is terrible

About
======
### Back Story
Hello, my name is Lime!
I owned my own public discord server, free to join for anyone with an affinity for dragons and all things scaly! I had dabbled in some bot work in the past but nothing too major. Some of which wasn't allowed by discord but they didn't seem to care all that much at the time. I decided that my server could do with it's own custom bot to take care of some clutter and basic things. So that is where the journey of NuggetBot began.


### Version 1
* Discord.py Async

NuggetBot (initially called: delete_dyno_messages) began life as a simple script which deleted Dyno messages running on a Raspberry PI 2 crammed behind a modem. It crashed everyday so it ran in an infinite loop from an sh file, crude but functional. 
As time passed more and more functionality was added to the bot.py file, including things like self assignable roles, giveaway functions, welcome messages for new members and even a shutdown command! Which didn't do anything since the bot ran in an infinite loop.


### Version 2
* Discord.py Async

After the bot became overwhelming for a single little file, the same logic [used in this music bot](https://github.com/Just-Some-Bots/MusicBot/) was applied to NuggetBot, remnants of this can still be found in the bot today.
This allowed for NuggetBot to support a much greater number of commands and for much easier growth. This change also retired the infinite loop sh file, allowing the shutdown command to actually work now. 
Admittedly, quite a lot of code was lifted directly from that music bot and my own understanding at the time was limited, this has improved overtime. However keeping up with the needs of my own growing discord server, Nugget was growing fast.


### Version 3
* Discord.py Async

At this point the days of the discord.py async were coming to an end, Rapptz had decided to rewrite discord.py (again). Massive amount of work would have been required to use the re-write and I decided not to do it at that time. The new library was too new for comfort and seemed prone to semi-frequent incompatibility updates.

NuggetBot had been outgrowing his clothes once again and it was time for another major change for the bot. This came with the introduction of the asyncpg library and it's own dedicated PostgreSQL database. The amount of things the bot did with it's database increased rather quickly, it was a fun challenge to make and use the SQL commands. This change brought about member leveling and some commands to help our artists out with commissions.


### The Bad Days
Staff on my old server saw fit to remove me from the picture. As a result, development of NuggetBot halted for several months. After a period of mourning my old server and perceived status I decided to build my own server from scratch. Bringing my NuggetBot with me. 
Of course this brings on the need to update NuggetBot to the re-write, since doing it down the line would have created more work than it would have saved.


### Version 4
* Discord.py Re-Write

Currently, the raw updating process from async to re-write library's is complete. However, NuggetBot never took advantage of the bot.ext side of the discord.py. The majority of NuggetBots functionality has been ported over to the Cogs system which after some initial confusion (mostly due to Rapptz ruining the documentation for the re-write, I had to follow some do as I do's instead of do as I say's) turned out to be fairly straightforward. The current work process is polishing various parts of NuggetBot to work well with several improvements and experiments.


Why make the bot public?
======
I took a lot of pride in NuggetBot and what it does. It does pale in comparison to other bots and my own skills are severely limited compared to others, however NuggetBot is a compilation of my best programming work. I vehemently reject the title of "Programmer" due to nothing but bad experiences with people who call themselves programmers. I'm just a nerd who programs.
I kept the code of NuggetBot under lock and key for the entire time it was active on my old server. Only myself and two trusted people had access to all of the source code, some others saw bits which were relevant to them figuring out something for their own bots. This stemmed from my old server having a secrets and mistrust at it's core mentality. For my new server, I am determined to make everything as transparent as possible; this includes making the code for the servers bot publicly available for all to see.

* Want to know what information we keep on our members?
* Want to know if the giveaways are rigged?
* Want to know what commands are available to staff?
* Want to copy some functionality to your own bot?

It's all right here!


Setup
======

debian, blah blah blah