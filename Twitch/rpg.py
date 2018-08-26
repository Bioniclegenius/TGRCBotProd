from functools import wraps
import xml.etree.ElementTree as et
import os.path

#   self,   pf,     accesslevel,    sock,   username,   msgsource,  msgtype,    msg,    channame,   isprimary
#    0      1            2           3         4            5          6         7         8            9

def accesslvl(accesslevel):
    def accesslevel_decorator(func):
        @wraps(func)
        def accesslevelwrapper(*args):
            if args[2]>=accesslevel:
                func(*args)
            else:
                args[1].chat(args[3],"You do not have access to that command, {}!".format(args[4]),args[5])
        accesslevelwrapper.__accesslevel__=accesslevel
        return accesslevelwrapper
    return accesslevel_decorator

def option(optionname,default,goal):
    def option_decorator(func):
        @wraps(func)
        def optionwrapper(*args):
            if args[1].getoptioninternal(args[5],optionname,default,True)==goal:
                func(*args)
        optionwrapper.__optionname__=optionname
        return optionwrapper
    return option_decorator

def nopm(func):
    @wraps(func)
    def nopmwrapper(*args):
        if args[6]=="chat" and args[4]!=args[5]:
            func(*args)
    nopmwrapper.__chatonly__=True
    return nopmwrapper

def canpm(func):
    @wraps(func)
    def canpmwrapper(*args):
        if args[9] or args[6]=="chat":
            func(*args)
    canpmwrapper.__pmuseable__=True
    return canpmwrapper

def pmonly(func):
    @wraps(func)
    def pmonlywrapper(*args):
        if args[9] and args[6]!="chat":
            func(*args)
    pmonlywrapper.__pmonly__=True
    return pmonlywrapper

