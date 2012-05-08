# -*- coding: utf-8 -*
import traceback
import asyncore
import socket

# 소켓에 바로 붙어서 패킷 처리를 담당함.
class PacketProcessor( asyncore.dispatcher ):

	def __init__( self, sock, onReceive, onClose ):
		asyncore.dispatcher.__init__( self, sock )
		self.readBuffer = ''
		self.sendBuffer = ''
		self.onReceive = onReceive
		self.onClose = onClose

	# from asyncore.dispatcher {
	def handle_close( self ):
		self.doClose( 'connection closed' )

	def handle_read( self ):
		newData = self.recv( 8192 )
		self.readBuffer += newData

		begin = 0
		delimPos = self.readBuffer.find( '\n' )
		while delimPos >= 0:
			fields = self.readBuffer[ begin:delimPos ].split( '\t' )
			fields = [ x.replace( '\\n', '\n' ).replace( '\\t', '\t' ).replace( '\r', '' ) for x in fields ]
			self.onReceive( self, fields )
			begin = delimPos + 1
			delimPos = self.readBuffer.find( '\n', begin )

		self.readBuffer = self.readBuffer[ begin: ]
		if len( self.readBuffer ) > 8192:
			self.doClose( 'recv buffer overflow' )
		
	def handle_write( self ):
		sent = self.send( self.sendBuffer )
		if sent == len( self.sendBuffer ):
			self.sendBuffer = ''
		else:
			self.doClose( 'send buffer overflow' )

	def writable( self ):
		return len( self.sendBuffer ) > 0
	# from asyncore.dispatcher }

	def sendPacket( self, fields ):
		fields = [ x.replace( '\n', '\\n' ).replace( '\t', '\\t' ) for x in fields ]
		self.sendBuffer += '\t'.join( fields ) + '\n'

	def doClose( self, why ):
		print( why )
		self.close()
		self.onClose( self )


# 바이트 스트림이 PacketProcessor 통해서 올라오면 그에 맞춰 적절한 동작을 취함.
allConns = set()
class WebConnection:
	def __init__( self, sock ):
		self.packetProc = PacketProcessor( sock, self.onReceive, self.onClose )
		allConns.add( self )

	def onClose( self, pp ):
		allConns.remove( self )

	def onReceive( self, pp, fields ):
		try:
			print( 'onReceive' + str( fields ) )
			#conn.sendPacket( ['RECEIVED'] + fields )
			attrName = 'on_' + fields[ 0 ]
			if hasattr( self, attrName ):
				getattr( self, attrName )( *fields[1:] )
			else:
				raise Exception( 'unknown command' )

		except Exception, e:
			traceback.print_exc()
			#self.packetProc.doClose( sys.exc_info()[0] )

	# PACKET HANDLER: login
	def on_login( self, userID ):
		print( 'login as ' + userID )
		pass

# acceptor.
class WebConnectionAcceptor( asyncore.dispatcher ):

	def __init__( self, host, port ):
		asyncore.dispatcher.__init__( self )
		self.create_socket( socket.AF_INET, socket.SOCK_STREAM )
		self.set_reuse_addr()
		self.bind( (host, port) )
		self.listen( 5 )

	def handle_accept( self ):
		pair = self.accept()
		if pair is None:
			pass
		else:
			sock, addr = pair
			print 'Incoming connection from %s' % repr(addr)
			WebConnection( sock )

server = WebConnectionAcceptor( '', 8080 ) # '' 대신 'localhost' 쓰면 로컬에서의 접속만 받는다
asyncore.loop()

