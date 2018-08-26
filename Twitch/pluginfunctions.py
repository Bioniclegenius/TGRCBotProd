import cfg
import cfg2
import socket
import re
import time
import datetime
import random
import importlib
import urllib
import urllib.request
import urllib.parse
import dateutil.relativedelta
import math
import rpg as rpgcode
import xml.etree.ElementTree as et
import xml.dom.minidom as minidom
import sys
import os
import shutil
import traceback
import inspect
from random import gauss
from functools import wraps
from bs4 import BeautifulSoup
from urllib.request import urlopen
from xml.dom.minidom import parseString

#   self,   accesslevel,    sock,       username,   msgsource,  msgtype,    msg,        channame,   isprimary
#   0           1           2           3           4           5           6           7           8

def accesslvl(accesslevel):
    def accesslevel_decorator(func):
        @wraps(func)
        def accesslevelwrapper(*args):
            if args[1]>=accesslevel:
                func(*args)
            else:
                args[0].chat(args[2],"You do not have access to that command, {}!".format(args[3]),args[4])
        accesslevelwrapper.__accesslevel__=accesslevel
        return accesslevelwrapper
    return accesslevel_decorator

def option(optionname,default,goal):
    def option_decorator(func):
        @wraps(func)
        def optionwrapper(*args):
            if args[0].getoptioninternal(args[4],optionname,default,True)==goal:
                func(*args)
        optionwrapper.__optionname__=optionname
        return optionwrapper
    return option_decorator

def nopm(func):
    @wraps(func)
    def nopmwrapper(*args):
        if args[5]=="chat" and args[3]!=args[4]:
            func(*args)
    nopmwrapper.__chatonly__=True
    return nopmwrapper

def canpm(func):
    @wraps(func)
    def canpmwrapper(*args):
        if args[8] or args[5]=="chat":
            func(*args)
    canpmwrapper.__pmuseable__=True
    return canpmwrapper

def pmonly(func):
    @wraps(func)
    def pmonlywrapper(*args):
        if args[8] and args[5]!="chat":
            func(*args)
    pmonlywrapper.__pmonly__=True
    return pmonlywrapper

def encountered(func):
    @wraps(func)
    def encounteredwrapper(*args):
        if args[0].isInEncounter and args[3]==args[0].userInEncounter:
            func(*args)
    encounteredwrapper.__encounter__=True
    return encounteredwrapper