class RPG:

    def loadMap(self,mapname):
        filepath="rpg/{}.txt".format(mapname)
        if os.path.isfile(filepath):
            fileObj=open(filepath,"r")
            filemap=fileObj.read().split('\n')
            fileObj.close()
            maxlen=len(filemap)
            x=0
            while x<maxlen:
                if filemap[x].find('-')!=-1:
                    filemap[x]=filemap[x][:filemap[x].find('-')]
                    x+=1
                elif filemap[x].find(' ')!=-1:
                    del filemap[x]
                    maxlen-=1
            return filemap
        else:
            return [""]

    def addUserNode(self,pf,channame,username,nodename,nodevalue="",nodePath=""):
        username=username.lower()
        nodename=nodename.lower()
        user=pf.userroot.find(".//user[@name='{}']".format(username))
        if user==None:
            return -1# User not found
        parent=user
        if nodePath!="":
            parent=user.find(nodePath)
        if parent==None:
            return -2# Parent node not found
        child=et.Element(nodename)
        if nodevalue!="":
            child.text=nodevalue
        parent.append(child)
        pf.saveusers(channame)
        return 1

    def editUserNode(self,pf,channame,username,nodepath,nodevalue=""):
        username=username.lower()
        user=pf.userroot.find(".//user[@name='{}']".format(username))
        if user==None:
            return -1# User not found
        node=user.find(nodepath)
        if node==None:
            return -2# Node not found
        node.text=nodevalue
        pf.saveusers(channame)
        return 1

    def getUserNode(self,pf,username,nodepath):
        username=username.lower()
        user=pf.userroot.find(".//user[@name='{}']".format(username))
        if user==None:
            return -1# User not found
        node=user.find(nodepath)
        if node==None:
            return -2# Node not found
        return node.text

    def delUserNode(self,pf,channame,username,nodename):
        username=username.lower()
        nodename=nodename.lower()
        user=pf.userroot.find(".//user[@name='{}']".format(username))
        if user==None:
            return -1# User not found
        node=pf.userroot.find(nodename)
        if node==None:
            return -1# Couldn't find node
        user.remove(node)
        pf.saveusers(channame)
        return 1

    def newUser(self,pf,username,channame):
        self.addUserNode(pf,channame,username,"rpg")
        self.addUserNode(pf,channame,username,"location","",".//rpg")
        self.addUserNode(pf,channame,username,"map","default",".//rpg/location")
        self.addUserNode(pf,channame,username,"x","50",".//rpg/location")
        self.addUserNode(pf,channame,username,"y","50",".//rpg/location")

    @accesslvl(6)
    @nopm
    def addnode(self,pf,accesslevel,sock,username,msgsource,msgtype,msg,channame,isprimary):
        """
        Adds a node to the specified user.

        Usage: "!rpg addnode <username> <nodename> [nodevalue] [nodepath]"
        """
        if len(msg)<3:
            pf.chat(sock,"Not enough parameters, {}!".format(username),msgsource)
        else:
            targetname=msg[1].lower()
            nodename=msg[2].lower()
            nodevalue=""
            if len(msg)>=4:
                nodevalue=msg[3]
            nodepath=""
            if len(msg)>=5:
                nodepath=msg[4]
            val=self.addUserNode(pf,channame,targetname,nodename,nodevalue,nodepath)
            if val==-1:
                pf.chat(sock,"User {} doesn't exist, {}!".format(username),msgsource)
            elif val==-2:
                pf.chat(sock,"That node path isn't valid, {}!".format(username),msgsource)
            else:
                pf.chat(sock,"{} successfully added to {} with a value of {}, {}.".format(nodename,targetname,nodevalue,username),msgsource)

    @accesslvl(6)
    @nopm
    def editnode(self,pf,accesslevel,sock,username,msgsource,msgtype,msg,channame,isprimary):
        """
        Edits a node on the specified user.

        Usage: "!rpg editnode <username> <nodepath> [nodevalue]"
        """
        if len(msg)<3:
            pf.chat(sock,"Not enough parameters, {}!".format(username),msgsource)
        else:
            targetname=msg[1].lower()
            nodepath=msg[2]
            nodevalue=""
            if len(msg)>=4:
                nodevalue=msg[3]
            val=self.editUserNode(pf,channame,targetname,nodepath,nodevalue)
            if val==-1:
                pf.chat(sock,"User {} doesn't exist, {}!".format(username),msgsource)
            elif val==-2:
                pf.chat(sock,"That node path isn't valid, {}!".format(username),msgsource)
            else:
                pf.chat(sock,"{} on {} successfully edited to {}, {}.".format(nodepath,targetname,nodevalue,username),msgsource)
                
    @accesslvl(6)
    @nopm
    def getnode(self,pf,accesslevel,sock,username,msgsource,msgtype,msg,channame,isprimary):
        """
        Gets the node value.

        Usage: "!rpg getnode <username> <nodepath>"
        """
        if len(msg)<3:
            pf.chat(sock,"Not enough parameters, {}!".format(username),msgsource)
        else:
            targetname=msg[1]
            nodepath=msg[2]
            result=self.getUserNode(pf,targetname,nodepath)
            if result==-1:
                pf.chat(sock,"User {} doesn't exist, {}!".format(targetname,username),msgsource)
            elif result==-2:
                pf.chat(sock,"Nodepath {} wasn't found, {}!".format(nodepath,username),msgsource)
            else:
                pf.chat(sock,"Value of {} on {}: {}".format(nodepath,targetname,result),msgsource)
                
    @accesslvl(6)
    @nopm
    def delnode(self,pf,accesslevel,sock,username,msgsource,msgtype,msg,channame,isprimary):
        """
        Deletes the specified node.

        Usage: "!rpg delnode <username> <nodepath>"
        """
        if len(msg)<3:
            pf.chat(sock,"Not enough parameters, {}!".format(username),msgsource)
        else:
            targetname=msg[1]
            nodepath=msg[2]
            result=self.delUserNode(pf,channame,targetname,nodepath)
            if result==-1:
                pf.chat(sock,"User {} doesn't exist, {}!".format(targetname,username),msgsource)
            elif result==-2:
                pf.chat(sock,"Nodepath {} wasn't found, {}!".format(nodepath,username),msgsource)
            else:
                pf.chat(sock,"Node {} was successfully removed from {}, {}!".format(nodepath,targetname,username),msgsource)

    @accesslvl(6)
    @canpm
    def testmap(self,pf,accesslevel,sock,username,msgsource,msgtype,msg,channame,isprimary):
        """
        Prints a map to console for testing purposes. Will be very spammy on large maps.
        """
        if len(msg)>=2:
            mapname=msg[1]
        else:
            mapname="Default"
        curmap=self.loadMap(mapname)
        if curmap!=[""]:
            print(curmap)
            print("{} : {}".format(int(len(curmap[0])/2),len(curmap)))
            pf.chat(sock,"Loaded map {} and printed it to console, {}!".format(mapname,username),msgsource)
        else:
            pf.chat(sock,"That isn't an existing map, {}!".format(username),msgsource)
        
    @accesslvl(0)
    @canpm
    def help(self,pf,accesslevel,sock,username,msgsource,msgtype,msg,channame,isprimary):
        """
        Describes a specified RPG command.

        Usage: "!rpg help [rpg command name]".

        Online documentation: http://goo.gl/fIului
        """
        funcName="help"
        if len(msg)>=2:
            funcName=msg[1].lower()
        if len(funcName)>1:
            if funcName[0]=='!':
                funcName=funcName[1:]
        if hasattr(self,funcName):
            func=getattr(self,funcName)
            docString=func.__doc__
            if docString==None:
                docString="Could not find description."
            docString=docString.replace('\n',' ').replace("POINTS",pf.pointname(channame,0)).replace("POINT",pf.pointname(channame,1))
            docString=' '.join(docString.split())
            accesslevel=""
            if hasattr(func,"__accesslevel__"):
                accesslevel="Access level: {}".format(func.__accesslevel__)
                pf.chat(sock,"!rpg {} - {}. {}".format(func.__name__,accesslevel,docString),msgsource)
            else:
                pf.chat(sock,"{} is not a command, {}!".format(funcName,username),msgsource)
        else:
            pf.chat(sock,"{} is not a command, {}!".format(funcName,username),msgsource)

    def rpgCore(self,pf,accesslevel,sock,username,msgsource,msgtype,msg,channame,isprimary):
        if self.getUserNode(pf,username,".//rpg")==-2:
            self.newUser(pf,username,channame)
        if len(msg)>=2:
            msg[1]=msg[1].lower()
            if hasattr(self,msg[1]):
                if hasattr(getattr(self,msg[1]),"__accesslevel__"):
                    getattr(self,msg[1])(pf,accesslevel,sock,username,msgsource,msgtype,msg[1:],channame,isprimary)
        else:
            pf.chat(sock,"You must enter an RPG command, {}! Try \"!rpg help\".".format(username),msgsource)