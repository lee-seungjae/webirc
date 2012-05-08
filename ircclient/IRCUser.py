# -*- coding: utf-8 -*

import AsyncClient
from IRCClient import IRCClient, nm_to_n
from AsyncClient import AsyncSSLClient
from AsyncClient import AsyncSocketClient
from protocol import encodeList
import traceback
import time

class IRCChannel:
	def __init__( self, redis, userID, serverName, chanName ):
		self.chanLogKey = encodeList( [ u'log', userID, serverName, chanName ] )
		self.redis = redis
		self.userID = userID
		self.chanName = chanName
		self.serverName = serverName
		self.users = {}

		id = self.redis.hget( self.chanLogKey, 'end' )
		if id == None:
			self.redis.hset( self.chanLogKey, 'begin', 0 )
			self.logEndID = 0
		else:
			self.logEndID = int( id )

	def appendLog( self, msg ):
		k = self.chanLogKey

		# 갱신
		newLogID = str( self.logEndID )
		self.redis.hset( k, newLogID, encodeList( msg ) )
		self.logEndID += 1
		self.redis.hset( k, 'end', str( self.logEndID ) )
		self.redis.publish( 'i2h', encodeList( [ u'newlog', self.userID, self.serverName, self.chanName, unicode( newLogID ) ] ) )
	
	def setTopic( self, topic ):
		k = self.chanLogKey
		self.redis.hset( k, 'topic', encodeList( [ topic ] ) )

	def markAsJoined( self, joined ):
		k = self.chanLogKey
		if joined:
			self.redis.hset( k, 'joined', '1' )
		else:
			self.redis.hdel( k, 'joined' )
			self.redis.publish( 'i2h', encodeList( [ u'newlog', self.userID, self.serverName, self.chanName, u'' ] ) )
	
	# 관련 로그를 쓰는 것보다 addUser 등을 호출하는 것이 앞서야 함에 주의
	def addUser( self, nick, mod ):
		assert( isinstance( nick, unicode ) )
		assert( isinstance( mod, unicode ) )
		self.users[ nick ] = mod
		self.dumpUsersToDB()

	def removeUser( self, nick ):
		assert( isinstance( nick, unicode ) )
		self.users.pop( nick )
		self.dumpUsersToDB()
	
	def hasUser( self, nick ):
		assert( isinstance( nick, unicode ) )
		return ( self.users.get( nick ) != None )

	def changeUserNick( self, oldNick, newNick ):
		assert( isinstance( oldNick, unicode ) )
		assert( isinstance( newNick, unicode ) )
		self.users[ newNick ] = self.users.pop( oldNick )
		self.dumpUsersToDB()

	def dumpUsers( self ):
		return [ unicode( self.logEndID ) ] + [ nick for (nick, mod) in sorted(self.users.items()) ]

	def dumpUsersToDB( self ):
		d = self.dumpUsers()
		self.redis.hset( self.chanLogKey, 'users', encodeList( d ) )
		
