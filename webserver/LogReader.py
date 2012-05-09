#!/usr/bin/env python
# -*- coding: utf-8 -*-
# 유티에프팔

import protocol

# -----------------------------------------------------------------------------
INIT_LOG_LINES = 30
UPDATE_LOG_LINES = 5
OLD_LOG_LINES = 60

# -----------------------------------------------------------------------------
# 주의: 로그는 언제든지 지워질 수 있다는 점을 염두에 두자

# -----------------------------------------------------------------------------
def getLog(R, logKey, begin, end):
	# 가져올 게 없으면 아예 스킵
	if begin >= end:
		return []

	# redis 명령어 호출 횟수가 적은 편이 좋으므로, 가져올 ID를 먼저 리스트로 묶는다
	logIDs = [ str(i) for i in range(begin, end) ]

	# 로그를 가져와서 파싱한다
	ret = []
	rawLogs = R.hmget(logKey, logIDs)
	for logID, rawLog in zip(logIDs, rawLogs):
		if rawLog is not None:
			ret.append([int(logID)] + protocol.decodeList(rawLog))
	return ret

# -----------------------------------------------------------------------------
# for LOG_INIT. [디비끝-n, 디비끝)
def getRecentLog(R, logKey):
	#app.logger.debug('--------getRecentLog logKey: %s', logKey)
	
	[ begin, end ] = R.hmget(logKey, ['begin', 'end'])
	if (begin is None) or (end is None):
		return []

	readingEnd = int(end)
	readingBegin = max(int(begin), readingEnd - INIT_LOG_LINES)
	return getLog(R, logKey, readingBegin, readingEnd)

# -----------------------------------------------------------------------------
# for LOG_UPDATE. [아는끝, 디비끝)
def getLogAfter(R, logKey, knownLastID):
	#app.logger.debug('--------getLogAfter logKey: %s knownLastID: %s', logKey, knownLastID)

	[ begin, end ] = R.hmget(logKey, ['begin', 'end'])
	if (begin is None) or (end is None):
		return []

	readingBegin = max(int(begin), knownLastID)
	readingEnd = min(int(end), readingBegin + UPDATE_LOG_LINES)
	return getLog(R, logKey, readingBegin, readingEnd)


# -----------------------------------------------------------------------------
# for LOG_OLD, [아는처음-n, 아는처음)
def getLogBefore(R, logKey, knownFirstID):
	#app.logger.debug('--------getLogBefore logKey: %s knownFirstID: %d', logKey, knownFirstID)

	[ begin, end ] = R.hmget(logKey, ['begin', 'end'])
	if (begin is None) or (end is None):
		return []

	readingEnd = min(int(end), knownFirstID)
	readingBegin = max(int(begin), readingEnd - OLD_LOG_LINES)
	return getLog(R, logKey, readingBegin, readingEnd)


"""
import redis
R = redis.Redis()
R.select(2)
print getRecentLog(R, 'log|735067610|upnl|#berryz_dev|')
print getLogAfter(R, 'log|735067610|upnl|#berryz_dev|', 50)
print getLogBefore(R, 'log|735067610|upnl|#berryz_dev|', 100)
"""