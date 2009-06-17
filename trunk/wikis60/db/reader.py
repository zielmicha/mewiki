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

import pair
import container
import binarysearch
import encoding
import tools
import zlib
import json

NotFoundError = binarysearch.NotFoundError

class reversedrange:
    def __init__(self, i):
        self.last = i
    def __getitem__(self, i):
        return self.last - i - 1
    def __len__(self):
        return self.last

class CmpList(binarysearch.CmpList):
    class Wrapper:
        def __init__(self, (pos, item)):
            self.item = encoding.ee(item)
            self.pos = pos
        def __cmp__(self, other):
            return cmp(self.item, other)

class StartsWithList(binarysearch.CmpList):
    class Wrapper:
        def __init__(self, (pos, item)):
            self.item = encoding.ee(item)
            self.pos = pos
        def __cmp__(self, other):
            if self.item.startswith(other):
                return 0
            return cmp(self.item, other)

class Reader:
    def __init__(self, input):
        self.cont = container.Reader(input)
        try:
            config = json.loads(self.cont.get('meta').read())
        except KeyError:
            config = {'slen': 32, 'version': '0'}
        if config['version'] != '0':
            raise NotImplementedError('0 is the only one implemented version (not %s)' % config['version'])
        self.slen = int(config['slen'])
    def _get_article(self, name, exactly=True):
        reader = pair.PairReader(self.cont.get('index'), self.slen)
        wrapped = (exactly and CmpList or StartsWithList)(reader)
        ret = binarysearch.binarysearch(wrapped, encoding.ee(name))
        return ret[0], (ret[1].pos, ret[1].item)
    def get_article(self, name):
        ret = self._get_article(name)[1]
        return ret[0]
    def get_data(self, pos):
        file = self.cont.get('data')
        file.seek(pos)
        size = tools.unpack_int64(file)
        return zlib.decompress(file.read(size))
    def find(self, looking, limit=49):
        looking = encoding.ee(looking)
        begin, (pos, name) = self._get_article(looking, exactly=False)
        result = []
        reader = pair.PairReader(self.cont.get('index'), self.slen)
        reader.seek(begin)
        for pos, name in reader:
            if not encoding.ee(name).startswith(looking):
                break
            if limit < 0:
                break
            limit -= 1
            result.append((pos, name))
        
        for i in reversedrange(begin):
            pos, name = reader[i]
            if not encoding.ee(name).startswith(looking):
                break
            if limit < 0:
                break
            limit -= 1
            result.append((pos, name))
        
        return result
        
def test():
    import sys
    rd = Reader(open(sys.argv[1], 'rb'))
    all = rd.find(sys.argv[2])
    print 'Found:'
    for id, name in all:
        print id, name
    f = open('/tmp/s60wiki', 'w')
    for id, name in all:
        print >>f, rd.get_data(id)
    f.close()
    print 'Saved to /tmp/s60wiki'

if __name__ == '__main__':
    test()