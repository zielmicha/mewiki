#!/usr/bin/env python
# coding: utf-8
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

'some useful tools'

import struct
import __builtin__

BLOCK_SIZE = 4096
BS = BLOCK_SIZE

MAXINT64 = 2 << 62
INT64_LEN = 8

def reversed(a):
    o =[]
    for i in xrange(len(a)):
        o.append(a[-i-1])
    return o


class const:
    '''
    unique const
    const('a') != const('a') (comparation is based on memory adress)
    '''
    def __init__(self, name='Const'):
        self.name = name
    def __repr__(self):
        return self.name
    __slots__=[ 'name' ]

RAISE = const('RAISE')

def pack_int64(i):
    if i > MAXINT64:
        raise OverflowError('int is to big to pack to 8 bytes')
    assert i >= 0
    r = struct.pack('!q', i)
    assert len(r) == 8
    return r

def unpack_int64(str, on_eof=RAISE):
    read = str.read(8)
    if len(read) != 8:
        if on_eof is RAISE:
            raise EOFError('Read only %d bytes' % len(read))
        else:
            return on_eof
    return struct.unpack('!q', read)[0]

class Version:
    def __init__(self, *args):
        self.numbers = tuple(args)
        if len(self.numbers) > 4:
            raise ValueError('maximum version length is 4')
        self.numbers += tuple([0] * (4 - len(self.numbers)))
        for num in self.numbers:
            if num not in xrange(256):
                raise ValueError('version component must be in range(256)')
    def toint(self):
        multi = 1
        number = 0
        for num in reversed(self.numbers):
            number += num * multi
            multi <<= 8
        return number
    def fromint(cls, num):
        nums = [0, 0, 0, 0]
        for i in xrange(4):
            nums[i] = num & 0xff
            num >>= 8
        if num:
            raise ValueError('version number is too big (>0xffffffff)')
        return cls(*reversed(nums))
    fromint = classmethod(fromint)
    def __repr__(self):
        return '.'.join(map(str, self.numbers))

'''
def split_by(list, by):
    'DO NOT use it with list(). For in memory split_by use lSplitBy(list(iter))'
    list = BufferedIter(list)
    def helper():
        for i in xrange(by):
            yield list.next()
    while list.has_next():
        yield helper()
'''

class BufferedIter:
    def __init__(self, iterator):
        self.iter = iter(iterator)
        self.cache = None
        self.incache = False
        self.last_incache = False
    def __iter__(self):
        return self
    def has_next(self):
        self.fill_cache()
        return self.incache
    def fill_cache(self):
        if not self.incache:
            try:
                self.cache = self.iter.next()
                self.last_incache = False
                self.incache = True
            except StopIteration:
                pass
    def next(self):
        self.fill_cache()
        if not self.incache:
            raise StopIteration
        self.incache = False
        self.last_incache = True
        return self.cache
    def prev(self):
        if not self.last_incache:
            raise InvalidStateError('there is currently no prev item in cache (you called fill_cache?)')
        self.incache = True
        self.last_incache = False

class lSplitBy:
    def __init__(self, list, by):
        self.by = by
        self.list = list
    def __getitem__(self, i):
        if i * self.by >= len(self.list):
            raise IndexError
        return ListRange(self.list, self.by * i, self.by)

class ListRange:
    def __init__(self, list, offset, length):
        self.list = list
        self.offset = offset
        self.length = length
    def __getitem__(self, i):
        if i < 0:
            i = self.length + i
        if i >= self.length or i < 0:
            raise IndexError()
        return self.list[i + self.offset]
    def __setitem__(self, i, to):
        if i < 0:
            i = self.length + i
        if i >= self.length or i < 0:
            raise IndexError()
        self.list[i + self.offset] = to
    def __delitem__(self, i):
        if i < 0:
            i = self.length + i
        if i >= self.length or i < 0:
            raise IndexError()
        del self.list[i + self.offset]
    def __len__(self):
        return self.length
    def __repr__(self):
        return 'tools.ListRange(%r, offset=%d, length=%d)' % (self.list, self.offset, self.length)

none_function = lambda *args, **kwargs: None;

def flush(stream):
    'flushes stream if it has attribute "flush", '\
    'returns True if stream was flushed'
    if hasattr(stream, 'flush'):
        stream.flush()
        return True
    else:
        return False

def isfile(stream):
    return hasattr(stream, 'read') or hasattr(stream, 'write')

def open(stream, *args, **kwargs):
    if isfile(stream):
        return stream
    return __builtin__.open(stream, *args, **kwargs)

def check_magic(stream, magic):
    read = stream.read(len(magic))
    if read != magic:
        raise IOError(('Bad magic', read, magic))

class InvalidStateError(RuntimeError):
    pass

if __debug__:
    class Corruptable(object):
        'If some errors happend in object and the state is invalid use it'
        def __getattribute__(self, name):
            try:
                if object.__getattribute__(self, '_corrupted'):
                    raise InvalidStateError('object is corrupted')
            except AttributeError:
                self._corrupted = False
            if name == 'corrupt':
                def corrupt():
                    self._corrupted = True
                return corrupt
            else:
                return object.__getattribute__(self, name)
else:
    class Corruptable(object):
        def corrupt(self):
            pass # do nothing

def encode(str, coding):
    if isinstace(str, unicode):
        return str.encode(coding)
    return str

# progress monitor

import os, sys

class CommandLineProgressMonitor:
    def __init__(self, size=80):
        self.size = size
        self.i = 0
        self.last = 0
    def __call__(self, progress):
        self.last = progress
        print >>sys.stderr, '\r', self.draw(self.size, self.i, progress),
        sys.stdout.flush()
        self.i += 1
        self.i %= len(self.chars)
    def draw(self, size, i, progress):
        size -= 10
        char = self.chars[i]
        perc = str(int(progress * 1000) / 10.).rjust(4)
        bar  = '=' * int(size * progress)
        bar = bar.ljust(size)
        return '%s %% |%s| %s' % (perc, bar, char)
    draw = classmethod(draw)
    chars = ['|', '/', '-', '|', '\\']

class BlockInput:
    def __init__(self):
        self.buffer = ''
    def read(self, i=-1):
        output = []
        if i == -1:
            i = 2 ** 64
        while True:
            if not self.buffer:
                self.buffer = self.readblock()
                if not self.buffer:
                    break
            if len(self.buffer) > i:
                output.append(self.buffer[:i])
                self.buffer = self.buffer[i:]
                break
            else:
                output.append(self.buffer)
                i -= len(self.buffer)
                self.buffer = ''
        return ''.join(output)


class ProgressInputMonitorProxy(BlockInput):
    def __init__(self, input, monitor, size, bs=1024 * 4):
        self.input = input
        self.monitor = monitor
        self.gone = 0
        self.size = size
        self.bs = bs
        BlockInput.__init__(self)
    def readblock(self):
        data = self.input.read(self.bs)
        self.gone += len(data)
        self.monitor(float(self.gone) / self.size)
        return data
    def close(self):
        BlockInput.close(self)
        self.input.close()

def progress_open(path):
    size = os.path.getsize(path)
    return ProgressInputMonitorProxy(open(path, 'rb'), CommandLineProgressMonitor(), size)