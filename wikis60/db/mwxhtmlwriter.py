#! /usr/bin/env python

# Copyright (c) 2007-2009 PediaPress GmbH                               
#                                                                       
# All rights reserved.                                                  
#                                                                       
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#
# * Redistributions of source code must retain the above copyright
#   notice, this list of conditions and the following disclaimer.
#
# * Redistributions in binary form must reproduce the above
#   copyright notice, this list of conditions and the following
#   disclaimer in the documentation and/or other materials provided
#   with the distribution.
#
# * Neither the name of PediaPress GmbH nor the names of its
#   contributors may be used to endorse or promote products derived
#   from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
# PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
# LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
# NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

# Copyright (c) 2009, Michal Marek Zielinski
# 
# All rights reserved.
#
# *   Redistribution and use in source and binary forms, with or without modification,
#     are permitted provided that the following conditions are met:
#     
# *   Redistributions of source code must retain the above copyright notice, this list
#     of conditions and the following disclaimer.
#     
# *   Redistributions in binary form must reproduce the above copyright notice, this
#     list of conditions and the following disclaimer in the documentation and/or
#     other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR
# ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
# ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.



"""
Generate valid XHTML from the DOM tree generated by the parser.

This implements the proposed format at:
http://www.mediawiki.org/wiki/Extension:XML_Bridge/MWXHTML

Basically XHTML is used adding semantics by using microformats

http://meta.wikimedia.org/wiki/Help:Advanced_editing
http://meta.wikimedia.org/wiki/Help:HTML_in_wikitext

see the corresponding test_xhtmlwriter.py unit test.

if invoked with py.test test_xhtmlwriter.py tests are
executed and xhtml output is validated by xmllint.


ToDo: 

 * templates / parser has to support marking of boundaries first
 * always add vlist data if available / if supported by the parser
 * strategy to move to xhtml1.1 in order to validate w/ mathml
"""

import urllib
import sys
import cgi
import StringIO
import xml.etree.cElementTree as ET

import encoding

from mwlib import parser
from mwlib import advtree
from mwlib import xmltreecleaner
from mwlib import writerbase
from mwlib.uparser import parseString

version = "0.2-wikis60"


def escapeLink(link):
    if not link:
        return None
    return '/ask?url=' + urllib.quote(link.encode('utf-8'))

def setVList(element, node):
    """
    sets html attributes as found in the wikitext
    if this method is used it should be called *after* 
    the class attribute is set to some xvalue.
    """
    if hasattr(node, "vlist") and node.vlist:
        saveclass = element.get("class")
        for k,v in xserializeVList(node.vlist):
            element.set(k,v)
        if saveclass and element.get("class") != saveclass:
            element.set("class", " ".join((saveclass, element.get("class"))))

def xserializeVList(vlist):
    args = [] # list of (key, value)
    styleArgs = []
    gotClass = 0
    gotExtraClass = 0
    for (key,value) in vlist.items():
        if isinstance(value, (basestring, int)):
            args.append((key, unicode(value)))
        if isinstance(value, dict) and key=="style":
            for (_key,_value) in value.items():
                styleArgs.append("%s:%s" % (_key, _value))
            args.append(("style", '%s' % '; '.join(styleArgs)))
    return args

class SkipChildren(object):
    "if returned by the writer no children are processed"
    def __init__(self, element=None):
        self.element = element

