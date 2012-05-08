Ext.Loader.setConfig({enabled:true});

Ext.require([
    'Ext.form.Panel',
    'Ext.data.Store',
    'Ext.List',
    'Ext.Panel',
    'Ext.Carousel',
    'Ext.plugin.PullRefresh'
    ]);

Ext.define('Log.Model', {
  extend: 'Ext.data.Model',
  fields: ['logid', 'date', 'who','type','text'],
  load: function() { console.log("load!!!"); }
});
var carousel = null;
var fbInfo = undefined;

/*
function ShowOldLog(response, request) 
{
    console.log("oldLog!");
    console.log(response);
    var channels = response.channels;
    for( var i = 0; i < channels.length; ++i ) 
    {
        var currChan = channels[i];
        // 얘기한 적이 없는 채널에 대해 LOG_OLD를 요청했을리 없다. 무시하자
        var currChanInfo = GetChannelInfo(currChan.server, currChan.name);
        if( currChanInfo === undefined ) 
        {
            continue;
        }

        var logStore = Ext.data.StoreManager.lookup(currChanInfo.storeID);

        // 로그를 행 별로 분석한다.
        var currLogInfo = {};
        for( var j = 0; j < currChan.log.length; ++j ) {
            currLogInfo.item = ParseLog(currChan.log[j], currLogInfo, currChanInfo);

            // 교집합이 있을 경우 처리. 가끔 같은 로그가 2번 들어와 있는 경우가 있다.
            if( !currLogInfo.latestLog || 
                (currLogInfo.latestLog.logid !== undefined 
                && currLogInfo.latestLog.logid < currLogInfo.item.logid 
                && currLogInfo.item.logid < currChanInfo.oldestLogID ) )
            {
                logStore.add(currLogInfo.item);

                // 마지막 로그 정보를 현재 로그로 업데이트한다
                currLogInfo.latestLog = currLogInfo.item;
            }
            else {
                console.log("duplicated log");
                console.log(currLogInfo);
            }
        }

        // 변경 로그가 없으면 다음 채널을 처리하자
        if( currChan.log.length == 0 ) {
            continue;
        }

        Ext.getCmp(currChanInfo.listID).refresh();

        // log id 정보 업데이트
        currChanInfo.oldestLogID = logStore.first().raw.logid;
        currChanInfo.newestLogID = logStore.last().raw.logid;
    }
}

var refreshplugin = 
{
    type: 'pullrefresh',
    refreshFn: function(plugin) {
        var currChanInfo = GetChanInfoByStoreID(plugin._list.config.store);
        var request = { 
            'req': 'LOG_OLD', 
            'channel': currChanInfo.name, 
            'server': currChanInfo.server, 
            'lastid': currChanInfo.oldestLogID 
        };
        RemoteRequest(request,
        ShowOldLog,
        function(response, opts) {
        // TODO: LOG_OLD 는 실패하면 정책을 어떻게 할 것인가.
        }
        ,
        20000);
    }
};
*/

// 서버에 XHR을 보낸다
// request : 요청으로 보낼 객체(JSON.stringify 할 객체)
// successCallback : 요청이 성공했을 때 불릴 Callback.
//                   function(response, textStatus, jqXHR)
// errorCallback : 요청이 실패했을 때 불릴 Callback.
//                 function(jqXHR, textStatus, errorThrown)
// timemout : 타임아웃 시간(milliseconds)
// TODO : 인터페이스 바꿀 필요가 있을 지도? Object 하나만 받도록.
function RemoteRequest(request, successCallback, errorCallback, timeout) {
    return Ext.Ajax.request({
        url: '/xhr',
        method: 'GET',
        params: { 'req': Ext.JSON.encode(request), 'fbInfo': Ext.JSON.encode(fbInfo) },
        success:function(result, request) {
            var r = Ext.JSON.decode(result.responseText, true);
            if( r !== null )
                return successCallback(r, request);
            else
                return errorCallback(result, request);
        },
        failure: errorCallback,
        timeout: timeout
    });
}

// channel 정보를 다시 그린다.
function RefreshChanInfo()
{
}

// chat line 에서 보낼 때
function Say() {
    request = {
    req: 'CMD',
     cmd: 'say',
     server: GetCurrentServer(), 
     channel: GetCurrentChannel(),
     arg: [Ext.getCmp("chatbox").getValue()]
    };

    // 서버로 ajax 요청
    RemoteRequest(request,
            function(response, request) {
                if( response['err'] ) { 
                    // TODO: XHR 단의 에러와 프로토콜단의 err를 통합해서 하나로 묶을까 -_-;
                    alert('say error ' + response['err']);
                }
                Ext.getCmp("chatbox").setValue('');
            },
            function(response, opt) {
                console.log(response);
                console.log(opt);
                alert("say error " + errorThrown);
            },
            30000
            );
    return false;
}
// 새 채널 정보를 표시할 element를 만든다.
function CreateChannelElement(chanInfo) {
    var storeID = chanInfo.storeID;
    console.log("create channelinfo " + chanInfo.name + "( "+ chanInfo.id +" )");
    var store = Ext.create('Ext.data.Store', {
                id: storeID,
                model: 'Log.Model',
                sorters: 'logid',
                autoLoad: false
            });
    console.log(store);

    Ext.getCmp("mainCarousel").add([
        {
            xtype: 'list',
            id: chanInfo.listID,
            itemTpl: '{text}',
            mode: 'SINGLE',
            allowDeselect: false,
            disclosure: false,
            flex: 1,
            store: storeID,
            plugins: refreshplugin,
            scrollable: 
            { 
                direction: 'vertical',
                directionLock: true
            }
        }]);
}

