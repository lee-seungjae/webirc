/*
   log를 파싱해 div나 span 으로 쪼개주는 코드
*/

// log line 을 parsing 해서 반영하고 html을 리턴하는 함수들
var IDX_ID = 0
var IDX_DATE = 1
var IDX_TYPE = 2
var IDX_CONTENT = 3
function logTimeString(log) {
	// javascript 는 python 과 달리 epoch 단위가 milisecond 이다.
	return "<span class='logDate'>" + (new Date(log[IDX_DATE] * 1000)).toLocalHHMMString() + "</span>";
}


// logInfo : 처리할 log Entry와 Old log 여부, 바로 전 로그 정보 등등이 들어감
// chanInfo : 로그의 채널 정보
var logParser = new Object();
logParser.say = function (logInfo, chanInfo) {
	var log = logInfo.log;
	var latestLog = logInfo.latestLog;
	var hiddenClass = (latestLog.who === log[IDX_CONTENT+0] && latestLog.type === 'say')? ' hidden ': '';
	var ret = "<div class='say'>"
		+ "<span class='logWho" + hiddenClass + "'>"
		+ log[IDX_CONTENT+0] 
		+ "</span>"
		+ "<span class='logSay'>" + log[IDX_CONTENT+1] + "</span>"
		+ logTimeString(log)
		+ "</div>";
	return ret;
}

logParser.topic = function (logInfo, chanInfo) {
	var ret = "<div class='topiclog'>"
		+ "<span class='logText'>"
		+ logInfo.log[IDX_CONTENT]
		+ " changed topic to '"
		+ logInfo.log[IDX_CONTENT+1]
		+ "'</span>"
		+ logTimeString(logInfo.log)
		+ "</div>";

	if( !logInfo.isOldLog ) {
		chanInfo.topic = logInfo.log[IDX_CONTENT+1];
		// 현재 확인중인 채널이라면 토픽을 바꿔주자
		if( GetCurrentChannel() == chanInfo.name ) {
			RefreshChanInfo();
		}
	}
	return ret;
}

logParser.currenttopic = function (logInfo, chanInfo) {
	var ret = "<div class='currenttopic'>"
		+ "<span class='logText'>"
		+ "Current topic is '"
		+ logInfo.log[IDX_CONTENT]
		+ "'</span>"
		+ logTimeString(logInfo.log)
		+ "</div>";

	if( !logInfo.isOldLog ) {
		chanInfo.topic = logInfo.log[IDX_CONTENT];
		// 현재 확인중인 채널이라면 토픽을 바꿔주자
		if( GetCurrentChannel() == chanInfo.name ) {
			RefreshChanInfo();
		}
	}
	return ret;
}

logParser.topicinfo = function (logInfo, chanInfo) {
	var ret = "<div class='topicinfo'>"
		+ "<span class='logText'>"
		+ "Topic set by "
		+ logInfo.log[IDX_CONTENT]
		+ "(" + (new Date(logInfo.log[IDX_CONTENT+1] * 1000)).toLocaleString() + ")"
		+ "</span>"
		+ logTimeString(logInfo.log)
		+ "</div>"
		return ret;
}

logParser.etc = function (logInfo, chanInfo) {
	var ret = "<div class='etc'>"
		+ "<span class='logText'>" + logInfo.log.slice(IDX_CONTENT).join(" ") + "</span>"
		+ logTimeString(logInfo.log)
		+ "</div>";
	return ret;
}

logParser.join = function(logInfo, chanInfo) {
	var ret = "<div class='join'>"
		+ "<span class='logText'>"
		+ logInfo.log[IDX_CONTENT]
		+ " has joined " + chanInfo.name
		+ logTimeString(logInfo.log)
		+ "</div>";
	return ret;
}

logParser.quit = function(logInfo, chanInfo) {
	var ret = "<div class='quit'>"
		+ "<span class='logText'>"
		+ logInfo.log[IDX_CONTENT]
		+ " has quit " + chanInfo.name
		+ " (" + logInfo.log[IDX_CONTENT+1] + ")"
		+ logTimeString(logInfo.log)
		+ "</div>";
	return ret;
}

logParser.part = function(logInfo, chanInfo) {
	var ret = "<div class='part'>"
		+ "<span class='logText'>"
		+ logInfo.log[IDX_CONTENT]
		+ " has left " + chanInfo.name
		+ " (" + logInfo.log[IDX_CONTENT+1] + ")"
		+ logTimeString(logInfo.log)
		+ "</div>";
	return ret;
}

logParser.nick = function(logInfo, chanInfo) {
	var ret = "<div class='nick'>"
		+ "<span class='logText'>"
		+ logInfo.log[IDX_CONTENT]
		+ " is now known as " + logInfo.log[IDX_CONTENT+1]
		+ logTimeString(logInfo.log)
		+ "</div>";
	return ret;
}

logParser.__default__ = function (logInfo, chanInfo) {
	var ret = "<div>"
		+ "<span>" + logInfo.log[IDX_TYPE] + "</span>"
		+ "<span class='logText'>" + logInfo.log.slice(IDX_CONTENT).join(" ") + "</span>"
		+ logTimeString(logInfo.log)
		+ "</div>";
	return ret;
}

