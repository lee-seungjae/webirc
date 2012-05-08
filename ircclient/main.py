#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import time
import getopt
import asyncore
import traceback
import config
import redisutil
from commandProcess import CommandProcessor
from connectionMgr import ConnectionManager

# 실행 인자 처리
#opts, args = getopt.getopt( sys.argv[1:], 'n:' )
#for o, a in opts:
#	if o == '-n' and a.isdigit():
#		setRedisDB( int(a) )

# 초기화
rpool = redisutil.ConnectionPool( host=config.REDIS_ADDR, port=config.REDIS_PORT, db=config.REDIS_DB, password=config.REDIS_PASSWORD )
connMgr = ConnectionManager( rpool )
cmdProc = CommandProcessor( rpool, connMgr )

# 메인 루프
while True:
	try:
		asyncore.loop( 0.5, True, None, 1 )
		cmdProc.update()
		connMgr.update()
		time.sleep( 0.1 )

	except KeyboardInterrupt:
		print( '장비를 정지합니다.' );
		os._exit( 1 )

	except:
		traceback.print_exc()

# never reaches here
assert( False )


