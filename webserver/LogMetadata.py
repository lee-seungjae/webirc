#!/usr/bin/env python
# -*- coding: utf-8 -*-

import threading
import copy
import protocol
import config
import redisutil
from etc import *

# ==== 스레드 정책 ====
#   여기 있는 모든 내용에 접근하기 위해서는 락 변수 lock을 잡고 들어와야 한다.
#   이 조건은 needLock( lock ) 으로 강제된다.


lock = threading.Lock()
_users = {} # [ userID -> User ]
_rpool = None

def init():
	global _rpool
	_rpool = redisutil.ConnectionPool( host=config.REDIS_ADDR, port=config.REDIS_PORT, db=config.REDIS_DB, password=config.REDIS_PASSWORD )

def getUser( userID ):
	needLock( lock )
	assertUnicode( userID )

	u = _users.get( userID )
	if u == None:
		u = User( userID )
		_users[ userID ] = u
	return u

# ------------------------------------------------------------------------
# 유저별 마지막 ChatID를 보관한다
# 생성되는 시점에 DB에서 읽으며, 이후에 변경되는 내용은 i2h 채널을 통해서 지속적으로 갱신한다.

class User:
	def __init__( self, userID ):
		assertUnicode( userID )
		self._userID = userID
		self._lastChatIDs = {}   # { ( server, channel ) -> int ]
		self._waitingEvents = [] # [ Event ]

		# 채널별 lastID 읽기
		needLock( lock )
		keyPattern = protocol.encodeList( [ u'log', self._userID, u'*' ] )
		print( 'loading logmeta: ' + keyPattern )
		with _rpool.get() as R:
			for strKey in R.keys( keyPattern ):
				print( ' -> ' + strKey )
				k = protocol.decodeList( strKey )
				assert( k[ 0 ] == u'log' )
				assert( k[ 1 ] == self._userID )
				server = k[ 2 ]
				channel = k[ 3 ]

				attrs = R.hmget( strKey, [ 'end', 'joined' ] )
				last = int( attrs[ 0 ] ) - 1
				joined = ( attrs[ 1 ] == '1' )
				if joined:
					self._lastChatIDs[ ( server, channel ) ] = last

		assertValidChatIDDict( self._lastChatIDs )
		
	def newLogIDArrived( self, server, channel, newLogID ):
		needLock( lock )
		assertUnicode( server, channel )
		assert( type( newLogID ) == type( 0 ) )

		self._lastChatIDs[ ( server, channel ) ] = newLogID
		assertValidChatIDDict( self._lastChatIDs )

		print( '----newLogIDArrived: ' + str( (self._userID, server, channel, newLogID) ) )

		for ev in self._waitingEvents:
			print( '-awake!' )
			ev.set()

	def channelClosed( self, server, channel ):
		needLock( lock )
		assertUnicode( server, channel )

		k = ( server, channel )
		if self._lastChatIDs.get( k ):
			self._lastChatIDs.pop( k )
			assertValidChatIDDict( self._lastChatIDs )
			print( '----channelClosed: ' + str( (self._userID, server, channel) ) )

			for ev in self._waitingEvents:
				print( '-awake!' )
				ev.set()

	def addWaitingEvent( self, e ):
		needLock( lock )
		self._waitingEvents.append( e )

	def removeWaitingEvent( self, e ):
		needLock( lock )
		self._waitingEvents.remove( e )

	def newerLogExists( self, chatIDs ):
		needLock( lock )
		assertValidChatIDDict( chatIDs )
		return chatIDs != self._lastChatIDs
		"""
		# 알고 있는 것 중에 새로운 것이 있는가
		for e in self.latestChatIDs.items():
			reqLast = chatIDs.get( e[0] )
			if reqLast != None and reqLast != e[1]:
				print( '--- DIFFERENT ID, CHANNEL:' + e[0] + ' KNOWNID:' + str(e[1]) + ' REQID:' + str(reqLast) )
				return True

		# 요청받은 것 중에 모르는 것이 있는가
		for e in chatIDs.items():
			if self.latestChatIDs.get( e[0] ) is None:
				logKey = protocol.encodeList( [ 'log', self.userID, 'upnl', e[0] ] ) #TODO: 서버이름이 하드코딩되어있음
				with sharedRedisLock:
					endID = sharedRedis.hget( logKey, 'end' )
					if endID != None:
						self.latestChatIDs[ e[0] ] = int( endID )
						return True
			else:
				pass # 위에서 이미 확인했다

		return False
		"""

	def getLastChatIDs( self ):
		needLock( lock )
		return copy.deepcopy( self._lastChatIDs )


# ------------------------------------------------------------------------
# 로그 정보를 얻는다.

def getLastChatIDs( userID ): # -> { channelName: chatID }
	with lock:
		u = getUser( userID )
		return u.getLastChatIDs()


# ------------------------------------------------------------------------
# 추가된 로그가 있을 때까지 대기한다.
# 클라이언트가 알고 있는 것과 달라진 것이 있으면 대기하지 않고 즉시 리턴한다.

