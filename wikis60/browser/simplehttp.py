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

'Simple HTTP Server'

ERROR_HEADING = 'An error occured while handling request:\n'

responses = {
    100: 'Continue',                                                 
    101: 'Switching Protocols',                                      
    200: 'OK',                                                       
    201: 'Created',                                                  
    202: 'Accepted',                                                 
    203: 'Non-Authoritative Information',                            
    204: 'No Content',                                               
    205: 'Reset Content',                                            
    206: 'Partial Content',                                          
    300: 'Multiple Choices',                                         
    301: 'Moved Permanently',                                        
    302: 'Found',                                                    
    303: 'See Other',                                                
    304: 'Not Modified',
    305: 'Use Proxy',
    307: 'Temporary Redirect',
    400: 'Bad Request',
    401: 'Unauthorized',
    402: 'Payment Required',
    403: 'Forbidden',
    404: 'Not Found',
    405: 'Method Not Allowed',
    406: 'Not Acceptable',
    407: 'Proxy Authentication Required',
    408: 'Request Timeout',
    409: 'Conflict',
    410: 'Gone',
    411: 'Length Required',
    412: 'Precondition Failed',
    413: 'Request Entity Too Large',
    414: 'Request-URI Too Long',
    415: 'Unsupported Media Type',
    416: 'Requested Range Not Satisfiable',
    417: 'Expectation Failed',
    500: 'Internal Server Error',
    501: 'Not Implemented',
    502: 'Bad Gateway',
    503: 'Service Unavailable',
    504: 'Gateway Timeout',
    505: 'HTTP Version Not Supported'
 }


import socket
import thread
import traceback
import url
import StringIO

BAD, GOOD = False, True

# I know BaseHTTPServer

class HTTPServer:
    def __init__(self, adress):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind(adress)
        self.sock.listen(1)
    def log(self, *msg):
        print '[HTTPServer]:', ', '.join(map(str, msg))
    def loop(self):
        try:
            try:
                while True:
                    obj, info = self.sock.accept()
                    thread.start_new_thread(self._handle, (obj, info))
            finally:
                self.log('closing socket')
                self.sock.close()
        except KeyboardInterrupt:
            pass
    def _parse_request(self, sock):
        file = sock.makefile('rb')
        begin = file.readline().strip()
        tpl = begin.split(' ', 2)
        if len(tpl) != 3:
            return (BAD, 'Bad request heading')
        method, path, version = tpl
        method = method.upper()
        headers = {}
        while True:
            header = file.readline().strip()
            if not header:
                break
            tpl = header.split(':', 1)
            if len(tpl) != 2:
                return (BAD, 'No colon in header')
            name, value = tpl
            name = name.strip()
            value = value.strip()
            headers[name] = value
        if method in ('POST', 'PUT'):
            length = -1
            headers = _lower_case(headers)
            if 'content-length' in headers:
                try:
                    length = int(headers['content-length'])
                except ValueError:
                    return (BAD, 'Content-Length is not integer')
            if 'connection' in headers:
                if headers['connection'] == 'close':
                    length = -1
            data = file.read(length)
        else:
            data = None
        return (GOOD, method, path, headers, data)
    def _handle(self, sock, addr):
        try:
            tpl = self._parse_request(sock)
            if tpl[0] == BAD:
                self.log('bad request', tpl[1])
                self._respond(sock, 400, {}, tpl[1] + '\n')
            else:
                self.log('request', tpl[1], tpl[2])
                try:
                    status, headers, data = self.handle_encoding(*tpl[1:])
                except:
                    status, headers, data = 500, {'content-type': 'text/plain'}, ERROR_HEADING + format_exc()
                self.log('responding', status)
                self._respond(sock, status, headers, data)
        finally:
            sock.close()
    def _respond(self, sock, status, headers, data):
        file = sock.makefile('wb')
        file.write('HTTP/1.0 %d %s\n' % (status, responses[status]))
        headers = _lower_case(headers)
        headers['connection'] = 'close'
        headers['content-length'] = str(len(data))
        for key, value in headers.items():
            assert '\n' not in key and ':' not in key
            file.write(
                key + ': ' + value.replace('\n', '\n ') + '\n'
            )
        file.write('\n')
        file.write(data)
    def handle_encoding(self, *args):
        code, headers, data = self.handle(*args)
        if isinstance(data, unicode):
            mime = ('content-type' in headers) and headers['content-type'] or 'text/plain'
            mime += '; charset=utf-8'
            data = data.encode('utf-8')
            headers['content-type'] = mime
        return code, headers, data
    def handle(self, method, path, headers, data):
        raise NotImplementedError('have to be implemented by subclassing or by using Handler')

def format_exc():
    io = StringIO.StringIO()
    traceback.print_exc(file=io)
    return io.getvalue()

class Done(Exception): pass

class Handler:
    def __init__(self, method, path, headers, body):
        self.path = url.Path(path)
        self.inp = StringIO.StringIO(body)
        self.method = method
        self.inheaders = headers
        self.out = StringIO.StringIO()
        self.status = 200
        self.headers = {}
    def write(self, data):
        self.out.write(data)
    def redirect(self, url):
        self.headers['location'] = url
        self.status = 301
    def get(self, name):
        if name in self.path.vars:
            return self.path.vars[name].decode('utf-8')
        else:
            return ''
    def handle(self):
        raise NotImplementedError('have to be implemented by subclassing')
    def _handle(cls, serv, *args):
        inst = cls(*args)
        inst.serv = serv
        try:
            inst.handle()
        except Done:
            pass
        return inst.status, inst.headers, inst.out.getvalue()
    _handle = classmethod(_handle)
    def serve(cls, adr, *args, **kwargs):
        serv = HTTPServer(adr)
        cls.init(serv, *args, **kwargs)
        serv.handle = lambda *args: cls._handle(serv, *args)
        serv.loop()
    serve = classmethod(serve)
    def init(cls, serv):
        pass
    init = classmethod(init)

def test_serve(handler, addr, name=None):
    import time
    serv = HTTPServer(addr)
    try:
        while True:
            obj, info = serv.sock.accept()
            handler = _reload_handler(handler, name)
            t = time.time()
            serv.handle = lambda *args: handler._handle(serv, *args)
            serv._handle(obj, info)
            serv.log('handled in', time.time() - t, 'secs')
    finally:
        serv.sock.close()

def _reload_handler(handler, name):
    modname = handler.__module__
    if modname == '__main__':
        if not name:
            print 'provide handler module name as third argument of test_serve'
            raise SystemExit
        else:
            modname = name
    mod = __import__(modname, {}, {}, [0])
    import sys
    for module in sys.modules.values():
        try:
            reload(module)
        except (TypeError, ImportError):
            pass
    return getattr(mod, handler.__name__)

def _lower_case(dictionary):
    'clones all keys as lower case'
    return  dict([
        (key.lower(), value)
        for key, value in dictionary.items()
    ])