class MWXHTMLWriter(object):

    ignoreUnknownNodes = True
    namedLinkCount = 1

    header=''

    paratag = "div" # [p,div] switch to 'div' if xhtml validation is required (or fix parser)

    def __init__(self, title):
        self.root = ET.Element("html")
        # add head + title
        e = ET.SubElement(self.root, "title") 
        e.text = title
        self.title = title
        # start body
        self.xmlbody = ET.SubElement(self.root, "body")        
        self.errors = []
        self.references = []
        
    def asstring(self):
        def _r(obj, p=None):
            for c in obj:
                assert c is not None
                for k,v in c.items():
                    if v is None:
                        print k,v
                        assert v is not None
                _r(c,obj)
        _r(self.root)
        res = self.header + ET.tostring(self.root)
        return res
    
    def writeText(self, obj, parent):
        # todo: templates
        self._writeText(obj.caption, parent)
    
    def _writeText(self, data, parent):
        if parent.getchildren(): # add to tail of last tag
            t = parent.getchildren()[-1]
            if not t.tail:
                t.tail = data
            else:
                t.tail += data
        else:
            if not parent.text:
                parent.text = data
            else:
                parent.text += data

    def writeparsetree(self, tree):
        out = StringIO.StringIO()
        parser.show(out, tree)
        self.root.append(ET.Comment(out.getvalue().replace("--", " - - ")))
        

    def write(self, obj, parent=None):
        # if its text, append to last node
        if isinstance(obj, parser.Text):
            self.writeText(obj, parent)
        else:
            # check for method
            m = "xwrite" + obj.__class__.__name__
            m=getattr(self, m, None)
            if m: # find handler
                e = m(obj)
            elif self.ignoreUnknownNodes:
                e = None
            else:
                raise Exception("unknown node:%r" % obj)
            
            if isinstance(e, SkipChildren): # do not process children of this node
                return e.element
            elif e is None:
                e = parent

            for c in obj.children[:]:
                ce = self.write(c,e)
                if ce is not None and ce is not e:                    
                    e.append(ce)
            return e

    def writeChildren(self, obj, parent): # use this to avoid bugs!
        "writes only the children of a node"
        for c in obj:                    
            res = self.write(c, parent)
            if res is not None and res is not parent:
                parent.append(res)

    def writeBook(self, book, output=None):
        self.xmlbody.append(self.write(book))
        #self.write(book, self.xmlbody)
        if output:
            if not hasattr(output, 'write'):
                output = open(output, "w")
            output.write(self.asstring())

    def xwriteBook(self, obj):
        e = ET.Element("div")
        e.set("class", "xcollection")
        return e # do not return an empty top level element

    def xwriteArticle(self, a):
        # add article name as first section heading
        e = ET.Element("div")
        e.set("class", "xarticle")
        h = ET.SubElement(e, "h1")
        h.text = a.caption
        self.writeChildren(a, e)
        return SkipChildren(e)


    def xwriteChapter(self, obj):
        e = ET.Element("div")
        e.set("class", "xchapter")
        h = ET.SubElement(e, "h1")
        self.write(obj.caption)
        return e


    def xwriteSection(self, obj):
        e = ET.Element("div")
        e.set("class", "xsection")
        level = 2 + obj.getLevel() # starting with h2
        h = ET.SubElement(e, "h%d" % level)
        self.write(obj.children[0], h)
        obj.children = obj.children[1:]
        return e

        
    def xwriteNode(self, n):
        pass # simply write children


    def xwriteCell(self, cell):
        td = ET.Element("td")
        setVList(td, cell)           
        return td
            
    def xwriteRow(self, row):
        return ET.Element("tr")

    def xwriteTable(self, t):           
        table = ET.Element("table")
        setVList(table, t)           
        if t.caption:
            c = ET.SubElement(table, "caption")
            self.writeText(t.caption, c)
        return table




    # Special Objects


    def xwriteTimeline(self, obj): 
        s = ET.Element("object")
        s.set("class", "xtimeline")
        s.set("type", "application/mediawiki-timeline")
        s.set("src", "data:text/plain;charset=utf-8,%s" % obj.caption)
        em = ET.SubElement(s, "em")
        em.set("class", "xtimeline_alternate")
        em.text = u"Timeline"
        return s

    def xwriteHiero(self, obj):
        return SkipChildren()


    def xwriteMath(self, obj):
        s = ET.Element("object")
        s.text = obj.caption
        return s

    xwriteMath_WITH_OBJECT = xwriteMath


    # Links ---------------------------------------------------------


    def xwriteLink(self, obj): # FIXME (known|unknown)
        obj.url = 'go?item=' + urllib.quote(obj.target.encode('utf-8')) # ---
        obj.title = obj.target.encode('utf-8')
        a = ET.Element("a", href=obj.url or "#")
        a.set("class", "xlink_article")
        if not obj.children:
            if obj.target.startswith('Grafika:'):
                return SkipChildren()
            a.text = obj.target
        return a

    xwriteArticleLink = xwriteLink
    xwriteInterwikiLink = xwriteLink
    xwriteNamespaceLink = xwriteLink


    def xwriteURL(self, obj):
        a = ET.Element("a", href=escapeLink(obj.caption))
        a.set("class", "xlink_external")
        if not obj.children:
            a.text = obj.caption
        return a

    def xwriteNamedURL(self, obj):
        a = ET.Element("a", href=escapeLink(obj.caption))
        a.set("class", "xlink_external")
        if not obj.children:
            name = "[%s]" % self.namedLinkCount
            a.text = name
        return a
    
    def xwriteMath(self, obj):
        a = ET.Element("div")
        a.set('class', 'xmath')
        a.text = obj.caption
        return a

    def xwriteSpecialLink(self, obj): # whats that?
        return SkipChildren()
       
    def xwriteImageLink(self, obj): 
        return SkipChildren()

    def xwriteImageMap(self, obj):
        return SkipChildren()

    def xwriteGallery(self, obj):
        return SkipChildren()

    def xwriteLangLink(self, obj):
        return SkipChildren()

    def writeLanguageLinks(self):
        return SkipChildren()
        
    def xwriteReference(self, t):
        assert t is not None
        self.references.append(t)
        t =  ET.Element("sup")
        t.set("class", "xreference")
        t.text = unicode( len(self.references))
        return SkipChildren(t)

    def xwriteReferenceList(self, t):
        if not self.references:
            return
        ol = ET.Element("ol")
        ol.set("class", "xreferences")
        for i,ref in enumerate(self.references):
            li = ET.SubElement(ol, "li", id="cite_note-%s" % i)
            self.writeChildren(ref, parent=li)
        self.references = []            
        return ol

    # ---------- Generic XHTML Elements --------------------------------

    def xwriteGenericElement(self, t):
        if not hasattr(t, "starttext"):
            if hasattr(t, "_tag"):
                e = ET.Element(t._tag)
                setVList(e, t)
                return e
            else:
                return
        else: 
            # parse html and return ET elements
            stuff = t.starttext + t.endtext
            try:
                if not t.endtext and not "/" in t.starttext:
                    stuff = t.starttext[:-1] + "/>"
                p =  ET.fromstring(stuff)
            except Exception, e:
                raise e
        return p

    xwriteEmphasized = xwriteGenericElement
    xwriteStrong = xwriteGenericElement
    xwriteSmall = xwriteGenericElement
    xwriteBig = xwriteGenericElement
    xwriteCite = xwriteGenericElement
    xwriteSub = xwriteGenericElement
    xwriteSup = xwriteGenericElement
    xwriteCode = xwriteGenericElement
    xwriteBreakingReturn = xwriteGenericElement
    xwriteHorizontalRule = xwriteGenericElement
    xwriteTeletyped = xwriteGenericElement
    xwriteDiv = xwriteGenericElement
    xwriteSpan = xwriteGenericElement
    xwriteVar= xwriteGenericElement
    xwriteRuby = xwriteGenericElement
    xwriteRubyBase = xwriteGenericElement
    xwriteRubyParentheses = xwriteGenericElement
    xwriteRubyText = xwriteGenericElement
    xwriteDeleted = xwriteGenericElement
    xwriteInserted = xwriteGenericElement
    xwriteTableCaption = xwriteGenericElement
    xwriteDefinitionList = xwriteGenericElement
    xwriteDefinitionTerm = xwriteGenericElement
    xwriteDefinitionDescription = xwriteGenericElement
    xwriteFont = xwriteGenericElement
    
    def xwritePreFormatted(self, n):
        return ET.Element("pre")

    def xwriteParagraph(self, obj):
        """
        currently the parser encapsulates almost anything into paragraphs, 
        but XHTML1.0 allows no block elements in paragraphs.
        therefore we use the html-div-element. 

        this is a hack to let created documents pass the validation test.
        """
        e = ET.Element(self.paratag) # "div" or "p"
        e.set("class", "xparagraph")
        return e


    # others: Index, Gallery, ImageMap  FIXME
    # see http://meta.wikimedia.org/wiki/Help:HTML_in_wikitext

    # ------- TAG nodes (deprecated) ----------------

    def xwriteOverline(self, s):
        e = ET.Element("span")
        e.set("class", "xstyle_overline")
        return e    

    def xwriteUnderline(self, s):
        e = ET.Element("span")
        e.set("class", "xstyle_underline")
        return e

    def xwriteSource(self, s):       
        # do we have a lang attribute here?
        e = ET.Element("code")
        e.set("class", "xsource")
        return e
    
    def xwriteCenter(self, s):
        e = ET.Element("span")
        e.set("class", "xstyle_center")
        return e

    def xwriteStrike(self, s):
        e = ET.Element("span")
        e.set("class", "xstyle_strike")
        return e

    def _xwriteBlockquote(self, s, klass): 
        e = ET.Element("blockquote")
        e.set("class", klass)
        level = len(s.caption) # FIXME
        return e
    
    def xwriteBlockquote(self, s):
        "margin to the left & right"
        return self._xwriteBlockquote(s, klass="xblockquote")

    def xwriteIndented(self, s):
        "margin to the left"
        return self._xwriteBlockquote(s, klass="xindented")

    def xwriteItem(self, item):
        ch = item.children
        if len(ch) >= 2:
            if isinstance(ch[0], type(u'')):
                if ch.lower().startswith('redirect'):
                    linkto = ch[1].caption
                    if encoding.ee(linkto) == encoding.ee(self.title):
                        raise __init__.Skip
        return ET.Element("li")

    def xwriteItemList(self, lst):
        if lst.numbered:
            tag = "ol"
        else:
            tag = "ul"
        return ET.Element(tag)

def preprocess(root):
    advtree.buildAdvancedTree(root)
    xmltreecleaner.removeChildlessNodes(root)
    xmltreecleaner.fixLists(root)
    xmltreecleaner.fixParagraphs(root)
    xmltreecleaner.fixBlockElements(root)

def translate(title, data):
    print title.encode('utf-8')
    r = parseString(title=title, raw=data)
    preprocess(r)
    dbw = MWXHTMLWriter(title=title)
    dbw.writeBook(r)
    try:
        return dbw.asstring()
    except:
        print >>sys.stderr, 'could not process article', title
        import traceback
        traceback.print_exc()
        return '<div class="error">Error occured while processing this article</div>'

def main():
    for fn in sys.argv[1:]:
        input = unicode(open(fn).read(), 'utf8')
        data = writexhtml(fn, input)
        nf = open("%s.html" % fn, "w")
        nf.write(data)
        nf.close()

import __init__
 
if __name__=="__main__":
    main()
