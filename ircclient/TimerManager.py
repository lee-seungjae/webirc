# -*- coding: utf-8 -*

import heapq
import time
import traceback

class TimerManager:
	def __init__( self ):
		self.waiting = []
		self.counter = 0

	def setTimeout( self, func, delay ):
		expires = time.time() + delay
		heapq.heappush( self.waiting, ( expires, self.counter, func ) )
		self.counter += 1
	
	def update( self ):
		now = time.time()
		while len( self.waiting ) > 0:
			top = self.waiting[ 0 ]
			if top[ 0 ] > now:
				break

			heapq.heappop( self.waiting )
			try:
				top[ 2 ]()
			except Exception:
				traceback.print_exc()

# 테스트
if __name__ == '__main__':
	def test( x ):
		print( x )

	def crash( x ):
		return 1 / 0

	mgr = TimerManager();
	mgr.setTimeout( lambda: crash('0'), 0.0 )
	mgr.setTimeout( lambda: test('3'), 0.03 )
	mgr.setTimeout( lambda: test('2'), 0.02 )
	mgr.setTimeout( lambda: test('1'), 0.01 )
	mgr.setTimeout( lambda: test('0a'), 0.0 )
	mgr.setTimeout( lambda: test('0b'), 0.0 )
	mgr.setTimeout( lambda: test('0c'), 0.0 )

	mgr.update()
	print( '-' )
	time.sleep( 0.1 )
	mgr.update()

