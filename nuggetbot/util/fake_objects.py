import datetime

#Message server and channel
class MessageSC(object):
    id = 0
    channel = ""
    server = ""

    def __repr__(self):
        return "<FakeMessageServerandChannel, id={}, channel={} guild={}>".format(
            self.id,
            self.channel,
            self.server
        )

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return (self.id == other.id
                    and self.server == other.server 
                    and self.channel == other.channel)
        return False 

    def __ne__(self, other):
        if isinstance(other, self.__class__):
            return (self.id != other.id
                    or self.server != other.server 
                    or self.channel != other.channel)
        return False 

    def __init__(self, id, server, channel):
        self.id = id
        self.server = server
        self.channel = channel


#Message server and channel
class FakeMsg1(object):
    id = 0
    type = 0
    content = ""
    clean_content = ""
    channel = None 
    author = None
    attactments = list()
    embeds = list()
    raw_mentions = list()
    raw_role_mentions = list()
    pinned = False
    mention_everyone = False
    tts = False
    created_at = datetime.datetime.utcnow()
    edited_at = None

    def __init__(self, f, guild):
        self.id = int(f['id'])
        self.type = f['type']
        self.content = f['content']
        self.clean_content = f['content']
        self.channel = FakeChannel1(f['channel_id']) 
        self.author = FakeAuthor1(f['author'])
        self.guild = FakeGuild1(guild) if guild is not None else None
        self.attactments = f['attachments']
        self.embeds = f['embeds']
        self.raw_mentions = f['mentions']
        self.raw_role_mentions = f['mention_roles']
        self.pinned = f['pinned']
        self.mention_everyone = f['mention_everyone']
        self.tts = f['tts']
        self.created_at = datetime.datetime.fromisoformat(f['timestamp'])
        self.edited_at =  datetime.datetime.fromisoformat(f['edited_timestamp']) if f['edited_timestamp'] else None

    def __repr__(self):
        return "<FakeMessage, id={}>".format(
            self.id
        )

    def __str__(self):
        return "<FakeMessage, id={}>".format(
            self.id
        )

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return (self.id == other.idl)
        return False 

    def __ne__(self, other):
        if isinstance(other, self.__class__):
            return (self.id != other.id)
        return False 

class FakeAuthor1(object):
    id = 0
    username =""
    avatar = '' 
    discriminator = ''
    bot = False

    def __init__(self, f):
        self.id = int(f['id'])
        self.username = f['username']
        self.avatar = f['avatar']
        self.discriminator = f['discriminator']
        self.bot = f['bot']

    def __repr__(self):
        return "<FakeAuthor, id={}>".format(
            self.id
        )

    def __str__(self):
        return "<FakeAuthor, id={}>".format(
            self.id
        )

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return (self.id == other.id)
        return False 

    def __ne__(self, other):
        if isinstance(other, self.__class__):
            return (self.id != other.id)

        return False 

class FakeChannel1(object):
    id = 0

    def __init__(self, f):
        self.id = int(f)

    def __repr__(self):
        return "<FakeChannel1, id={}>".format(
            self.id
        )

    def __str__(self):
        return "<FakeChannel1, id={}>".format(
            self.id
        )

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return (self.id == other.id)
        return False 

    def __ne__(self, other):
        if isinstance(other, self.__class__):
            return (self.id != other.id)

        return False 

class FakeGuild1(object):
    id = 0

    def __init__(self, f):
        self.id = int(f)

    def __repr__(self):
        return "<FakeGuild1, id={}>".format(
            self.id
        )

    def __str__(self):
        return "<FakeGuild1, id={}>".format(
            self.id
        )

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return (self.id == other.id)
        return False 

    def __ne__(self, other):
        if isinstance(other, self.__class__):
            return (self.id != other.id)

        return False