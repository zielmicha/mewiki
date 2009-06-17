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

import simplehttp
import url
import cgi
import os
import binascii
import wikis60.db.reader as reader

def qattr(s):
    return s.replace('"', '')

history = 'e:\\data\\wikihistory.txt'

class WikiHandler(simplehttp.Handler):
    def handle(self):
        if self.path.path == '/':
            self.redirect('/f/hello.html')
            return
        if self.path.path == '/favicon.ico':
            self.redirect('/f/favicon.ico')
            return
        module = self.path.spath[0]
        getattr(self, 'do_' + module.lower())(*self.path.spath[1:])
    def do_ask(self):
        gourl = self.get('url')
        self.html()
        self.write('<title>Wiki</title>Go to <a href="%s">%s</a>!' % (qattr(gourl), cgi.escape(gourl)))
    def do_f(self, name):
        if '\\' in name or '/' in name:
            raise simplehttp.Done
        self.write(open(os.path.join(os.path.dirname(__file__), 'static', name), 'rb').read())
    def do_go(self):
        item = self.get('item')
    def do_choice(self):
        open(history, 'a')
        self.html()
        self.write('<title>Wiki</title><form action="/choose" method=GET>Path: <input type=text name=path><input type=submit></form>')
        for item in open(history):
            item = item.strip()
            self.write('<a href="/content/%s/search" title="%s">%s</a><br>' % (binascii.hexlify(item), qattr(item), cgi.escape(os.path.basename(item))))
        self.write('<br><a href="/clean" class="btn">Clean history</a>')
    def do_choose(self):
        path = self.get('path')
        self.save_history(path)
        enc = binascii.hexlify(path)
        self.redirect('/content/' + enc + '/search?find=')
    def do_clean(self):
        open(history, 'w')
        self.redirect('/')
    def save_history(self, path):
        try:
            f = open(history, 'a')
            f.write(path + '\n')
            f.close()
        except:
            pass
    def do_content(self, file, module):
        file = binascii.unhexlify(file)
        getattr(self, 'content_' + module.lower())(file)
    def get_db(self, file):
        return reader.Reader(open(file, 'rb'))
    def content_search(self, file):
        self.html()
        db = self.get_db(file)
        find = self.get('find')
        self.write('''
            <title>Wiki</title>
            <body onload="v=document.f.find;v.focus();v.selectionStart=v.selectionEnd=v.value.length;">
            <a href="/">Another</a>
            <form action="search" method=GET name=f>
            Name starts with:
            <input type=text name=find value="%s">
            <input type=submit>
            </form>
        ''' % qattr(find))
        if not find:
            return
        try:
            response = db.find(find, limit=49)
        except reader.NotFoundError:
            self.write('<h2>Not found</h2>')
            return
        lfind = find.lower()
        try:
            num = db.get_article(find)
            self.write('<h2>Found <a href="num?num=%d">%s</a></h2>' % (num, cgi.escape(find)))
        except reader.NotFoundError:
            pass
        self.write('''
            <h2>Results</h2>
            <ol id="ls">
        ''')
        for num, name in response:
            self.write('<li><a href="num?num=%d">%s</a><br>' % (num, cgi.escape(name)))
    def content_num(self, file):
        num = int(self.get('num'))
        self.html()
        db = self.get_db(file)
        self.write('<a href="search">Find!</a>')
        self.write(db.get_data(num))
    def content_go(self, file):
        self.html()
        name = self.get('item')
        db = self.get_db(file)
        try:
            i = db.get_article(name)
        except reader.NotFoundError:
            self.write('<a href="search">Find!</a><h2>Article %s not found</h2>' % (cgi.escape(name)))
        else:
            self.redirect('num?num=%d' % i)
    def html(self):
        self.write('<link ref="/f/favicon.ico" rel="shortcut icon" type="image/x-icon"><link href="/f/main.css" rel=stylesheet type="text/css">')
        self.headers['content-type'] = 'text/html'
    
if __name__ == '__main__':
    simplehttp.test_serve(WikiHandler, ('localhost', 12394), 'wikis60.browser.browser')