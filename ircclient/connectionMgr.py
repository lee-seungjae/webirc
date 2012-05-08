#!/usr/bin/env python
# -*- coding: utf-8 -*-

from IRCUser import IRCUser
from protocol import *
from etc import *
import TimerManager

class ConnectionManager:
	def __init__( self, rpool ):
		self.clients = {} # UserID => IRCUser
		self.timerMgr = TimerManager.TimerManager()
		self.rpool = rpool

		# DB의 joined 플래그 클리어
		with self.rpool.get() as R:
			for chKey in R.keys( encodeList( [ u'log', u'*' ] ) ):
				ch = decodeList( chKey )
				R.hdel( chKey, 'joined' )
				R.publish( 'i2h', encodeList( [ u'newlog', ch[1], ch[2], ch[3], u'' ] ) )

	def get( self, uid ):
		assert( isinstance( uid, unicode ) )
		u = self.clients.get( uid )
		if( u != None ):
			return u

		# 생성
		with self.rpool.get() as R:
			for svKey in R.keys( encodeList( [ u'server', uid, u'*' ] ) ):
				svName = decodeList( svKey )[ 2 ]
				svSettings = R.hgetall( svKey )
				svSettings['name'] = svName

				channels = {}
				for chKey in R.keys( encodeList( [ u'channel', uid, svName, u'*' ] ) ):
					chName = decodeList( chKey )[ 3 ]
					chSettings = R.hmgetAsDict( chKey, [ u'autojoin', u'key' ] )
					channels[ chName ] = chSettings

				# 일단 유저당 서버는 하나만
				u = IRCUser( uid, self.timerMgr, R, svSettings, channels )
				self.clients[ uid ] = u
				return u

		return None

	def update( self ):
		self.timerMgr.update()

		# 타임아웃된 커넥션 걸러내기.
		# 순회 중에 컨테이너 건드리기가 불안해서 별도의 리스트로 묶어낸 다음 하나씩 폐기한다.
		deadClients = []
		for uid, client in self.clients.items():
			if not client.isAlive():
				deadClients.append( (uid, client) )

		# 파괴 및 재접속 예약은 여기서만 한다
		for uid, client in deadClients:
			print( uid + ' is timed out.' )
			del self.clients[ uid ]
			client.destroy()

			# 일단 무조건 30초 후 재접속하도록 고정해 둠.
			self.reserveConnect( uid, 30.0 )

	def reserveConnect( self, uid, delay ):
		self.timerMgr.setTimeout( lambda: self.get( uid ), delay )
			