class IRCUser:
	def __init__( self, userID, timerMgr, redis, svSettings, chSettings ):
		if svSettings['ssl'] == '1':
			self.transport = AsyncSSLClient( svSettings['addr'], int(svSettings['port']), self )
		else:
			self.transport = AsyncSocketClient( svSettings['addr'], int(svSettings['port']), self )

		self.redis = redis
		self.userID = userID
		self.irc = IRCClient( self.send, timerMgr, self )
		self.nickname = svSettings['nickname'].decode( 'utf-8' )
		self.realNickname = None
		self.servername = svSettings['name'].decode( 'utf-8' )
		self.username = svSettings['username'].decode( 'utf-8' )
		self.realname = svSettings['realname'].decode( 'utf-8' )
		self.channels = {}
		self.chSettings = chSettings
		self.isClosed = False
		self.lastReceiveAt = time.time()

	def isAlive( self ):
		# 일단 타임아웃 시간은 10분
		timeoutSecond = 10.0 * 60.0
		return ( not self.isClosed ) and ( time.time() - self.lastReceiveAt < timeoutSecond )

	def destroy( self ):
		self.transport.destroy( 'by application' )

	def getChannel( self, chanName ):
		assert( isinstance( chanName, unicode ) )
		ch = self.channels.get( chanName )
		if ch == None:
			ch = IRCChannel( self.redis, self.userID, self.servername, chanName )
			ch.markAsJoined( True )
			self.channels[ chanName ] = ch
		return ch

	def channelClosed( self, chanName ):
		assert( isinstance( chanName, unicode ) )
		ch = self.channels.get( chanName )
		if ch != None:
			ch.markAsJoined( False )
			self.channels.pop( chanName )

	def getSystemChannel( self ):
		return self.getChannel( u'!' )

	def onUserCommand( self, msg ):
		fname = 'cmd_' + str( msg[ 0 ] )
		if( not hasattr( self, fname ) ):
			print( 'unknown command' )
			return

		getattr( self, fname )( msg )

	def cmd_say( self, msg ):
		( server, chan, text ) = msg[ 2 ], msg[ 3 ], msg[ 4 ]
		self.irc.privmsg( chan, text )
		self.getChannel(chan).appendLog( [ int(time.time()), u'say', self.realNickname, text ] )

	def cmd_query( self, msg ):
		( server, target, text ) = msg[ 2 ], msg[ 3 ], msg[ 4 ]
		self.irc.privmsg( target, text )
		self.getChannel(target).appendLog( [ int(time.time()), u'say', self.realNickname, text ] )

	def cmd_join( self, msg ):
		self.irc.join( msg[ 3 ], msg[ 4 ] or u'' )

	def cmd_part( self, msg ):
		( chan, text ) = msg[ 3 ], msg[ 4 ]
		if chan[0] == u'#':
			self.irc.part( chan, text )
		else:
			self.channelClosed( chan )

	def cmd_nick( self, msg ):
		self.nickname = msg[ 3 ]
		self.irc.nick( msg[ 3 ] )

	def cmd_topic( self, msg ):
		self.irc.topic( msg[ 3 ], msg[ 4 ] )

	def cmd_update( self, msg ):
		self.lastUpdateAt = time.time()

	def cmd_kick( self, msg ):
		self.irc.kick( msg[ 3 ], msg[ 4 ], msg[ 5 ] or u'' )


	# for AsyncSSLClient ------------------------------------------------
	def onConnect( self, con ):
		print( '(onConnect/)' )
		self.irc.nick( self.nickname )
		self.irc.user( self.username, self.realname )

	def onReceive( self, con, data ):
		#print( '(onReceive)' + data + '(/onReceive)' )
		self.lastReceiveAt = time.time()
		try:
			self.irc.processData( data )
		except:
			traceback.print_exc()

	def onClose( self, con, why ):
		print( '(onClose/) ' + why )
		self.isClosed = True;


	# for IRCClient -----------------------------------------------------
	def send( self, data ):
		print( '(send)' + data + '(/send)' )
		self.transport.sendData( data )

	def on_default( self, irc, e ):
		assert( self.irc == irc )
		msg = u'%s: %s' % ( e.eventType, u', '.join( e.arguments ) )
		self.getSystemChannel().appendLog( [ int(time.time()), u'etc', msg ] )
		print( u'[DEFAULT]%s/%s/%s/%s' % ( e.eventType, e.source, e.target, e.arguments ) )

	def on_join( self, irc, e ):
		ch = e.target
		nick = nm_to_n( e.source )
		self.getChannel( ch ).addUser( nick, u'' )
		self.getChannel( ch ).appendLog( [ int(time.time()), u'join', e.source ] )
	
	def on_part( self, irc, e ):
		ch = e.target
		nick = nm_to_n( e.source )
		message = u''
		if len(e.arguments) > 0:
			message = e.arguments[ 0 ]
		self.getChannel( e.target ).removeUser( nick )
		self.getChannel( e.target ).appendLog( [ int(time.time()), u'part', e.source, message ] )
		if nick == self.realNickname: # me
			self.channelClosed( ch )

	def on_kick( self, irc, e ):
		ch = e.target
		kicker = nm_to_n( e.source )
		victim = nm_to_n( e.arguments[ 0 ] )
		message = u''
		if len(e.arguments) > 1:
			message = e.arguments[ 1 ]
		self.getChannel( e.target ).removeUser( victim )
		self.getChannel( e.target ).appendLog( [ int(time.time()), u'kick', kicker, victim, message ] )
		if victim == self.realNickname: # me
			self.channelClosed( ch )

	def on_quit( self, irc, e ):
		nick = nm_to_n( e.source )
		message = u''
		if len(e.arguments) > 0:
			message = e.arguments[ 0 ]

		for _, chan in self.channels.items():
			if chan.hasUser( nick ):
				chan.removeUser( nick )
				chan.appendLog( [ int(time.time()), u'quit', e.source, message ] )

	def on_ping( self, irc, e ):
		irc.pong( e.target )

	def on_welcome( self, irc, e ):
		print( '----REAL NICKNAME: ' + nm_to_n( e.target ) )
		self.realNickname = nm_to_n( e.target )
		for chName, chSetting in self.chSettings.items():
			if chSetting['autojoin'] == '1':
				key = chSetting['key'] or ''
				irc.join( chName.decode( 'utf-8' ), key.decode( 'utf-8' ) )

	def on_nick( self, irc, e ):
		oldNick = nm_to_n( e.source )
		newNick = nm_to_n( e.target )

		if self.realNickname == oldNick:
			self.realNickname = newNick

		for _, chan in self.channels.items():
			if chan.hasUser( oldNick ):
				chan.changeUserNick( oldNick, newNick )
				chan.appendLog( [ int(time.time()), u'nick', oldNick, newNick ] )

	def on_nicknameinuse( self, irc, e ):
		# realNickname이 있을 때는 이미 최초 닉네임 설정이 성공한 뒤다.
		# 그렇다면 유저가 요청한 닉네임 변경의 결과로 이 메세지가 왔을 것이고
		# 다른 닉으로 시도할 필요가 없이 에러 메세지만 보내면 된다.
		self.getSystemChannel().appendLog( [ int(time.time()), u'etc', u'%s: %s' % ( e.arguments[ 0 ], e.arguments[ 1 ] ) ] )
		if self.realNickname == None:
			self.irc.nick( e.arguments[ 0 ] + u'_' )

	def on_namreply( self, irc, e ):
		# e.arguments()[0] == "@" for secret channels,
		#                     "*" for private channels,
		#                     "=" for others (public channels)
		# e.arguments()[1] == channel
		# e.arguments()[2] == nick list

		ch = e.arguments[1]
		for nick in e.arguments[2].split():
			mode = u''
			if nick[0] == u"@":
				nick = nick[1:]
				mode = u'o'
			elif nick[0] == u"+":
				nick = nick[1:]
				mode = u'v'
			self.getChannel( ch ).addUser( nick, mode )

	def on_pubmsg( self, irc, e ):
		nick = nm_to_n( e.source )
		self.getChannel( e.target ).appendLog( [ int(time.time()), u'say', nick, e.arguments[ 0 ] ] )

	def on_privmsg( self, irc, e ):
		nick = nm_to_n( e.source )
		self.getChannel( nick ).appendLog( [ int(time.time()), u'say', nick, e.arguments[ 0 ] ] )
		pass

	def on_notopic( self, irc, e ):
		ch = e.arguments[ 0 ]
		self.getChannel( ch ).setTopic( u'' )

	def on_currenttopic( self, irc, e ): # 내가 조인할 때
		( ch, topic ) = ( e.arguments[ 0 ], e.arguments[ 1 ] )
		self.getChannel( ch ).setTopic( topic )
		self.getChannel( ch ).appendLog( [ int(time.time()), u'currenttopic', topic ] )

	def on_topic( self, irc, e ): # 새로 토픽이 설정될 때
		nick = nm_to_n( e.source )
		topic = e.arguments[ 0 ]
		self.getChannel( e.target ).setTopic( topic )
		self.getChannel( e.target ).appendLog( [ int(time.time()), u'topic', nick, topic ] )

	def on_topicinfo( self, irc, e ):
		( ch, who, when ) = ( e.arguments[ 0 ], e.arguments[ 1 ], e.arguments[ 2 ] )
		self.getChannel( ch ).appendLog( [ int(time.time()), u'topicinfo', who, when ] )


# test ------------------------------------------------------------------------
if __name__ == '__main__':
	import redisutil
	rpool = redisutil.ConnectionPool( host='localhost', port=6379, db=15, password='' )
	r = rpool.create()

	c = IRCChannel( r, u'testuser', u'testserver', u'testchannel' )
	r.delete( c.chanLogKey )
	c = IRCChannel( r, u'testuser', u'testserver', u'testchannel' )

	# add/remove/changenick user
	assert( not c.hasUser( u'someuser' ) )
	c.addUser( u'someuser', u'v' )
	assert( c.hasUser( u'someuser' ) )
	c.changeUserNick( u'someuser', u'someuser2' )
	assert( c.hasUser( u'someuser2' ) )
	assert( not c.hasUser( u'someuser' ) )
	c.removeUser( u'someuser2' )
	assert( not c.hasUser( u'someuser2' ) )

	# appendLog
	c.appendLog( [u'type', u'content1', u'content2'] )
	assert( c.logEndID == 1 )

	# addUser
	c.addUser( u'유저1', u'o' )
	c.addUser( u'유저2', u'v' )
	c.addUser( u'유저3', u'' )
	assert( encodeList( c.dumpUsers() ) == '1|유저1|유저2|유저3|' )