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
  config: {
          fields: ['logid', 'date', 'who','type','text']
  }
});
var fbInfo = undefined;

function ShowOldLog(response, request) 
{
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

        // log id 정보 업데이트
        currChanInfo.oldestLogID = logStore.first().raw.logid;
        currChanInfo.newestLogID = logStore.last().raw.logid;
    }
}


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
                var chatbox = Ext.getCmp("chatbox");
                chatbox.setValue('');
                chatbox.enable();
                chatbox.focus();
            },
            function(response, opt) {
                console.log(response);
                console.log(opt);
                var chatbox = Ext.getCmp("chatbox");
                chatbox.enable();
                chatbox.focus();
                alert("Message sending failed. Resend please.");
            },
            30000
            );
    var chatbox = Ext.getCmp("chatbox");
    chatbox.disable();

    return false;
}
// 새 채널 정보를 표시할 element를 만든다.
function CreateChannelElement(chanInfo) {
    var storeID = chanInfo.storeID;
    var store = Ext.create('Ext.data.Store', {
                storeId: storeID,
                id: storeID,
                model: 'Log.Model',
                sorters: 'logid',
                autoLoad: false,
                listeners: {
                    addrecords: function(st, records, eOpts) {
                        var list = Ext.getCmp(GetChanInfoByStoreID(st.config.id).listID);
                        list.fireEvent("updatedata", list, records, eOpts);
                    }
                }
            });

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
                        // LOG_OLD 는 실패해도 재시도할 필요는 없다. 그냥 에러메시지만 보여주고 말자.
                        console.log("OLD_LOG failed");
                        console.log(response);
                        alert("Loading old log failed.");
                    },
                    20000);
            }
    };
    
    Ext.getCmp("mainCarousel").add([
        {
            xtype: 'list',
            id: chanInfo.listID,
            itemTpl: '{text}',
            mode: 'SINGLE',
            allowDeselect: false,
            disclosure: false,
            cls: 'logList',
            flex: 1,
            store: storeID,
            selectedCls: 'selectedlog',
            pressedCls: 'pressedlog',
            plugins: refreshplugin,
            scrollable: 
            { 
                direction: 'vertical',
                directionLock: true
            },
            showAnimation: 'slideIn',
            listeners: {
                itemtap: function() {
                    // FIXME: Timer & 화면 내 다른 영역 터치로 수정하자.
                    HideChanInfo();
                },
                updatedata: function(list, newData, eOpts) {
                    var scroller = list.getScrollable().getScroller();
                    if( !scroller.scrollLock )
                    {
                        scroller.scrollToEnd();
                    }
                }
            }
        }]);
    
    var scroll = Ext.getCmp(chanInfo.listID).getScrollable().getScroller();
    // list 영역 크기에 변경이 있을 경우
    scroll.on(
        "maxpositionchange", 
        function(scroller, maxPosition, eOpts) {
            if( !scroller.scrollLock && scroller.minPosition.y != maxPosition.y )
            {
                scroller.scrollToEnd();
            }
        });

    // scrollLock 여부를 결정하는 함수
    var decideScrollLock = 
        function(scroller, x, y, eOpts) {
            scroller.scrollLock = scroller.maxPosition.y > y;
        };

    // scroll 이 끝났을 경우 해당 위치를 가지고 scrollLock을 판단한다.
    scroll.on("scroll", decideScrollLock);
    scroll.on("scrollend", decideScrollLock);

    // scroll이 시작할 때에는 일단 어느 위치까지 스크롤하지 모르니 scrollLock을 켜자.
    scroll.on(
        "scrollstart", 
        function(scroller, x, y, eOpts) {
            scroller.scrollLock = true;
            // FIXME: Timer & 화면 내 다른 영역 터치로 수정하자.
            HideChanInfo();
        }
    );
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
            newestChannel = currChanInfo;

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

        // 받아온 로그를 행 별로 분석한다.
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

        // log id 정보 업데이트
        currChanInfo.oldestLogID = logStore.first().raw.logid;
        currChanInfo.newestLogID = logStore.last().raw.logid;

        // TODO: 현재 확인중인 채널이 아니면 updated 되었음을 알려주자(say 한정).
        // http://www.sencha.com/forum/showthread.php?118125-Carousel-indicator-overlapping-with-form-controls 근데 2.0에서 되는지는 테스트가 필요할 듯.

    }
    // 새로 들어간 채널이 있다면, 그 채널로 포커스가 옮겨가도록 한다.
    if( newestChannel !== undefined )
    {
        Ext.getCmp("mainCarousel").setActiveItem(Ext.getCmp(newestChannel.listID));
    }
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
                // 서버 오류가 아니면 재시도가 낫겠군
                if( response.status != 200 && ( response.status > 600 || response.status < 200 ) )
                {
                    RequestLogUpdate();
                }
            }
            ,
            60000);
}

