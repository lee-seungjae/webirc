# -*- coding: utf-8 -*
# ��Ƽ������

import redis
import threading

#-----------------------------------------------------------------------------
# redis ����.
# ���� ���ϰ� �� �� �ֵ��� & Ŀ�ؼ� Ǯ��
class RedisEx( redis.Redis ):
	def __init__( self, host, port, db, password ):
		redis.Redis.__init__( self, host, port, db, password )
		self.busy = False
		self.pubSubPrefix = str( db ) + '/'

	# hash�� (key, value)�� ����Ʈ�� ���ϵǴµ� �̰��� ����� dict�� �ٷ�� ���� ���ϴ�.
	def hmgetAsDict( self, k, hkeys ):
		return dict( zip( hkeys, self.hmget( k, hkeys ) ) )

	# pub/sub�� DB�� �������� �ʴµ� �츮 �ý��ۿ����� ������ �ʿ��ϴ�;;
	# �׷��� 
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
# redis Ŀ�ؼ� Ǯ
class ConnectionPool:
	def __init__( self, host, port, db, password ):
		self.host = host
		self.port = port
		self.db = db
		self.password = password
		self.connections = []
		self.lock = threading.Lock()

		# ���� �׽�Ʈ
		with self.get() as rc:
			assert( rc.ping() )
		
	def get( self ):
		""" redis�� Ÿ�Ӿƿ����� ������� �� �־ ���� Ŀ�ؼ�Ǯ���� �����ϴ�.
			�̿� ���� ��ġ�� ���� ������ �Ź� �����ϵ��� �ص�.
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
# �׽�Ʈ

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