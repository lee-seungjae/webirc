# -*- coding: utf-8 -*-
# 유텝팔

import protocol
import redisutil

#------------------------------------------------------------------------------
"""
사용 시나리오:
 * 유저의 전체 서버 목록 조회
 * 유저의 서버 하나를 통째로 변경
 * 유저의 채널을 삭제
 * 유저의 서버를 삭제

웹서버에서 서버 설정을 바꾸면 대몬은 어떻게 반응해야 하는가:
 * 서버 정보 변경 통지가 날아왔다 -> 한 서버를 다시 읽는다
 * 채널 정보 변경 통지가 날아왔을 때 -> ... 이건 join으로 오겠지?
"""

#------------------------------------------------------------------------------
# 유저의 서버별 설정.
class ServerSetting:
	def __init__( self, name ):
		self.name = name
		self.channels = {}

	def importFromDict( self, optDict ):
		self.addr = optDict[u'addr']
		self.port = optDict[u'port']
		self.ssl  = optDict[u'ssl']
		self.nickname = optDict[u'nickname']
		self.username = optDict[u'username']
		self.realname = optDict[u'realname']

	def exportToDict( self ):
		return {
			u'addr':     self.addr,
			u'port':     self.port,
			u'ssl':      self.ssl,
			u'username': self.nickname,
			u'nickname': self.username,
			u'realname': self.realname }


#------------------------------------------------------------------------------
# 유저별 설정.
# 설정의 읽기/저장을 책임진다.
class UserSetting:
	def __init__( self, rpool, uid ):
		self.uid = uid
		self.rpool = rpool

	def dump( self ):
		pass

	def setServerSetting( self, svSetting ):
		svKey = protocol.encodeList( [ u'server', self.uid, svSetting.name ] )
		opt = svSetting.exportToDict()

		with self.rpool.get() as R:
			R.hmset( svKey, opt )

	# 채널별 세팅만을 저장 (기존에 없었으면 추가)
	def setChannelSetting( self, svName, chName, chOptionDict ):
		with self.rpool.get() as R:
			chKey = protocol.encodeList( [ u'channel', self.uid, svName, chName ] )
			R.hmset( chKey, chOptionDict )

	# 서버이름 → 서버 키로 변환
	def getServerKeyFromName( self, name ):
		return protocol.encodeList( [u'server', self.uid, name] );

	# 서버 키 → 서버이름으로 변환
	def getServerNameFromKey( self, key ):
		return protocol.decodeList(key)[ 2 ];

	# 모든 서버 키 얻기 (아마 직접 쓸 일이 없을 듯)
	def getAllServerKey( self ):
		with self.rpool.get() as R:
			keyPattern = self.getServerKeyFromName( u'*' )
			return R.keys( keyPattern )

	# 모든 서버 이름 얻기
	def getAllServerName( self ):
		keys = self.getAllServerKey()
		return [ self.getServerNameFromKey(k) for k in keys ]

	# 서버 설정 가져오기. 없으면 None
	def getServerSetting( self, svName ):
		svKey = self.getServerKeyFromName( svName )
		with self.rpool.get() as R:
			if not R.exists( svKey ):
				return None

			retval = ServerSetting( svName )

			# 서버별 설정
			opt = R.hmgetAsDict( svKey, [ u'nickname', u'username', u'realname', u'addr', u'port', u'ssl' ] )
			retval.importFromDict( opt )

			# 그 서버의 채널별 설정
			channels = {}
			keyPattern = protocol.encodeList( [ u'channel', self.uid, svName, u'*' ] )
			for chKey in R.keys( keyPattern ):
				chName = protocol.decodeList( chKey )[ 3 ]
				chSettings = R.hmgetAsDict( chKey, [ u'autojoin', u'key' ] )
				channels[ chName ] = chSettings

			retval.channels = channels

			return retval

	# 서버와 그에 딸린 채널들을 모두 삭제
	#def removeServer( self, svName ):
	#	pass

	#def removeChannel( self, svName, chName ):
	#	pass




#------------------------------------------------------------------------------
def _test():
	# 테스트 전용 디비. 테스트 수행할 때마다 데이터베이스 날리고 새로 생성하므로 서비스하는 DB 건드리지 않도록 주의할 것
	TEST_REDIS_DB = 15
	rp = redisutil.ConnectionPool( host='localhost', port=6379, db=TEST_REDIS_DB )

	with rp.get() as R:
		R.flushdb() # 데이터베이스 전체 날려버리는 명령어임. 사용에 극도로 주의할 것

		#----------------------------------------------------------------------
		# 쓰기 테스트
		tu = UserSetting( rp, u'UID' )

		s1 = ServerSetting( u'SERVERa' )
		s1.addr = u'a1'
		s1.port = u'p1'
		s1.ssl = u's1'
		s1.nickname = u'n1'
		s1.realname = u'n1'
		s1.username = u'n1'
		tu.setServerSetting( s1 )

		s2 = ServerSetting( u'SERVERb' )
		s2.addr = u'a2'
		s2.port = u'p2'
		s2.ssl = u's2'
		s2.nickname = u'n2'
		s2.realname = u'n2'
		s2.username = u'n2'
		tu.setServerSetting( s2 )

		s3 = ServerSetting( u'SERVERc' )
		s3.addr = u'a3'
		s3.port = u'p3'
		s3.ssl = u's3'
		s3.nickname = u'n3'
		s3.realname = u'n3'
		s3.username = u'n3'
		tu.setServerSetting( s3 )

		tu.setChannelSetting( u'SERVERa', u'#CHANNEL1', {u'autojoin': u'1'} )
		tu.setChannelSetting( u'SERVERa', u'#CHANNEL2', {u'autojoin': u'1'} )
		tu.setChannelSetting( u'SERVERa', u'#CHANNEL3', {u'autojoin': u'1'} )

		#----------------------------------------------------------------------
		# 읽기 테스트
		
		# 모든 서버 목록
		svNames = tu.getAllServerName()
		svNames.sort()
		assert( svNames == [u'SERVERa', u'SERVERb', u'SERVERc'] )

		tu = UserSetting( rp, u'UID' )

		# 없는 서버
		assert( tu.getServerSetting( u'SERVERx' ) == None )

		# 있는 서버
		a = tu.getServerSetting( u'SERVERa' )
		assert( a.name == u'SERVERa' )
		assert( a.addr == u'a1' )
		assert( a.port == u'p1' )
		assert( a.ssl == u's1' )
		assert( a.nickname == u'n1' )
		assert( a.realname == u'n1' )
		assert( a.username == u'n1' )

		# 채널별
		assert( a.channels[u'#CHANNEL1'][u'autojoin'] == u'1' )
		assert( a.channels.get(u'#CHANNELx') == None )

if __name__ == '__main__':
	_test()