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

def getLogList( r, logKey, begin=None, end=None, maxLogLine=30 ):
	app.logger.debug('--------getLogList logKey: %s begin:%s end:%s', logKey, begin, end)
	
	logs = []

	# 로그 가져올 ID 범위 계산
	idRange = [ int(i) for i in r.hmget(logKey, ['begin', 'end']) ]
	if begin is not None and begin > idRange[0]:
		idRange[0] = begin
	if end is not None and end < idRange[1]:
		idRange[1] = end

	logIds = [ str(i) for i in range(*idRange) ][-maxLogLine:]

	# 가져올 로그가 없으면 빈 리스트를 반환한다.
	if len(logIds) == 0:
		return logs

	# 로그 가져와 파싱
	for lid, rawLog in zip(logIds, r.hmget(logKey, logIds)):
		l = [int(lid)] + protocol.decodeList( rawLog )
		logs.append(l)

	return logs

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
					'log': getLogList(R, logKey),
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
			if lastID <> None:
				beginID = int( lastID ) + 1
			else:
				beginID = None
			endID = ch[1] + 1

			log = None
			if beginID == endID:
				log = []
			else:
				logKey = protocol.encodeList( [ u'log', uid, svName, chName ] )
				with rpool.get() as R:
					log = getLogList( R, logKey, beginID, endID )

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
				'log': getLogList(R, logKey, end=lastID)
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
	
# 핸들러들 
@app.route('/')
def index():
	return flask.redirect(flask.url_for('static', filename='chat.html'))

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
		if( (flask.request.method != 'GET') or
			('req' not in flask.request.values) or
			('fbInfo' not in flask.request.values) ):
			abort(500)
			return
		print( flask.request.values['req'] )
		reqObject = json.loads(flask.request.values['req'])
		fbInfo = json.loads(flask.request.values['fbInfo'])

		# cookie 출력
		app.logger.debug(" cookie - %s", str(flask.request.cookies))

		# fbInfo 출력
		app.logger.debug(" fbInfo - %s", str(fbInfo))

		uid = fbInfo[ u'userID' ]

		return xhrHandlers[ reqObject['req'] ] (uid, reqObject)
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