// 로그 업데이트를 반영한다
// 해당 채널이 없으면 새 carousel을 만든다.
function ApplyLogUpdate(response, request) {
    var channels = response.channels;
    var newestChannel = undefined; // 가장 최근에 새로 들어간 채널. 없으면 undefined
    for( var i = 0; i < channels.length; ++i ) {
        var currChan = channels[i];
        // 얘기한 적이 없는 채널이면 새 채널이다.
        var currChanInfo = GetChannelInfo(currChan.server, currChan.name);
        if( currChanInfo === undefined ) {
            // 채널 정보를 기록한다.
            currChanInfo = AddChannel( currChan.name, currChan.topic, currChan.users, currChan.server );
            newestChannel = currChanInfo.id;

            // 새 채널에 대한 정보를 화면에 표시한다.
            CreateChannelElement(currChanInfo);
        }
        // 로그를 출력한다.
        // Update, Init 의 정보만 처리하도록. 
        // log는 id(시간) 순으로 정렬되어 있다고 가정한다.
        var logStore = Ext.data.StoreManager.lookup(currChanInfo.storeID);

        // 기존 마지막 로그정보를 얻어온다.
        var currLogInfo = new Object();
        currLogInfo.latestLog = logStore.last()? logStore.last().raw: undefined;

        // 가장 아래로 스크롤되어 있는지 확인한다.
        var currList = Ext.getCmp(currChanInfo.listID);
        var scroller = currList.getScrollable().getScroller();
        var isBottom = scroller.maxPosition.y === scroller.position.y;

        // 로그를 행 별로 분석한다.
        for( var j = 0; j < currChan.log.length; ++j ) {
            currLogInfo.item = ParseLog(currChan.log[j], currLogInfo, currChanInfo);

            // 교집합이 있을 경우 처리. 가끔 같은 로그가 2번 들어와 있는 경우가 있다.
            if( !currLogInfo.latestLog || (currLogInfo.latestLog.logid !== undefined && currLogInfo.latestLog.logid < currLogInfo.item.logid) )
            {
                logStore.add(currLogInfo.item);

                // 마지막 로그 정보를 현재 로그로 업데이트한다
                currLogInfo.latestLog = currLogInfo.item;
            }
            else {
                console.log("duplicated log");
                console.log(currLogInfo);
            }
        }

        // 변경 로그가 없으면 다음 채널을 처리하자
        if( currChan.log.length == 0 ) {
            continue;
        }

        currList.refresh();

        // log id 정보 업데이트
        currChanInfo.oldestLogID = logStore.first().raw.logid;
        currChanInfo.newestLogID = logStore.last().raw.logid;

        // TODO: 현재 확인중인 채널이 아니면 updated 되었음을 알려주자(say 한정).
        // http://www.sencha.com/forum/showthread.php?118125-Carousel-indicator-overlapping-with-form-controls 근데 2.0에서 되는지는 테스트가 필요할 듯.

        // 과거 최신 로그가 화면 안에 보이는 상황이면 스크롤을 내리자.
        if( isBottom )
        {
            console.log("scroll to bottom . channel : " + currChanInfo.name);
            scroller.refresh();
            scroller.scrollToEnd();
            console.log(scroller);
        }
    }
    // TODO: 새로 들어간 채널이 있다면, 그 채널로 포커스가 옮겨가도록 한다.
    //if( newestChannel !== undefined )
}

// 새 로그 업데이트분을 요청한다.
function RequestLogUpdate() {
    var request = { 'req': 'LOG_UPDATE', 'channels': [] };
    for( var chan in chanDict ) {
        if( chanDict[chan].newestLogID == undefined ) {
            continue;
        }
        request.channels.push({ 'name': chanDict[chan].name, 'lastid': chanDict[chan].newestLogID, 'server': chanDict[chan].server });
    }
    RemoteRequest(request,
            PollingLogUpdate,
            function(response, opts) {
            //TODO : timeout 이나 네트워크 에러면 재시도..라기보다 서버 오류가 아니면 재시도가 낫겠군
            }
            ,
            60000);
}

// 로그 업데이트를 반영하고 다시 감시한다.
function PollingLogUpdate(response, request) {
    console.log("logupdate start");
    ApplyLogUpdate(response, request); // 로그 내용을 받아온다.    
    //CloseChannel(response); // 로그 업데이트가 없었던 채널을 정리한다.
    RequestLogUpdate(); // 감시를 시작한다!
    console.log("logupdate done");
}

