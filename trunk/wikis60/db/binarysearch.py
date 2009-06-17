#!/usr/bin/env python

slicetype = type(slice(0))

def _binarysearch(list, looking_for):
    # print list.begin, list.len + list.begin
    if list is ListRange.EMPTY:
        raise NotFoundError
    item = list.get_item_in_half()
    if looking_for < item:
        return _binarysearch(list.get_first_half(), looking_for)
    elif looking_for > item:
        return _binarysearch(list.get_second_half(), looking_for)
    elif looking_for == item:
        return list.get_half_abspos(), item
    else:
        raise RuntimeError

def binarysearch(list, looking_for):
    return _binarysearch(
        ListRange.wrap(list), looking_for
    )

class ListRange:
    def __init__(self, ls, begin, len):
        self.ls = ls
        self.begin = begin
        self.len = len
        self.half = self.len // 2
    def wrap(cls, list):
        return cls(list, 0, len(list))
    wrap = classmethod(wrap)
    def __getitem__(self, i):
        if isinstance(i, slicetype):
            assert i.stop >= 0 and i.start >= 0
            if i.step:
                raise TypeError('slicing with step not supported')
            if i.start > i.stop:
                raise ValueError('start > end')
            if i.stop > self.len:
                raise IndexError('slice.stop > len(self)')
            if i.start == i.stop:
                return ListRange.EMPTY # should return it for "is"
            return ListRange(self.ls, self.begin + i.start, i.stop - i.start)
        else:
            assert i >= 0
            if i >= self.len:
                raise IndexError
            else:
                return self.ls[self.begin + i]
    def __len__(self):
        return self.len
    def get_first_half(self):
        return self[
            0 : self.half
        ]
    def get_second_half(self):
        return self[
            self.half + 1 : self.len
        ]
    def get_item_in_half(self):
        return self[self.half]
    def get_half_abspos(self):
        return self.half + self.begin
    def __repr__(self):
        return 'ListRange(%r)' % list(self)

ListRange.EMPTY = ListRange.wrap([])

class CmpList:
    def __init__(self, ls):
        self.ls = ls
    def __getitem__(self, i):
        return self.Wrapper(
            self.ls[i]
        )
    def __len__(self):
        return len(self.ls)

class NotFoundError(LookupError):
    pass