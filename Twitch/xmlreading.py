import xml.etree.ElementTree

tree=xml.etree.ElementTree.parse("test.xml")
e=tree.getroot()
poketree=xml.etree.ElementTree.parse("pokemon.xml")
pokeroot=poketree.getroot()

def printusers():
    global e
    global pokeroot
    print('='*30)
    for atype in e.findall("user"):
        print(atype.get("name")+":")
        print("  Points: "+atype.find("points").text)
        if atype.find("pokemon")!=None:
            print("  Pokemon:")
        for pokemon in atype.findall("pokemon"):
            desc="    "
            if pokemon.find("num")!=None:
                num=pokemon.find("num").text
                desc+="#"+num+" "
                try:
                    desc+=pokeroot.find(".//pkmn[@num='"+num+"']/name").text
                except AttributeError:
                    desc=desc[:desc.find('#')]
                    num=str(0)
                    desc+="#"+num+" "
                    desc+=pokeroot.find(".//pkmn[@num='"+num+"']/name").text
            if pokemon.find("level")!=None:
                desc+="\n      L"+pokemon.find("level").text
            print(desc)
    print('='*30)

def saveusers():
    global tree
    global e
    tree.write("test.xml")

def addpoints(username,numpoints):
    global e
    if e.find(".//user[@name='"+username+"']")!=None:
        e.find(".//user[@name='"+username+"']").find("points").text=str(int(e.find("user").find("points").text
)+numpoints)
    else:
        points=xml.etree.ElementTree.Element("points")
        points.text=str(numpoints)
        user=xml.etree.ElementTree.Element("user",{"name":username})
        user.append(points)
        e.append(user)

printusers()
addpoints("Test",2)
printusers()
saveusers()
