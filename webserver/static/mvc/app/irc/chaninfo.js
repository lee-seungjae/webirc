/* 
   채널 정보를 관리하기 위한 코드들을 모아둠
*/

var chanDict = {}; // 현재 들어가 있는 채널 정보(key: id)
var chanNameMap = {}; // 채널 이름으로 채널 id 를 얻어내는 Map(key:channel@server)

// 서버와 채널 이름으로 채널 정보를 얻어온다.
function GetChannelInfo(server, channel) {
	var infoID = chanNameMap[channel+"@"+server];
	if( infoID !== undefined )
		return chanDict[infoID];
	else
		return undefined;
}

// 현재 대화중인 채널 정보를 얻어온다.
function GetCurrentChannelInfo() {
	var current = Ext.getCmp("mainCarousel").getActiveItem();
	return GetChanInfoByStoreID(current.config.store); // store id 형태 : store_ID
}

// 현재 대화중인 채널 이름을 얻어온다.
function GetCurrentChannel() {
	return GetCurrentChannelInfo().name;
}

// 현재 대화중인 서버 이름을 얻어온다.
function GetCurrentServer() {
	return GetCurrentChannelInfo().server;
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
function ChannelInfo(id, name, topic, users, server) 
{
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
	this.storeID = "store_" + id;
	this.listID = "list_" + id;
}

// 새 채널 정보를 등록한다.
function AddChannel(name, topic, users, server)
{
	var newID = Ext.id(null, '_');
	var newChannel = new ChannelInfo( newID, name, topic, users, server );
	chanDict[newID] = newChannel;
	chanNameMap[name+"@"+server] = newID;
	return newChannel;
}

// 채널 정보를 Store로부터 구한다
function GetChanInfoByStoreID(storeID)
{
	return chanDict[storeID.substr(6)]; // store id 형태 : store_ID
}
