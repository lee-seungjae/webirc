# -*- coding: utf-8 -*
# 유티에프팔

import redis
import threading

#-----------------------------------------------------------------------------
# redis 래퍼.
# 좀더 편하게 쓸 수 있도록 & 커넥션 풀링
class RedisEx( redis.Redis ):
	def __init__( self, host, port, db, password ):
		redis.Redis.__init__( self, host, port, db, password )
		self.busy = False
		self.pubSubPrefix = str( db ) + '/'

	# hash가 (key, value)의 리스트로 리턴되는데 이것은 개념상 dict로 다루는 것이 편하다.
	def hmgetAsDict( self, k, hkeys ):
		return dict( zip( hkeys, self.hmget( k, hkeys ) ) )

	# pub/sub은 DB를 구분하지 않는데 우리 시스템에서는 구분이 필요하다;;
	# 그래서 
	def publish( self, ch, text ):
		return redis.Redis.publish( self, self.pubSubPrefix + ch, text )

	def subscribe( self, ch ):
		return redis.Redis.subscribe( self, self.pubSubPrefix + ch )

	# with connectionPool.get() as r:
	def __enter__( self ):
		self.busy = True
		return self

	# with connectionPool.get() as r:
	def __exit__( self, type, value, traceback ):
		self.busy = False

#-----------------------------------------------------------------------------
# redis 커넥션 풀
class ConnectionPool:
	def __init__( self, host, port, db, password ):
		self.host = host
		self.port = port
		self.db = db
		self.password = password
		self.connections = []
		self.lock = threading.Lock()

		# 접속 테스트
		with self.get() as rc:
			assert( rc.ping() )
		
	def get( self ):
		""" redis가 타임아웃으로 끊어버릴 수 있어서 아직 커넥션풀링은 위험하다.
			이에 대한 조치를 취할 때까지 매번 생성하도록 해둠.
		with self.lock:
			for c in self.connections:
				if not c.busy:
					return c

			r = RedisEx( self.host, self.port, self.db )
			self.connections.append( r )
			print 'redis connection #' + str(len(self.connections)) + ' created.'
			return r
		"""
		return RedisEx( self.host, self.port, self.db, self.password )

	def create( self ):
		return RedisEx( self.host, self.port, self.db, self.password )

#-----------------------------------------------------------------------------
# 테스트

if __name__ == '__main__':
	rpool = ConnectionPool( host='localhost', port=6379, db=15, password='' )

	"""
	with rpool.get() as r:
		assert( len(rpool.connections) == 1 )
	
	with rpool.get() as r:
		assert( len(rpool.connections) == 1 )
		with rpool.get() as r2:
			assert( len(rpool.connections) == 2 )
			pass
	"""