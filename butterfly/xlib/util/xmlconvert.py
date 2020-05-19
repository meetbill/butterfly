# coding:utf8

'''
Xml与py对象相互转换的工具集
'''

from xml.etree import cElementTree as ElementTree
from xml.sax.saxutils import escape


def addXmlNodes2Dict(xmlParentNode, resultDict):
    def addChild(parentNode, childNodeName, childNode):
        if parentNode.get(childNodeName):
            if not isinstance(parentNode[childNodeName], list):
                parentNode[childNodeName] = [parentNode[childNodeName]]
            parentNode[childNodeName].append(childNode)
        else:
            parentNode[childNodeName] = childNode

    xmlChildNodes = xmlParentNode.getchildren()
    if xmlChildNodes:
        newNode = {}
        addChild(resultDict, xmlParentNode.tag, newNode)
        for xmlChildNode in xmlChildNodes:
            addXmlNodes2Dict(xmlChildNode, newNode)
    else:
        addChild(resultDict, xmlParentNode.tag, xmlParentNode.text)
    return resultDict


def xml2dict(xmlStr):
    '''
    Convert an XML format string to python dict, attributes in XML node will be ignored
    @param xmlStr: XML String
    @return: Python dict
    @unittest:
    >>> s = "<note><to>Tove</to><from>Jani</from><heading>Reminder</heading><body>Don't forget me this weekend!</body></note>"
    >>> xml2dict(s)
    {'note': {'body': "Don't forget me this weekend!", 'to': 'Tove', 'from': 'Jani', 'heading': 'Reminder'}}
    '''
    if not xmlStr:
        return {}

    return addXmlNodes2Dict(ElementTree.fromstring(xmlStr), {})


def dict2xml(d):
    '''
    Convert a dictionary to xml string, no version head, no attributes
    @param d: dictionary
    @return : XML string
    @unittest:
    >>> sample = {'key':{'subkey':'value1'}}
    >>> dict2xml(sample)
    '<key><subkey>value1</subkey></key>'
    >>> sample = {'key':(1, 2, 3)}
    >>> dict2xml(sample)
    '<key>1</key><key>2</key><key>3</key>'
    >>> sample = {'key':[{'subkey1':1}, {'subkey2':2}]}
    >>> dict2xml(sample)
    '<key><subkey1>1</subkey1></key><key><subkey2>2</subkey2></key>'
    '''
    if not isinstance(d, dict):
        return ''

    strList = []

    def addNodes(parentName, pyObj):
        if isinstance(parentName, tuple):
            parentHead = '<%s ' % parentName[0] + \
                " ".join(parentName[1:]) + '>'
            parentTail = '</%s>' % parentName[0]
        else:
            parentHead = '<%s>' % parentName
            parentTail = '</%s>' % parentName
        if isinstance(pyObj, dict):
            strList.append(parentHead)
            for key, value in pyObj.items():
                addNodes(key, value)
            strList.append(parentTail)
        elif isinstance(pyObj, (list, tuple)):
            for item in pyObj:
                addNodes(parentName, item)
        else:
            if isinstance(pyObj, unicode):
                pyObj = pyObj.encode("utf8")
            pyObj = escape(str(pyObj))
            strList.append(parentHead)
            strList.append(pyObj)
            strList.append(parentTail)
    for key, value in d.items():
        addNodes(key, value)
    return ''.join(strList)


def xml2dict_ignore_xmlns(xmlStr):
    if not xmlStr:
        return {}

    def addXmlNodes2Dict_ignore_xmlns(xmlParentNode, resultDict):
        def addChild(parentNode, childNodeName, childNode):
            if parentNode.get(childNodeName):
                if not isinstance(parentNode[childNodeName], list):
                    parentNode[childNodeName] = [parentNode[childNodeName]]
                parentNode[childNodeName].append(childNode)
            else:
                parentNode[childNodeName] = childNode

        tag = xmlParentNode.tag
        i = tag.find("}")
        if i > 0:
            tag = tag[i + 1:]
        xmlChildNodes = xmlParentNode.getchildren()
        if xmlChildNodes:
            newNode = {}
            addChild(resultDict, tag, newNode)
            for xmlChildNode in xmlChildNodes:
                addXmlNodes2Dict_ignore_xmlns(xmlChildNode, newNode)
        else:
            addChild(resultDict, tag, xmlParentNode.text)
        return resultDict
    return addXmlNodes2Dict_ignore_xmlns(ElementTree.fromstring(xmlStr), {})


if __name__ == '__main__':
    xmlStr = '''<?xml version="1.0" encoding="utf-8" ?><xLive result="ok">
    <getSameDomainPerson_2><args>mailDomain</args><args>Domain</args><name>getSameDomainPerson</name></getSameDomainPerson_2>
    <getGlobalVersion_2><args>mailDomain</args><args>Domain</args><name>getGlobalVersion</name></getGlobalVersion_2>
    </xLive>'''
    ret = xml2dict(xmlStr)
    import doctest
    doctest.testmod()
