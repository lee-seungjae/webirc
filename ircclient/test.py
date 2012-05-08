# -*- coding: utf-8 -*
# À¯Æ¼¿¡ÇÁÆÈ

from protocol import *
from redisutil import *

rpool = ConnectionPool( host='localhost', port=6379, db=15, password='' )
r = rpool.create()

def readSettings( id ):
	for svKey in r.keys( encodeList( [ u'server', id, u'*' ] ) ):
		svName = decodeList( svKey )[ 2 ]
		svSettings = r.hmget( svKey, [ u'addr', u'port', u'ssl', u'nickname' ] )
		print( svSettings[ 0 ] )
		print( svSettings[ 1 ] )
		print( svSettings[ 2 ] )
		print( svSettings[ 3 ] )

		for chKey in r.keys( encodeList( [ u'channel', id, svName, u'*' ] ) ):
			chName = decodeList( chKey )[ 3 ]
			chSettings = r.hmget( chKey, [ u'autojoin' ] )
			print( chSettings[ 0 ] )

		return # single server now


#readSettings( '735067610' )

for chKey in r.keys( encodeList( [ u'log', u'*' ] ) ):
	r.hdel( chKey, u'joined' )