def waitForChange( userID, requestedChatIDs ): # -> { channelName: chatID } or None
	assertUnicode( userID )
	assertValidChatIDDict( requestedChatIDs )
	print( '----Entering WaitForChange: ' + userID )
	doneEvent = None

	# 알고 있는 것과 달라졌는지 확인해 본다.
	# 달라진 게 있으면 즉시 리턴하고, 없으면 변화가 생길 때까지 기다린다.
	with lock:
		u = getUser( userID )
		if u.newerLogExists( requestedChatIDs ):
			return u.getLastChatIDs()
		else:
			doneEvent = threading.Event()
			u.addWaitingEvent( doneEvent )

	doneEvent.wait( 25 )

	# wait()가 타임아웃으로 끝난 이후에도 다른 스레드에 의해 lastChatID가 갱신될 수 있다.
	# (락을 잡은 채로 대기하는 것이 아니므로)
	# 따라서 응답하는 스레드가 아니라 요청하는 스레드가 리스너를 제거하는 주체가 되도록 하는 것이 간단하다.
	# 요청하는 스레드가 리스너를 지워야 할지 말아야 할지를 생각하지 않아도 되기 때문이다.
	with lock:
		u = getUser( userID )
		u.removeWaitingEvent( doneEvent )

		# 타임아웃으로 끝났으면 변화가 없었던 것이다.
		# 이벤트가 타임아웃되고 나서 lock을 다시 잡는 사이에 lastChatID가 갱신될 수도 있지만 문제가 되지는 않는다.
		# 여기서 '바뀐 거 없음' 응답을 보내더라도 클라이언트가 즉시 다시 XHR 요청을 넣을 것이기 때문이다.
		# 클라이언트가 알고 있는 채널별 최신 chatID는 그때 다시 보내지고, 다시 검사될 것이다.
		# 물론 한번의 RTT가 더 발생하긴 하지만 애초에 아주 낮은 확률로 벌어질 일이니 성능 걱정은 하지 않는다.
		if doneEvent.isSet():
			return u.getLastChatIDs()
		else:
			return None


# ------------------------------------------------------------------------
# i2h 채널로 도착하는 메세지를 해당하는 User 객체로 보내준다.
# 대기중인 리스너가 있을 경우 깨워주는 역할만 한다.

class NotificationListeningThread( threading.Thread ):
	def run( self ):
		R = _rpool.create()
		R.subscribe( 'i2h' )
		for rawmsg in R.listen():
			try:
				if rawmsg['type'] == 'message':
					print( '----rcvd: ' + rawmsg['data'] )
					msg = protocol.decodeList( rawmsg['data'] )
					print( '----decoded: ' + str( msg ) )
					getattr( self, "on_" + msg[ 0 ] )( msg )
			except:
				traceback.print_exc()

	def on_newlog( self, msg ):
		uid     = msg[ 1 ]
		server  = msg[ 2 ]
		channel = msg[ 3 ]

		with lock:
			u = getUser( uid )
			if len( msg[ 4 ] ) == 0:
				u.channelClosed( server, channel )
			else:
				logID = int( msg[ 4 ] )
				u.newLogIDArrived( server, channel, logID )


def startNotificationListening():
	thr = NotificationListeningThread().start()


# key: ( unicode, unicode )
# value: int
def assertValidChatIDDict( d ):
	for (k, v) in d.items():
		assertUnicode( k[0], k[1] )
		assert( type( v ) == type( 0 ) )

def assertUnicode( *params ):
	for e in params:
		assert( type( e ) == type( u'' ) )

if __name__ == '__main__':
	# 테스트 데이터 저장
	# 유저:0, 서버:'upnl', 채널:#channel, 로그 범위:[573, 576)
	init()
	r = _rpool.create()

	svKey = protocol.encodeList( [u'server', 0, u'upnl'] )
	r.hset( svKey, 'ssl', 1 )
	r.hset( svKey, 'nickname', 'nickzero' )
	r.hset( svKey, 'addr', 'upnl.org' )
	r.hset( svKey, 'port', '16661' )
	r.hset( svKey, '', '' )
	r.hset( svKey, '', '' )

	logKey = protocol.encodeList( [u'log', 0, u'upnl', u'#channel'] )
	r.hset( logKey, 'begin', 573 )
	r.hset( logKey, 'end', 576 )
	r.hset( logKey, 'joined', 1 )
	r.hset( logKey, '573', '0|say|rica|three|' )
	r.hset( logKey, '574', '0|say|rica|four|' )
	r.hset( logKey, '575', '0|say|rica|five|' )

	chKey = protocol.encodeList( [u'channel', 0, u'upnl', u'#channel'] )
	r.hset( chKey, 'autojoin', 1 )

	assertValidChatIDDict( { ( u'a', u'b' ): 0 } )

	# 본격적인 테스트
	with lock:
		id = u'0'
		user = getUser( id )

		assert( user.newerLogExists( {} ) == True )
		assert( user.newerLogExists( { (u'upnl', u'#channel'): 575 } ) == False )
		assert( user.getLastChatIDs() == { (u'upnl', u'#channel'): 575 } )

		ev = threading.Event()
		user.addWaitingEvent( ev )
		assert( not ev.isSet() )
		user.newLogIDArrived( u'upnl', u'#channel', 576 )
		assert( ev.isSet() )
		user.removeWaitingEvent( ev )

		assert( user.getLastChatIDs() == { (u'upnl', u'#channel'): 576 } )
		user.newLogIDArrived( u'upnl', u'#channel2', 69 )
		assert( user.getLastChatIDs() == { (u'upnl', u'#channel'): 576, (u'upnl', u'#channel2'): 69 } )

	waitForChange( u'0', {} )
