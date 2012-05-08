#!/usr/bin/env python
# -*- coding: utf-8 -*-

import Queue
import os
import traceback
from etc import *
from protocol import *
from threading import Thread

class CommandProcessor( Thread ):
	def __init__( self, rpool, connMgr ):
		Thread.__init__( self )
		self.rpool = rpool
		self.connMgr = connMgr
		self.cmdQueue = Queue.Queue()
		self.start()

	# from Thread
	# 들어오는 요청들을 큐에 쌓는다.
	def run( self ):
		try:
			R = self.rpool.create()
			R.subscribe( 'h2i' )
			print( 'connected to redis.' );

			for a in R.listen():
				if a['type'] == 'message':
					msg = decodeList( a['data'] )
					if msg[0] == u'cmd':
						self.cmdQueue.put( msg[1:] )
		except:
			traceback.print_exc()
			os._exit( 2 )

	# 큐에 쌓인 redis 커맨드들을 처리한다.
	# 메인 쓰레드에서만 수행되어야 함.
	def update( self ):
		try:
			while True:
				msg = self.cmdQueue.get_nowait()
				if( len( msg ) < 2 ):
					print( 'malformed command:' + str( msg ) )
					continue

				targetUser = self.connMgr.get( msg[ 1 ] )
				if( targetUser == None ):
					print( 'no target user:' + str( msg ) )
					continue

				targetUser.onUserCommand( msg )

		except Queue.Empty:
			# 큐에 항목이 더이상 없다면 여기로 빠져나오게 된다.
			# 설마 starvation되진 않겠지
			pass

		except:
			# 으으
			traceback.print_exc()
