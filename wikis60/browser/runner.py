#!/usr/bin/env python
import thread
import time
import appuifw
import random
import browser

portnum = 2**10*8 + random.randint(1, 1024)
adress = 'http://127.0.0.1:%d' % portnum

def _main():
    print 'will serve'
    browser.simplehttp.test_serve(browser.WikiHandler, ('127.0.0.1', portnum), 'wikis60.browser.browser')

try:
    import webbrowser, e32
    thread.start_new_thread(_main, ())
    appuifw.note(u'please wait')
    print 'waiting for server to bind...'
    while not browser.simplehttp.ready:
        e32.ao_yield()
    print adress
    e32.ao_sleep(1)
    webbrowser.open(adress)
    import sys
    sys.exit()
except Exception, val:
    appuifw.note(repr(val).decode('utf8'), 'error')
    raise