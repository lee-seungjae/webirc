#!/usr/bin/env python
# -*- coding: utf-8 -*-
# 유티에프팔

# 세션키 := md5따위( 유저아이덴티티 + 랜덤소금 )
# 시크릿 := md5따위( 랜덤소금 )
# DB 저장 포맷: ['session', 세션키, 시크릿] = [유저아이덴티티]

import hashlib
import random
import base64

import protocol

# -----------------------------------------------------------------------------
# 신원 확인된 유저에 대해 세션을 생성
def createSession( R, userIdentity, expireSeconds ): # -> (sessionKey, secret)
	assert( type(userIdentity) == unicode );

	ret = None
	while ret is None:
		m = hashlib.md5()
		m.update(str(random.getrandbits(64)))
		secret = unicode(base64.b64encode(m.digest()))

		m.update(userIdentity)
		sessionKey = unicode(base64.b64encode(m.digest()))

		dbKey = protocol.encodeList( [u'session', sessionKey, secret] )
		encodedUID = protocol.encodeList( [userIdentity] );

		if R.setnx(dbKey, encodedUID) == 1:
			R.expire(dbKey, expireSeconds)
			ret = (sessionKey, secret)
		else:
			# 재수없게 세션 키 충돌이 났다. 정말 재수없게....
			# while의 시작으로 돌아가서 다시 시도
			pass

	return ret

# -----------------------------------------------------------------------------
# 유저가 주장한 세션키와 시크릿이 멀쩡한 세션을 나타내는지 확인
def checkSession( R, sessionKey, secret ): # -> userIdentity | None
	dbKey = protocol.encodeList( [u'session', sessionKey, secret] )
	dbData = R.get(dbKey)
	if dbData is None:
		return None
	else:
		return protocol.decodeList(dbData)[0]


# 명령행 실행: 테스트
if __name__ == '__main__':
	import redis
	R = redis.Redis()

	# 세션 발급
	(skey, secr) = createSession( R, u'15', 1 )

	# 멀쩡한 세션
	assert( checkSession( R, skey, secr ) == u'15' )

	# 안 멀쩡한 세션
	assert( checkSession( R, skey, u'1' ) == None )

	# 시간 지나서 세션 파기됨
	import time
	time.sleep(2)
	assert( checkSession( R, skey, secr ) == None )


