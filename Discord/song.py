from __future__ import unicode_literals
import asyncio
import discord
import re
import math
import youtube_dl
import voiceclasses
from functools import wraps

def accesslevel(accesslvl):
    """
    A decorator to limit function access based on user access level
    """
    def accesslevel_decorator(func):
        @wraps(func)
        async def accesslevelwrapper(*args):
            if args[2] >= accesslvl or args[2] == -1:
                await func(*args)
            else:
                await args[0].sendMessage(args[1],"You do not have access to !{}, {}!".format(func.__name__,args[1].author.mention))
        accesslevelwrapper.__accesslevel__ = accesslvl
        return accesslevelwrapper
    return accesslevel_decorator

class song(object):
    """
    Handles commands that work in #song
    """

    def init(self,c):
        self.client = c
        self.channels = ["song","testing"]
        self.voice = None
        self.voice_states = {}

    async def onReady(self):
        await self.initVoice()

    async def beforeReload(self):
        state = self.get_voice_state()
        if state.is_playing():
            player = state.player
            player.stop()
        try:
            state.audio_player.cancel()
            del self.voice_states[message.server.id]
            await state.voice.disconnect()
        except:
            pass

    def get_voice_state(self):
        for server in self.client.servers:
            if server.name == self.client.user.name:
                state = self.voice_states.get(server.id)
                if state is None:
                    state = voiceclasses.VoiceState(self.client)
                    self.voice_states[server.id] = state
                return state

    @accesslevel(0)
    async def test(self,message,accesslevel,users):
        """
        Test command for song module
        """
        state = self.get_voice_state()
        print(state)
        print(state.voice)
        print(state.is_playing())
        await self.sendMessage(message,"Test!")

    @accesslevel(1)
    async def play(self,message,accesslevel,users):
        """
        Plays music over the voice channel. Or attempts to, anyways.

        Usage: !play <link or search term>
        """
        await self.sendMessage(message,"Attempting to grab song...")
        msg = message.content.split(" ")
        if len(msg)<2:
            await self.sendMessage(message,"You must enter a song to play, {}!".format(message.author.mention))
            return
        opts = {
            'default_search': 'auto',
            'quiet': True,
        }
        state = self.get_voice_state()
        if state.voice is None:
            await self.initVoice()
            state = self.get_voice_state()
        player = await state.voice.create_ytdl_player(" ".join(msg[1:]),ytdl_options = opts,after = state.toggle_next)
        print("\"{}\" - \"{}\"".format(" ".join(msg[1:]),player.url))
        player.volume = 0.6
        entry = voiceclasses.VoiceEntry(message, player)
        await state.songs.put(entry)
        await self.sendMessage(message,"Song queued: {}".format(str(entry)))

    @accesslevel(1)
    async def skip(self,message,accesslevel,users):
        """
        Skips the specified song.

        If you are below mod, you may only skip songs you request.

        Usage: !skip [song number]
        """
        state = self.get_voice_state()
        if state.is_playing():
            player = state.player
            msg = message.content.split(" ")
            numsong = 1
            if len(msg)>1:
                try:
                    numsong = int(msg[1])
                except Exception:
                    await self.sendMessage(message,"You must enter a valid song number to skip, {}!".format(message.author.mention))
                    return
            if numsong < 1:
                await self.sendMessage(message,"That's an invalid song number to skip, {}!".format(message.author.mention))
                return
            if numsong > len(state.songs._queue) + 1:
                await self.sendMessage(message,"There aren't that many songs in the queue, {}!".format(message.author.mention))
                return
            numsong -= 2
            if accesslevel >= 2 or state.songs._queue[numsong].requester == message.author.id:
                state.skip(numsong)
                await self.sendMessage(message,"Song {} skipped by {}.".format(numsong + 2,message.author.mention))
            elif accesslevel < 2:
                await self.sendMessage(message,"You do not have access to skip others' songs, {}.".format(message.author.mention))
            else:
                await self.sendMessage(message,"Um... I'm not totally certain what just happened here.")


    @accesslevel(3)
    async def stop(self,message,accesslevel,users):
        """
        Stops the currently playing song and dumps the queue.
        """
        state = self.get_voice_state()
        if state.is_playing():
            player = state.player
            player.stop()
        try:
            state.audio_player.cancel()
            del self.voice_states[message.server.id]
            await state.voice.disconnect()
        except:
            pass
        await self.sendMessage(message,"Playback stopped.")

    @accesslevel(2)
    async def volume(self,message,accesslevel,users):
        """
        Changes the current song's volume in the voice channel. Defaults to 60% for each.
        """
        state = self.get_voice_state()
        if state.is_playing():
            player = state.player
            msg = message.content.split(" ")
            if len(msg)<2:
                await self.sendMessage(message,"You must enter a volume level, {}!".format(message.author.mention))
                return
            volume = 100
            try:
                volume = int(msg[1])
            except Exception:
                await self.sendMessage(message,"You must enter a valid number 0-100 for volume, {}!".format(message.author.mention))
                return
            if volume < 0:
                volume = 0
            if volume > 100:
                volume = 100
            player.volume = volume / 100
            await self.sendMessage(message,"Volume set to {}%.".format(volume))

    async def action(self,message,users):
        """
        Runs various commands in #song
        """
        if message.channel.name in self.channels and not message.channel.is_private:
            #Run various commands
            accesslevel = int(users.getNode(message.author.mention,"identity/accesslevel").text)
            command = message.content.split(" ")[0].lower()
            if command[0] == "!":
                if hasattr(self,command[1:]):
                    if hasattr(getattr(self,command[1:]),"__accesslevel__"):
                        await getattr(self,command[1:])(message,accesslevel,users)

    async def sendMessage(self,msgObj,message):
        """
        Sends messages to Discord
        """
        await self.client.send_message(msgObj.channel,message)
        print("#{} - {}: {}".format(msgObj.channel,self.client.user.name,message))

    async def initVoice(self):
        state = self.get_voice_state()
        if state.voice == None:
            for i in self.client.servers:
                if i.name == self.client.user.name:
                    if not self.client.is_voice_connected(i):
                        for j in i.channels:
                            if j.name in self.channels and str(j.type) is "voice":
                                state.voice = await self.client.join_voice_channel(j)
                    else:
                        for j in self.client.voice_clients:
                            if j.server == i:
                                state.voice = j