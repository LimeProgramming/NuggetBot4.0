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



