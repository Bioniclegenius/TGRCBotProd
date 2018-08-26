import asyncio
import discord
import re
import math
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

class chanbot(object):
    """
    Handles commands that work in #bot

    Command  | Access Level   | Channels
    ---------|----------------|---------
    !calc    | everyone   (0) | bot     
    !ping    | everyone   (0) | bot     
    """

    def init(self,c):
        self.client = c
        self.channels = ["bot","testing"]
        
    @accesslevel(0)
    async def ping(self,message,accesslevel,users):
        """
        Pong!
        """
        await self.sendMessage(message,"Pong!")

    @accesslevel(0)
    async def calc(self,message,accesslevel,users):
        """
        Attempts to evaluate a given mathematical expression. Ignores if it's invalid.

        Usage: !calc <expression>
        Example: !calc 1+(2*3)^4/5-6
        """
        line = message.content[message.content.find(" ")+1:]
        if expressionTerm.search(line.replace(" ","")) != None:
            msg = line.replace(" ","")
            expression = expressionTerm.search(msg).group(0)
            matches = re.match("(-|)[0-9.]+",msg)
            if expression == msg and (matches == None or matches.group(0) != msg):
                parentheseCount = 0
                for i in range(0,len(expression)):
                    if expression[i] == '(':
                        parentheseCount += 1
                    elif expression[i] == ')':
                        parentheseCount -= 1
                    if parentheseCount < 0:
                        break
                if parentheseCount == 0:
                    expression = self.evalExpr(expression)
                    if expression.find("ERROR") != -1:
                        await self.error(message,"Invalid equation")
                    else:
                        await self.sendMessage(message,expression)
                else:
                    await self.error(message,"Mismatched parentheses")

    async def action(self,message,users):
        """
        Runs various commands in #bot
        """
        if message.channel.name in self.channels and not message.channel.is_private:
            #Run various commands
            accesslevel = int(users.getNode(message.author.mention,"identity/accesslevel").text)
            command = message.content.split(" ")[0].lower()
            if command[0] == "!":
                if hasattr(self,command[1:]):
                    if hasattr(getattr(self,command[1:]),"__accesslevel__"):
                        await getattr(self,command[1:])(message,accesslevel,users)
            #Play the kinky word game
            word = users.getNode(self.client.user.mention,"kinky").text
            if word == None:
                users.setNode(self.client.user.mention,"kinky","pound")
                word = users.getNode(self.client.user.mention,"kinky").text
            word = word.lower()
            expressionTerm = re.compile("[0-9\(\)\+\-/\*\.\^]+")
            searchterm = ".*"
            for i in range(0,len(word)-1):
                searchterm+=word[i]+"[ ]*"
            searchterm+=word[len(word)-1]
            if re.match(searchterm,message.content.lower())!=None:
               await self.sendMessage(message,"Kinky.")

    def evalExpr(self,expression):
        """
        Attempts to evaluate a mathematical expression
        """
        if expression.count('(')>0:
            left=expression[:expression.find('(')]
            right=expression[expression.rfind(')') + 1:]
            if len(left) > 0:
                if left[len(left) - 1] in "0123456789.":
                    left = "{}*".format(left)
            expression = "{}{}{}".format(left,self.evalExpr(expression[expression.find('(') + 1:expression.rfind(')')]),right)
        while expression.find('^') != -1:
            opLoc = expression.find('^')
            left = expression[:opLoc]
            right = expression[opLoc + 1:]
            for scanLoc in range(len(left) - 1,-1,-1):
                if left[scanLoc] not in "0123456789.-":
                    if left[scanLoc] == '-':
                        if scanLoc == 0:
                            break
                        else:
                            if left[scanLoc - 1] not in "/*-+^":
                                return "ERROR"
                    left = left[scanLoc + 1:]
                    break
            for scanLoc in range(len(right)):
                if right[scanLoc] not in "0123456789.-":
                    right = right[:scanLoc]
                    break
                if right[scanLoc] == '-':
                    if scanLoc != 0:
                        right = right[:scanLoc]
                        break
            if left == "" or right == "":
                return "ERROR"
            try:
                if left.find('.') != -1:
                    leftNum = float(left)
                else:
                    leftNum = int(left)
            except Exception:
                return "ERROR"
            try:
                if right.find('.') != -1:
                    rightNum = float(right)
                else:
                    rightNum = int(right)
            except Exception:
                return "ERROR"
            total = math.pow(leftNum,rightNum)
            if total == int(total):
                total = int(total)
            expression="{}{}{}".format(expression[:opLoc - len(left)],total,expression[opLoc + len(right) + 1:])
        while expression.find('/') != -1 or expression.find('*') != -1:
            opLoc = expression.find('/')
            if opLoc == -1 or (expression.find('*') < opLoc and expression.find('*') != -1):
                opLoc = expression.find('*')
            left = expression[:opLoc]
            right = expression[opLoc + 1:]
            for scanLoc in range(len(left) - 1,-1,-1):
                if left[scanLoc] not in "0123456789.-":
                    if left[scanLoc] == '-':
                        if scanLoc == 0:
                            break
                        else:
                            if left[scanLoc - 1] not in "/*-+^":
                                return "ERROR"
                    left = left[scanLoc + 1:]
                    break
            for scanLoc in range(len(right)):
                if right[scanLoc] not in "0123456789.-":
                    right = right[:scanLoc]
                    break
                if right[scanLoc] == '-':
                    if scanLoc != 0:
                        right = right[:scanLoc]
                        break
            if left == "" or right == "":
                return "ERROR"
            try:
                if left.find('.') != -1:
                    leftNum = float(left)
                else:
                    leftNum = int(left)
            except Exception:
                return "ERROR"
            try:
                if right.find('.') != -1:
                    rightNum = float(right)
                else:
                    rightNum = int(right)
            except Exception:
                return "ERROR"
            total = 0
            if expression[opLoc] == '*':
                total = leftNum * rightNum
            if expression[opLoc] == '/':
                total = leftNum / rightNum
            if total == int(total):
                total = int(total)
            expression="{}{}{}".format(expression[:opLoc - len(left)],total,expression[opLoc + len(right) + 1:])
        while expression.find('+') != -1 or expression[1:].find('-') != -1:
            opLoc = expression.find('+')
            if opLoc == -1 or (expression[1:].find('-')+1 < opLoc and expression[1:].find('-') != -1):
                opLoc = expression[1:].find('-') + 1
            left = expression[:opLoc]
            right = expression[opLoc + 1:]
            for scanLoc in range(len(left) - 1,-1,-1):
                if left[scanLoc] not in "0123456789.-":
                    if left[scanLoc] == '-':
                        if scanLoc == 0:
                            break
                        else:
                            if left[scanLoc-1] not in "/*-+^":
                                return "ERROR"
                    left = left[scanLoc+1:]
                    break
            for scanLoc in range(len(right)):
                if right[scanLoc] not in "0123456789.-":
                    right = right[:scanLoc]
                    break
                if right[scanLoc] == '-':
                    if scanLoc != 0:
                        right=right[:scanLoc]
                        break
            if left == "" or right == "":
                return "ERROR"
            try:
                if left.find('.') != -1:
                    leftNum = float(left)
                else:
                    leftNum = int(left)
            except Exception:
                return "ERROR"
            try:
                if right.find('.') != -1:
                    rightNum = float(right)
                else:
                    rightNum = int(right)
            except Exception:
                return "ERROR"
            total = 0
            if expression[opLoc] == '+':
                total = leftNum + rightNum
            if expression[opLoc] == '-':
                total = leftNum - rightNum
            if total == int(total):
                total = int(total)
            expression="{}{}{}".format(expression[:opLoc - len(left)],total,expression[opLoc + len(right) + 1:])
        if expression.count(".") > 1:
            return "ERROR"
        return expression

    async def sendMessage(self,msgObj,message):
        """
        Sends messages to Discord
        """
        await self.client.send_message(msgObj.channel,message)
        print("#{} - {}: {}".format(msgObj.channel,self.client.user.name,message))