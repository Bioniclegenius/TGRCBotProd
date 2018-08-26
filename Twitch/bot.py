# bot.py

import cfg
import cfg2
import socket
import re
import time
import importlib
import urllib.request
import datetime
import traceback
import os.path
import sys
import _thread

CHAT_MSG=re.compile(r"^:\w+!\w+@\w+\.tmi\.twitch\.tv PRIVMSG #\w+ :")
WHISPER=re.compile(r"^:\w+!\w+@\w+\.tmi\.twitch\.tv WHISPER \w+ :")
USERSTATE=re.compile(r"^:tmi\.twitch\.tv USERSTATE #\w+")
NOTICE=re.compile(r"^:tmi\.twitch\.tv NOTICE ")
JOIN=re.compile(r"^:\w+!\w+@\w+\.tmi\.twitch\.tv JOIN #\w+")
PART=re.compile(r"^:\w+!\w+@\w+\.tmi\.twitch\.tv PART #\w+")

keeprunning={}
primarychannel=""

def stripchansign(chan):
    if chan[0]=="#":
        return chan[1:]
    return chan

def makechandir(chan):
    chan=stripchansign(chan)
    if not os.path.exists(chan):
        os.makedirs(chan)
    if sys.platform=="linux":
        if not os.path.exists("/var/www/html/bot/{}".format(stripchansign(chan))):
            os.makedirs("/var/www/html/bot/{}".format(stripchansign(chan)))

def log(source,msg,doprint=True):
    if doprint:
        print(msg)
    if source[0]=="#":
        if not os.path.exists("logs/{}".format(stripchansign(source))):
            os.makedirs("logs//{}".format(stripchansign(source)))
        with open("logs/{}/{}.txt".format(stripchansign(source),getlogdate()),"a") as logfile:
            logfile.write("{}  |  {}\r\n".format(datetime.datetime.now().strftime("%I:%M:%S %p"),msg))
    else:
        with open("logs/{}{}.txt".format(getlogdate(),source),"a") as logfile:
            logfile.write("{}  |  {}\r\n".format(datetime.datetime.now().strftime("%I:%M:%S %p"),msg))
    with open("logs/{}Global.txt".format(getlogdate()),"a") as logfile:
        logfile.write("{}  |  {}\r\n".format(datetime.datetime.now().strftime("%I:%M:%S %p"),msg))

def getlogdate():
    return datetime.datetime.now().strftime("%Yy-%mm-%dd-%a")

def writecustomplugin(chan):
    f=open("{}plugin.py".format(stripchansign(chan)),"w+")
    f.write("import pluginfunctions\n")
    f.write("import importlib\n")
    f.write("\n")
    f.write("class pf(pluginfunctions.pf):\n")
    f.write("\n")
    f.write("    def __init__(self):\n")
    f.write("        importlib.reload(pluginfunctions)\n")
    f.write("        super(pf,self)\n")
    f.write("\n")
    f.write("    def action(self,sock,usr,msg,accesslevel,messagetype,messagesource,channame,isprimary):\n")
    f.write("        super(pf,self).action(sock,usr,msg,accesslevel,messagetype,messagesource,channame,isprimary)\n")
    f.close()
    

def chat(sock,msg,msgsource,p):
    whisperback=False
    if len(msgsource)>0:
        if msgsource[0]!='#':
            whisperback=True
    if whisperback:
        try:
            sock.send("PRIVMSG {} :.w {} {}".format("#jtv",msgsource,str(msg)+"\r\n").encode("utf-8"))
        except ConnectionResetError:
            return -1
        except Exception:
            log(msgsource,"EXCEPTION\r\n{}".format(traceback.format_exc()))
            return -1
        log(msgsource,"{}*WHISPER  TO  {} : {}".format(gettime(p,msgsource),msgsource.upper(),str(msg)))
    else:
        try:
            sock.send("PRIVMSG {} :{}".format(msgsource,str(msg)+"\r\n").encode("utf-8"))
        except ConnectionResetError:
            return -1
        except Exception:
            log(msgsource,"EXCEPTION\r\n{}".format(traceback.format_exc()))
            return -1
        log(msgsource,"{}{} {}: {}".format(gettime(p,msgsource),msgsource,cfg2.NICK,msg))
    return 1