// 로그 업데이트가 없었던 채널을 정리한다.
function CloseChannel(response)
{
    var channels = response.channels;
    var updatedChannels = {};
    var lastUpdatedChannel = undefined;
    var lastUpdatedTime = undefined;
    for( var i = 0; i < channels.length; ++i ) {
        updatedChannels[channels[i].name] = channels[i].server;

        // 가장 최근에 업데이트가 있었던 채널 정보를 구해 놓는다.
        if( lastUpdatedTime === undefined 
                || ( channels[i].log.length > 0 
                    && lastUpdatedTime < channels[i].log[channels[i].log.length-1].date ) ) {
            lastUpdatedChannel = GetChannelInfo(channels[i].server, channels[i].name);
            if( channels[i].log.length > 0 ) {
                lastUpdatedTime = channels[i].log[channels[i].log.length-1].date;
            }
        }
    }

    var carousel = Ext.getCmp("mainCarousel");
    for( var ch in chanDict ) {
        var currChan = chanDict[ch];

        // 업데이트된 내용이 있으면 통과
        if( updatedChannels[currChan.name] == currChan.server ) {
            continue;
        }

        // 닫을 채널이 활성화된 채널이면 가장 최근에 업데이트된 채널을 활성화
        var activeChannel = GetCurrentChannelInfo();
        if( activeChannel.name == currChan.name && activeChannel.server == currChan.server && lastUpdatedChannel ) {
            carousel.setActiveItem(Ext.getCmp(lastUpdatedChannel.listID));
        }

        // list component Element 날리기
        carousel.remove(Ext.getCmp(currChan.listID), true);
        Ext.data.StoreManager.unregister(currChan.storeID);

        // 자료구조 날리기
        delete chanNameMap[currChan.name+"@"+currChan.server];
        delete chanDict[ch];
    }
}

// 로그 업데이트를 반영하고 다시 감시한다.
function PollingLogUpdate(response, request) {
    ApplyLogUpdate(response, request); // 로그 내용을 받아온다.    
    CloseChannel(response); // 로그 업데이트가 없었던 채널을 정리한다.
    RequestLogUpdate(); // 감시를 시작한다!
}

function HideChanInfo()
{
    Ext.Viewport.remove(Ext.getCmp('ChannelInfoPanel'), false);
}

function ShowChanInfo(chanInfo)
{
    var infoPanel = Ext.getCmp('ChannelInfoPanel');
    var html = chanInfo.server+"/"+ chanInfo.name + "<br />" 
                + chanInfo.topic + "<br />"
                + chanInfo.users.length + " users";
    infoPanel.setHtml(html);
    Ext.Viewport.add(infoPanel);
}

function CreateMainView()
{
    Ext.create('Ext.Panel', {
        id: 'ChannelInfoPanel',
        cls: 'channelInfo',
        centered: true,
        minWidth: '30%',
        minHeight: '3em',
        maxWidth: '90%',
        maxHeight: '10em',
        border: '0.1px',
        padding: 3,
        });

  var chatLine = Ext.create('Ext.form.Panel', {
        id: "chatpanel",
        scrollable: false,
        layout: { type: 'hbox' },
      items: [{
               xtype: 'textfield',
               name: 'chat',
               id: 'chatbox',
               clearIcon: false,
               tabIndex: 1,
               minWidth: '90%',
               listeners:{
               keyup: function(field, e) {
                    var keycode = e.event.keyCode;
                    if( keycode == 13 )
                    {
                        Say();
                    }
               },
               focus: function(field, e, eOpts) {
                    // FIXME: Timer & 화면 내 다른 영역 터치로 수정하자.
                    HideChanInfo();
               }
               }
             }],
    height: 40});


    var carousel = Ext.create('Ext.Carousel', {
        id: "mainCarousel",
        flex: 1,
        listeners: {
            activeitemchange: function(carousel, value, oldValue, eOpts) {
                ShowChanInfo(GetChanInfoByStoreID(value.config.store));
            }
        }
    });

/*
    if (!Ext.is.Phone) {
      var panel = Ext.create('Ext.Panel',
          {
            layout: { type: 'vbox', align: 'stretch'},
            width: 350,
            height: 370,
            centered: true,
            modal: true,
            hideOnMaskTap: false,
            items: [carousel, chatLine]
          });
    }
    else {
    */
      var panel = Ext.create('Ext.Panel', {
        layout: { type: 'vbox', align: 'stretch'},
        fullscreen: true,
        items: [carousel, chatLine]
      });
//    }

    Ext.Viewport.add(panel);
    panel.setActiveItem(); // for android 
}

Ext.setup({
  tabletStartupScreen: 'tablet_startup.png',
  phoneStartupScreen: 'phone_startup.png',
  icon: 'icon.png',
  glossOnIcon: false,
  onReady : function() {
// FACEBOOK 인증 시작 - 이후 세션 기반으로 바뀌면 제거해야 한다
    Ext.get("divLoad").setHtml("Processing auth info....");
    FB.init( {
        appId:'182399195162695',
        cookie:true,
        status:true,
        oauth:true
        } );
    FB.getLoginStatus( function(response) {
        if( ! response.authResponse )
        {
            // Login 실패
            window.location = '/static/login.html'
            return;
        }

        fbInfo = response.authResponse;
        // FACEBOOK 인증정보 처리 끝.

        CreateMainView();

        var request = { 'req': 'LOG_INIT' };
        RemoteRequest(request,
                function(response, request) {
                    Ext.get("divLoad").destroy();
                    PollingLogUpdate(response, request);
                },
                function(response, opts) {
                    alert("error " + response.responseText);
                    // TODO: 네트워크 에러면 몇 번 더 시도해보자.
                    // 더 해서 안되면 사용자 확인 후 페이지 리프레쉬!
                },
                60000);
        Ext.get("divLoad").setHtml("Loading initial log....");
    });
  }
});