class pf:

    def stripchansign(self,chan):
        if chan[0]=="#":
            return chan[1:]
        return chan

    def pointname(self,chan,numpoints,singlename="",pluralname=""):
        if numpoints==1:
            if singlename=="":
                return self.getoptioninternal(chan,"pointname","point",True)
            else:
                return singlename
        else:
            if pluralname=="" and singlename=="":
                return "{}s".format(self.getoptioninternal(chan,"pointname","point",True))
            elif pluralname=="" and singlename!="":
                return "{}s".format(singlename)
            else:
                return pluralname

    def __init__(self):
        self.initialize()

    def initialize(self):
        self.moderators=[]
        self.staff=[]
        self.admins=[]
        self.global_mods=[]
        self.viewers=[]
        self.supers=[]
        self.botsupers=[]
        self.botmods=[]
        self.betUsernames=[]

        self.isInEncounter=False

        self.voteoptions={}
        self.uservotes={}
        self.votegoing=False

        self.hourchange=0
        self.maxpointsusername=""
        self.maxpointsvalue=0

        #Encounter Variables
        self.forceEncounter=0
        self.isInEncounter=False
        self.userInEncounter=""
        self.wildPokeEncounter=0
        self.wildPokeLevel=40
        self.encounterTimerString=""
        self.usedPokemon=0
        self.encounterTimer=datetime.datetime.utcnow()
        importlib.reload(rpgcode)
        self.rpgobject=rpgcode.RPG()

    def getoptioninternal(self,chan,optionname,defaultValue="",asString=True):
        optionname=optionname.lower()
        defaultValue="{}".format(defaultValue).lower()
        if chan[0]=='#':
            chan=chan[1:]
        returnvalue=""
        if self.optionsroot.find(".//option[@name='"+optionname+"']")!=None:
            returnvalue=self.optionsroot.find(".//option[@name='"+optionname+"']").text
            if returnvalue==None:
                if defaultValue!="":
                    self.setoptioninternal(chan,optionname,defaultValue)
                    returnvalue="{}".format(defaultValue)
        elif defaultValue!="":
            self.setoptioninternal(chan,optionname,defaultValue)
            returnvalue="{}".format(defaultValue)
        if(asString):
            return returnvalue
        else:
            try:
                return int(returnvalue)
            except ValueError:
                try:
                    return int(defaultValue)
                except ValueError:
                    return 0

    def setoptioninternal(self,chan,optionname,value):
        optionname=optionname.lower()
        value="{}".format(value).lower()
        if chan[0]=='#':
            chan=chan[1:]
        if self.optionsroot.find(".//option[@name='"+optionname+"']")!=None:
            self.optionsroot.find(".//option[@name='"+optionname+"']").text=value
            if value=="":
                self.optionsroot.remove(self.optionsroot.find(".//option[@name='"+optionname+"']"))
        elif value!="":
            option=et.Element("option",{"name":optionname})
            option.text=value
            self.optionsroot.append(option)
        self.saveoptions(chan)

    def limittime(self,time):
        return max(min(59,time),0)

    def encountertimeleft(self,chan,sock,messagesource):
        if self.getoptioninternal(chan,"encountertimeexpire",300,False)>3599:
            self.setoptioninternal(chan,"encountertimeexpire",3599)
        if self.getoptioninternal(chan,"encountertimeexpire",300,False)<30:
            self.setoptioninternal(chan,"encountertimeexpire",30)
        encountertime=self.getoptioninternal(chan,"encountertimeexpire",300,False)
        maxtime=datetime.time(hour=0,minute=encountertime//60,second=encountertime%60)
        timeleft=dateutil.relativedelta.relativedelta(datetime.datetime.utcnow(),self.encounterTimer)
        if timeleft.seconds>=maxtime.second and timeleft.minutes>=maxtime.minute and self.isInEncounter==True:
            self.isInEncounter=False
            self.chat(sock,"The wild {} ran away from {}!".format(self.getpokename(self.wildPokeEncounter),self.userInEncounter),messagesource)
        else:
            minutesLeft=encountertime//60-timeleft.minutes;
            secondsLeft=encountertime%60-timeleft.seconds;
            if secondsLeft<0:
                secondsLeft+=60
                minutesLeft-=1
            self.encounterTimerString="[{}:{}] ".format("%02i"%minutesLeft,"%02i"%secondsLeft)

    def log(self,source,msg,doprint=True):
        if doprint:
            print(msg)
        if source[0]=="#":
            if not os.path.exists("logs/{}".format(self.stripchansign(source))):
                os.makedirs("logs//{}".format(self.stripchansign(source)))
            with open("logs/{}/{}.txt".format(self.stripchansign(source),self.getlogdate()),"a") as logfile:
                logfile.write("{}  |  {}\r\n".format(datetime.datetime.now().strftime("%I:%M:%S %p"),msg))
        else:
            with open("logs/{}{}.txt".format(self.getlogdate(),source),"a") as logfile:
                logfile.write("{}  |  {}\r\n".format(datetime.datetime.now().strftime("%I:%M:%S %p"),msg))
        with open("logs/{}Global.txt".format(self.getlogdate()),"a") as logfile:
            logfile.write("{}  |  {}\r\n".format(datetime.datetime.now().strftime("%I:%M:%S %p"),msg))

    def getlogdate(self):
        return datetime.datetime.now().strftime("%Yy-%mm-%dd-%a")

    def escape(self,escapethis):
        escapethis=escapethis.replace("'","").lower()
        return escapethis

    def blacklisted(self,username):
        username=username.lower()
        blacklist=['tmi','jtv',cfg2.NICK.lower(),'nightbot','moobot',"jokes_bot","ceresbot","nuttybot"]
        return username in blacklist

    def allviewers(self,channel,blacklist=True):
        viewers=[]
        try:
            with urllib.request.urlopen("https://tmi.twitch.tv/group/user/"+channel[1:]+"/chatters") as response:
                html = response.read()
            html=html.decode("utf-8")
            html=html[html.find("moderators")+11:]
            m=html[:html.find("]")]
            html=html[html.find("staff")+6:]
            st=html[:html.find("]")]
            html=html[html.find("admins")+7:]
            a=html[:html.find("]")]
            html=html[html.find("global_mods")+12:]
            g=html[:html.find("]")]
            html=html[html.find("viewers")+8:]
            v=html[:html.find("]")]
            while m.find("\"")!=-1:
                m=m[m.find("\"")+1:]
                if not self.blacklisted(m[:m.find("\"")]) or not blacklist:
                    viewers.append(m[:m.find("\"")])
                m=m[m.find("\"")+1:]
            while st.find("\"")!=-1:
                st=st[st.find("\"")+1:]
                if not self.blacklisted(st[:st.find("\"")]) or not blacklist:
                    viewers.append(st[:st.find("\"")])
                st=st[st.find("\"")+1:]
            while a.find("\"")!=-1:
                a=a[a.find("\"")+1:]
                if not self.blacklisted(a[:a.find("\"")]) or not blacklist:
                    viewers.append(a[:a.find("\"")])
                a=a[a.find("\"")+1:]
            while g.find("\"")!=-1:
                g=g[g.find("\"")+1:]
                if not self.blacklisted(g[:g.find("\"")]) or not blacklist:
                    viewers.append(g[:g.find("\"")])
                g=g[g.find("\"")+1:]
            while v.find("\"")!=-1:
                v=v[v.find("\"")+1:]
                if not self.blacklisted(v[:v.find("\"")]) or not blacklist:
                    viewers.append(v[:v.find("\"")])
                v=v[v.find("\"")+1:]
            return viewers
        except Exception:
            self.log(chan,"EXCEPTION\r\n{}".format(traceback.format_exc()))
            return []

    def randomviewerinternal(self,channel):
        viewers=self.allviewers(channel)
        if len(viewers)>0:
            return viewers[random.randint(0,len(viewers)-1)]
        return ""

    def pricecheck(self,pokeid):
        poke=self.pokeroot.find(".//pkmn[@num='"+str(pokeid)+"']")
        if poke!=None:
            if poke.find("price")!=None:
                return int(poke.find("price").text)
            return -2
        else:
            return -1

    def evointernal(self,channame,username,pokeid,itemname=""):
        username=username.lower()
        itemname=itemname.lower()
        user=self.userroot.find(".//user[@name='"+username+"']")
        if self.getitemname(itemname)=="" and itemname!="":
            return -8#That's not a real item.
        if itemname!="" and not self.userhasitem(username,itemname):
            return -9#You don't actually, you know, have that item.
        if user!=None:
            pokes=user.findall("pokemon")
            for x in pokes:#WOOOAAAAH
                if int(x.find("id").text)==pokeid:
                    species=self.pokeroot.find(".//pkmn[@num='"+str(x.find("num").text)+"']")
                    if species!=None:
                        evos=species.findall("evolution")
                        if len(evos)>0:#WE'RE HALFWAY THEEEERE
                            randomevos=species.findall(".//evolution[type='random']")
                            timeevos=species.findall(".//evolution[type='day']")
                            if len(randomevos)>0 and itemname=="":
                                evolveto=random.randint(0,len(randomevos)-1)
                                y=randomevos[evolveto]
                                to=self.pokeroot.find(".//pkmn[@num='"+y.find("to").text+"']")
                                requ=int(y.find("requ").text)
                                level=int(x.find("lvl").text)
                                if level>=requ:
                                    if to!=None:
                                        cost=0
                                        if to.find("price")!=None:
                                            cost=int(to.find("price").text)
                                        if self.getpoints(username)>=cost:
                                            x.find("num").text=y.find("to").text
                                            self.subpointsinternal(username,cost,channame)
                                            return 1
                                        else:
                                            return -7
                                    else:
                                        return -6
                                else:
                                    return -5
                            elif len(timeevos)>0 and itemname=="":
                                dayhour=self.getdayhour(channame)
                                y=species.find(".//evolution[type='night']")
                                if dayhour>=4 and dayhour<18:
                                    y=species.find(".//evolution[type='day']")
                                to=self.pokeroot.find(".//pkmn[@num='"+y.find("to").text+"']")
                                requ=int(y.find("requ").text)
                                level=int(x.find("lvl").text)
                                if level>=requ:
                                    if to!=None:
                                        cost=0
                                        if to.find("price")!=None:
                                            cost=int(to.find("price").text)
                                        if self.getpoints(username)>=cost:
                                            x.find("num").text=y.find("to").text
                                            self.subpointsinternal(username,cost,channame)
                                            return 1
                                        else:
                                            return -7
                                    else:
                                        return -6
                                else:
                                    return -5
                            else:
                                for y in evos:
                                    to=self.pokeroot.find(".//pkmn[@num='"+y.find("to").text+"']")
                                    foundlevelup=False
                                    if y.find("type").text=="level" and itemname=="":
                                        foundlevelup=True
                                        requ=int(y.find("requ").text)
                                        level=int(x.find("lvl").text)
                                        if level>=requ:#WOOOAAAAAH
                                            if to!=None:
                                                cost=0
                                                if to.find("price")!=None:
                                                    cost=int(to.find("price").text)
                                                if self.getpoints(username)>=cost:#LIZARD ON A CHAAAAIR
                                                    x.find("num").text=y.find("to").text
                                                    self.subpointsinternal(username,cost,channame)
                                                    return 1
                                                else:#LEMON AND A PEAR
                                                    return -7#You can't afford to evolve that pokemon
                                            else:
                                                return -6#...The species it evolves to doesn't exist... what? DB error.
                                        else:
                                            return -5#That pokemon isn't a high enough level
                                    elif y.find("type").text=="stone" and itemname[-5:]=="stone":
                                        requ=y.find("requ").text
                                        if requ==itemname[:-5]:
                                            x.find("num").text=y.find("to").text
                                            self.remitem(channame,username,itemname)
                                            return 1#EVO BY STONE COMPLETE
                                    elif y.find("type").text=="trade" and itemname=="linkcable":
                                        x.find("num").text=y.find("to").text
                                        self.remitem(channame,username,itemname)
                                        return 1#EVO BY LINK CABLE COMPLETE
                                    elif y.find("type").text=="special" and itemname!="":
                                        requ=y.find("requ").text
                                        if requ.lower()==itemname.lower():
                                            x.find("num").text=y.find("to").text
                                            self.remitem(channame,username,itemname)
                                            return 1#EVO BY ITEM COMPLETE
                                if itemname!="":
                                    return -5#That item doesn't do anything
                                elif foundlevelup==False:
                                    return -8#The pokemon doesn't evolve by leveling up
                        else:
                            return -4#That pokemon doesn't evolve
                    else:
                        return -3#...Species doesn't exist? Wat?
            return -2#pokemon doesn't exist
        else:
            return -1#user doesn't exist

    def getpokenum(self,pokename):
        pokename=pokename.lower()
        pokes=self.pokeroot.findall("pkmn")
        for x in pokes:
            if x.find("name").text.lower()==pokename:
                return int(x.get("num"))
            nicknames=x.findall("nickname")
            for y in nicknames:
                if y.text.lower()==pokename:
                    return int(x.get("num"))
        return -1

    def getcapturerate(self,pokenum):
        output=0
        pokes=self.pokeroot.find(".//pkmn[@num='"+str(pokenum)+"']")
        if pokes!=None:
            if pokes.find("catchrate")!=None:
                output=int(pokes.find("catchrate").text)
        return output

    def getpoketypeone(self,pokenum):
        output=""
        pokes=self.pokeroot.find(".//pkmn[@num='"+str(pokenum)+"']")
        if pokes!=None:
            if pokes.find("type1")!=None:
                output=pokes.find("type1").text
        return output

    def getpoketype(self,pokenum):
        output=""
        pokes=self.pokeroot.find(".//pkmn[@num='"+str(pokenum)+"']")
        if pokes!=None:
            if pokes.find("type1")!=None:
                output=pokes.find("type1").text
                if pokes.find("type2")!=None:
                    output+="/{}".format(pokes.find("type2").text)
        return output

    def getpoketypebyname(self,pokename):
        return self.getpoketype(self.getpokenum(pokename))

    def getitemname(self,itemname):
        itemname=itemname.lower()
        item=self.itemroot.find(".//item[@name='"+itemname+"']")
        if item==None:
            return ""
        return item.find("name").text

    def userhasitem(self,username,itemname):
        username=username.lower()
        itemname=itemname.lower()
        user=self.userroot.find(".//user[@name='"+username+"']")
        if user.find(".//item[@name='"+itemname+"']")!=None:
            return True
        return False

    def getItemCost(self,itemname):
        itemname=self.escape(itemname)
        item=self.itemroot.find(".//item[@name='"+itemname+"']")
        if item==None:
            return -1#That item doesn't exist
        cost=item.find("price")
        if cost!=None:
            return int(cost.text)
        else:
            return -2#You can't buy that item (not buyable/no price set)

    def buyitem(self,username,itemname,quantity,channame):
        itemname=self.escape(itemname)
        item=self.itemroot.find(".//item[@name='"+itemname+"']")
        if item==None:
            return -1#That item doesn't exist
        cost=self.getItemCost(itemname)*quantity
        if cost>=0:
            if self.getpoints(username)>=cost:
                self.subpointsinternal(username,cost,channame)
                for x in range(quantity):
                    self.additeminternal(username,itemname,channame)
                return 1#Everything A-Okay
            else:
                if self.getpoints(username)>self.getItemCost(itemname):
                    return -4#You can't afford that many of that
                return -2#That item is too expensive
        else:
            return -3#You can't buy that item (not buyable/no price set)

    def additeminternal(self,username,itemname,channame):
        username=username.lower()
        user=self.userroot.find(".//user[@name='"+username+"']")
        if user!=None:
            item=self.itemroot.find(".//item[@name='"+itemname+"']")
            if item!=None:
                itm=et.Element("item")
                itm.set("name",itemname)
                user.append(itm)
                self.saveusers(channame)
            else:
                return -2#No such item exists
        else:
            return -1#no such user exists

    def remitem(self,channame,username,itemname,itemspec=""):
        username=username.lower()
        itemname=itemname.lower()
        user=self.userroot.find(".//user[@name='"+username+"']")
        itemexists=self.getitemname(itemname)
        if itemexists=="":
            return -2
        if user!=None:
            item=user.findall("item")
            found=False
            for x in item:
                if x.get("name")==itemname:
                    user.remove(x)
                    found=True
                    break
            if found:
                self.saveusers(channame)
                return 1
            return -3
        else:
            return -1

    #===============================================================================
    #BET FUNCTIONS
    #===============================================================================

    def addbet(self,channame,username,category,amount):
        username=username.lower()
        category=category.lower()
        if category=="" or amount<=0:
            return -1#invalid bet
        user=self.userroot.find(".//user[@name='{}']".format(username))
        bet=user.find("bet")
        if bet!=None:
            existingCategory=bet.get("category")
            if existingCategory==category:
                if amount<=self.getpoints(username):
                    existingPoints=int(bet.text)
                    existingPoints+=amount
                    bet.text=str(existingPoints)
                    self.addpointsinternal(username,-1*amount,channame)
                    return 2#user upped a bet
                else:
                    return -4#bet too much
            else:
                return -3#user already has a bet
        if user!=None:
            if amount<=self.getpoints(username):
                bet=et.Element("bet")
                bet.set("category",category)
                bet.text=str(amount)
                user.append(bet)
                self.addpointsinternal(username,-1*amount,channame)
                self.betUsernames.append(username)
                return 1#success!
            else:
                return -4#bet too much
        else:
            return -2#user doesn't exist

    def getbet(self,username):
        username=username.lower()
        user=self.userroot.find(".//user[@name='{}']".format(username))
        if user!=None:
            bet=user.find("bet")
            if bet!=None:
                return bet.get("category"),int(bet.text)
        return "",0

    def rembet(self,channame,username,refund=True):
        username=username.lower()
        user=self.userroot.find(".//user[@name='{}']".format(username))
        if user!=None:
            if username in self.betUsernames:
                self.betUsernames.remove(username)
                bets=user.findall("bet")
                for bet in bets:
                    betpoints=int(bet.text)
                    user.remove(bet)
                    if refund:
                        self.addpointsinternal(username,betpoints,channame)
                self.saveusers(channame)
                return 1#success
            else:
                return -2#user isn't registered as having a bet
        else:
            return -1#user doesn't exist

    def endbetinternal(self,channame,category):
        category=category.lower()
        winningusernames=[]
        winninguserbets=[]
        totalwinbets=0
        totalbets=0
        if len(self.betUsernames)==0:
            return -1#nobody's made a bet
        for username in self.betUsernames:
            totalbets+=int(self.userroot.find(".//user[@name='{}']/bet".format(username)).text)
            if self.userroot.find(".//user[@name='{}']/bet".format(username)).get("category")==category:
                winningusernames.append(username)
                winninguserbets.append(int(self.userroot.find(".//user[@name='{}']/bet".format(username)).text))
                totalwinbets+=winninguserbets[-1]
        while len(self.betUsernames)>0:
            self.rembet(channame,self.betUsernames[0],False)
        self.saveusers(channame)
        if totalwinbets>0:
            for x in range(len(winningusernames)):
                self.addpointsinternal(winningusernames[x],int(round((totalbets+self.getpoints("bet"))*winninguserbets[x]/totalwinbets)),channame)
            self.setpointsinternal(channame,"bet",0)
            return 1#success!
        else:
            self.addpointsinternal("bet",totalbets,channame)
            return -2#nobody won

    def levelpoke(self,username,pokeid,numlevels,channame):
        if self.getoptioninternal(channame,"pokelevelupcost",2,False)<0:
            self.setoptioninternal(channame,"pokelevelupcost",2)
        if numlevels<1:
            return -1
        username=username.lower()
        user=self.userroot.find(".//user[@name='"+username+"']")
        if user!=None:
            if self.getpoints(username)<self.getoptioninternal(channame,"pokelevelupcost",2,False)*numlevels:
                return -2
            pokes=user.findall("pokemon")
            if len(pokes)>0:
                for x in pokes:
                    if int(x.find("id").text)==pokeid:
                        level=int(x.find("lvl").text)
                        if level+numlevels>100:
                            numlevels=100-level
                        if level==100:
                            return -4
                        x.find("lvl").text=str(numlevels+level)
                        self.subpointsinternal(username,self.getoptioninternal(channame,"pokelevelupcost",2,False)*numlevels,channame)
                        return numlevels
                return -5
            else:
                return -6
        else:
            return -3

    def rempoke(self,username,pokeid,channame):
        username=username.lower()
        user=self.userroot.find(".//user[@name='"+username+"']")
        if user!=None:
            poke=user.findall("pokemon")
            found=False
            speciesnum=0
            for x in poke:
                if int(x.find("id").text)==pokeid:
                    speciesnum=int(x.find("num").text)
                    user.remove(x)
                    found=True
            if found:
                self.saveusers(channame)
                return speciesnum
            return -2
        else:
            return -1

    def listpokeids(self,username):
        username=username.lower()
        user=self.userroot.find(".//user[@name='"+username+"']")
        if user!=None:
            poke=user.findall("pokemon")
            pokeids=[]
            for x in poke:
                pokeids.append(x.find("id").text)
            return pokeids
        else:
            return -1

    def isshiny(self,username,pokeid):
        username=username.lower()
        pokeid="%05d"%pokeid
        user=self.userroot.find(".//user[@name='"+username+"']")
        if user!=None:
            pokes=user.find(".//pokemon[id='"+pokeid+"']")
            if pokes!=None:
                if pokes.find("shiny").text=="True":
                    return 1
                return 0
            else:
                return -2
        else:
            return -1

    def getpokelvlbyid(self,username,pokeid):
        username=username.lower()
        user=self.userroot.find(".//user[@name='"+username+"']")
        if user!=None:
            pokes=user.findall("pokemon")
            for x in pokes:
                if int(x.find("id").text)==pokeid:
                    return int(x.find("lvl").text)
            return -2
        else:
            return -1

    def getpokenamebyid(self,username,pokeid):
        username=username.lower()
        user=self.userroot.find(".//user[@name='"+username+"']")
        if user!=None:
            pokes=user.findall("pokemon")
            for x in pokes:
                if int(x.find("id").text)==pokeid:
                    return self.getpokename(int(x.find("num").text))
        else:
            return "Error"

    def getpokename(self,pokenum):
        pokemon=self.pokeroot.find(".//pkmn[@num='"+str(pokenum)+"']")
        if pokemon==None:
            return "Missingno"
        return pokemon.find("name").text

    def ispokeoritem(self,name):
        pokenum=-1
        try:
            pokenum=int(name)
        except ValueError:
            pokenum=self.getpokenum(name)
        if pokenum==-1:
            itemname=self.escape(name)
            item=self.itemroot.find(".//item[@name='"+itemname+"']")
            if item==None:
                return -1#Not an item or a pokemon
            else:
                return 2#it's an item
        else:
            return 1#it's a pokemon


    def buypoke(self,username,pokenum,channame):
        pokemon=self.pokeroot.find(".//pkmn[@num='"+str(pokenum)+"']")
        if pokemon==None:
            return -1#That pokemon doesn't exist
        cost=pokemon.find("price")
        buyable=pokemon.find("buyable")
        if cost!=None and buyable!=None:
            if buyable.text.lower()=="yes":
                cost=int(cost.text)
                if self.getpoints(username)>=cost:
                    self.subpointsinternal(username,cost,channame)
                    self.addpokeinternal(channame,username,pokenum)
                    return 1#Everything A-Okay
                else:
                    return -2#That pokemon is too expensive
            else:
                return -3#You can't buy that pokemon (not buyable)
        else:
            return -3#You can't buy that pokemon (not buyable/no price set)

    def addpokeinternal(self,channame,username,pokenum,lvl=5,shiny=False):
        username=username.lower()
        if self.getoptioninternal(channame,"shinyrate",1024,False)<1:
            self.setoptioninternal(channame,"shinyrate",1)
        odds=random.randint(1,self.getoptioninternal(channame,"shinyrate",1024,False))
        if odds==1:
            shiny=True
        user=self.userroot.find(".//user[@name='"+username+"']")
        if lvl<1:
            lvl=1
        if lvl>100:
            lvl=100
        if user!=None:
            pokemon=self.pokeroot.find(".//pkmn[@num='"+str(pokenum)+"']")
            if pokemon!=None:
                poke=et.Element("pokemon")
                pokenumb=et.Element("num")
                pokelvl=et.Element("lvl")
                pokeshine=et.Element("shiny")
                pokenumb.text=str(pokenum)
                pokelvl.text=str(lvl)
                pokeshine.text=str(shiny)
                pokeid=et.Element("id")
                poke.append(pokenumb)
                poke.append(pokelvl)
                poke.append(pokeshine)
                poke.append(pokeid)
                maxpokenum=0
                for alreadypokes in user.findall("pokemon"):
                    if int(alreadypokes.find("id").text)>maxpokenum:
                        maxpokenum=int(alreadypokes.find("id").text)
                maxpokenum+=1
                pokeid.text="%05d"%maxpokenum
                user.append(poke)
                self.saveusers(channame)
            else:
                return -2#No such pokemon exists
        else:
            return -1#no such user exists

    def pokedex(self,pokenum,username,chan):
        dexout="Error...?"
        if self.pokeroot.find(".//pkmn[@num='{}']".format(pokenum))==None:
            pokenum=0
        pokemon=self.pokeroot.find(".//pkmn[@num='{}']".format(pokenum))
        buyable=" not purchaseable"
        if pokemon.find("buyable")!=None:
            if pokemon.find("buyable").text.lower()=="yes":
                buyable=" purchaseable"
            else:
                buyable=" not purchaseable"
        else:
            buyable=" not purchaseable"
        price=""
        if pokemon.find("price")!=None:
            price=" - price: {} {}".format(pokemon.find("price").text,self.pointname(chan,pokemon.find("price").text))
        type=self.getpoketype(pokenum)
        if type!="":
            type=" - {}".format(type).lower()
        catchrate=""
        if pokemon.find("catchrate")!=None:
            catchrate=" - catch rate: {}".format(pokemon.find("catchrate").text)
        dexout="#{} {}: {}{}{}{}.".format(pokenum,self.getpokename(pokenum),buyable,price,type,catchrate)
        nicknames=pokemon.findall("nickname")
        nicks=""
        for x in nicknames:
            nicks+=", {}".format(x.text)
        if nicks!="":
            dexout+=" Nicknames: {}".format(nicks[1:])
        return dexout

    def deluserinternal(self,username,channame):
        recheck=False
        if username==self.maxpointsusername:
            recheck=True
        if self.userroot.find(".//user[@name='"+username+"']")!=None:
            self.userroot.remove(self.userroot.find(".//user[@name='"+username+"']"))
            self.saveusers(channame)
            if recheck:
                self.itermostpoints()
            return 1
        else:
            return -1

    def startvoteinternal(self,options):
        if len(options)<3:
            return -1
        try:
            if self.votegoing:
                return -2
        except AttributeError:
            self.votegoing=False
        self.voteoptions={}
        self.uservotes={}
        for x in range(1,len(options)):
            self.voteoptions[options[x].lower()]=0
        self.votegoing=True
        return 1

    def endvoteinternal(self):
        if self.votegoing:
            winner={}
            maxvotes=0
            for x in self.voteoptions:
                if self.voteoptions[x]>maxvotes:
                    winner={}
                    maxvotes=self.voteoptions[x]
                    winner[x]=self.voteoptions[x]
                elif self.voteoptions[x]==maxvotes and maxvotes!=0:
                    winner[x]=self.voteoptions[x]
            self.votegoing=False
            self.voteoptions={}
            self.uservotes={}
            return winner
        else:
            return -1

    def uservote(self,username,option):
        option=option.lower()
        if self.votegoing:
            if option in self.voteoptions and username.lower() not in self.uservotes:
                self.voteoptions[option]+=1
                self.uservotes[username.lower()]=1
                return 1
            elif option in self.voteoptions:
                return -3
            else:
                return -1
        else:
            return -2

    def prettifyxml(self,elem):
        rough=et.tostring(elem,"utf-8")
        rough=rough.decode("utf-8")
        rough=rough.replace("  ","")
        rough=rough.replace("\n","")
        rough=rough.replace("\t","")
        rough=rough.encode("utf-8")
        reparsed=minidom.parseString(rough)
        return reparsed.toprettyxml(indent="  ")

    def loadusers(self,chan):
        if not os.path.exists("{}/users.xml".format(self.stripchansign(chan))):
            f=open("{}/users.xml".format(self.stripchansign(chan)),"w+")
            f.write("<users></users>")
            f.close()
        if not os.path.exists("{}/commands.xml".format(self.stripchansign(chan))):
            f=open("{}/commands.xml".format(self.stripchansign(chan)),"w+")
            f.write("<commands></commands>")
            f.close()
        if not os.path.exists("{}/options.xml".format(self.stripchansign(chan))):
            f=open("{}/options.xml".format(self.stripchansign(chan)),"w+")
            f.write("<options></options>")
            f.close()
        self.optionstree=et.parse("{}/options.xml".format(self.stripchansign(chan)))
        self.optionsroot=self.optionstree.getroot()
        self.comtree=et.parse("{}/commands.xml".format(self.stripchansign(chan)))
        self.comroot=self.comtree.getroot()
        self.usertree=et.parse("{}/users.xml".format(self.stripchansign(chan)))
        self.userroot=self.usertree.getroot()
        self.poketree=et.parse("pokemon.xml")
        self.pokeroot=self.poketree.getroot()
        self.itemtree=et.parse("items.xml")
        self.itemroot=self.itemtree.getroot()
        self.hourchange=self.getoptioninternal(chan,"timezone",0,False)
        for usernode in self.userroot.findall(".//user[bet]"):
            self.betUsernames.append(usernode.get("name"))

    def init(self,chan,isprimary=False):
        self.initialize()
        if sys.platform=="linux":
            if not os.path.exists("{}/users.xml".format(self.stripchansign(chan))):
                f=open("{}/users.xml".format(self.stripchansign(chan)),"w+")
                f.write("<users></users>")
                f.close()
            if not os.path.exists("{}/commands.xml".format(self.stripchansign(chan))):
                f=open("{}/commands.xml".format(self.stripchansign(chan)),"w+")
                f.write("<commands></commands>")
                f.close()
            shutil.copy("{}/users.xml".format(self.stripchansign(chan)),"/var/www/html/bot/{}".format(self.stripchansign(chan)))
            if isprimary:
                shutil.copy("pokemon.xml","/var/www/html/bot/")
                shutil.copy("items.xml","/var/www/html/bot/")
        self.loadusers(chan)
        self.itermostpoints()

    def addpointsinternal(self,username,numpoints,channame):
        username=username.lower()
        recheck=False
        if username==self.maxpointsusername:
            recheck=True
        if not self.blacklisted(username):
            if len(username)>0:
                if username[0]=='@':
                    username=username[1:]
            if username.find(' ')==-1:
                if self.userroot.find(".//user[@name='"+username+"']")!=None:
                    self.userroot.find(".//user[@name='"+username+"']").find("points").text=str(int(self.userroot.find(".//user[@name='"+username+"']").find("points").text)+numpoints)
                    if int(self.userroot.find(".//user[@name='"+username+"']").find("points").text)>self.maxpointsvalue:
                        self.maxpointsusername=username
                        self.maxpointsvalue=int(self.userroot.find(".//user[@name='"+username+"']").find("points").text)
                else:
                    points=et.Element("points")
                    points.text=str(numpoints)
                    user=et.Element("user",{"name":username})
                    user.append(points)
                    self.userroot.append(user)
                    if numpoints>self.maxpointsvalue:
                        self.maxpointsusername=username
                        self.maxpointsvalue=numpoints
                self.saveusers(channame)
        if recheck:
            self.itermostpoints()

    def givepoints(self,user1,user2,numpoints,channame):
        user1=user1.lower()
        user2=user2.lower()
        if numpoints>0:
            if self.getpoints(user1)>=numpoints:
                if self.userroot.find(".//user[@name='"+user2+"']")!=None:
                    self.subpointsinternal(user1,numpoints,channame)
                    self.addpointsinternal(user2,numpoints,channame)
                    return 1
                else:
                    return -2
            else:
                return -1
        else:
            return -3

    def autoclaimcycle(self,username,numpoints,channame):
        username=username.lower()
        if self.getoptioninternal(channame,"cyclelength",1440,False)>1440:
            self.setoptioninternal(channame,"cyclelength",1440)
        if self.getoptioninternal(channame,"cyclelength",1440,False)>0:
            if not self.blacklisted(username):
                user=self.userroot.find(".//user[@name='"+username+"']")
                if user!=None:
                    lastclaim=user.find("daily")
                    if lastclaim!=None:
                        lastclaimtimestamp=None
                        try:
                            lastclaimtimestamp=datetime.datetime.strptime(lastclaim.text,"%a%b%d%Y%H%M%S")
                        except Exception:
                            try:
                                lastclaimtimestamp=datetime.datetime.strptime("{}000000".format(lastclaim.text),"%a%b%d%Y%H%M%S")
                            except Exception:
                                lastclaimtimestamp=datetime.datetime.strptime("SatJan012000000000","%a%b%d%Y%H%M%S")
                            self.userroot.find(".//user[@name='"+username+"']").find("daily").text=self.getnospacedate(channame)
                            self.saveusers(channame)
                        timeDif=dateutil.relativedelta.relativedelta(datetime.datetime.now()+datetime.timedelta(hours=self.getoptioninternal(channame,"timezone",0,False)),lastclaimtimestamp)
                        minutesSince=timeDif.days
                        minutesSince*=24
                        minutesSince+=timeDif.hours
                        minutesSince*=60
                        minutesSince+=timeDif.minutes
                        if minutesSince>=self.getoptioninternal(channame,"cyclelength",1440,False):
                            self.addpointsinternal(username,numpoints,channame)
                            self.userroot.find(".//user[@name='"+username+"']").find("daily").text=self.getnospacedate(channame)
                            self.saveusers(channame)
                    else:
                        self.addpointsinternal(username,numpoints,channame)
                        claim=et.Element("daily")
                        claim.text=self.getnospacedate(channame)
                        user=self.userroot.find(".//user[@name='"+username+"']")
                        user.append(claim)
                        self.saveusers(channame)
                if user==None:
                    self.addpointsinternal(username,numpoints,channame)
                    claim=et.Element("daily")
                    claim.text=self.getnospacedate(channame)
                    user=self.userroot.find(".//user[@name='"+username+"']")
                    user.append(claim)
                    self.saveusers(channame)

    def subpointsinternal(self,username,numpoints,channame):
        self.addpointsinternal(username,-1*numpoints,channame)

    def setpointsinternal(self,channame,username,numpoints):
        username=username.lower()
        recheck=False
        if username==self.maxpointsusername:
            recheck=True
        if not self.blacklisted(username):
            if len(username)>0:
                if username[0]=='@':
                    username=username[1:]
            if username.find(' ')==-1:
                if self.userroot.find(".//user[@name='"+username+"']")!=None:
                    self.userroot.find(".//user[@name='"+username+"']").find("points").text=str(numpoints)
                    if numpoints>self.maxpointsvalue:
                        self.maxpointsusername=username
                        self.maxpointsvalue=numpoints
                else:
                    points=et.Element("points")
                    points.text=str(numpoints)
                    user=et.Element("user",{"name":username})
                    user.append(points)
                    self.userroot.append(user)
                    if numpoints>self.maxpointsvalue:
                        self.maxpointsusername=username
                        self.maxpointsvalue=numpoints
                self.saveusers(channame)
        if recheck:
            self.itermostpoints()

    def getpoints(self,username):
        username=username.lower()
        if len(username)>0:
            if username[0]=='@':
                username=username[1:]
        if username==cfg2.NICK.lower():
            return self.maxpointsvalue+1
        elif self.userroot.find(".//user[@name='"+username+"']")!=None:
            return int(self.userroot.find(".//user[@name='"+username+"']").find("points").text)
        else:
            return 0

    def itermostpoints(self):
        username=""
        maxpoints=None
        for user in self.userroot.findall("user"):
            if user.find("points")!=None:
                if maxpoints==None:
                    username=user.get("name")
                    maxpoints=int(user.find("points").text)
                elif int(user.find("points").text)>maxpoints:
                    username=user.get("name")
                    maxpoints=int(user.find("points").text)
        if maxpoints!=None:
            self.maxpointsusername=username
            self.maxpointsvalue=maxpoints

    def getmostpoints(self,chan):
        return "Sir {} currently has the most {} with {}.".format(self.maxpointsusername,self.pointname(chan,self.maxpointsvalue),self.maxpointsvalue)

    def saveusers(self,chan):
        f=open("{}/users.xml".format(self.stripchansign(chan)),"w")
        f.write(self.prettifyxml(self.userroot))
        f.close()
        self.usertree=et.parse("{}/users.xml".format(self.stripchansign(chan)))
        self.userroot=self.usertree.getroot()
        if sys.platform=="linux":
            shutil.copy("{}/users.xml".format(self.stripchansign(chan)),"/var/www/html/bot/{}".format(self.stripchansign(chan)))

    def savecommands(self,chan):
        f=open("{}/commands.xml".format(self.stripchansign(chan)),"w")
        f.write(self.prettifyxml(self.comroot))
        f.close()
        self.comtree=et.parse("{}/commands.xml".format(self.stripchansign(chan)))
        self.comroot=self.comtree.getroot()
        if sys.platform=="linux":
            shutil.copy("{}/commands.xml".format(self.stripchansign(chan)),"/var/www/html/bot/{}".format(self.stripchansign(chan)))

    def saveoptions(self,chan):
        f=open("{}/options.xml".format(self.stripchansign(chan)),"w")
        f.write(self.prettifyxml(self.optionsroot))
        f.close()
        self.optionstree=et.parse("{}/options.xml".format(self.stripchansign(chan)))
        self.optionsroot=self.optionstree.getroot()
        if sys.platform=="linux":
            shutil.copy("{}/options.xml".format(self.stripchansign(chan)),"/var/www/html/bot/{}".format(self.stripchansign(chan)))

    def addcommand(self,chan,comname,result):
        if self.comroot.find(".//command[@name='{}']".format(comname))!=None:
            self.comroot.find(".//command[@name='{}']".format(comname)).find("response").text=result
        else:
            response=et.Element("response")
            response.text=result
            accesslevel=et.Element("accesslevel")
            accesslevel.text=str(0)
            command=et.Element("command",{"name":comname})
            command.append(response)
            command.append(accesslevel)
            self.comroot.append(command)
        self.savecommands(chan)

    def delcommand(self,chan,comname):
        if self.comroot.find(".//command[@name='{}']".format(comname))!=None:
            self.comroot.remove(self.comroot.find(".//command[@name='{}']".format(comname)))
            self.savecommands(chan)
            return 1
        return -1
                                
    def setcommandal(self,chan,comname,level):
        if self.comroot.find(".//command[@name='{}']".format(comname))!=None:
            self.comroot.find(".//command[@name='{}']".format(comname)).find("accesslevel").text=str(level)
            self.savecommands(chan)
            return 1
        return -1

    def isacommand(self,comname):
        if self.comroot.find(".//command[@name='{}']".format(comname))!=None:
            return True
        return False

    def getcomresponse(self,comname):
        if self.comroot.find(".//command[@name='{}']".format(comname))!=None:
            return self.comroot.find(".//command[@name='{}']".format(comname)).find("response").text
        return ""

    def getcomaccesslevel(self,comname):
        if self.comroot.find(".//command[@name='{}']".format(comname))!=None:
            return int(self.comroot.find(".//command[@name='{}']".format(comname)).find("accesslevel").text)
        return -1

    def getcomlist(self):
        comlist=[]
        for command in self.comroot.findall("command"):
            comlist.append(command.get("name"))
        return comlist

    def rreplace(self,mainstring,toreplace,replacewith):
        last=mainstring.rfind(toreplace)
        return "{}{}{}".format(mainstring[0:last],replacewith,mainstring[last+len(toreplace):])

    def parsecommand(self,msg,usr,chan):
        comline=self.getcomresponse(msg[0])
        ispm=False
        commands=["param","rand","getpoints","addpoints","setpoints","pm"]
        searchforinit="\([a-zA-Z0-9-,!'\[\]\{\}\\\\\|\.\^\*\?\+\$\s]*\)"
        searchfor=searchforinit
        for x in range(len(commands)):
            searchfortemp=commands[len(commands)-x-1]
            if x!=0:
                searchfortemp+="|"
            else:
                searchfortemp+=")"
            searchfor=searchfortemp+searchfor
        searchfor="("+searchfor
        resultiter=list(re.finditer(searchfor,comline))
        while len(resultiter)>0:
            x=resultiter[len(resultiter)-1].group(0)
            #param parsing
            if x[:len(commands[0])]==commands[0]:
                inputparam=comline[comline.index(x)+len(commands[0])+1:comline.index(x)+len(x)-1]
                if inputparam!="":
                    if inputparam.find(",")==-1:
                        try:
                            paramnum=int(inputparam)
                            result="ERROR"
                            if paramnum==0:
                                result=usr
                            elif paramnum<len(msg):
                                result=msg[paramnum]
                            comline=self.rreplace(comline,x,result)#re.sub(searchfor,result,comline,1)
                        except ValueError:
                            comline=self.rreplace(comline,x,"ERROR")#re.sub(searchfor,"ERROR",comline,1)
                    else:
                        params=inputparam.split(",")
                        if len(params)>=2:
                            try:
                                paramnum=int(params[0])
                                result=params[1]
                                if paramnum==0:
                                    result=usr
                                elif paramnum<len(msg):
                                    result=msg[paramnum]
                                comline=self.rreplace(comline,x,result)
                            except ValueError:
                                comline=self.rreplace(comline,x,"ERROR")
                        else:
                            comline=self.rreplace(comline,x,"ERROR")
            #rand parsing
            elif x[:len(commands[1])]==commands[1]:
                inputrand=comline[comline.index(x)+len(commands[1])+1:comline.index(x)+len(x)-1]
                if inputrand!="":
                    if inputrand[0]=='[' and inputrand[-1]==']':
                        inputrand=inputrand[1:-1]
                        options=inputrand.split(",")
                        output=options[random.randint(0,len(options)-1)]
                        comline=self.rreplace(comline,x,output)
                    else:
                        if inputrand.find(",")==-1:
                            try:
                                maxrand=int(inputrand)
                                result=random.randint(1,maxrand)
                                comline=self.rreplace(comline,x,str(result))#re.sub(searchfor,"{}".format(result),comline,1)
                            except ValueError:
                                comline=self.rreplace(comline,x,"ERROR")
                        else:
                            params=inputrand.split(",")
                            if len(params)>=2:
                                try:
                                    maxrand=int(params[0])
                                    offset=int(params[1])-1
                                    result=random.randint(1,maxrand)+offset
                                    comline=self.rreplace(comline,x,str(result))
                                except ValueError:
                                    comline=self.rreplace(comline,x,"ERROR")
                            else:
                                comline=self.rreplace(comline,x,"ERROR")
            #getpoints parsing
            elif x[:len(commands[2])]==commands[2]:
                inputparam=comline[comline.index(x)+len(commands[2])+1:comline.index(x)+len(x)-1]
                if inputparam!="":
                    try:
                        username=inputparam
                        numpoints=str(self.getpoints(username))
                        comline=self.rreplace(comline,x,numpoints)
                    except Exception:
                        comline=self.rreplace(comline,x,"ERROR")
                else:
                    comline=self.rreplace(comline,x,"ERROR")
            #addpoints parsing
            elif x[:len(commands[3])]==commands[3]:
                inputparam=comline[comline.index(x)+len(commands[3])+1:comline.index(x)+len(x)-1]
                if inputparam!="":
                    if inputparam.find(",")!=-1:
                        params=inputparam.split(",")
                        if len(params)>=2:
                            try:
                                username=params[0]
                                numpoints=int(params[1])
                                successmessage=""
                                if len(params)>=3:
                                    successmessage=params[2]
                                failmessage=""
                                if len(params)>=4:
                                    failmessage=params[3]
                                message="I have no idea what just happened."
                                if username.lower()==usr.lower() or username=="ERROR":
                                    message=failmessage
                                else:
                                    self.addpointsinternal(username,numpoints,chan)
                                    message=successmessage
                                comline=self.rreplace(comline,x,message)
                            except ValueError:
                                comline=self.rreplace(comline,x,"ERROR")
                        else:
                            comline=self.rreplace(comline,x,"ERROR")
            #setpoints parsing
            elif x[:len(commands[4])]==commands[4]:
                inputparam=comline[comline.index(x)+len(commands[4])+1:comline.index(x)+len(x)-1]
                if inputparam!="":
                    if inputparam.find(",")!=-1:
                        params=inputparam.split(",")
                        if len(params)>=2:
                            try:
                                username=params[0]
                                numpoints=int(params[1])
                                successmessage=""
                                if len(params)>=3:
                                    successmessage=params[2]
                                failmessage=""
                                if len(params)>=4:
                                    failmessage=params[3]
                                message="I have no idea what just happened."
                                if username.lower()==usr.lower() or username=="ERROR":
                                    message=failmessage
                                else:
                                    self.setpointsinternal(chan,username,numpoints)
                                    message=successmessage
                                comline=self.rreplace(comline,x,message)
                            except ValueError:
                                comline=self.rreplace(comline,x,"ERROR")
                        else:
                            comline=self.rreplace(comline,x,"ERROR")
            #pm parsing
            elif x[:len(commands[5])]==commands[5]:
                comline=self.rreplace(comline,x,"")
                ispm=True
            else:
                comline=self.rreplace(comline,x,"ERROR")
            resultiter=list(re.finditer(searchfor,comline))
        #done
        return ' '.join(comline.split()),ispm

    def plural(self,s,n):
        s=" "+s
        if n!=1:
            s+="s"
        return s

    def makenice(self,rd):
        years=rd.years
        months=rd.months
        weeks=math.floor(rd.days/7)
        days=rd.days%7
        hours=rd.hours
        minutes=rd.minutes
        seconds=rd.seconds
        output=str(seconds)+self.plural("second",seconds)
        if years>0:
            output=str(years)+self.plural("year",years)+" "
            output+=str(months)+self.plural("month",months)+", "
            output+=str(weeks)+self.plural("week",weeks)+", "
            output+=str(days)+self.plural("day",days)+", "
            output+=str(hours)+self.plural("hour",hours)+", "
            output+=str(minutes)+self.plural("minute",minutes)+", and "
            output+=str(seconds)+self.plural("second",seconds)
        elif months>0:
            output=str(months)+self.plural("month",months)+", "
            output+=str(weeks)+self.plural("week",weeks)+", and "
            output+=str(days)+self.plural("day",days)+", "
            output+=str(hours)+self.plural("hour",hours)+", "
            output+=str(minutes)+self.plural("minute",minutes)+", and "
            output+=str(seconds)+self.plural("second",seconds)
        elif weeks>0:
            output=str(weeks)+self.plural("week",weeks)+" and "
            output+=str(days)+self.plural("day",days)+", "
            output+=str(hours)+self.plural("hour",hours)+", "
            output+=str(minutes)+self.plural("minute",minutes)+", and "
            output+=str(seconds)+self.plural("second",seconds)
        elif days>0:
            output=str(days)+self.plural("day",days)+", "
            output+=str(hours)+self.plural("hour",hours)+", "
            output+=str(minutes)+self.plural("minute",minutes)+", and "
            output+=str(seconds)+self.plural("second",seconds)
        elif hours>0:
            output=str(hours)+self.plural("hour",hours)+", "
            output+=str(minutes)+self.plural("minute",minutes)+", and "
            output+=str(seconds)+self.plural("second",seconds)
        elif minutes>0:
            output=str(minutes)+self.plural("minute",minutes)+" and "
            output+=str(seconds)+self.plural("second",seconds)
        return output

    def getyoutubetitle(self,url):
        html=urllib.request.urlopen(url).read().decode("utf-8")
        title=html[html.find("eow-title"):html[html.find("eow-title"):].find(">")+html.find("eow-title")-1]
        title=title[title.rfind("\"")+1:].replace("&#39;","'").replace("&quot;","\"")
        authorstart=html.find("http://www.youtube.com/user/")
        author=html[authorstart:html[authorstart:].find("\"")+authorstart]
        author=author[author.rfind("/")+1:]
        return "\"{}\" - {}".format(title,author)

    def chat(self,sock,msg,msgsource):
        whisperback=False
        demo=False
        me=False
        if msg.find(" ")!=-1:
            if msg[0:msg.find(" ")]==".me":
                me=True
                msg=msg[msg.find(" ")+1:]
        try:
            demo=cfg2.DEMO
        except Exception:
            demo=False
        msg=msg.replace("\n","").replace("\r","")
        if len(msgsource)>0:
            if msgsource[0]!='#':
                whisperback=True
        if whisperback==False and self.isInEncounter==True:
            msg="{}{}".format(self.encounterTimerString,msg)
        if demo:
            msg="[DEMO] {}".format(msg)
        if me:
            msg=".me {}".format(msg)
        if len(msg)>500:
            msg="{}...".format(msg[:497])
        if whisperback:
            sock.send("PRIVMSG {} :.w {} {}".format("#jtv",msgsource,str(msg)+"\r\n").encode("utf-8"))
            self.log(msgsource,"{}*WHISPER  TO  {} : {}".format(self.gettime(msgsource),msgsource.upper(),str(msg)))
        else:
            sock.send("PRIVMSG {} :{}".format(msgsource, str(msg)+"\r\n").encode("utf-8"))
            self.log(msgsource,"{}{} {}: {}".format(self.gettime(msgsource),msgsource,cfg2.NICK.lower(),msg))

    def gettime(self,chan):
        return (datetime.datetime.now()+datetime.timedelta(hours=self.getoptioninternal(chan,"timezone",0,False))).strftime("%I:%M:%S %p ")

    def getdayhour(self,chan):
        return int((datetime.datetime.now()+datetime.timedelta(hours=self.getoptioninternal(chan,"timezone",0,False))).strftime("%H"))

    def getnospacedate(self,chan):
        return (datetime.datetime.now()+datetime.timedelta(hours=self.getoptioninternal(chan,"timezone",0,False))).strftime("%a%b%d%Y%H%M%S")

    def getdate(self,chan):
        return (datetime.datetime.now()+datetime.timedelta(hours=self.getoptioninternal(chan,"timezone",0,False))).strftime("%a, %b %d, %Y")

    def getcycletime(self,chan,username):
        if self.getoptioninternal(chan,"cyclelength",1440,False)>0:
            if not self.blacklisted(username):
                user=self.userroot.find(".//user[@name='"+username+"']")
                if user!=None:
                    lastclaim=user.find("daily")
                    if lastclaim!=None:
                        lastclaimtimestamp=datetime.datetime.now()
                        try:
                            lastclaimtimestamp=datetime.datetime.strptime(lastclaim.text,"%a%b%d%Y%H%M%S")
                        except Exception:
                            lastclaimtimestamp=datetime.datetime.strptime("{}000000".format(lastclaim.text),"%a%b%d%Y%H%M%S")
                        maxtime=self.getoptioninternal(chan,"cyclelength",1440,False)
                        lastclaimtimestamp=lastclaimtimestamp+datetime.timedelta(days=maxtime//1440,hours=((maxtime//60)%24),minutes=maxtime%60)
                        timeDif=dateutil.relativedelta.relativedelta(lastclaimtimestamp,datetime.datetime.now()+datetime.timedelta(hours=self.getoptioninternal(chan,"timezone",0,False)))
                        if timeDif.days>0:
                            return "{}d {}:{}:{}".format(timeDif.days,"%02i"%timeDif.hours,"%02i"%timeDif.minutes,"%02i"%timeDif.seconds)
                        else:
                            return "{}:{}:{}".format("%02i"%timeDif.hours,"%02i"%timeDif.minutes,"%02i"%timeDif.seconds)
                    else:
                        return "0d 00:00:00"
                else:
                    return "0d 00:00:00"
        else:
            return ""

    def setacclevels(self,mods,stf,adm,gmod,view,sup,bsup,bmod):
        self.moderators=mods[:]
        self.staff=stf[:]
        self.admins=adm[:]
        self.global_mods=gmod[:]
        self.viewers=view[:]
        self.supers=sup[:]
        self.botmods=bmod[:]
        self.botsupers=bsup[:]

    def msgcont(self,msg,start=1):
        temp=""
        if len(msg)>start:
            for x in range(start,len(msg)):
                temp+=msg[x]
                if msg[x]!="":
                    if msg[x][-2:]=="\r\n":
                        break
                if x<len(msg)-1:
                    temp+=" "
        return temp

    def getusernameparam(self,msg):
        temp=self.msgcont(msg)
        if len(temp)>0:
            if temp[0]=="@":
                temp=temp[1:]
        return temp
    
    def video_id(self,value):
        """
        Examples:
        - http://youtu.be/SA2iWivDJiE
        - http://www.youtube.com/watch?v=_oPAwA_Udwc&feature=feedu
        - http://www.youtube.com/embed/SA2iWivDJiE
        - http://www.youtube.com/v/SA2iWivDJiE?version=3&amp;hl=en_US
        """
        value="http://www.youtube.com{}".format(value)
        query = urllib.parse.urlparse(value)
        if query.hostname == 'youtu.be':
            return query.path[1:]
        if query.hostname in ('www.youtube.com', 'youtube.com'):
            if query.path == '/watch':
                p = urllib.parse.parse_qs(query.query)
                return p['v'][0]
            if query.path[:7] == '/embed/':
                return query.path.split('/')[2]
            if query.path[:3] == '/v/':
                return query.path.split('/')[2]
        # fail?
        return ""
    
    '''
    @accesslvl(4)
    @option("rpgenabled","false","true")
    def rpg(self,accesslevel,sock,username,msgsource,msgtype,msg,channame,isprimary):
        """
        Runs the RPG stuff. Use !rpg help <rpg command> for detailed help on RPG commands.
        """
        self.rpgobject.rpgCore(self,accesslevel,sock,username,msgsource,msgtype,msg,channame,isprimary)
    '''
        
    @accesslvl(0)
    @option("pokemon","true","true")
    @nopm
    def encounterhelp(self,accesslevel,sock,username,msgsource,msgtype,msg,channame,isprimary):
        """
        Lists encounter-specific commands.
        """
        self.chat(sock,"When in an encounter, try the following: !throw <item> (uses pokeball), !switch <ID #> (switches leading Pokemon), !run (ends encounter)",msgsource)

    @accesslvl(0)
    @option("pokemon","true","true")
    @nopm
    @encountered
    def run(self,accesslevel,sock,username,msgsource,msgtype,msg,channame,isprimary):
        """
        Runs from the current encounter.
        """
        self.isInEncounter=False
        self.chat(sock,"{} ran from the wild {}!".format(username,self.getpokename(self.wildPokeEncounter)),msgsource)

    @accesslvl(0)
    @option("pokemon","true","true")
    @nopm
    @encountered
    def switch(self,accesslevel,sock,username,msgsource,msgtype,msg,channame,isprimary):
        """
        Switches your active pokemon in an encounter.
        
        Usage: "!switch <Pokemon ID>"
        """
        if len(msg)>=2:
            switchto=-1
            try:
                switchto=int(msg[1])
            except ValueError:
                switchto=-1
                self.chat(sock,"You must enter a valid Pokemon ID number, {}.".format(username),msgsource)
            if switchto!=-1 and switchto!=self.usedPokemon:
                switchto="%05d"%switchto
                pokeids=self.listpokeids(username)
                if switchto in pokeids:
                    self.usedPokemon=int(switchto)
                    self.chat(sock,"{} sent out {}!".format(usr,self.getpokenamebyid(username,int(switchto))),msgsource)
                else:
                    self.chat(sock,"You don't have a Pokemon with the ID {}, {}!".format(switchto,username),msgsource)
            elif switchto!=-1:
                self.chat(sock,"Your {} is already out, {}!".format(self.getpokenamebyid(username,self.usedPokemon),username),msgsource)

    @accesslvl(0)
    @option("pokemon","true","true")
    @nopm
    @encountered
    def throw(self,accesslevel,sock,username,msgsource,msgtype,msg,channame,isprimary):
        """
        Throws an item at the wild pokemon.
        
        Usage: "!throw <item name>"
        """
        if len(msg)>=2:
            throw=False
            itemthrown=msg[1].lower()
            capturerate=self.getcapturerate(self.wildPokeEncounter)
            capturerate*=2
            if itemthrown=="pokeball" or itemthrown=="friendball":
                throw=True
            elif itemthrown=="greatball" or itemthrown=="parkball":
                throw=True
                capturerate*=1.5
            elif itemthrown=="ultraball":
                throw=True
                capturerate*=2
            elif itemthrown=="masterball":
                throw=True
                capturerate*=255
            elif itemthrown=="loveball":
                throw=True
                if self.getpokenamebyid(username,self.usedPokemon)==self.getpokename(self.wildPokeEncounter):
                    capturerate*=8
            elif itemthrown=="heavyball":
                throw=True
                if self.getpokename(self.wildPokeEncounter) in ["Snorlax","Steelix"]:
                    capturerate+=30
                elif self.getpokename(self.wildPokeEncounter) in ["Dragonite","Golem","Gyarados","Lapras","Lugia","Mantine","Onix"]:
                    capturerate+=20
                elif self.getpokename(self.wildPokeEncounter) in ["Arcanine","Cloyster","Dewgong","Donphan","Entei","Exeggutor","Forretress"]:
                    capturerate+=0
                elif self.getpokename(self.wildPokeEncounter) in ["Graveler","Ho-Oh","Kingdra","Machamp","Mewtwo","Pupitar","Raikou","Rhydon","Rhyhorn","Scizor","Suicune","Tyranitar","Ursaring"]:
                    capturerate+=0
                else:
                    capturerate-=20
            elif itemthrown=="lureball":
                throw=True
                if self.getpoketypeone(self.wildPokeEncounter)=="Water":
                    capturerate*=3
            elif itemthrown=="fastball":
                throw=True
                if self.getpokename(self.wildPokeEncounter) in ["Grimer","Magnemite","Tangela"]:
                    capturerate*=4
            elif itemthrown=="moonball":
                throw=True
                if self.getpokename(self.wildPokeEncounter) in ["Clefairy","Jigglypuff","Nidorina","Nidorino"]:
                    capturerate*=4
            elif itemthrown=="levelball":
                throw=True
                pokelevel=self.getpokelvlbyid(username,self.usedPokemon)
                if pokelevel>self.wildPokeLevel:
                    capturerate*=2
                if pokelevel>2*self.wildPokeLevel:
                    capturerate*=2
                if pokelevel>=4*self.wildPokeLevel:
                    capturerate*=2
            capturerate=capturerate//3
            if capturerate>=255:
                capturerate=255
            if throw==True:
                removed=self.remitem(channame,username,itemthrown,self.msgcont(msg,2))
                if removed==-1:
                    self.chat(sock,"You don't exist, {}!".format(username),msgsource)
                elif removed==-2:
                    self.chat(sock,"That's not a valid item, {}!".format(username),msgsource)
                elif removed==-3:
                    self.chat(sock,"You don't have a {}, {}!".format(self.getitemname(itemthrown),username),msgsource)
                else:
                    x=random.randint(0,255)
                    self.log(msgsource,"Odds of catching: {}/255, rolled {}.".format(capturerate,x))
                    if x<=capturerate:#Conglaturations! Capture complete!
                        self.isInEncounter=False
                        self.addpokeinternal(channame,username,self.wildPokeEncounter,self.wildPokeLevel)
                        self.chat(sock,"Conglaturations, {}! You caught a L{} {}!".format(username,self.wildPokeLevel,self.getpokename(self.wildPokeEncounter)),msgsource)
                    else:
                        self.chat(sock,"Wild {} broke free!".format(self.getpokename(self.wildPokeEncounter)),msgsource)
            else:
                self.chat(sock,"You can't throw a {}, {}!".format(itemthrown,username),msgsource)
        else:
           self.chat(sock,"You must select an item to throw, {}!".format(username),msgsource)

    @accesslvl(5)
    @option("pokemon","true","true")
    @nopm
    def encounter(self,accesslevel,sock,username,msgsource,msgtype,msg,channame,isprimary):
        """
        Creates an encounter for the next eligible user.
        
        Usage: "!encounter [pokemon] [level]"
        """
        if self.isInEncounter==False:
            if len(msg)==1:
                self.forceEncounter=1
                self.chat(sock,"The next eligible user to speak will get an encounter!",msgsource)
            elif len(msg)==2:
                pokenum=self.getpokenum(msg[1])
                if pokenum<0:
                    try:
                        pokenum=int(msg[1])
                    except ValueError:
                        self.chat(sock,"You must give either a valid number or species name to encounter, {}!".format(username),msgsource)
                if pokenum>0:
                    self.forceEncounter=2
                    self.wildPokeEncounter=pokenum
                    self.chat(sock,"The next eligible user to speak will get an encounter with a wild {}!".format(self.getpokename(self.wildPokeEncounter)),msgsource)
            elif len(msg)==3:
                pokenum=self.getpokenum(msg[1])
                if pokenum<0:
                    try:
                        pokenum=int(msg[1])
                    except ValueError:
                        self.chat(sock,"You must give either a valid number or species name to encounter, {}!".format(username),msgsource)
                if pokenum>0:
                    wildlevel=-1
                    try:
                        wildlevel=int(msg[2])
                    except ValueError:
                        self.chat(sock,"You must give a valid number for a level, {}!".format(username),msgsource)
                        wildlevel=-1
                    if wildlevel!=-1:
                        self.forceEncounter=3
                        self.wildPokeEncounter=pokenum
                        self.wildPokeLevel=wildlevel
                        self.chat(sock,"The next eligible user to speak will get an encounter with a wild L{} {}!".format(self.wildPokeLevel,self.getpokename(self.wildPokeEncounter)),msgsource)
        else:
            self.chat(sock,"There is already an encounter in progress, {}!".format(username),messagesource)

    @accesslvl(5)
    @option("pokemon","true","true")
    @nopm
    def endencounter(self,accesslevel,sock,username,msgsource,msgtype,msg,channame,isprimary):
        """
        Ends the current encounter.
        """
        if self.isInEncounter==True:
            self.isInEncounter=False
            self.chat(sock,"{}'s encounter with the wild {} was ended by {}.".format(self.userInEncounter,self.getpokename(self.wildPokeEncounter),username),msgsource)
        else:
            self.chat(sock,"There is no current wild encounter in progress, {}!".format(username),msgsource)

    @accesslvl(6)
    @nopm
    def msg(self,accesslevel,sock,username,msgsource,msgtype,msg,channame,isprimary):
        """
        Outputs the given message to the current channel.
        
        Usage: "!msg <message>"
        """
        self.chat(sock,self.msgcont(msg),msgsource);

    @accesslvl(0)
    @nopm
    def accesslevel(self,accesslevel,sock,username,msgsource,msgtype,msg,channame,isprimary):
        """
        Checks the access level of a user.
        
        Usage: "!accesslevel [username]"
        """
        user=username
        al=accesslevel
        if len(msg)>1:
            user=self.getusernameparam(msg).lower()
            al=0
            if user in self.global_mods:
                al=1
            if user in self.admins:
                al=2
            if user in self.staff:
                al=3
            if user in self.moderators or username in self.botmods:
                al=4
            if user in self.supers:
                al=5
            if user in self.botsupers:
                al=6
        self.chat(sock,"{} has access level {}.".format(user,al),msgsource)

    @accesslvl(0)
    @nopm
    def followsince(self,accesslevel,sock,username,msgsource,msgtype,msg,channame,isprimary):
        """
        Checks when a user started following the current streamer.
        
        Usage: "!followsince [username]"
        """
        user=username
        if len(msg)>1:
            user=self.getusernameparam(msg)
        #old URL: http://api.newtimenow.com/follow-length/?channel={}&user={}".format(messagesource[1:],username)
        with urllib.request.urlopen("https://decapi.me/twitch/followed?channel={}&user={}".format(msgsource[1:],user)) as response:
            html = response.read()
        html=str.replace(str(html),"\\n","")[2:-1]
        try:
            #followdate=datetime.datetime.strptime(html,"%Y-%m-%d %H:%M:%S") old url's formatting
            followdate=datetime.datetime.strptime(html,"%b %d. %Y - %I:%M:%S %p (%Z)")+datetime.timedelta(hours=self.getoptioninternal(channame,"timezone",0,False))
            self.chat(sock,"{} has been following {} since [{}]".format(user,msgsource[1:],followdate.strftime("%a, %b %d %Y at %I:%M:%S %p")),msgsource)
        except ValueError:
            self.log(msgsource,"EXCEPTION\r\n{}".format(traceback.format_exc()))
            self.chat(sock,"{} is not following {}!".format(user,msgsource[1:]),msgsource)

    @accesslvl(0)
    @nopm
    def followage(self,accesslevel,sock,username,msgsource,msgtype,msg,channame,isprimary):
        """
        Checks how long a user has been following the current streamer.
        
        Usage: "!followage [username]"
        """
        user=username
        if len(msg)>1:
            user=self.getusernameparam(msg)
        with urllib.request.urlopen("https://decapi.me/twitch/followed?channel={}&user={}".format(msgsource[1:],user)) as response:
            html = response.read()
        html=str.replace(str(html),"\\n","")[2:-1]
        try:
            followdate=datetime.datetime.strptime(html,"%b %d. %Y - %I:%M:%S %p (%Z)")
            difference=dateutil.relativedelta.relativedelta(datetime.datetime.utcnow(),followdate)
            self.chat(sock,"{} has been following {} for [{}]".format(user,msgsource[1:],self.makenice(difference)),msgsource)
        except ValueError:
            self.log(msgsource,"EXCEPTION\r\n{}".format(traceback.format_exc()))
            self.chat(sock,"{} is not following {}!".format(user,msgsource[1:]),msgsource)

    howlong=followage

    @accesslvl(4)
    @nopm
    def mods(self,accesslevel,sock,username,msgsource,msgtype,msg,channame,isprimary):
        """
        Lists current channel bot mods.
        """
        temp="Bot mods: "
        for x in range(0,len(self.botmods)):
            temp+=self.botmods[x]
            if x<len(self.botmods)-1:
                temp+=", "
        if len(self.botmods)==0:
            temp+="None"
        self.chat(sock,temp,msgsource)

    @accesslvl(5)
    @nopm
    def supers(self,accesslevel,sock,username,msgsource,msgtype,msg,channame,isprimary):
        """
        Lists current bot supers.
        """
        temp="Bot supers: "
        for x in range(0,len(self.supers)):
            temp+=self.supers[x]
            if x<len(self.supers)-1:
                temp+=", "
        for x in range(0,len(self.botsupers)):
            temp+=self.botsupers[x]
            if x<len(self.botsupers)-1:
                temp+=", "
        self.chat(sock,temp,msgsource)

    @accesslvl(0)
    @nopm
    def points(self,accesslevel,sock,username,msgsource,msgtype,msg,channame,isprimary):
        """
        Lists how many POINTS a user has.

        Usage: "!points [username]"
        """
        user=username
        if len(msg)>=2:
            user=msg[1].lower()
        self.chat(sock,"{} has {} {}.".format(user,self.getpoints(user),self.pointname(channame,self.getpoints(user))),msgsource)

    @accesslvl(5)
    @nopm
    def addpoints(self,accesslevel,sock,username,msgsource,msgtype,msg,channame,isprimary):
        """
        Adds POINTS to a user.

        Usage: "!addpoints <username> <number of POINTS>"
        """
        if len(msg)>=3:
            user=""
            numpoints=0
            try:
                user=msg[1]
                numpoints=int(msg[2])
            except ValueError:
                self.chat(sock,"Invalid input!",messagesource)
            if user!="" and numpoints!=0:
                if user!="allviewers":
                    self.addpointsinternal(user,numpoints,channame)
                    self.chat(sock,user+" gained {} {}!".format(numpoints,self.pointname(channame,numpoints)),msgsource)
                else:
                    users=self.allviewers(msgsource)
                    for x in users:
                        self.addpointsinternal(x,numpoints,channame)
                    self.chat(sock,"Everybody gained {} {}!".format(numpoints,self.pointname(channame,numpoints)),msgsource)
        else:
            self.chat(sock,"Missing parameters. Try: !addpoints <username> <numpoints>",msgsource)

    @accesslvl(5)
    @nopm
    def subpoints(self,accesslevel,sock,username,msgsource,msgtype,msg,channame,isprimary):
        """
        Subtracts POINTS from a user.

        Usage: "!subpoints <username> <number of POINTS>"
        """
        if len(msg)>=2:
            user=""
            numpoints=0
            try:
                user=msg[1]
                numpoints=int(msg[2])
            except ValueError:
                self.chat(sock,"Invalid input!",messagesource)
            if user!="" and numpoints!=0:
                self.subpointsinternal(user,numpoints,channame)
                self.chat(sock,"{} lost {} {}.".format(user,numpoints,self.pointname(channame,numpoints)),msgsource)
        else:
            self.chat(sock,"Missing parameters. Try: !takepoints <username> <numpoints>",msgsource)

    @accesslvl(5)
    @nopm
    def setpoints(self,accesslevel,sock,username,msgsource,msgtype,msg,channame,isprimary):
        """
        Sets a user's POINTS to the specified value.

        Usage: "!setpoints <username> <number of POINTS>"
        """
        if len(msg)>=2:
            user=""
            numpoints=0
            try:
                user=msg[1]
                numpoints=int(msg[2])
            except ValueError:
                self.chat(sock,"Invalid input!",msgsource)
                user=""
            if user!="":
                self.setpointsinternal(channame,user,numpoints)
                self.chat(sock,"{} now has {} {}.".format(user,numpoints,self.pointname(channame,numpoints)),msgsource)
        else:
            self.chat(sock,"Missing parameters. Try: !setpoints <username> <numpoints>",msgsource)
    
    @accesslvl(0)
    @nopm
    def maxpoints(self,accesslevel,sock,username,msgsource,msgtype,msg,channame,isprimary):
        """
        Outputs who has the most POINTS, and how many they have.
        """
        if self.getmostpoints(channame)!="":
            self.chat(sock,self.getmostpoints(channame),msgsource)
        else:
            self.chat(sock,"Nobody has any {}! How disappointing.".format(self.pointname(channame,0)),msgsource)
    
    @accesslvl(5)
    @nopm
    def setoption(self,accesslevel,sock,username,msgsource,msgtype,msg,channame,isprimary):
        """
        Sets the specified option with the specified value.

        Usage: "!setoption <option name> <option value>"
        """
        if len(msg)>=3:
            optionname=msg[1]
            optionvalue=msg[2]
            oldvalue=self.getoptioninternal(channame,optionname,"")
            self.setoptioninternal(channame,optionname,optionvalue)
            if oldvalue!="":
                self.chat(sock,"{}, option \"{}\" was changed from {} to {}.".format(username,optionname,oldvalue,optionvalue),msgsource)
            else:
                self.chat(sock,"{}, option \"{}\" was set to {}.".format(username,optionname,optionvalue),msgsource)
        else:
            self.chat(sock,"You must enter both an option name and value, {}!".format(username),msgsource)
    
    @accesslvl(4)
    @nopm
    def getoption(self,accesslevel,sock,username,msgsource,msgtype,msg,channame,isprimary):
        """
        Gets the current setting of the specified option.

        Usage: "!getoption <option name>"
        """
        if len(msg)>=2:
            optionname=msg[1]
            if self.getoptioninternal(channame,optionname)=="":
                self.chat(sock,"That option does not currently exist, {}.".format(username),msgsource)
            else:
                self.chat(sock,"Option \"{}\" is currently set to {}, {}.".format(optionname,self.getoptioninternal(channame,optionname),username),msgsource)
        else:
            self.chat(sock,"You must enter an option name to check, {}!".format(username),msgsource)
    
    @accesslvl(5)
    @nopm
    def deloption(self,accesslevel,sock,username,msgsource,msgtype,msg,channame,isprimary):
        """
        Deletes the specified option.

        Usage: "!deloption <option name>"
        """
        if len(msg)>=2:
            optionname=msg[1]
            oldvalue=self.getoptioninternal(channame,optionname)
            self.setoptioninternal(channame,optionname,"")
            if oldvalue=="":
                self.chat(sock,"Option \"{}\" did not exist, {}.".format(optionname,username),msgsource)
            else:
                self.chat(sock,"Option \"{}\" was deleted, {}. Old value: {}".format(optionname,username,oldvalue),msgsource)
        else:
            self.chat(sock,"You must give an option name to delete, {}!".format(username),msgsource)
    
    @accesslvl(0)
    @nopm
    def time(self,accesslevel,sock,username,msgsource,msgtype,msg,channame,isprimary):
        """
        Outputs current channel bot time.
        """
        self.chat(sock,"Current bot time is {} on {}.".format(self.gettime(channame),self.getdate(channame)),msgsource)
    
    @accesslvl(0)
    @nopm
    def cycle(self,accesslevel,sock,username,msgsource,msgtype,msg,channame,isprimary):
        """
        Outputs how long until the specified user is eligible for the POINT cycle again.

        Usage: !cycle [username]
        """
        user=username
        if len(msg)>=2:
            user=msg[1].lower()
        if self.getcycletime(channame,user)=="":
            self.chat(sock,"{} cycles are disabled in this channel, {}.".format(self.pointname(channame,1).capitalize(),username),msgsource)
        else:
            self.chat(sock,"Time until {}'s {} cycle claim resets: {}".format(user,self.pointname(channame,1),self.getcycletime(channame,user)),msgsource)
    
    @accesslvl(4)
    @nopm
    def startvote(self,accesslevel,sock,username,msgsource,msgtype,msg,channame,isprimary):
        """
        Starts a vote.

        Usage: "!startvote <option 1> <option 2> [option 3+]"
        """
        votestart=self.startvoteinternal(msg)
        if votestart==-1:
            self.chat(sock,"You have to give some options for the vote, {}!".format(username),msgsource)
        elif votestart==-2:
            self.chat(sock,"There is already a vote going!",msgsource)
        else:
            self.chat(sock,"Vote successfully started!",msgsource)

    @accesslvl(0)
    @nopm
    def vote(self,accesslevel,sock,username,msgsource,msgtype,msg,channame,isprimary):
        """
        Participates in the currently running vote.

        Usage: "!vote <option>"
        """
        if len(msg)<2:
            self.chat(sock,"You have to vote for something, {}!".format(username),msgsource)
        else:
            voting=self.uservote(username,msg[1])
            if voting==-1:
                self.chat(sock,"That's not a valid vote option this time, {}!".format(username),msgsource)
            elif voting==-2:
                self.chat(sock,"There's no vote currently going, {}!".format(username),msgsource)
            elif voting==-3:
                self.chat(sock,"You have already voted, {}!".format(username),msgsource)

    @accesslvl(4)
    @nopm
    def endvote(self,accesslevel,sock,username,msgsource,msgtype,msg,channame,isprimary):
        """
        Ends the currently running vote and displays the results.
        """
        endingvote=self.endvoteinternal()
        if endingvote==-1:
            self.chat(sock,"There's no vote started!",msgsource)
        else:
            if len(endingvote)==0:
                self.chat(sock,"There were no votes!",msgsource)
            elif len(endingvote)==1:
                option=""
                value=0
                for x in endingvote:
                    option=x
                    value=endingvote[x]
                self.chat(sock,"{} won with {} votes!".format(option,value),msgsource)
            else:
                winners=""
                numvotes=0
                for option in endingvote:
                    winners+="'{}', ".format(option)
                    numvotes=endingvote[option]
                winners=winners[:-2]
                winners="{} and {}".format(winners[0:winners.rfind(' ')],winners[winners.rfind(' '):])
                if len(endingvote)==2:
                    winners=winners[0:winners.find(',')]+winners[winners.find(',')+1:]
                self.chat(sock,"{} tied for the win with {} votes!".format(winners,numvotes),msgsource)

    @accesslvl(0)
    @nopm
    def pay(self,accesslevel,sock,username,msgsource,msgtype,msg,channame,isprimary):
        """
        Pays the specified user the specified amount.

        Usage: "!pay <username> <number of POINTS>"
        """
        if len(msg)>=3:
            try:
                user2=msg[1]
                numpoints=int(msg[2])
                giving=self.givepoints(username,user2,numpoints,channame)
                if giving==-1:
                    self.chat(sock,"You don't have that many {} to give, {}!".format(self.pointname(channame,0),username),msgsource)
                elif giving==-2:
                    self.chat(sock,"{} isn't a valid user!".format(user2),msgsource)
                elif giving==-3:
                    self.chat(sock,"You have to pay more than 0 {}, {}!".format(self.pointname(channame,0),username),msgsource)
                else:
                    self.chat(sock,"{} paid {} {} {}.".format(username,user2,numpoints,self.pointname(channame,numpoints)),msgsource)
            except ValueError:
                self.chat(sock,"The amount has to be an integer, {}!".format(username),msgsource)
        else:
            self.chat(sock,"You have to enter a username and number of {} to pay, {}.".format(self.pointname(channame,0),username),msgsource)

    @accesslvl(5)
    @nopm
    def deluser(self,accesslevel,sock,username,msgsource,msgtype,msg,channame,isprimary):
        """
        Deletes the specified user.

        Usage: "!deluser <username>"
        """
        if len(msg)>=2:
            deleted=self.deluserinternal(msg[1],channame)
            if deleted==-1:
                self.chat(sock,"{} isn't a user, {}!".format(msg[1],username),msgsource)
            else:
                self.chat(sock,"{} successfully deleted, {}!".format(msg[1],username),msgsource)

    @accesslvl(0)
    @option("pokemon","true","true")
    @nopm
    def dex(self,accesslevel,sock,username,msgsource,msgtype,msg,channame,isprimary):
        """
        Gives basic information on a specified Pokemon species.

        Usage: "!dex <Pokemon>"
        """
        if len(msg)>=2:
            pokenum=self.getpokenum(msg[1])
            try:
                if pokenum<0:
                    pokenum=int(msg[1])
            except ValueError:
                pokenum=-1
                self.chat(sock,"You must enter a valid pokemon number or species name, {}!".format(username),msgsource)
            if pokenum>=0:
                self.chat(sock,self.pokedex(pokenum,username,channame),msgsource)
        else:
            self.chat(sock,"You must enter either a pokemon number or species name, {}!".format(username),msgsource)

    @accesslvl(5)
    @option("pokemon","true","true")
    @nopm
    def addpoke(self,accesslevel,sock,username,msgsource,msgtype,msg,channame,isprimary):
        """
        Gives the specified user the specified Pokemon.

        Usage: "!addpoke <username> <Pokemon> [level] [shiny? yes/no]"
        """
        if len(msg)>=3:
            pokenum=self.getpokenum(msg[2])
            user=""
            lvl=5
            shiny=False
            try:
                user=msg[1]
                if user[0]=="@":
                    user=user[1:]
                if pokenum<0:
                    pokenum=int(msg[2])
            except ValueError:
                user=""
                self.chat(sock,"You have to enter a valid integer or species name for the Pokemon to give, {}!".format(username),msgsource)
            if len(msg)>=4:
                try:
                    lvl=int(msg[3])
                except ValueError:
                    user=""
                    self.chat(sock,"Level has to be an integer, {}!".format(username),msgsource)
            if len(msg)>=5:
                if msg[4].lower()=="yes" or msg[4].lower()=="true" or msg[4].lower()=="y" or msg[4].lower()=="shiny":
                    shiny=True
            if user!="":
                added=self.addpokeinternal(channame,user,pokenum,lvl,shiny)
                if added==-1:
                    self.chat(sock,"That user doesn't exist, {}!".format(username),msgsource)
                elif added==-2:
                    self.chat(sock,"That Pokemon doesn't exist, {}!".format(username),msgsource)
                else:
                    output="{} was given a ".format(user)
                    if shiny:
                        output+="shiny "
                    output+="level {} {}!".format(lvl,self.getpokename(pokenum))
                    self.chat(sock,output,msgsource)

    @accesslvl(0)
    @nopm
    def info(self,accesslevel,sock,username,msgsource,msgtype,msg,channame,isprimary):
        """
        Outputs the link to the user's information page.

        Usage: "!info [username]"
        """
        if self.getusernameparam(msg)!="":
            if self.getusernameparam(msg).find(" ")==-1:
                self.chat(sock,"http://www.bioniclegenius.com/bot/?channel={}&user={}".format(channame[1:],self.getusernameparam(msg)),msgsource)
            else:
                self.chat(sock,"That's an invalid username, {}!".format(username),msgsource)
        else:
            self.chat(sock,"http://www.bioniclegenius.com/bot/?channel={}&user={}".format(channame[1:],username),msgsource)

    data=info

    @accesslvl(0)
    @nopm
    def channel(self,accesslevel,sock,username,msgsource,msgtype,msg,channame,isprimary):
        """
        Outputs the link to the channel's information page.
        """
        self.chat(sock,"http://www.bioniclegenius.com/bot/?channel={}".format(channame[1:]),msgsource);

    @accesslvl(5)
    @option("pokemon","true","true")
    @nopm
    def delpoke(self,accesslevel,sock,username,msgsource,msgtype,msg,channame,isprimary):
        """
        Deletes the specified user's Pokemon.

        Usage: "!delpoke <username> <Pokemon ID>"
        """
        if len(msg)>=3:
            user=""
            pokeid=-1
            try:
                user=msg[1]
                if user[0]=="@":
                    user=user[1:]
                pokeid=int(msg[2])
            except ValueError:
                user=""
                self.chat(sock,"The Pokemon ID must be a number, {}!".format(username),msgsource)
            if user!="":
                removed=self.rempoke(user,pokeid,channame)
                if removed==-1:
                    self.chat(sock,"That user doesn't exist, {}!".format(username),msgsource)
                elif removed==-2:
                    self.chat(sock,"That user doesn't own a Pokemon with that ID, {}!".format(username),msgsource)
                else:
                    self.chat(sock,"{} ({}) was cuessfully removed from {}, {}!".format(self.getpokename(removed),"%05d"%pokeid,user,username),msgsource)

    @accesslvl(0)
    @option("pokemon","true","true")
    @nopm
    def release(self,accesslevel,sock,username,msgsource,msgtype,msg,channame,isprimary):
        """
        Releases the specified Pokemon.

        Usage: "!release <Pokemon ID>"
        """
        if len(msg)>=2:
            pokenum=0
            try:
                pokenum=int(msg[1])
            except ValueError:
                self.chat(sock,"You have to select a Pokemon by ID number, {}!".format(username),msgsource)
            if pokenum!=0:
                removed=self.rempoke(username,pokenum,channame)
                if removed==-2:
                    self.chat(sock,"You don't own a Pokemon with that ID, {}!".format(username),msgsource)
                elif removed>0:
                    self.chat(sock,"Pokemon {} was successfully released! Bye bye, {}!".format("%05d"%pokenum,self.getpokename(removed)),msgsource)
        else:
            self.chat(sock,"You must enter an ID for a Pokemon to release, {}!".format(username),msgsource)

    @accesslvl(0)
    @option("pokemon","true","true")
    @nopm
    def lvl(self,accesslevel,sock,username,msgsource,msgtype,msg,channame,isprimary):
        """
        Levels up the specified Pokemon.

        Usage: "!lvl <Pokemon ID> <number of levels>"
        """
        if len(msg)>=3:
            pokeid=0
            numlevels=0
            try:
                pokeid=int(msg[1])
                numlevels=int(msg[2])
            except ValueError:
                self.chat(sock,"Invalid input, {}!".format(username),msgsource)
            if pokeid>0:
                leveled=self.levelpoke(username,pokeid,numlevels,channame)
                if leveled==-1:
                    self.chat(sock,"You can't enter 0 or negative levels, {}!".format(username),msgsource)
                elif leveled==-2:
                    self.chat(sock,"You don't have enough {}, {}!".format(self.pointname(channame,0),username),msgsource)
                elif leveled==-3:
                    self.chat(sock,"Weird, but you don't actually exist, {}.".format(username),msgsource)
                elif leveled==-4:
                    self.chat(sock,"Your pokemon {} (#{}) is already maxed out, {}!".format(self.getpokenamebyid(username,pokeid),"%05d"%pokeid,username),msgsource)
                elif leveled==-5:
                    self.chat(sock,"You don't have a Pokemon with the id of {}, {}!".format("%05d"%pokeid,username),msgsource)
                elif leveled==-6:
                    self.chat(sock,"You don't have any Pokemon yet, {}!".format(username),msgsource)
                else:
                    self.chat(sock,"{} leveled up {} ({}) by {} levels to {}!".format(username,self.getpokenamebyid(username,pokeid),"%05d"%pokeid,leveled,self.getpokelvlbyid(username,pokeid)),msgsource)
        else:
            self.chat(sock,"You must choose a Pokemon by id and a number of levels, {}!".format(username),msgsource)

    level=lvl

    @accesslvl(5)
    @nopm
    def additem(self,accesslevel,sock,username,msgsource,msgtype,msg,channame,isprimary):
        """
        Gives the specified user the specified item.

        Usage: "!additem <username> <item name>"
        """
        if len(msg)>=3:
            user=msg[1]
            itemname=msg[2]
            added=self.additeminternal(user,itemname,channame)
            if added==-1:
                self.chat(sock,"That user doesn't exist, {}!".format(username),msgsource)
            elif added==-2:
                self.chat(sock,"That item doesn't exist, {}!".format(username),msgsource)
            else:
                self.chat(sock,"{} was given a {}, {}!".format(user,self.getitemname(itemname),username),msgsource)
        else:
            self.chat(sock,"You must enter a username and an item to give to them, {}!".format(username),msgsource)

    @accesslvl(0)
    @nopm
    def buy(self,accesslevel,sock,username,msgsource,msgtype,msg,channame,isprimary):
        """
        Buys the specified item or Pokemon.

        Usage: "!buy <Pokemon or item name> [quantity, only for items]"
        """
        if len(msg)>=2:
            name=msg[1]
            ispokeoritem=self.ispokeoritem(name)
            if ispokeoritem==1 and self.getoptioninternal(channame,"pokemon","true",True)=="true":
                pokenum=self.getpokenum(msg[1])
                if pokenum<0:
                    try:
                        pokenum=int(msg[1])
                    except ValueError:
                        self.chat(sock,"You have to enter an integer or a species name for the Pokemon to buy, {}!".format(username),msgsource)
                if pokenum>0:
                    bought=self.buypoke(username,pokenum,channame)
                    if bought==-1:
                        self.chat(sock,"That Pokemon doesn't exist!",msgsource)
                    elif bought==-2:
                        self.chat(sock,"{} is too expensive for you, {}!".format(self.getpokename(pokenum),username),msgsource)
                    elif bought==-3:
                        self.chat(sock,"You can't buy a {}, {}!".format(self.getpokename(pokenum),username),msgsource)
                    else:
                        self.chat(sock,"{} has bought the Pokemon #{}, {}! Conglaturations!".format(username,pokenum,self.getpokename(pokenum)),msgsource)
            elif ispokeoritem==1:
                self.chat(sock,"Pokemon are disabled on this channel, {}.".format(username),messagesource)
            elif ispokeoritem==2:
                quantity=1
                if len(msg)>=3:
                    try:
                        quantity=int(msg[2])
                    except ValueError:
                        quantity=-1
                if quantity>=1:
                    bought=self.buyitem(username,msg[1],quantity,channame)
                    if bought==-1:
                        self.chat(sock,"That item doesn't exist, {}!".format(username),msgsource)
                    elif bought==-2:
                        self.chat(sock,"You can't afford that item, {}!".format(username),msgsource)
                    elif bought==-3:
                        self.chat(sock,"That item is not buyable, {}!".format(username),msgsource)
                    elif bought==-4:
                        self.chat(sock,"You can only afford {} {}s, {}!".format(int(self.getpoints(username)/self.getItemCost(msg[1])),msg[1],username),msgsource)
                    else:
                        if quantity==1:
                            self.chat(sock,"{} bought a {}!".format(username,self.getitemname(msg[1])),msgsource)
                        else:
                            self.chat(sock,"{} bought {} {}s!".format(username,quantity,self.getitemname(msg[1])),msgsource)
                else:
                    self.chat(sock,"Your quantity entered must be at least 1, {}.".format(username),msgsource)
            else:
                self.chat(sock,"That's not a valid pokemon name, number, or item name, {}.".format(username),msgsource)
        else:
            self.chat(sock,"You have to enter a Pokemon number or item to buy, {}!".format(username),msgsource)

    @accesslvl(5)
    @nopm
    def delitem(self,accesslevel,sock,username,msgsource,msgtype,msg,channame,isprimary):
        """
        Deletes the specified user's specified item.

        Usage: "!delitem <username> <item name>"
        """
        if len(msg)>=3:
            removed=self.remitem(channame,msg[1],msg[2],self.msgcont(msg,3))
            if removed==-1:
                self.chat(sock,"That user doesn't exist, {}!".format(username),msgsource)
            elif removed==-2:
                self.chat(sock,"That item doesn't exist, {}!".format(username),msgsource)
            elif removed==-3:
                self.chat(sock,"{} doesn't have a {}, {}!".format(msg[1],self.getitemname(msg[2]),username),msgsource)
            else:
                self.chat(sock,"One {} was successfully taken from {}, {}!".format(self.getitemname(msg[2]),msg[1],username),msgsource)
        else:
            self.chat(sock,"You must select a user and an item to remove, {}!".format(usr),msgsource)

    @accesslvl(0)
    @option("pokemon","true","true")
    @nopm
    def evo(self,accesslevel,sock,username,msgsource,msgtype,msg,channame,isprimary):
        """
        Evolves the specified Pokemon, if possible.

        Usage: "!evo <Pokemon ID>"
        """
        if len(msg)>=2:
            pokeid=0
            try:
                pokeid=int(msg[1])
            except ValueError:
                self.chat(sock,"A Pokemon id has to be an integer, {}!".format(username),msgsource)
            if pokeid!=0:
                oldspecies=self.getpokenamebyid(username,pokeid)
                evod=self.evointernal(channame,username,pokeid)
                if evod==-1:
                    self.chat(sock,"You're not a registered user, {}!".format(username),msgsource)
                elif evod==-2:
                    self.chat(sock,"You don't have a Pokemon with that id, {}!".format(username),msgsource)
                elif evod==-3:
                    self.chat(sock,"...That Pokemon species doesn't exist...?",msgsource)
                elif evod==-4:
                    self.chat(sock,"{} doesn't evolve!".format(oldspecies),msgsource)
                elif evod==-5:
                    self.chat(sock,"Your {} is not a high enough level to evolve yet, {}!".format(oldspecies,usr),msgsource)
                elif evod==-6:
                    self.chat(sock,"...The species that Pokemon evolves into doesn't exist...? That's a database error. Contact the dev, please, {}.".format(username),msgsource)
                elif evod==-7:
                    self.chat(sock,"You can't afford to evolve {} yet, {}!".format(self.getpokenamebyid(username,pokeid),username),msgsource)
                elif evod==-8:
                    self.chat(sock,"{} doesn't evolve by leveling up!".format(username),msgsource)
                else:#LIVIN' ON A PRAAAAYER
                    self.chat(sock,"{} successfully evolved their {} into a {}! Conglaturations, {}!".format(username,oldspecies,self.getpokenamebyid(username,pokeid),username),msgsource)
        else:
            self.chat(sock,"You must choose a Pokemon by id to evolve, {}!".format(username),msgsource)

    evolve=evo

    @accesslvl(0)
    @option("pokemon","true","true")
    @nopm
    def useitem(self,accesslevel,sock,username,msgsource,msgtype,msg,channame,isprimary):
        """
        Uses the specified item on the specified Pokemon.

        Usage: "!useitem <item name> <Pokemon ID>"
        """
        if len(msg)>=3:
            pokeid=0
            try:
                pokeid=int(msg[2])
            except ValueError:
                self.chat(sock,"A Pokemon id has to be an integer, {}!".format(username),msgsource)
            if pokeid!=0:
                oldspecies=self.getpokenamebyid(username,pokeid)
                evod=self.evointernal(channame,username,pokeid,msg[1])
                if evod==-1:
                    self.chat(sock,"You're not a registered user, {}!".format(username),msgsource)
                elif evod==-2:
                    self.chat(sock,"You don't have a Pokemon with that id, {}!".format(username),msgsource)
                elif evod==-3:
                    self.chat(sock,"...That Pokemon species doesn't exist...?",msgsource)
                elif evod==-4:
                    self.chat(sock,"{} doesn't evolve, {}!".format(oldspecies,username),msgsource)
                elif evod==-5:
                    self.chat(sock,"{} can't use that item, {}!".format(oldspecies,username),msgsource)
                elif evod==-8:
                    self.chat(sock,"\"{}\" isn't an item that exists, {}!".format(getitemname(msg[1]),username),msgsource)
                elif evod==-9:
                    self.chat(sock,"You don't have a {}, {}!".format(self.getitemname(msg[1]),username),msgsource)
                elif evod==1:
                    self.chat(sock,"{} successfully evolved their {} into a {}! Conglaturations, {}!".format(username,oldspecies,self.getpokenamebyid(username,pokeid),username),msgsource)
                else:
                    self.chat(sock,"Unknown error code, let the dev know about this, {}. Error code: {}".foramt(username,evod),msgsource)
        else:
            self.chat(sock,"You must choose a Pokemon by id and an item to use on it, {}!".format(username),msgsource)

    @accesslvl(4)
    @nopm
    def randomviewer(self,accesslevel,sock,username,msgsource,msgtype,msg,channame,isprimary):
        """
        Selects a random viewer.
        """
        viewer=self.randomviewerinternal(msgsource)
        if viewer!="":
            self.chat(sock,"The randomly selected viewer is {}. Conglaturations!".format(viewer),msgsource)
        else:
            self.chat(sock,"Couldn't pick a viewer. Try again in a bit, {}.".format(username),msgsource)

    @accesslvl(0)
    @option("pokemon","true","true")
    @nopm
    def pokestatus(self,accesslevel,sock,username,msgsource,msgtype,msg,channame,isprimary):
        """
        Outputs a brief summary of information on a user's Pokemon.

        Usage: "!pokestatus [username] [Pokemon ID]"
        """
        user=username
        pokeidcheck=-1
        if len(msg)==2:
            try:
                pokeidcheck=int(msg[1])
            except ValueError:
                user=msg[1]
                pokeidcheck=-1
        if len(msg)>=3:
            user=msg[1]
            try:
                pokeidcheck=int(msg[2])
            except ValueError:
                pokeidcheck=-1
        shiny=0
        if pokeidcheck!=-1:
            shiny=self.isshiny(user,pokeidcheck)
        pokeids=self.listpokeids(user)
        if pokeids!=-1:
            output=""
            if pokeidcheck==-1:
                output="{} has {} pokemon".format(user,len(pokeids))
                if len(pokeids)>=1 and len(pokeids)<=6:
                    output+=" with the following {}: ".format(self.pointname(channame,len(pokeids),"id"))
                    for x in range(len(pokeids)):
                        output+="{}".format(pokeids[x])
                        if x!=len(pokeids)-1:
                            output+=", "
                else:
                    output+="."
            elif shiny==-1:
                output="{} isn't a user!".format(user)
            elif shiny==-2:
                output="{} doesn't have a Pokemon with the id {}!".format(user,"%05d"%pokeidcheck)
            elif shiny==0:
                output="{}'s L{} {} ({}) isn't shiny.".format(user,self.getpokelvlbyid(user,pokeidcheck),self.getpokenamebyid(user,pokeidcheck),"%05d"%pokeidcheck)
                poketype=self.getpoketypebyname(self.getpokenamebyid(user,pokeidcheck))
                if poketype!="":
                    output+=" {} is {}.".format(self.getpokenamebyid(user,pokeidcheck),poketype)
            elif shiny==1:
                output="{}'s L{} {} ({}) is shiny!".format(user,self.getpokelvlbyid(user,pokeidcheck),self.getpokenamebyid(user,pokeidcheck),"%05d"%pokeidcheck)
                poketype=self.getpoketypebyname(self.getpokenamebyid(user,pokeidcheck))
                if poketype!="":
                    output+=" {} is {}.".format(self.getpokenamebyid(user,pokeidcheck),poketype)
            else:
                output="W-w-whaaat? D:"
            self.chat(sock,output,msgsource)
        else:
            self.chat(sock,"{} isn't a user!".format(user),msgsource)

    @accesslvl(0)
    @option("quotes","true","true")
    @nopm
    def quote(self,accesslevel,sock,username,msgsource,msgtype,msg,channame,isprimary):
        """
        Outputs a random or specified quote.

        Usage: "!quote [number or search phrase] [which option in the search - '#<number>']"
        """
        quotenum=-1
        searchterm=""
        whichone=1
        if len(msg)>=2:
            try:
                quotenum=int(msg[1])
            except ValueError:
                searchterm=msg[1:]
                if searchterm[len(searchterm)-1][0]=='#':
                    try:
                        whichone=int(searchterm[len(searchterm)-1][1:])
                        searchterm=searchterm[:-1]
                    except ValueError:
                        whichone=1
                searchterm=self.msgcont(searchterm,0)
                quotenum=-1
        if os.path.exists("{}/quotes.txt".format(self.stripchansign(msgsource))):
            f=open("{}/quotes.txt".format(self.stripchansign(msgsource)),"r")
            quotes=f.readlines()
            f.close()
            if searchterm!="":
                counter=0
                for x in range(0,len(quotes)):
                    if searchterm.lower() in quotes[x].lower():
                        counter+=1
                        quotenum=x+1
                        if counter==whichone:
                            break
            if quotenum>len(quotes):
                quotenum=len(quotes)
            elif quotenum<=0 and len(quotes)>1:
                quotenum=random.randint(1,len(quotes))
            elif len(quotes)==1:
                quotenum=1
            self.chat(sock,"[{}] {}".format(quotenum,quotes[quotenum-1]),msgsource)
        else:
            self.chat(sock,"There are no quotes for this channel! Try adding one with !addquote!",msgsource)

    @accesslvl(4)
    @option("quotes","true","true")
    @nopm
    def addquote(self,accesslevel,sock,username,msgsource,msgtype,msg,channame,isprimary):
        """
        Adds a new quote.

        Usage: "!addquote <quote>"
        """
        if len(msg)>=2:
            if not os.path.exists("{}/quotes.txt".format(self.stripchansign(msgsource))):
                f=open("{}/quotes.txt".format(self.stripchansign(msgsource)),"w+")
                f.write("{}\n".format(self.msgcont(msg)))
                f.close()
                self.chat(sock,"{} added quote [1]: {}".format(username,self.msgcont(msg)),msgsource)
            else:
                f=open("{}/quotes.txt".format(self.stripchansign(msgsource)),"a")
                f.write("{}\n".format(self.msgcont(msg)))
                f.close()
                f=open("{}/quotes.txt".format(self.stripchansign(msgsource)),"r")
                numquotes=len(f.readlines())
                f.close()
                self.chat(sock,"{} added quote [{}]: {}".format(username,numquotes,self.msgcont(msg)),msgsource)
        else:
            self.chat(sock,"You must enter a quote to add, {}!".format(username),msgsource)

    @accesslvl(4)
    @option("quotes","true","true")
    @nopm
    def delquote(self,accesslevel,sock,username,msgsource,msgtype,msg,channame,isprimary):
        """
        Deletes the specified quote.

        Usage: "!delquote <quote number>"
        """
        if len(msg)>=2:
            quotenum=-1
            try:
                quotenum=int(msg[1])
            except ValueError:
                quotenum=-1
                self.chat(sock,"Invalid quote number to delete, {}: {}".format(username,msg[1]),msgsource)
            if quotenum!=-1:
                if os.path.exists("{}/quotes.txt".format(self.stripchansign(msgsource))):
                    f=open("{}/quotes.txt".format(self.stripchansign(msgsource)),"r")
                    quotes=f.readlines()
                    f.close()
                    try:
                        del quotes[quotenum-1]
                        if len(quotes)>0:
                            f=open("{}/quotes.txt".format(self.stripchansign(msgsource)),"w")
                            for x in range(0,len(quotes)):
                                if quotes[x]!="":
                                    f.write("{}".format(quotes[x]))
                            f.close()
                        else:
                            os.remove("{}/quotes.txt".format(self.stripchansign(msgsource)))
                        self.chat(sock,"Quote {} was successfully deleted, {}!".format(quotenum,username),msgsource)
                    except Exception:
                        self.chat(sock,"Error deleting quote {}, {}.".format(quotenum,username),msgsource)
                else:
                    self.chat(sock,"This channel has no quotes to remove, {}!".format(username),msgsource)
        else:
            self.chat(sock,"You must enter a quote number to remove, {}!".format(username),msgsource)

    @accesslvl(0)
    @option("bets","true","true")
    @nopm
    def bet(self,accesslevel,sock,username,msgsource,msgtype,msg,channame,isprimary):
        """
        Bets the specified number of POINTS on the specified option.

        Usage: "!bet <number of POINTS> <bet option>"
        """
        if len(msg)>=3:
            category=""
            numpoints=0
            category=msg[2].lower()
            try:
                numpoints=int(msg[1])
            except ValueError:
                numpoints=0
                self.chat(sock,"You must enter a valid number of {} to bet, {}!".format(self.pointname(channame,0),username),msgsource)
            if numpoints!=0:
                result=self.addbet(channame,username,category,numpoints)
                if result==1:
                    self.chat(sock,"{} bet {} {} on {}.".format(username,numpoints,self.pointname(channame,numpoints),category),msgsource)
                elif result==2:
                    self.chat(sock,"{}'s bet on {} was raised by {} {}.".format(username,category,numpoints,self.pointname(channame,numpoints)),msgsource)
                elif result==-1:
                    self.chat(sock,"That bet is invalid, {}.".format(username),msgsource)
                elif result==-2:
                    self.chat(sock,"You don't exist, {}. Try again later?".format(username),msgsource)
                elif result==-3:
                    self.chat(sock,"You already have placed a bet, {}.".format(username),msgsource)
                elif result==-4:
                    self.chat(sock,"You don't have that many {} to bet, {}!".format(self.pointname(channame,0),username),msgsource)
        elif len(msg)==1:
            category,numpoints=self.getbet(username)
            if category!="":
                self.chat(sock,"You have {} {} bet on {}, {}.".format(numpoints,self.pointname(channame,numpoints),category,username),msgsource)
            else:
                self.chat(sock,"You have not placed a bet yet, {}.".format(username),msgsource)
        else:
            self.chat(sock,"You must enter both a bet category and an amount to bet, {}!".format(username),msgsource)

    @accesslvl(4)
    @option("bets","true","true")
    @nopm
    def undobet(self,accesslevel,sock,username,msgsource,msgtype,msg,channame,isprimary):
        """
        Undoes the specified user's bet.

        Usage: "!undobet <username>"
        """
        if len(msg)>=2:
            user=msg[1]
            result=self.rembet(channame,username)
            if result==1:
                self.chat(sock,"{}'s bet was successfully refunded and removed, {}.".format(user,username),msgsource)
            elif result==-1:
                self.chat(sock,"{} doesn't exist as a user, {}!".format(user,username),msgsource)
            elif result==-2:
                self.chat(sock,"{} doesn't have a bet on file, {}.".format(user,username),msgsource)
        else:
            self.chat(sock,"You must enter a user's username to undo their bet, {}.".format(username),msgsource)

    @accesslvl(5)
    @option("bets","true","true")
    @nopm
    def endbet(self,accesslevel,sock,username,msgsource,msgtype,msg,channame,isprimary):
        """
        Ends the bet and distributes the winnings.

        Usage: "!endbet <winning category>"
        """
        if len(msg)>=2:
            category=msg[1]
            result=self.endbetinternal(channame,category)
            if result==1:
                self.chat(sock,"All users who bet on {} won and gained {}!".format(category,self.pointname(channame,0)),msgsource)
            elif result==-1:
                self.chat(sock,"Nobody has bet on anything yet, {}!".format(username),msgsource)
            elif result==-2:
                self.chat(sock,"Nobody won the bet! The jackpot now has {} {} for the next bet sequence.".format(self.getpoints("bet"),self.pointname(channame,self.getpoints("bet"))),msgsource)
        else:
            self.chat(sock,"You must enter the category that won, {}!".format(username),msgsource)

    @accesslvl(5)
    @option("bets","true","true")
    @nopm
    def resetbet(self,accesslevel,sock,username,msgsource,msgtype,msg,channame,isprimary):
        """
        Resets and refunds all current bets.
        """
        if len(self.betUsernames)>0:
            while len(self.betUsernames)>0:
                self.rembet(channame,self.betUsernames[0])
            self.chat(sock,"All bets have been refunded and removed, {}.".format(username),msgsource)
        else:
            self.chat(sock,"Nobody has any bets to be refunded yet, {}!".format(username),msgsource)
        
    @accesslvl(5)
    @nopm
    def addcom(self,accesslevel,sock,username,msgsource,msgtype,msg,channame,isprimary):
        """
        Adds the specified custom command.

        Usage: "!addcom <command name> <command output>"
        Check the help document for more details on how to use this.
        """
        if len(msg)>=3:
            command=msg[1].lower()
            if "'" in command or "\"" in command:
                self.chat(sock,"A command name may not contain the characters ' or \", {}.".format(username),msgsource)
            else:
                result=self.msgcont(msg,2)
                if len(command)<=20:
                    if (result[0]!="." and result[0]!="/") or msg[2]==".me" or msg[2]=="/me":
                        self.addcommand(channame,command,result)
                        self.chat(sock,"{} set a command {}: {}".format(username,command,result),msgsource)
                    else:
                        self.chat(sock,"A command may not start with '.' or '/', {}, unless it's .me!".format(username),msgsource)
                else:
                    self.chat(sock,"A command name may not be more than twenty characters long, {}!".format(username),msgsource)
        else:
            self.chat(sock,"Custom commands must have a command and a result, {}!".format(username),msgsource)

    editcom=addcom
        
    @accesslvl(5)
    @nopm
    def delcom(self,accesslevel,sock,username,msgsource,msgtype,msg,channame,isprimary):
        """
        Deletes the specified custom command.

        Usage: "!delcom <command name>"
        """
        if len(msg)>=2:
            command=msg[1].lower()
            if self.delcommand(channame,command)!=-1:
                self.chat(sock,"Command {} was successfully deleted, {}!".format(command,username),msgsource)
            else:
                self.chat(sock,"{} isn't a custom command, {}!".format(command,username),msgsource)
        else:
            self.chat(sock,"{}, you must select a custom command to delete!".format(username),msgsource)
        
    @accesslvl(5)
    @nopm
    def setcomal(self,accesslevel,sock,username,msgsource,msgtype,msg,channame,isprimary):
        """
        Sets the specified command's access level.

        Usage: "!setcomal <command name> <access level 0-5>"
        """
        if len(msg)>=3:
            command=msg[1].lower()
            try:
                accesslevel=int(msg[2])
                if(accesslevel<0):
                    self.chat("The access level must be an integer from 0-5, {}!".format(username),msgsource)
                    accesslevel=-1
            except ValueError:
                accesslevel=-1
                self.chat(sock,"The access level must be an integer from 0-5, {}!".format(username),msgsource)
            if accesslevel!=-1:
                if accesslevel<=5:
                    if self.setcommandal(channame,command,accesslevel)==-1:
                        self.chat(sock,"That command doesn't exist, {}!".format(username),msgsource)
                    else:
                        self.chat(sock,"The access level for the command {} was set to {}, {}.".format(command,accesslevel,username),msgsource)
                else:
                    self.chat(sock,"The access level must be an integer from 0-5, {}!".format(username),msgsource)
        else:
            self.chat(sock,"You must enter a command name and access level to set it to, {}.".format(username),msgsource)

    setcomaccesslevel=setcomal
        
    @accesslvl(0)
    @nopm
    def listcoms(self,accesslevel,sock,username,msgsource,msgtype,msg,channame,isprimary):
        """
        Lists the custom commands for the channel.

        Usage: "!listcoms [page number]"
        """
        pagenumber=0
        numresultsperpage=8
        commandlist=self.getcomlist()
        numpages=(len(commandlist)-1)//numresultsperpage
        if len(msg)>1:
            try:
                pagenumber=int(msg[1])-1
            except ValueError:
                pagenumber=0
        if pagenumber>numpages:
            pagenumber=numpages
        if pagenumber<0:
            pagenumber=0
        output=""
        for x in range(pagenumber*numresultsperpage,min((pagenumber+1)*numresultsperpage,len(commandlist))):
            output+="{}, ".format(commandlist[x])
        output=output[:-2]
        if len(commandlist)==0:
            output="None"
        if numpages>0:
            self.chat(sock,"{}/{} Custom commands: {}".format(pagenumber+1,numpages+1,output),msgsource)
        else:
            self.chat(sock,"Custom commands: {}".format(output),msgsource)
        
    @accesslvl(0)
    @nopm
    def ping(self,accesslevel,sock,username,msgsource,msgtype,msg,channame,isprimary):
        """
        Pong!
        """
        if msgtype=="chat":
            self.chat(sock,"Pong!",msgsource)
        
    @accesslvl(6)
    @pmonly
    def announce(self,accesslevel,sock,username,msgsource,msgtype,msg,channame,isprimary):
        """
        Sends a bot announcement to all joined channels.

        Usage: PM the bot "!announce <announcement>"
        """
        self.chat(sock,".me *Bot announcement*: {}".format(self.msgcont(msg)),channame)
        
    @accesslvl(6)
    @canpm
    def raw(self,accesslevel,sock,username,msgsource,msgtype,msg,channame,isprimary):
        """
        Sends a raw message to IRC.

        Usage: "!raw <raw IRC message>"
        """
        self.log(msgsource,self.gettime(channame)+self.msgcont(msg))
        sock.send((self.msgcont(msg)+"\r\n").encode("utf-8"))
        
    @accesslvl(0)
    @canpm
    def roll(self,accesslevel,sock,username,msgsource,msgtype,msg,channame,isprimary):
        """
        Rolls a dice.

        Usage: "!roll [dice]"
        Acceptable formats for [dice]:
            6 - six-sided die.
            2d6 - two six-sided die.
            6+2 - six-sided die with a +2 bonus.
            1d6+3 - one six-sided die with a +3 bonus.
        """
        if len(msg)==1:
            res=random.randint(1,6)
            self.chat(sock,"{} rolled a {}.".format(username,res),msgsource)
        else:
            toroll=msg[1]
            numdie=1
            diesize=6
            baseadd=0
            if toroll.find('+')>=1:
                try:
                    baseadd=int(toroll[toroll.find('+')+1:])
                    toroll=toroll[:toroll.find('+')]
                except ValueError:
                    baseadd=0
            if toroll.find('d')>=1:
                try:
                    numdie=int(toroll[:toroll.find('d')])
                    diesize=int(toroll[toroll.find('d')+1:])
                except ValueError:
                    diesize=""
            elif toroll.find('d')==0:
                try:
                    diesize=int(toroll[toroll.find('d')+1:])
                except ValueError:
                    diesize=""
            else:
                try:
                    diesize=int(toroll)
                except ValueError:
                    diesize=""
            if diesize!="":
                if numdie<1:
                    numdie=1
                elif numdie>100 and accesslevel<4:
                    numdie=100
                elif numdie>1000:
                    numdie=1000
                if diesize<2:
                    diesize=2
                result=0
                if diesize==2:
                    for x in range(0,numdie):
                        result+=random.randint(0,1)
                    if numdie==1:
                        res="tails"
                        if result==1:
                            res="heads"
                        self.chat(sock,"{} flipped a coin and got {}.".format(username,res),msgsource)
                    else:
                        self.chat(sock,"{} flipped {} coins and got {} heads.".format(username,numdie,result),msgsource)
                else:
                    for x in range(0,numdie):
                        temp=random.randint(1,diesize)
                        result+=temp
                    comment=""
                    addition=""
                    if result==42:
                        comment+=" \o/"
                    if diesize==3:
                        comment+=" ...wait, what?"
                    if baseadd!=0:
                        addition="+{}".format(baseadd)
                    self.chat(sock,"{} rolled {}d{}{} and got {}.{}".format(username,numdie,diesize,addition,result+baseadd,comment),msgsource)
        
    @accesslvl(0)
    @canpm
    def flip(self,accesslevel,sock,username,msgsource,msgtype,msg,channame,isprimary):
        """
        Flips a coin, or a bunch of them.

        Usage: "!flip [number of coins]"
        """
        if len(msg)==1:
            res=random.randint(0,1)
            result="tails"
            if res==1:
                result="heads"
            self.chat(sock,"{} flipped a coin and got {}.".format(username,result),msgsource)
        else:
            numcoins=1
            try:
                numcoins=int(msg[1])
            except ValueError:
                numcoins=""
            if numcoins!="":
                if numcoins<1:
                    numcoins=1
                elif numcoins>100 and accesslevel<4:
                    numcoins=100
                elif numcoins>1000:
                    numcoins=1000
                result=0
                for x in range(0,numcoins):
                    result+=random.randint(0,1)
                if numcoins==1:
                    res="tails"
                    if result==1:
                        res="heads"
                    self.chat(sock,"{} flipped a coin and got {}.".format(username,res),msgsource)
                else:
                    self.chat(sock,"{} flipped {} coins and got {} heads.".format(username,numcoins,result),msgsource)
        
    @accesslvl(6)
    @canpm
    def pm(self,accesslevel,sock,username,msgsource,msgtype,msg,channame,isprimary):
        """
        PMs the specified user or channel the given message.

        Usage: "!pm <username or channel name> <message>"
        To specify a channel, start the name with a #.
        """
        if len(msg)>=2:
            chan=msg[1]
            message=self.msgcont(msg,2)
            self.log(msgsource,"{}*WHISPER TO {}*: {}".format(self.gettime(channame),chan.upper(),message))
            if chan[0]=='#':
                message="PRIVMSG "+chan+" :"+message
            else:
                message="PRIVMSG #jtv :.w {} {}".format(chan,message)
            if message[-2:]=="\r\n":
                message=message[:-2]
            sock.send(str(message+"\r\n").encode("utf-8"))
        
    @accesslvl(0)
    @canpm
    def price(self,accesslevel,sock,username,msgsource,msgtype,msg,channame,isprimary):
        """
        Outputs the price of the specified Pokemon or item.

        Usage: "!price <Pokemon or item name>"
        """
        if len(msg)>=2:
            pokenum=self.getpokenum(msg[1])
            if pokenum<0:
                try:
                    pokenum=int(msg[1])
                except ValueError:
                    self.chat(sock,"You must give either a valid number or species name to pricecheck, {}!".format(username),msgsource)
            if pokenum>0:
                price=self.pricecheck(pokenum)
                if price==-1:
                    self.chat(sock,"That Pokemon species number isn't a valid species, {}!".format(username),msgsource)
                elif price==-2:
                    self.chat(sock,"That Pokemon has no price (isn't buyabale and isn't evolved into by leveling).",msgsource)
                else:
                    self.chat(sock,"{} costs {} {}, {}.".format(self.getpokename(pokenum),price,self.pointname(channame,price),username),msgsource)
        else:
            self.chat(sock,"You must give a Pokemon number or species name to pricecheck, {}!".format(username),msgsource)
        
    @accesslvl(0)
    @canpm
    def bot(self,accesslevel,sock,username,msgsource,msgtype,msg,channame,isprimary):
        """
        Links the bot's discord.
        """
        self.chat(sock,"https://discord.gg/53UrSd6",msgsource)

    @accesslvl(0)
    @canpm
    def urban(self,accesslevel,sock,username,msgsource,msgtype,msg,channame,isprimary):
        """
        Returns the first hit on Urban Dictionary for the searched term.

        Usage: !urban <search term>
        """
        result=""
        try:
            with urllib.request.urlopen("http://www.urbandictionary.com/define.php?term={}".format("%20".join(msg[1:]))) as response:
                html = response.read()
            html=html.decode("utf-8")
            html=html.replace("\"","'").replace("&apos;","'").replace("&quot;","\"").replace("\n"," ")
            meaning=html[html.find("<div class='meaning'>"):]
            meaning=meaning[:meaning.find("</div>")]
            meaning=' '.join(meaning.split())
            meaning=re.sub("<[^>]*>","",meaning)
            example=html[html.find("<div class='example'>"):]
            example=example[:example.find("</div>")]
            example=' '.join(example.split())
            example=re.sub("<[^>]*>","",example)
            result="{}: {} Example: {}".format(' '.join(msg[1:]),meaning,example)
        except Exception:
            result="Error: grabbing result failed."
            print(traceback.format_exc())
        self.chat(sock,result,msgsource)

    @accesslvl(0)
    @nopm
    @option("songrequest","true","true")
    def sr(self,accesslevel,sock,username,msgsource,msgtype,msg,channame,isprimary):
        """
        Requests a song from YouTube.

        Usage: !sr [search phrase or URL]
        """
        if len(msg)>=2:
            link=""
            searchfor=re.compile("http(?:s?):\/\/(?:www\.)?youtu(?:be\.com\/watch\?v=|\.be\/)([\w\-\_]*)(&(amp;)?‌​[\w\?‌​=]*)?")
            if searchfor.search(" ".join(msg[1:]))!=None and msg[0]!="!sr":
                link=searchfor.search(" ".join(origmsg)).group(0)
            else:
                response = urlopen("https://www.youtube.com/results?search_query={}".format(urllib.parse.quote(' '.join(msg[1:]))))
                html = response.read()
                soup = BeautifulSoup(html)
                finalLink=""
                links=soup.findAll(attrs={'class':'yt-uix-tile-link'})
                link=""
                for vid in links:
                    if self.video_id(vid['href'])!="":
                        link=self.video_id(vid['href'])
                        break
            if sys.platform=="linux":
                filename="/var/www/html/bot/{}/songs.txt".format(msgsource[1:])
                songnum=0
                if not os.path.isfile(filename):
                    open(filename,"w")
                    os.chmod(filename,0o777)
                numsongs=sum(1 for line in open(filename))
                songs=[]
                with open(filename,"r") as songfile:
                    for x in range(0,numsongs):
                        songs.append(songfile.readline())
                try:
                    songs.remove("\n")
                except ValueError:
                    pass
                if link!="":
                    songs.append(link)
                songs="{}\n".format("\n".join(songs)).replace("\n\n","\n")
                with open(filename,"r+") as songfile:
                    songfile.seek(0)
                    songfile.write(songs)
                    songfile.truncate()
                songnum=numsongs+1
            if link!="":
                self.chat(sock,"Video added to songrequest list by {}: #{} - {}".format(username,songnum,self.getyoutubetitle("http://www.youtube.com/watch?v={}".format(link))),msgsource)
            else:
                self.chat(sock,"No valid video found, sorry. Try again, {}!".format(username),msgsource)
        else:
            self.chat(sock,"http://www.bioniclegenius.com/bot/songrequest.php?channel={}".format(msgsource[1:]),msgsource)

    @accesslvl(4)
    @nopm
    @option("songrequest","true","true")
    def skip(self,accesslevel,sock,username,msgsource,msgtype,msg,channame,isprimary):
        """
        Skips the specified song.

        Usage: "!skip <song number>"
        """
        if sys.platform=="linux":
            if len(msg)>1:
                try:
                    queuenum=int(msg[1])
                except ValueError:
                    queuenum=-1
                filename="/var/www/html/bot/{}/songs.txt".format(msgsource[1:])
                song=""
                numsongs=sum(1 for line in open(filename))
                if queuenum>numsongs:
                    self.chat(sock,"{} is past the end of the queue ({} songs in line), {}!".format(queuenum,numsongs,username),msgsource)
                songs=[]
                with open(filename,"r") as songfile:
                    for x in range(0,numsongs):
                        songs.append(songfile.readline())
                del songs[queuenum-1]
                try:
                    songs.remove("\n")
                except ValueError:
                    pass
                songs="{}\n".format("\n".join(songs)).replace("\n\n","\n")
                with open(filename,"r+") as songfile:
                    songfile.seek(0)
                    songfile.write(songs)
                    songfile.truncate()
                self.chat(sock,"Song #{} skipped by {}.".format(queuenum,username),msgsource)
            else:
                self.chat(sock,"You must select a song number to skip, {}!".format(username),msgsource)
        else:
            self.chat(sock,"Demobot can't do songrequest! :(",msgsource)

    @accesslvl(0)
    @nopm
    @option("songrequest","true","true")
    def song(self,accesslevel,sock,username,msgsource,msgtype,msg,channame,isprimary):
        """
        Outputs the title of the selected song in line.

        Usage: "!song [song number]"
        """
        if sys.platform=="linux":
            queuenum=1
            if len(msg)>1:
                try:
                    queuenum=int(msg[1])
                except ValueError:
                    queuenum=1
            filename="/var/www/html/bot/{}/songs.txt".format(msgsource[1:])
            song=""
            numsongs=sum(1 for line in open(filename))
            queuenum=min(queuenum,numsongs)
            with open(filename,"r") as songfile:
                for x in range(0,min(queuenum,numsongs)):
                    song=songfile.readline()
            songnum="Currently playing: "
            if queuenum!=1:
                songnum="Song #{} in queue: ".format(queuenum)
            if song!="":
                self.chat(sock,"{}{}".format(songnum,self.getyoutubetitle("http://www.youtube.com/watch?v={}".format(song))),msgsource)
            else:
                self.chat(sock,"There's no song currently playing, {}! Try requesting one with !sr.".format(username),msgsource)
        else:
            self.chat(sock,"Demobot can't do songrequest! :(",msgsource)
        
    '''
    @accesslvl(6)
    @nopm
    def listbuiltincoms(self,accesslevel,sock,username,msgsource,msgtype,msg,channame,isprimary):
        """
        Lists all commands available.
        """
        coms=inspect.getmembers(self,predicate=inspect.ismethod)
        finalcoms=[]
        for com in coms:
            if hasattr(com[1],"__accesslevel__"):
                finalcoms.append(com[1].__name__)
        finalcoms.sort()
        for com in finalcoms:
            print(com)
    '''
        
    @accesslvl(0)
    @canpm
    def help(self,accesslevel,sock,username,msgsource,msgtype,msg,channame,isprimary):
        """
        Describes a specified command.

        Usage: "!help <command name>".

        Online documentation: http://goo.gl/fIului
        """
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
                docString=docString.replace('\n',' ').replace("POINTS",self.pointname(channame,0)).replace("POINT",self.pointname(channame,1))
                docString=' '.join(docString.split())
                accesslevel=""
                if hasattr(func,"__accesslevel__"):
                    accesslevel="Access level: {}".format(func.__accesslevel__)
                    self.chat(sock,"!{} - {}. {}".format(func.__name__,accesslevel,docString),msgsource)
                else:
                    self.chat(sock,"{} is not a command, {}!".format(funcName,username),msgsource)
            else:
                self.chat(sock,"{} is not a command, {}!".format(funcName,username),msgsource)
        else:
            self.chat(sock,"http://goo.gl/fIului",msgsource);

    commands=help
    halp=help

    def action(self,sock,usr,msg,accesslevel,messagetype,messagesource,channame,isprimary):
        random.seed()
        self.getoptioninternal(channame,"timezone",0)
        self.getoptioninternal(channame,"pointname","point")
        self.getoptioninternal(channame,"encounterrate",500)
        self.getoptioninternal(channame,"encountertimeexpire",300)
        self.getoptioninternal(channame,"pokelevelupcost",2)
        self.getoptioninternal(channame,"shinyrate",1024)
        self.getoptioninternal(channame,"pointspercycle",10)
        self.getoptioninternal(channame,"cyclelength",1440)
        self.getoptioninternal(channame,"pokemon","true")
        origmsg=msg[:]
        if len(msg)>0:
            msg[0]=msg[0].lower()
        if not self.blacklisted(usr):
            if messagetype=="chat" and messagesource!=usr:
                #===================================================================================================
                #Cycle Points
                #===================================================================================================
                if self.getoptioninternal(channame,"pointspercycle",10,False)<0:
                    self.setoptioninternal(channame,"pointspercycle",0)
                self.autoclaimcycle(usr,self.getoptioninternal(channame,"pointspercycle",10,False),channame)
                #===================================================================================================
                #Encounters
                #===================================================================================================
                self.encountertimeleft(channame,sock,messagesource)
                if random.randint(1,self.getoptioninternal(channame,"encounterrate",500,False))==1 or self.forceEncounter>0:
                    if self.isInEncounter==False:
                        numpokes=len(self.listpokeids(usr))
                        if numpokes>0:
                            self.isInEncounter=True
                            if self.forceEncounter<3:
                                self.wildPokeLevel=int(random.gauss(45,20)+.5)
                                if self.forceEncounter<2:
                                    self.wildPokeEncounter=random.randint(1,251)
                            self.forceEncounter=0
                            if self.wildPokeLevel<1:
                                self.wildPokeLevel=1
                            if self.wildPokeLevel>100:
                                self.wildPokeLevel=100
                            self.userInEncounter=usr
                            self.encounterTimer=datetime.datetime.utcnow()#Timer for five minutes for the encounter, so it runs away after that
                            self.encountertimeleft(channame,sock,messagesource)
                            self.usedPokemon=int(self.listpokeids(usr)[0])
                            self.chat(sock,"{} encountered a wild L{} {}! Try !encounterhelp for assistance!".format(usr,self.wildPokeLevel,self.getpokename(self.wildPokeEncounter)),messagesource)
                #===================================================================================================
                #Youtube Link Metadata
                #===================================================================================================
                searchfor=re.compile("http(?:s?):\/\/(?:www\.)?youtu(?:be\.com\/watch\?v=|\.be\/)([\w\-\_]*)(&(amp;)?‌​[\w\?‌​=]*)?")
                if searchfor.search(" ".join(origmsg))!=None and msg[0]!="!sr":
                    videolink=searchfor.search(" ".join(origmsg)).group(0)
                    self.chat(sock,"{} linked a Youtube video: {}".format(usr,self.getyoutubetitle(videolink)),messagesource)
                #===================================================================================================
                #CUSTOM COMMANDS
                #===================================================================================================
                if not "'" in msg[0] and not "\"" in msg[0]:
                    if self.isacommand(msg[0]) and accesslevel>=self.getcomaccesslevel(msg[0]) and self.getcomaccesslevel(msg[0])!=-1:
                        output,dopm=self.parsecommand(msg,usr,channame)
                        if output!="":
                            testingforperiod=output
                            if output.find(" ")!=-1:
                                testingforperiod=output[0:output.find(" ")]
                            if (testingforperiod[0]!="." and testingforperiod[0]!="/") or testingforperiod==".me" or testingforperiod=="/me":
                                if dopm:
                                    self.chat(sock,output,usr)
                                else:
                                    self.chat(sock,output,messagesource)
            #===================================================================================================
            #Running function commands
            #===================================================================================================
            if msg[0][0]=='!':
                if hasattr(self,msg[0][1:]):
                    if hasattr(getattr(self,msg[0][1:]),"__accesslevel__"):
                        getattr(self,msg[0][1:])(accesslevel,sock,usr,messagesource,messagetype,msg,channame,isprimary)