def gettime(p,chan):
    hour=0
    try:
        hour=p.getoptioninternal(chan,"timezone",0,False)
    except Exception:
        log(chan,"EXCEPTION\r\n{}".format(traceback.format_exc()))
        chat(s,"Error! Check console for details.",chan,p)
        hour=0
    return (datetime.datetime.now()+datetime.timedelta(hours=hour)).strftime("%I:%M:%S %p ")

def grabusers(s,chan,isPrimary,p):
    moderators=[]
    staff=[]
    admins=[]
    global_mods=[]
    viewers=[]
    supers=[]
    botsupers=[]
    botmods=[]
    try:
        with urllib.request.urlopen("https://tmi.twitch.tv/group/user/"+chan[1:]+"/chatters") as response:
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
            moderators.append(m[:m.find("\"")])
            m=m[m.find("\"")+1:]
        while st.find("\"")!=-1:
            st=st[st.find("\"")+1:]
            staff.append(st[:st.find("\"")])
            st=st[st.find("\"")+1:]
        while a.find("\"")!=-1:
            a=a[a.find("\"")+1:]
            admins.append(a[:a.find("\"")])
            a=a[a.find("\"")+1:]
        while g.find("\"")!=-1:
            g=g[g.find("\"")+1:]
            global_mods.append(g[:g.find("\"")])
            g=g[g.find("\"")+1:]
        while v.find("\"")!=-1:
            v=v[v.find("\"")+1:]
            viewers.append(v[:v.find("\"")])
            v=v[v.find("\"")+1:]
    except urllib.error.HTTPError:
        log(chan,"{}{} Grabbing users failed.".format(gettime(p,chan),chan))
        raise Exception("Grabbing users failed.")
    except Exception:
        log(chan,"EXCEPTION\r\n{}".format(traceback.format_exc()))
        chat(s,"Error! Check console for details.",chan,p)
        raise Exception("Grabbing users failed.")
    if os.path.exists("supers.txt"):
        f=open("supers.txt")
        for line in f:
            if line!="\n":
                if line.find("\n")!=-1:
                    botsupers.append(line[:line.find("\n")])
                else:
                    botsupers.append(line)
        if chan[1:] not in supers:
            supers.append(chan[1:])
    else:
        f=open("supers.txt","w+")
        f.close()
    if os.path.exists("{}/botmods.txt".format(stripchansign(chan))):
        f=open("{}/botmods.txt".format(stripchansign(chan)))
        for line in f:
            if line!="\n":
                if line.find("\n")!=-1:
                    botmods.append(line[:line.find("\n")])
                else:
                    botmods.append(line)
    else:
        f=open("{}/botmods.txt".format(stripchansign(chan)),"w+")
        f.close()
    try:
        p.setacclevels(moderators,staff,admins,global_mods,viewers,supers,botsupers,botmods)
    except Exception:
        log(chan,"EXCEPTION\r\n{}".format(traceback.format_exc()))
        chat(s,"Error! Check console for details.",chan,p)
        raise Exception("Grabbing users failed.")
    return moderators,staff,admins,global_mods,viewers,supers,botmods,botsupers

def msgcont(msg):
    temp=""
    if len(msg)>1:
        for x in range(1,len(msg)):
            temp+=msg[x]
            if x<len(msg)-1:
                temp+=" "
    return temp

def getusernameparam(msg):
    temp=msgcont(msg)
    if len(temp)>0:
        if temp[0]=="@":
            temp=temp[1:]
    return temp

