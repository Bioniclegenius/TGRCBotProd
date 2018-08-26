import asyncio
import discord
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

class globalfunctions(object):
    """
    Functions available in any channel of chat

    Command  | Access Level   | Channels
    ---------|----------------|---------
    !delnode | Bot Coders (4) | any     
    !setnode | Bot Coders (4) | any     
    !clear   | Mods       (2) | any     
    !link    | everyone   (0) | any     
    """

    def init(self,c):
        self.client = c
        self.channels = ["any"]

    @accesslevel(2)
    async def clear(self,message,accesslevel,users):
        """
        Clears messages from the chat.

        Usage: !clear [username or number of message] [number of messages or username]
        """
        com = message.content.lower().split(" ")
        number = 100
        username=""
        if len(com) == 2:
            try:
                number = int(com[1])
            except ValueError:
                number = 100
                username = com[1]
        elif len(com) >= 3:
            try:
                number = int(com[1])
                username = com[2]
            except ValueError:
                try:
                    number = int(com[2])
                    username = com[1]
                except ValueError:
                    number = 0
                    username = ""
        await self.clearMessages(message.channel,number,username)

    @accesslevel(0)
    async def link(self,message,accesslevel,users):
        """
        Gives the link to the bot's discord.
        """
        await self.sendMessage(message,"https://discord.gg/jeAzUnc")

    @accesslevel(4)
    async def getnode(self,message,accesslevel,users):
        """
        Gets a node under a user.

        Usage: !getnode <@username> <nodepath>
        """
        msg = message.content.lower().split(" ")
        if len(msg)<3:
            await self.sendMessage(message,"There aren't enough parameters, {}!".format(message.author.mention))
            return
        username = msg[1]
        path = msg[2]

    @accesslevel(4)
    async def setnode(self,message,accesslevel,users):
        """
        Adds a node under a user.

        Usage: !setnode <@username> <nodepath> <value>

        Warning: very little error-checking here. Be sure of your values.
        """
        msg = message.content.lower().split(" ")
        if len(msg)<4:
            await self.sendMessage(message,"There aren't enough parameters, {}!".format(message.author.mention))
            return
        username = msg[1]
        path = msg[2]
        value = msg[3]
        users.setNode(username,path,value)
        await self.sendMessage(message,"User node added.")

    @accesslevel(4)
    async def getnode(self,message,accesslevel,users):
        """
        Gets the value of a node of a user.

        Usage: !getnode <username> <nodepath>
        
        Be careful of using a mention - if @username, user will be created if they don't exist.
        """
        msg = message.content.split(" ")
        if len(msg)<3:
            await self.sendMessage(message,"There aren't enough parameters, {}!".format(message.author.mention))
            return
        username = msg[1]
        nodepath = msg[2]
        node = users.getNode(username,nodepath)
        if node != None:
            if node.text.replace("\n","").replace(" ","") != "":
                await self.sendMessage(message,"{}/{} has a value of \"{}\".".format(username,nodepath,node.text))
            else:
                await self.sendMessage(message,"{}/{} exists, but is not a leaf node.".format(username,nodepath))
        else:
            await self.sendMessage(message,"{}/{} is an invalid node path.".format(username,nodepath))

    @accesslevel(4)
    async def getuserid(self,message,accesslevel,users):
        """
        Gets a user ID by nick, name, or mention.
        Usage: !getuserid <nick/username/mention/id>
        """
        msg = message.content.split(" ")
        if len(msg)<2:
            await self.sendMessage(message,"There aren't enough parameters, {}!".format(message.author.mention))
            return
        username = " ".join(msg[1:])
        id = users.getUserID(username)
        if id == "":
            await self.sendMessage(message,"Error, user ID not found!")
        else:
            await self.sendMessage(message,"{} has a user ID of {}.".format(username,id))

    @accesslevel(4)
    async def delnode(self,message,accesslevel,users):
        """
        Deletes a node from under a user.

        Usage: !delnode <@username> <nodepath>

        Warning: very little error-checking here. Be sure of your values.
        """
        msg = message.content.lower().split(" ")
        if len(msg)<3:
            await self.sendMessage(message,"There aren't enough parameters, {}!".format(message.author.mention))
            return
        username = msg[1]
        path = msg[2]
        users.deleteNode(username,path)
        await self.sendMessage(message,"User node deleted.")

    async def action(self,message,users):
        """
        Runs all commands in globalfunctions
        """
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

    async def clearMessages(self,channel,number = 100,username=""):
        """
        Clears messages from a channel, with a specified number and/or username
        Defaults to 100 messages unless specified
        Defaults to clearing from all users unless specified
        """
        number = int(number)
        counter = 0
        pinnedMessages = []
        async for x in self.client.logs_from(channel,limit = 100):
            if counter < number:
                if username == "" or username == x.author.mention:
                    if not x.pinned:
                        await self.client.delete_message(x)
                        counter += 1
                        await asyncio.sleep(0.5)
                    else:
                        pinnedMessages.append(x)
        return pinnedMessages
                

    def getRoleName(self,message,roleNumber):
        """
        Gets the name of a role by role position from the server
        """
        for i in client.server.roles:
            if i.position == roleNumber:
                roleName = i.name
                if roleName[0] == '@':
                    roleName = roleName[1:]
                return roleName