/* 
   채널 정보를 관리하기 위한 코드들을 모아둠
*/

var chanDict = {}; // 현재 들어가 있는 채널 정보(key: 채널명)
var chanIDMap = {}; // id로부터 채널 이름을 얻어내기 위한 테이블
var nextChanID = 0; // 다음 채널 ID로 할당할 숫자

// 현재 대화중인 채널 이름을 얻어온다.
function GetCurrentChannel() {
	return $(".channelNavBar:first>a.ui-btn-active:first").text();
}


// 현재 대화중인 서버 이름을 얻어온다.
// TODO : 서버 정보 얻어오기
function GetCurrentServer() {
	return 'upnl';
}

// channel user 객체
function ChannelUser(username) {
	this.name = '';
	this.op = false;
	this.voice = false;
	if( username ) {
		switch( username.charAt(0) ) {
			case '@':
				this.op = true;
				this.name = username.substr(1);
				break;

			case '+':
				this.voice = true;
				this.name = username.substr(1);
				break;

			default:
				this.name = username;
				break;
		}
	}
}

// channel info 객체
function ChannelInfo(id, name, topic, users, server) {
	this.id = id;
	this.name = name;
	this.server = server;
	this.topic = topic? topic: '';
	this.users = [];
	if( users ) {
		for( var i = 0; i < users.length; ++i ) {
			this.users.push(new ChannelUser(users[i]));
		}
	}
	this.oldestLogID = undefined;
	this.newestLogID = undefined;
}
