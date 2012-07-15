#!/usr/bin/env python
# -*- coding: utf-8 -*-

from gevent import monkey
monkey.patch_all( socket=True, dns=True, time=True, select=True, thread=True, os=True, ssl=True, httplib=False, aggressive=True )

from datetime import datetime, timedelta
import threading
import sys
import json
import time
import getopt
import traceback

import protocol
import LogMetadata
import LogReader
import Session
from etc import *
from setting import *
import redisutil
import config

#------------------------------------------------------------------------------
rpool = redisutil.ConnectionPool( host=config.REDIS_ADDR, port=config.REDIS_PORT, db=config.REDIS_DB, password=config.REDIS_PASSWORD )

### 웹서버 ################################################################

# for debug
maxLogID = 10001
# for debug end

import flask
app = flask.Flask(__name__)

def getTopic( r, logKey ):
	topic = r.hget(logKey, 'topic')
	if topic:
		return protocol.decodeList( topic )[ 0 ]
	else:
		return u''

def getUsers( r, logKey ):
	users = r.hget(logKey, 'users')
	if users:
		return protocol.decodeList( users )
	else:
		return []

def xhrLogInit( uid, request ):
	knownChatIDs = LogMetadata.getLastChatIDs( uid )
	with rpool.get() as R:
		channels = []
		for ch in knownChatIDs.items():
			svName = ch[0][0]
			chName = ch[0][1]
			logKey = protocol.encodeList( [ u'log', uid, svName, chName ] )
			channels.append({
					'name': chName,
					'topic': getTopic(R, logKey),
					'server': svName,
					'log': LogReader.getRecentLog(R, logKey),
					'users': getUsers(R, logKey)
					})
	
	response = {
		'err': '',
		'channels': channels
	}

	app.logger.debug('-------init return:%s', str(response)) 
	return flask.jsonify(**response)

def xhrLogUpdate( uid, request ):
	with rpool.get() as R:
		R.publish( 'h2i', protocol.encodeList( [ u'cmd', u'update', uid ] ) )

	# 변화를 기다린다
	requestedChatIDs = {}
	for ch in request['channels']:
		chName = ch['name']
		svName = ch['server']
		lastID = int( ch['lastid'] )

		requestedChatIDs[ (svName, chName) ] = lastID

	app.logger.debug('---------WAITING%s', str(requestedChatIDs))
	knownChatIDs = LogMetadata.waitForChange( uid, requestedChatIDs )

	# 대기가 끝났으니 결과를 조립한다
	channels = []
	if knownChatIDs == None:
		app.logger.debug( '---------NO CHANGE' )
		for ch in request[u'channels']:
			channels.append({
				'name': ch[u'name'],
				'server': svName,
				'log': []
				})
	else:
		app.logger.debug( '---------CHANGED' )
		app.logger.debug( knownChatIDs )
		for ch in knownChatIDs.items():
			svName = ch[0][0]
			chName = ch[0][1]
			lastID = requestedChatIDs.get( (svName, chName) )

			with rpool.get() as R:
				logKey = protocol.encodeList( [ u'log', uid, svName, chName ] )
				if lastID is None:
					# 이전까지 몰랐는데 이제 알게 된 채널 (새 채널에 조인한 경우)
					# 처음 접속한 것과 마찬가지로 로그를 얻어온다
					log = LogReader.getRecentLog( R, logKey )
				else:
					# 이전에도 알고 있었고 이번에 갱신된 채널.
					beginID = int( lastID ) + 1
					log = LogReader.getLogAfter( R, logKey, beginID )

			channels.append({
				'name': chName,
				'server': svName,
				'log': log
				})

	response = {
		'err': '',
		'channels': channels
	}

	app.logger.debug( '---------RESPONSE: %s', str(response) )

	return flask.jsonify(**response)

def xhrLogOld( uid, request ):
	with rpool.get() as R:
		# TODO: 서버이름 요청에서 받아오기. 지금은 서버가 1개라 잘 동작한다.
		svKey = R.keys( protocol.encodeList( [ u'server', uid, u'*' ] ) )[ 0 ]
		svName = protocol.decodeList( svKey ) [ 2 ]
		chName = request['channel']
		lastID = int( request.get('lastid') or '0' )
		# TODO: 없는 채널에 대해 요청할 경우?, 더 이상 로그가 없을 경우?
		logKey = protocol.encodeList( [ u'log', uid, svName, chName ] )
		
		response = {
			'err': '',
			'channels': [
			{
				'name': chName,
				'server': svName,
				'log': LogReader.getLogBefore(R, logKey, lastID)
			}]
		}

		app.logger.debug( str(request['req']) )
		return flask.jsonify(**response)

def xhrConfigGet( uid, request ):
	u = UserSetting( rpool, uid )
	svNames = u.getAllServerName()
	svNames.sort()

	response = {
		'err': '',
		'servers': {} }

	for svName in svNames:
		s = u.getServerSetting( svName )
		response['servers'][svName] = s.exportToDict()

	return flask.jsonify(response);

def xhrConfigSetServer( uid, request ):
	u = UserSetting( rpool, uid )

	ss = ServerSetting( request['name'] );
	ss.importFromDict( request );
	u.setServerSetting( ss );

	response = { 'err': '' }
	return flask.jsonify(response);

