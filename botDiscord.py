import discordnot
import asyncio
import re
import importlib
import traceback
import interface

client = discord.Client()
plugin = interface.interface()

@client.event
async def on_ready():
    """
    Runs once the bot has loaded up and connected to Discord
    """
    print('Logged in as')
    print(client.user.name)
    print(client.user.id)
    print('------')
    await plugin.reload(client)

def getAccessLevel(user):
    """
    Fetches the access level of the given user from the bot's server - even works in PM or other servers
    """
    maxrole = 0
    for i in client.servers:
        if i.name == client.user.name:
            for j in i.members:
                if j.id == user.id:
                    for k in j.roles:
                        if k.position > maxrole:
                            maxrole = k.position
    return maxrole

@client.event
async def on_message(message):
    """
    Handles all messages. Only command hardcoded here is !reload, which'll reload all subplugins.
    Passes everything else through.
    """
    global plugin
    if message.author == client.user:
        return
    try:
        print("#{} - {}: {}".format(message.channel.name,str(message.author),message.content))
    except UnicodeEncodeError:
        print("#{} - {}: [UNENCODEABLE]".format(message.channel.name,str(message.author)))
    except Exception as exception:
        await handleException(message,exception)
    if message.content.split(" ")[0].lower() == "!reload":
        accesslevel = getAccessLevel(message.author)
        if accesslevel >= 4:
            try:
                await plugin.beforeReload()
                importlib.reload(interface)
                plugin = interface.interface()
                await plugin.reload(client)
                await sendMessage(message,"Reloaded!")
            except Exception as exception:
                await handleException(message,exception)
        else:
            await sendMessage(message,"You don't have access to !reload, {}.".format(message.author.mention))
    try:
        await plugin.action(message)
    except Exception as exception:
        await handleException(message,exception)

async def sendMessage(msgObj,message):
    """
    Sends messages to Discord
    """
    await client.send_message(msgObj.channel,message)
    print("#{} - {}: {}".format(msgObj.channel,client.user.name,message))

async def handleException(message,exception):
    """
    Handles exceptions and prints stack traces.
    Also logs brief error summary to Discord.
    """
    print("EXCEPTION\r\n{}".format(traceback.format_exc()))
    await sendMessage(message,"ERROR: {} - check console for stack trace".format(exception))

client.run('Mzc1MDMyNDA2MjExNjkwNDk3.DNp7qw.kAZFmIEKKTIrmxdFc5LWvm_8KUk')

#https://github.com/Rapptz/discord.py
