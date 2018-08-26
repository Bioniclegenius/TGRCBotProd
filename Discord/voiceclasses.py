import asyncio
import discord

class VoiceState:
    def __init__(self, bot):
        self.current = None
        self.voice = None
        self.bot = bot
        self.play_next_song = asyncio.Event()
        self.songs = asyncio.Queue()
        self.skip_votes = set() # a set of user_ids that voted
        self.audio_player = self.bot.loop.create_task(self.audio_player_task())

    def is_playing(self):
        if self.voice is None or self.current is None:
            return False

        player = self.current.player
        return not player.is_done()

    @property
    def player(self):
        return self.current.player

    def skip(self,num = -1):
        self.skip_votes.clear()
        if num == -1:
            if self.is_playing():
                self.player.stop()
        else:
            del self.songs._queue[num-1]

    def toggle_next(self):
        self.bot.loop.call_soon_threadsafe(self.play_next_song.set)

    async def audio_player_task(self):
        while True:
            self.play_next_song.clear()
            self.current = await self.songs.get()
            await self.bot.send_message(self.current.channel, 'Now playing ' + str(self.current))
            self.current.player.start()
            await self.play_next_song.wait()

class VoiceEntry:
    def __init__(self, message, player):
        self.requester = message.author
        self.channel = message.channel
        self.player = player

    def __str__(self):
        duration = self.player.duration
        dur = ""
        if duration:
            dur = ' [length: {0[0]}h {0[1]}m {1[1]}s]'.format(divmod(duration//60,60),divmod(duration, 60))
        fmt = "*{0.title}* uploaded by {0.uploader} and requested by {1.display_name}{2}".format(self.player,self.requester,dur)
        return fmt