def xhrCmd( uid, request ):
	def normalize(v):
		assert( isinstance( v, unicode ) )
		return v

	# irc command 의 alias 저장을 위한 테이블
	def parseCommand(channel, l):
		aliasTable = {
			u'j': u'join',
			u'wc': u'part',
			u'n': u'nick',
			u'k': u'kick'
		}
		cmdTable = {
			u'join': {'argCount': 3, 'currChannel': False},
			u'query': {'argCount': 2, 'currChannel': False},
			u'part': {'argCount': 1, 'currChannel': True},
			u'kick': {'argCount': 2, 'currChannel': True},
			u'nick': {'argCount': 1, 'currChannel': False},
			u'topic': {'argCount': 1, 'currChannel': True}
		}
		cmd = u'say'

		# 대화창을 통해 입력되었고 첫 문자가 /로 시작하면 명령으로 간주한다.
		if l[0] == u'/':
			cmd = l[1:].split()[0].lower()
			cmd = aliasTable.get(cmd, cmd)

		if cmd in cmdTable:
			cmdConf = cmdTable[cmd]
			arg = l.split(None, cmdConf['argCount'])[1:]
			# 갯수가 맞지 않으면 채운다.
			while len(arg) < cmdConf['argCount']:
				arg.append(u'')
			if cmdConf['currChannel']:
				arg = [channel] + arg
		else:
			# 테이블에 없는 경우는 say로 처리하자.
			# say 일 경우도 이쪽으로 넘어온다.
			# TODO : 없는 명령의 경우 그냥 에러로 처리하는 것이 나을까?
			cmd = u'say'
			arg = [channel, l]

		return cmd, arg

	app.logger.debug( str(request[u'req']) )
	cmd = normalize(request[u'cmd'].lower())
	server = normalize(request[u'server'])
	arg = [ normalize(a) for a in request.get(u'arg', [u'']) ]

	# 대화창을 통해 입력된 내용을 파싱한다.
	# say 의 인자는 1개만 온다고 가정한다.
	if cmd == u'say':
		( cmd, arg ) = parseCommand( request[u'channel'], arg[0] )

	msg = protocol.encodeList( [ u'cmd', cmd, uid, server ] + arg )

	with rpool.get() as R:
		R.publish( 'h2i', msg )
	
	response = { u'err': u'' }
	return flask.jsonify(**response)
	
def errorResponse(err):
	response = { u'err': err }
	return flask.jsonify(**response)

# 핸들러들 
@app.route('/')
def index():
	return flask.redirect(flask.url_for('static', filename='chat.html'))

# 로그인 처리
@app.route('/login', methods=['GET'])
def processLogin():
	fbInfo = json.loads(flask.request.values['fbInfo'])
	userID = fbInfo.get(u'userID')
	if userID == None:
		return errorResponse('no userID')
	
	with rpool.get() as R:
		sessionLifetime = 86400 * 14 # 2weeks
		(skey, secr) = Session.createSession(R, userID, sessionLifetime)
		response = {}
		ret = flask.jsonify(**response)
		ret.set_cookie(u'skey', skey, sessionLifetime)
		ret.set_cookie(u'secr', secr, sessionLifetime)
		return ret


# XMLHttpRequest 처리
@app.route('/xhr', methods=['GET'])
def processXHR():
	try:
		# handler Dictionary
		xhrHandlers = {
			'LOG_INIT':   xhrLogInit,
			'LOG_UPDATE': xhrLogUpdate,
			'LOG_OLD':    xhrLogOld,
			'CMD':        xhrCmd,
			'CONFIG_GET': xhrConfigGet,
			'CONFIG_SET_SERVER': xhrConfigSetServer,
			}

		# json으로 넘어온 request object 파싱
		if (flask.request.method != 'GET') or ('req' not in flask.request.values):
			abort(500)
			return
		print( flask.request.values['req'] )
		reqObject = json.loads(flask.request.values['req'])

		# cookie로부터 인증 정보를 수집
		#app.logger.debug(" cookie - %s", str(flask.request.cookies))
		userID = None
		print( flask.request.cookies )
		sessionKey = flask.request.cookies.get('skey')
		secret = flask.request.cookies.get('secr')
		if sessionKey is not None and secret is not None:
			with rpool.get() as R:
				userID = Session.checkSession(R, sessionKey, secret)

		# 인증 정보가 없으면 에러 응답
		if userID is None:
			response = { u'err': u'LOGIN_REQUIRED' }
			return flask.jsonify(**response)

		# 인증을 통과함. 정상 응답
		return xhrHandlers[ reqObject['req'] ] (userID, reqObject)
	except:
		traceback.print_exc()
	

# 명령행 실행
if __name__ == '__main__':
	# 명령행에서 포트를 인자로 받도록 함.
	#port = 8081
	#opts, args = getopt.getopt(sys.argv[1:], 'p:n:')
	#for o, a in opts:
	#	if o == '-p' and a.isdigit():
	#		port = int(a)
	#	if o == '-n' and a.isdigit():
	#		setRedisDB( int(a) )

	LogMetadata.init()
	LogMetadata.startNotificationListening()

	from gevent import pywsgi
	pywsgi.WSGIServer( ('', config.WEBSERVER_PORT), app, keyfile='../ssl/new.key', certfile='../ssl/new.cert').serve_forever()
