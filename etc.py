#!/usr/bin/env python
# -*- coding: utf-8 -*-
# 잡다한 공용 코드를 넣는 곳. 파일을 좀더 쪼갤 필요도 있겠다.

import threading
import traceback
import os

def needLock( lock ):
	assert( not lock.acquire( False ) )

def die():
	traceback.print_exc()
	os._exit( -1 )

# test ------------------------------------------------------------------------
if __name__ == '__main__':
	l = threading.Lock()
	l.acquire()
	needLock( l )
	l.release()

