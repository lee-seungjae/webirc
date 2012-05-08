#!/usr/bin/env python
# -*- coding: utf-8 -*

# redis에 저장되거나 redis를 통하는 포맷:
# 각 문자열의 끝에 '|' 를 붙인다.
# 캐리지 리턴은 '\n' 으로, 문자열 내부에 등장하는 '|'는 '\:' 로, '\'는 '\\'로 이스케이핑한다. 

def _decodeSafely( x ):
	assert( type( x ) == type( '' ) )
	x = x.replace( '\\:', '|' ).replace( '\\n', '\n' ).replace( '\\\\', '\\' )

	try:
		return x.decode( 'utf-8' )
	except UnicodeDecodeError:
		x = x[:-1]
	
	while len( x ) > 0:
		try:
			return x.decode( 'utf-8' ) + u'?'
		except UnicodeDecodeError:
			x = x[:-1]

	return u'?'

def _encodeSafely( x ):
	if type( x ) == type( 0 ):
		return str( x )
	elif type( x ) == type( u'' ):
		return x.encode( 'utf-8' )
	assert( False )

def decodeList( text ):
	assert( type( text ) == type( '' ) );
	fields = text.split( '|' )
	ret = [ _decodeSafely( x ) for x in fields ]
	ret.pop()
	return ret

def encodeList( lst ):
	assert( type( lst ) == type( [] ) );
	lst = [ _encodeSafely( x ).replace( '\\', '\\\\' ).replace( '\n', '\\n' ).replace( '|', '\\:' ) for x in lst ]
	lst.append( '' )
	return '|'.join( lst )

# 테스트
if __name__ == '__main__':
	def assertSame( l, s ):
		assert( encodeList( l ) == s );
		assert( decodeList( s ) == l );

	assertSame( [], '' );
	assertSame( [u''], '|' );
	assertSame( [u'\n', u'|', u'\\'], '\\n|\\:|\\\\|' );
	assertSame( [u'\n|\\'], '\\n\\:\\\\|' );
	assertSame( [u'Hello', u'World'], 'Hello|World|' );
	assert( encodeList( [0] ) == '0|' )
	assert( decodeList( '0|' ) == [u'0'] )

	def encodeDecodeTest( a, b ):
		print decodeList( encodeList( a ) )[ 0 ]
		print b
		assert( decodeList( encodeList( a ) )[ 0 ] == b )

	assert( decodeList( '유텝팔|' ) == [ u'유텝팔' ] )
	assert( decodeList( '유텝팔'[:-1] + '|' ) == [ u'유텝?' ] )
	assert( decodeList( '유텝팔'[:-2] + '|' ) == [ u'유텝?' ] )
	assert( decodeList( '유텝팔'[:-3] + '|' ) == [ u'유텝' ] )
