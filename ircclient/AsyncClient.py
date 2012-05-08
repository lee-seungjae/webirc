# -*- coding: utf-8 -*

import asyncore
import socket
import ssl

# AsyncSSLClient와 ASyncSocketClient의 공통 부분
class AsyncClient( asyncore.dispatcher ):
	def __init__( self, addr, port, handler ):
		asyncore.dispatcher.__init__( self )
		self.create_socket( socket.AF_INET, socket.SOCK_STREAM )

		self.handler = handler
		self.buffer = ''
		self.closed = False
		self.connect( ( addr, port ) )

		assert( handler.onReceive )
		assert( handler.onConnect )
		assert( handler.onClose )

	def writable_check_buffer( self ):
		return len( self.buffer ) > 0

	def writable_true( self ):
		return True
	
	def writable_false( self ):
		return False

	def handle_close( self ):
		self.destroy( 'handle_close' )

	def destroy( self, why ):
		if not self.closed:
			self.handler.onClose( self, why )
			self.closed = True
			self.close()

	def sendData( self, data ):
		#print( '[SEND]' + data )
		assert( isinstance( data, str ) )
		self.buffer += data


# 일반 소켓을 쓰는 Asyncore client
class AsyncSocketClient( AsyncClient ):
	def __init__( self, addr, port, handler ):
		AsyncClient.__init__( self, addr, port, handler )

	def handle_connect( self ):
		self.writable = self.writable_check_buffer
		self.handler.onConnect( self )

	def handle_read( self ):
		newData = self.recv( 4096 )
		#print( '[[SOCKET:' + newData + ']]' )
		self.handler.onReceive( self, newData )

	def handle_write( self ):
		sent = self.send( self.buffer )
		self.buffer = self.buffer[ sent: ]


# SSL을 쓰는 Asyncore client
class AsyncSSLClient( AsyncClient ):
	def __init__( self, addr, port, handler ):
		AsyncClient.__init__( self, addr, port, handler )

	def handle_connect( self ):
		self.ssl = ssl.wrap_socket( self, None, None, False, ssl.CERT_NONE, ssl.PROTOCOL_SSLv23, None, False, False )
		self.writable = self.writable_true
		self.handle_write = self.handle_ssl_handshake
		self.handle_read = self.handle_ssl_handshake

	def handle_ssl_handshake( self ):
		#print( self.ssl )
		try:
			self.ssl.do_handshake()

			print( 'handshake OK' )
			self.writable = self.writable_check_buffer
			self.handle_read = self.handle_read_ssl
			self.handle_write = self.handle_write_ssl
			self.handler.onConnect( self )

		except ssl.SSLError, err:
			if err.args[ 0 ] == ssl.SSL_ERROR_WANT_READ:
				self.writable = self.writable_false
			elif err.args[ 0 ] == ssl.SSL_ERROR_WANT_WRITE:
				self.writable = self.writable_true
			else:
				destroy( self, 'SSL handshake error' )

	def handle_read_ssl( self ):
		try:
			newData = self.ssl.read( 4096 )
			print( '[[SSL:' + newData + ']]' )
			if len( newData ) > 0:
				self.handler.onReceive( self, newData )
			else:
				self.destroy( 'received zero bytes' )

		except ssl.SSLError, err:
			if err.args[ 0 ] == ssl.SSL_ERROR_WANT_READ:
				pass
			elif err.args[ 0 ] == ssl.SSL_ERROR_WANT_WRITE:
				pass
			else:
				self.destroy( 'SSL error' );

	def handle_write_ssl( self ):
		sent = self.ssl.write( self.buffer )
		self.buffer = self.buffer[ sent: ]


# 테스트
if __name__ == '__main__':
	class TestHandler:
		def onConnect( self, con ):
			print( '(onConnect) ' )
			con.sendData( 'HTTP 1.0 GET /\r\n\r\n\r\n' )

		def onReceive( self, con, data ):
			print( '(onReceive) ' + data );

		def onClose( self, con, why ):
			print( '(onClose) ' + why );

	for i in xrange( 1, 3 ):
		c2 = AsyncSSLClient( 'twitter.com', 443, TestHandler() )
		c1 = AsyncSocketClient( 'twitter.com', 80, TestHandler() )

	asyncore.loop()
