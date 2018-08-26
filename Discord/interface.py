import asyncio
import importlib
import datetime
import sys
import traceback
from operator import itemgetter
from functools import wraps

import users
import chanbot
import globalfunctions
import song

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

class interface(object):
    """
    Interface between core and plugins

    Handles reloading each plugin, so the only one the core has to reload is this one
    Handles access levels and tracking basic user data
    Invokes sub-plugin action methods

    Command  | Access Level   | Channels
    ---------|----------------|---------
    !help    | everyone   (0) | any     
    """

    def init(self,c):
        """
        Initializes each sub-plugin with the client
        """
        self.client = c
        self.channels = ["any"]

        self.plugins = []
        for i in self.plugin_classes:
            self.plugins.append(i())
            self.plugins[-1].init(c)
        self.users = users.users()
        self.users.init()

    async def beforeReload(self):
        if hasattr(self,"plugins"):
            for i in self.plugins:
                if hasattr(i,'beforeReload'):
                    await i.beforeReload()

    async def reload(self,c):
        """
        Reloads sub-plugins and initializes everything
        """
        toReload = [
                            users
                   ]
        self.plugin_classes = [
                                chanbot.chanbot,
                                globalfunctions.globalfunctions,
                                song.song
                              ]
        for i in self.plugin_classes:
            toReload.append(sys.modules[getattr(i,'__module__')])
        for i in toReload:
            importlib.reload(i)
        self.init(c)
        for i in self.plugins:
            if hasattr(i,'onReady'):
                await i.onReady()
        await self.generateDocumentation()

    async def generateDocumentation(self):
        """
        Generates the user-based documentation
        """
        comms = []
        scan = [self]
        scan.extend(self.plugins)
        for i in scan:
            comms.extend(self.getDocumentation(i))
        comms.sort(key=itemgetter(0))
        comms.sort(key=itemgetter(1),reverse=True)
        comms.sort(key=itemgetter(2))
        maxcomlength = len("Command")
        maxaccesslevellength = len("Access Level")
        maxchanlength = len("Channels")
        for i in comms:
            if len(i[0]) > maxcomlength:
                maxcomlength = len(i[0])
            if len(self.getRoleName(i[1],True)) > maxaccesslevellength:
                maxaccesslevellength = len(self.getRoleName(i[1],True))
            if len("/".join(i[2])) > maxchanlength:
                maxchanlength = len("/".join(i[2]))
        line = "```\n"
        line += "{} | {} | {}\n".format("Command".ljust(maxcomlength),"Access Level".ljust(maxaccesslevellength),"Channels".ljust(maxchanlength))
        line += "{}|{}|{}\n".format("-" * (maxcomlength + 1),"-" * (maxaccesslevellength + 2),"-" * (maxchanlength + 1))
        for i in comms:
            line += "{} | {} | {}\n".format(i[0].ljust(maxcomlength),
                                            self.getRoleName(i[1],True).replace(" "," " * (maxaccesslevellength - len(self.getRoleName(i[1],True)) + 1)),
                                            "/".join(i[2]).ljust(maxchanlength))
        line += "```"
        for i in self.client.servers:
            if i.name == self.client.user.name:
                for j in i.channels:
                    if j.name == "command-list":
                        for i in self.plugins:
                            if hasattr(i,'clearMessages'):
                                msgs = await i.clearMessages(j)
                                if len(msgs)>0:
                                    await self.client.edit_message(msgs[0],line)
                                else:
                                    msg = await self.client.send_message(j,line)
                                    await self.client.pin_message(msg)
                                break

    def getDocumentation(self,plugin):
        comms = []
        attrs = dir(plugin)
        for i in attrs:
            func = getattr(plugin,i)
            if hasattr(func,"__accesslevel__"):
                channels = []
                channels.extend(plugin.channels)
                if "testing" in channels:
                    channels.remove("testing")
                comms.append(["!{}".format(func.__name__),func.__accesslevel__,channels])
        return comms

    def getAccessLevel(self,user):
        """
        Fetches the access level of the given user from the bot's server - even works in PM or other servers
        """
        maxrole = 0
        for i in self.client.servers:
            if i.name == self.client.user.name:
                for j in i.members:
                    if j.id == user.id:
                        for k in j.roles:
                            if k.position > maxrole:
                                maxrole = k.position
        return maxrole

    @accesslevel(0)
    async def help(self,message,accesslevel,users):
        """
        Describes a specified command.

        Usage: "!help [command name]".
        """
        funcName=""
        if len(message.content.split(" ")) >= 2:
            funcName = message.content.split(" ")[1].lower()
        if len(funcName) > 1:
            if funcName[0] == '!':
                funcName = funcName[1:]
        if funcName == "":
            funcName = "help"
        scan = [self]
        scan.extend(self.plugins)
        for i in scan:
            if hasattr(i,funcName):
                func = getattr(i,funcName)
                docString = func.__doc__
                if docString == None:
                    docString = "Could not find description."
                docString = docString.split(" ")
                docString[:] = [x for x in docString if x != ""]
                docString = ' '.join(docString)
                docString = docString.split("\n")
                docString[:] = [x for x in docString if x != ""]
                docString = '\n'.join(docString)
                accesslevel = ""
                if hasattr(func,"__accesslevel__"):
                    accesslevel = "Access level: {}".format(self.getRoleName(func.__accesslevel__,True))
                    channels = []
                    channels.extend(i.channels)
                    if "testing" in channels:
                        channels.remove("testing")
                    inChannel = ""
                    if len(channels) == 0:
                        inChannel = "Channels: None"
                    elif len(channels) == 1:
                        inChannel = "Channel: {}".format(channels[0])
                    else:
                        inChannel = "Channels: {}".format("/".join(channels))
                    await self.sendMessage(message,"!{} - {}. {}.\n{}".format(func.__name__,accesslevel,inChannel,docString))

    async def action(self,message):
        """
        Action method - collates basic data about a user and runs sub-plugin actions
        Also runs commands in this plugin (which should only be !help)
        """
        self.users.setNode(message.author.mention,"identity/accesslevel",self.getAccessLevel(message.author))
        self.users.setNode(message.author.mention,"identity/name",message.author.name)
        self.users.setNode(message.author.mention,"identity/lastseen",datetime.datetime.utcnow().strftime("%a, %b %d %Y %I:%M:%S %p"))
        if not message.channel.is_private:
            self.users.setNode(message.author.mention,"identity/nick","" if message.author.nick == None else message.author.nick)
        for i in self.plugins:
            await i.action(message,self.users)
        command = message.content.split(" ")[0].lower()
        if command[0] == "!":
            if hasattr(self,command[1:]):
                if hasattr(getattr(self,command[1:]),"__accesslevel__"):
                    await getattr(self,command[1:])(message,self.getAccessLevel(message.author),self.users)
    
    def getRoleName(self,roleNumber,includeRoleNumber = False):
        """
        Gets the name of a role by role position from the server
        """
        roleName = ""
        for i in self.client.servers:
            if i.name == self.client.user.name:
                for j in i.roles:
                    if j.position == roleNumber:
                        roleName = j.name
                        if roleName[0] == '@':
                            roleName = roleName[1:]
        if includeRoleNumber:
            roleName += " ({})".format(roleNumber)
        return roleName

    async def sendMessage(self,msgObj,message):
        """
        Sends messages to Discord
        """
        await self.client.send_message(msgObj.channel,message)
        print("#{} - {}: {}".format(msgObj.channel,self.client.user.name,message))