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

'Support for streams of (string, int) pairs'


import tools
from tools import unpack_int64, pack_int64, reversed
import encoding

MAGIC = 'w'

__version__ = tools.Version(1, 0, 0)
formatversion = tools.Version(1, 0, 0).toint()

# STRING_ENTRY_LEN = 32

MAGIC = 'PairStrm'

__all__ = [ 'PairReader', 'PairWriter' ]

class PairReader(tools.Corruptable):
    def __init__(self, stream, string_len):
        self.string_len = string_len
        self.stream = stream
        self.stream.seek(0)
        tools.check_magic(self.stream, MAGIC)
        self.length = unpack_int64(self.stream)
        self.begin = self.stream.tell()
        self.pos = 0
    def next(self):
        if self.pos >= self.length:
            raise StopIteration()
        self.pos += 1
        pair = read_pair(self.stream, self.string_len)
        if pair is None:
            print 'Warning! read EOF pair!'
            raise StopIteration()
        return pair
    def seek(self, i):
        self.pos = i
        assert isinstance(self.pos, (int, long)), repr(i)
        if self.pos >= self.length:
            err = EOFError('seek beyond of file byte %d in %d byte file' % (self.pos, self.length))
            self.corrupt()
            raise err
        self.stream.seek(i * (self.string_len + tools.INT64_LEN) + self.begin)
    def __iter__(self):
        return self
    def __getitem__(self, i):
        self.seek(i)
        return self.next()
    def __len__(self):
        return self.length

class PairWriter:
    def __init__(self, stream, count, string_len):
        self.stream = stream
        self.string_len = string_len
        stream.write(MAGIC)
        stream.write(pack_int64(count))
        self.remaining = count
        self.used = 0
    def write(self, pair):
        assert len(pair) == 2
        assert type(pair[0]) == int, pair
        assert type(pair[1]) in (unicode, str), pair
        write_pair(self.stream, pair, self.string_len)
        self.remaining -= 1
        self.used += 1
    def tell(self):
        return self.used
    def check_length(self):
        if self.remaining != 0:
            raise tools.InvalidStateException('Not all pairs has been written')

def write_pair(out, pair, slen):
    (int, string) = pair
    string = encoding.utf8encode(string, slen)
    if type(string) == unicode:
        string = string.encode('utf-8')
    string = string.ljust(slen, '\x01')[:slen]
    assert len(string) == slen
    out.write(pack_int64(int))
    out.write(string)

def skip_end(key, char='\x01'):
    end = len(key)
    for ch in reversed(key):
        if ch != char:
            break
        end -= 1
    assert end >= 0
    return key[:end]

def read_pair(inp, slen):
    int = unpack_int64(inp, on_eof=None)
    string = inp.read(slen)
    if int is None or len(string) != slen:
        return None
    string = skip_end(string)
    return (int, string.decode('utf-8'))

def test():
    pairs = [
             (5, 'asdad'),
             (10, 'csdf'),
             (32, 'asda')
             ]
    import StringIO
    out = StringIO.StringIO()
    writer = PairWriter(out, len(pairs))
    for pair in pairs:
        writer.write(pair)
    writer.check_length()
    out.seek(0)
    reader = PairReader(out)
    for pair1, pair2 in zip(pairs, reader):
        print pair1, pair2
    out.seek(0)
    print list(reader)
    return out