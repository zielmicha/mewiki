#!/usr/bin/env python
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

from xml.etree import cElementTree as et
import tools
import writer
import sys
import re
from xhtmlwriter import translate

ends = '<div id="wikia-credits"><br /><br /><small>From [http://nonsensopedia.wikia.com Nonsensopedia], a [http://www.wikia.com Wikia] wiki.</small></div>'

skip = re.compile('^(mediawiki|forum|dyskusja|talk|user|u.ytkownik|grafika|kategoria|nonsensopedysta)(.*)\:', re.IGNORECASE)

class ReadTo:
    def __init__(self, input, bs = 1024):
        self.input = input
        self.buff = ''
        self.bs = bs
    def readto(self, str):
        while str not in self.buff:
            data = self.input.read(self.bs)
            if not data:
                return None
            self.buff += data
        index = self.buff.index(str)
        buff = self.buff[:index]
        self.buff = self.buff[index + len(str):]
        return buff
    def get_remaining(self):
        buff = self.buff + self.input.read()
        self.buff = ''
        return buff


def chunk_iter(input, on_yield):
    readto = ReadTo(input)
    while readto.readto('<page>') is not None:
        on_yield(readto.readto('</page>'))

def iter_parse(input, on_yield):
    def func(elem):
        x = et.XML('<page>' + elem + '</page>')
        text = x.find('revision/text').text
        title = x.find('title').text
        if skip.search(title):
            return
        if text is None:
            print >>sys.stderr, 'empty article', title
        else:
            if text.endswith(ends):
                text = text[:-len(ends)]
            on_yield(title, text)
    chunk_iter(input, func)

def write(out, input):
    def feedfunc(writer):
        iter_parse(input, writer.feed)
    writer.write(feedfunc, out, translate)

if __name__ == '__main__':
    import sys
    try:
        import psyco
        psyco.full()
    except ImportError:
        pass
    input = tools.progress_open(sys.argv[2])
    out = open(sys.argv[1], 'wb')
    write(out, input)

