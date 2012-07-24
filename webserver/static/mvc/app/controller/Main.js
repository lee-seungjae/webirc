Ext.define('WebIRC.controller.Main', {
    extend: 'Ext.app.Controller',
    config: {
        refs: {
            chatbox: '#chatbox',
            mainCarousel: '#mainCarousel',
            chanInfoPanel: '#channelInfoPanel',
            mainPanel: '#mainPanel',
            logList: '#mainCarousel > list'
        },
        control: {
            chatbox: {
                keyup: 'checkChatBox',
                focus: 'hideChanInfo'
            },
            mainCarousel: {
                activeitemchange: 'activeChanChange',
                tap: 'hideChanInfo'
            },
            logList: {
                itemtap: 'hideChanInfo'
            }
        }
    },

    init: function() {
        Ext.get("divLoad").setHtml("Constructing components....");
    },

    launch: function() {
        Ext.get("divLoad").setHtml("Loading initial log....");
        // TODO: controller 객체를 붙여 넘길 수단을 찾아보자.
        connection.init(this.connEstablished, this.logUpdate, this.initFailed);
    },

    connEstablished: function() {
        Ext.get("divLoad").destroy();
    },

    initFailed: function() {
        Ext.get("divLoad").setHtml("connection failed! refreshing this page....");
        // TODO: refresh page
        console.log("initFailed");
    },


    // TODO: 일단 여기서 다 처리하게 해 놓고, 나중에 분리 생각하자
    logUpdate: function(response, request) {
        var mainController = WebIRC.app.getController('Main');
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
                mainController.createChanComponent(currChanInfo);
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
    },

    createChanComponent: function(chanInfo) {
        var storeID = chanInfo.storeID;
        var store = Ext.create('Ext.data.Store', {
                    storeId: storeID,
                    id: storeID,
                    model: 'WebIRC.model.Log',
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
                  connection.requestOldLog(currChanInfo, 
                      WebIRC.app.getController('Main').oldLog, 
                      function(response, opts) {
                        // LOG_OLD 는 실패해도 재시도할 필요는 없다. 그냥 에러메시지만 보여주고 말자.
                        console.log("OLD_LOG failed");
                        console.log(response);
                        alert("Loading old log failed.");
                    });
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
                // TODO: listner 정보만 남기고 사실 carousel 생성은 다 view로 넘겨야지?
                listeners: {
                    itemtap: function() {
                        // FIXME: Timer & 화면 내 다른 영역 터치로 수정하자.
                        //HideChanInfo();
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
                //HideChanInfo();
            }
        );
    },

    oldLog: function(response, request) {
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
            var currLogInfo = {isOldLog: true};
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
    },

    checkChatBox: function(field, e) {
        if( e.event.keyCode != 13 ) {
            // 엔터키만 처리하면 된다
            return;
        }

        var chatbox = this.getChatbox();
        connection.requestSay(GetCurrentServer(), GetCurrentChannel(),
                chatbox.getValue(),
                function(response, request) {
                    if( response['err'] ) { 
                        // TODO: XHR 단의 에러와 프로토콜단의 err를 통합해서 하나로 묶을까 -_-;
                        alert('say error ' + response['err']);
                    }
                    // TODO: 신뢰성 있는 say를 도입하면 callback으로 채팅창 건드릴 필요는 없어진다.
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
                });
    },

    activeChanChange: function(carousel, value, oldValue, eOpts) {
        this.getChanInfoPanel().show(GetChanInfoByStoreID(value.config.store));
    },

    hideChanInfo: function() {
        this.getChanInfoPanel().hide();
    }
});