def savebotmods(s,chan,p,moderators,staff,admins,global_mods,viewers,supers,botsupers,botmods):
    f=open("{}/botmods.txt".format(stripchansign(chan)),'w')
    for x in range(0,len(botmods)):
        f.write(botmods[x].lower()+"\n")
    f.close()
    try:
        p.setacclevels(moderators,staff,admins,global_mods,viewers,supers,botsupers,botmods)
    except Exception:
        log(chan,"EXCEPTION\r\n{}".format(traceback.format_exc()))
        chat(s,"Error! Check console for details.",chan,p)

def savechans():
    lines="NICK = \"{}\"\n".format(cfg2.NICK);
    lines+="PASS = \"{}\"\n".format(cfg2.PASS);
    lines+="CHAN = [";
    for x in keeprunning:
        if keeprunning[x]:
            lines+="\""+x+"\","
    lines=lines[:-1]
    lines+="]\n"
    f=open("cfg2.py","w")
    f.write(lines)
    f.close()

def initconnect(chan):
    s=socket.socket()
    s.settimeout(600)
    s.connect((cfg.HOST,cfg.PORT))
    s.send("PASS {}\r\n".format(cfg2.PASS).encode("utf-8"))
    s.send("NICK {}\r\n".format(cfg2.NICK).encode("utf-8"))
    s.send("CAP REQ :twitch.tv/membership\r\n".encode("utf-8"))
    #s.send("CAP REQ :twitch.tv/tags\r\n".encode("utf-8"));
    s.send("CAP REQ :twitch.tv/commands\r\n".encode("utf-8"));
    s.send("JOIN {}\r\n".format(chan).encode("utf-8"))
    return s

