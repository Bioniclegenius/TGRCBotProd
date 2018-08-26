import os
import xml.etree.ElementTree as et
import xml.dom.minidom as minidom
import datetime

class users(object):
    """
    Handles the user file and interactions with it.
    
    Available methods:

    init()
        - loads user file
    saveUsers()
        - saves to the user file
    getUser(username)
        - gets the specified user, creates if they don't exist
    getNode(username,nodepath)
        - gets the node from a specified user
    setNode(username,nodepath,value)
        - sets a node value under a user, tries to create if it doesn't exist
        - value will be cast to a string
    deleteNode(username,nodepath)
        - deletes a node from under a user

    """

    def prettifyXml(self,elem):
        """
        Cleans up an XML root to format nicely, with indentation and everything
        """
        rough=et.tostring(elem,"utf-8")
        rough=rough.decode("utf-8")
        rough=rough.replace("  ","")
        rough=rough.replace("\n","")
        rough=rough.replace("\t","")
        rough=rough.encode("utf-8")
        reparsed=minidom.parseString(rough)
        return reparsed.toprettyxml(indent="  ")

    def stripMention(self,username):
        """
        Strips extra characters from the start and end of a mention, to get just the user ID
        """
        while username[0] not in "0123456789":
            username = username[1:]
            if username == "":
                return ""
        if len(username) > 0:
            while username[len(username) - 1] not in "0123456789":
                username = username[:-1]
                if username == "":
                    return ""
        return username

    def init(self,client = None):
        """
        Loads up the user file - one-time call (users.xml)
        """
        self.users = None
        if not os.path.exists("users.xml"):
            f = open("users.xml","w+")
            f.write("<users></users>")
            f.close()
        else:
            self.userstree = et.parse("users.xml")
            self.users = self.userstree.getroot()
        self.saveUsers()

    def saveUsers(self):
        """
        Saves to the user file (users.xml)
        """
        f = open("users.xml","w")
        f.write(self.prettifyXml(self.users))
        f.close()
        self.userstree = et.parse("users.xml")
        self.users = self.userstree.getroot()

    def getUser(self,username):
        """
        Gets a specified user node. If it doesn't exist, creates said user with a timestamp of creation, if specified.
        """
        if username == "" or self.users == None:
            return None
        usernameTemp = self.getUserID(username)
        if usernameTemp == "":
            usernameTemp = self.stripMention(username)
        username = usernameTemp
        if username != "":
            user = self.users.find(".//user[@id='{}']".format(username))
            if user == None:
                since = datetime.datetime.utcnow().strftime("%a, %b %d %Y %I:%M:%S %p")
                user = et.Element("user",{"id":username,"since":since})
                self.users.append(user)
                self.saveUsers()
                user = self.users.find(".//user[@id='{}']".format(username))
            return user
        return None

    def getUserID(self,username):
        """
        Will not create a user if not found.
        Looks for a user by nickname, then by username, then by ID.
        If nothing is found, will return ""
        """
        if username == "" or self.users == None:
            return ""
        user = self.users.find(".//user/identity[nick='{}']/..".format(username))
        if user != None:
            return user.get("id")
        user = self.users.find(".//user/identity[name='{}']/..".format(username))
        if user != None:
            return user.get("id")
        username = self.stripMention(username)
        user = self.users.find(".//user[@id='{}']".format(username))
        if user != None:
            return username
        return ""

    def getNode(self,username,nodepath):
        """
        Gets a node from a specified user
        Returns None if the node does not exist
        """
        user = self.getUser(username)
        if user == None:
            return user
        node = user.find(nodepath)
        return node

    def setNode(self,username,nodepath,value):
        """
        Edits a node value on a user - creates tree to node if it doesn't exist
        Will not make changes if node value already is value.

        Warning: xpaths aren't acceptable in the case of creating the node, so try to avoid that.
        For creation of a tree to a node, E.G. creating rpg/inventory/item/type with a value of "sword,"
            we can't have rpg[@type=whatever]/inventory. Can't create the rpg node by xpath if it doesn't exist.
            For best practices, run a getnode before a setNode, and create a basic xpath to it if getNode returns None.

        """
        value=str(value)
        user = self.getUser(username)
        curNode = self.getNode(username,nodepath)
        if curNode != None:
            if curNode.text != value and not (value == "" and curNode.text == None):
                curNode.text = value
                self.saveUsers()
            return
        path = nodepath.split("/")
        curNode = user
        for i in range(0,len(path)):
            if curNode.find(path[i]) == None:
                newNode = et.Element(path[i])
                curNode.append(newNode)
            curNode = curNode.find(path[i])
        curNode.text = value
        self.saveUsers()

    def deleteNode(self,username,nodepath):
        """
        Deletes a node from under a user by path.

        WARNING: all node data will be deleted! There is no recovery after deletion!
        """
        user = self.getUser(username)
        path = nodepath.split("/")
        curNode = user
        for i in range(0,len(path)-1):
            if curNode.find(path[i]) == None:
                return
            curNode = curNode.find(path[i])
        if curNode.find(path[-1]) != None:
            curNode.remove(curNode.find(path[-1]))
            self.saveUsers()