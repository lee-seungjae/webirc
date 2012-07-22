Ext.define('WebIRC.view.Main', {
    extend: 'Ext.Panel',

    config: {
        fullscreen: true,
        layout: { type: 'vbox', align: 'stretch'},
        items: [
        // carousel for chat log
        {
            id: 'mainCarousel',
            xtype: 'carousel',
            flex: 1
        },
        // chatting form
        {
            xtype: 'formpanel',
            id: 'chatform',
            scrollable: false,
            layout: { type: 'hbox' },
            height: 40,

            items: [
            {
               xtype: 'textfield',
               name: 'chat',
               id: 'chatbox',
               clearIcon: false,
               tabIndex: 1,
               minWidth: '90%'
            }]
        }]
    },
    _chanInfoPanel: undefined,
    showChanInfo: function() {
        // 없으면 패널 생성 if( 
    },
    hideChanInfo: function() {
    }
});

Ext.define('WebIRC.view.Main.ChanInfoPanel', {
    extend: 'Ext.Panel',

    config: {
        id: 'ChannelInfoPanel',
        cls: 'channelInfo',
        centered: true,
        minWidth: '30%',
        minHeight: '3em',
        maxWidth: '90%',
        maxHeight: '10em',
        border: '0.1px',
        padding: 3,
    },
    show: function() {},
    hide: function() {},
    _visible: false,
    _hideTimer: undefined
});