def recvchan(chan,uhh):
    makechandir(chan)
    global keeprunning
    global primarychannel
    import pluginfunctions as pf
    if os.path.exists("{}plugin.py".format(stripchansign(chan))):
        custompf=__import__("{}plugin".format(stripchansign(chan)))
    else:
        writecustomplugin(chan)
        custompf=__import__("{}plugin".format(stripchansign(chan)))
    p=custompf.pf()
    p.init(chan,primarychannel==chan)
    moderators=[]
    staff=[]
    admins=[]
    global_mods=[]
    viewers=[]
    supers=[]
    botsupers=[]
    botmods=[]
    hourchange=0
    log(chan,"{}{} Initializing channel...".format(gettime(p,chan),chan))
    s = initconnect(chan)
    time.sleep(1)
    try:
        moderators,staff,admins,global_mods,viewers,supers,botmods,botsupers = grabusers(s,chan,primarychannel==chan,p)
    except Exception:
        pass
    lastgrab=datetime.datetime.now()
    tries=1
    if chat(s,"Hello, everybody!",chan,p)==-1:
        tries+=1
        log(chan,"{} deaded. Retrying {}...".format(chan,tries))
        s=initconnect(chan)
    while keeprunning[chan]:
        res=""
        try:
            res = s.recv(1024).decode("utf-8")
        except Exception:
            tries+=1
            log(chan,"{} deaded. Retrying {}...".format(chan,tries))
            s=initconnect(chan)
        while res.find("\r\n")!=-1:
            response=res[:res.find("\r\n")+2]
            res=res[res.find("\r\n")+2:]
            if response == "PING :tmi.twitch.tv\r\n":
                s.send("PONG :tmi.twitch.tv\r\n".encode("utf-8"))
                log(chan,"{}{} Pinged.".format(gettime(p,chan),chan))
                lastgrab=datetime.datetime.now()
                try:
                    moderators,staff,admins,global_mods,viewers,supers,botmods,botsupers = grabusers(s,chan,primarychannel==chan,p)
                except Exception:
                    pass
            else:
                username="ERROR ERROR"
                if re.search(r"\w+", response)!=None:
                    username = re.search(r"\w+", response).group(0)
                message=""
                messagetype=""
                messagesource=username
                isawhisper=False
                hide=False
                isajoinpart=False
                if re.match(CHAT_MSG,response)!=None:
                    message = CHAT_MSG.sub("", response)
                    messagetype="chat"
                    messagesource=re.search(r"#\w+",response).group(0)
                elif re.match(WHISPER,response)!=None:
                    message = WHISPER.sub("", response)
                    isawhisper=True
                    messagetype="pm"
                    messagesource=username
                elif re.match(USERSTATE,response)!=None:
                    message=""
                    hide=True
                    messagetype="userstate"
                    messagesource=re.search(r"#\w+",response).group(0)
                elif re.match(NOTICE,response)!=None:
                    hide=True
                    messagetype="notice"
                elif re.match(JOIN,response)!=None:
                    messagetype="join"
                    messagesource=re.search(r"#\w+",response).group(0)
                    message=username.upper()+" JOIN "+messagesource.upper()
                    isajoinpart=True
                elif re.match(PART,response)!=None:
                    messagetype="part"
                    messagesource=re.search(r"#\w+",response).group(0)
                    message=username.upper()+" PART "+messagesource.upper()
                    isajoinpart=True
                else:
                    message = CHAT_MSG.sub("", response)
                    messagetype="unknown"
                messagesource=messagesource.lower()
                if message[-2:]=="\r\n":
                    message=message[:-2]
                if message!="":
                    if isawhisper:
                        log(messagesource,"{}{} *WHISPER FROM {}*: {}".format(gettime(p,chan),chan,username.upper(),message))
                    elif isajoinpart:
                        log(chan,"{}{} {}".format(gettime(p,chan),chan,message))
                    else:
                        log(chan,"{}{} {}: {}".format(gettime(p,chan),messagesource,username,message))
                    message=message.split()
                    accesslevel=0
                    if username in global_mods:
                        accesslevel=1
                    if username in admins:
                        accesslevel=2
                    if username in staff:
                        accesslevel=3
                    if username in moderators or username in botmods:
                        accesslevel=4
                    if username in supers:
                        accesslevel=5
                    if username in botsupers:
                        accesslevel=6
                    if accesslevel>=5 and message[0]=="!reload":
                        if not os.path.exists("{}plugin.py".format(stripchansign(chan))):
                            writecustomplugin(chan)
                        try:
                            importlib.reload(pf)
                            importlib.reload(custompf)
                            p=custompf.pf()
                            p.init(chan,primarychannel==chan)
                            if messagesource[0]=='#':
                                chat(s,"Reloaded from {}!".format(chan),messagesource,p)
                        except Exception:
                            log(chan,"EXCEPTION\r\n{}".format(traceback.format_exc()))
                            chat(s,"Error in {}! Check console for details.".format(chan),messagesource,p)
                        try:
                            moderators,staff,admins,global_mods,viewers,supers,botmods,botsupers = grabusers(s,chan,primarychannel==chan,p)
                        except Exception:
                            pass
                        lastgrab=datetime.datetime.now()
                    if accesslevel>=5 and message[0]=="!mod":
                        if len(message)>1:
                            username2=getusernameparam(message).lower()
                            if username2 in botmods:
                                chat(s,username2+" is already a bot-mod!",messagesource,p)
                            elif username2 in supers or username2 in botsupers:
                                chat(s,username2+" already has super access!",messagesource,p)
                            elif username2!="":
                                botmods.append(username2)
                                savebotmods(s,chan,p,moderators,staff,admins,global_mods,viewers,supers,botsupers,botmods)
                                chat(s,username2+" is now a bot-mod! Congrats, "+username2,messagesource,p)
                            else:
                                chat(s,"Who did you want me to bot-mod, {}?".format(username),messagesource,p)
                        else:
                            chat(s,"Who did you want me to bot-mod, {}?".format(username),messagesource,p)
                    if accesslevel>=5 and message[0]=="!unmod":
                        if len(message)>1:
                            username2=getusernameparam(message).lower()
                            if username2 not in botmods:
                                chat(s,username2+" isn't a bot-mod!",messagesource,p)
                            else:
                                botmods.remove(username2)
                                savebotmods(s,chan,p,moderators,staff,admins,global_mods,viewers,supers,botsupers,botmods)
                                chat(s,username2+" has been removed as a bot-mod.",messagesource,p)
                        else:
                            chat(s,"Who did you want me to remove from the bot-mod list, {}?".format(username),messagesource,p)
                    if accesslevel>=6 and (message[0]=="!shutdown" or message[0]=="!delchan" or message[0]=="!remchan" or message[0]=="!leave" or message[0]=="!part") and (primarychannel==chan or messagetype=="chat"):
                        if len(message)>1:
                            isup=False
                            channame=message[1]
                            if channame[0]!="#":
                                channame="#"+channame
                            if channame in keeprunning:
                                isup=keeprunning[channame]
                            if isup:
                                keeprunning[channame]=False
                                chat(s,"Goodbye, {}!".format(channame),messagesource,p)
                                savechans()
                            else:
                                chat(s,"{} isn't up to start with.".format(channame),messagesource,p)
                        else:
                            chat(s,"Enter a channel name to be closed.",messagesource,p)
                    if accesslevel>=6 and (message[0]=="!addchannel" or message[0]=="!addchan" or message[0]=="!newchan" or message[0]=="!newchannel" or message[0]=="!join") and (primarychannel==chan or messagetype=="chat"):
                        if len(message)>1:
                            isup=False
                            newchan=message[1].lower()
                            if newchan[0]!="#":
                                newchan="#"+newchan
                            if newchan in keeprunning:
                                isup=keeprunning[newchan]
                            if isup:
                                chat(s,"{} is already up!".format(newchan),messagesource,p)
                            else:
                                keeprunning[newchan]=True
                                _thread.start_new_thread(recvchan,(newchan,True))
                                chat(s,"{} has been added!".format(newchan),messagesource,p)
                                savechans()
                        else:
                            chat(s,"Enter a channel name to be added.",messagesource,p)
                    if accesslevel>=0 and (message[0]=="!listchans" or message[0]=="!listchan" or message[0]=="!listchannels") and (primarychannel==chan or messagetype=="chat"):
                        channellist=""
                        for x in keeprunning:
                            if keeprunning[x]:
                                channellist+=x+", "
                        channellist=channellist[:-2]
                        chat(s,"Channels I am in right now: {}".format(channellist),messagesource,p)
                    try:
                        p.action(s,username,message,accesslevel,messagetype,messagesource,chan,primarychannel==chan)
                    except Exception:
                        log(chan,"EXCEPTION\r\n{}".format(traceback.format_exc()))
                        chat(s,"Error! Check console for details.",chan,p)
                elif not hide:
                    log(chan,response)
        if (datetime.datetime.now()-lastgrab).total_seconds()>300:#five minutes have passed since we last heard any ping from the server
            log(chan,"{}{} Time limit reached, reconnecting...".format(gettime(p,chan),chan))
            s=initconnect(chan)
            lastgrab=datetime.datetime.now()
        time.sleep(1/cfg.RATE)
    log(chan,"{}{} Leaving.".format(gettime(p,chan),chan))
    keeprunning[chan]=False
    if primarychannel==chan:
        primarychannel=""
        for x in keeprunning:
            if keeprunning[x]:
                primarychannel=x
                break
                
if len(cfg2.CHAN)>0:
    primarychannel=cfg2.CHAN[0].lower()
for x in range(len(cfg2.CHAN)):
    log(cfg2.CHAN[x].lower(),"Initializing {}.".format(cfg2.CHAN[x].lower()))
    _thread.start_new_thread(recvchan,(cfg2.CHAN[x].lower(),True))
    keeprunning[cfg2.CHAN[x].lower()]=True
    time.sleep(1)

while True:
    time.sleep(1)

for x in keeprunning:
    keeprunning[x]=False
