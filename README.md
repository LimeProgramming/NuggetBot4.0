# NuggetBot4.0
 Made again because GitHub is terrible

About
======
### Version 1
* Discord.py Async

NuggetBot (initally called: delete_dyno_messages) began life as a simple script which deleted Dyno messages running on a Raspberry PI 2 crammed behind a modem.
It crashed everyday so it ran in an infinate loop from an sh file, crude but functional. 


### Version 2
* Discord.py Async

As time passed more and more functionality was added to the NuggetBot file, including things like self assignable roles, giveaway functions, and even a shutdown command! Which didn't do anything since the bot ran in an infinate loop.
After the bot became overwhelming for a single little file, the same logic [applied in this bot](https://github.com/Just-Some-Bots/MusicBot/) was applied to NuggetBot, remints of this can still be found in the bot today.


### Version 3
* Discord.py Async

At this point the days of the discord.py async were coming to an end, Rapptz had decided to rewrite discord.py (again). Massive amount of work would have been required to use the re-write and I decided not to do it at that time. The new library was too new for comfort and seemed prone to semi-frequent incompatibility updates.

NuggetBot had been outgrowing his clothes once again and it was time for another major change for the bot. This came with the introduction of the asyncpg library and it's own dedicated PostgreSQL database. 