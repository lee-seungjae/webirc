Ext.define('WebIRC.view.Main', {
    extend: 'Ext.Panel',

    config: {
        id: 'mainPanel',
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

    initialize: function() {
        this.callParent(arguments);
        Ext.create('WebIRC.view.Main.ChanInfoPanel');
    }
});

Ext.define('WebIRC.view.Main.ChanInfoPanel', {
    extend: 'Ext.Panel',

    config: {
        id: 'channelInfoPanel',
        cls: 'channelInfo',
        centered: true,
        minWidth: '30%',
        minHeight: '3em',
        maxWidth: '90%',
        maxHeight: '10em',
        border: '0.1px',
        padding: 3,
    },
    show: function(chanInfo) {
        var html = chanInfo.server+"/"+ chanInfo.name + "<br />" 
                    + chanInfo.topic + "<br />"
                    + chanInfo.users.length + " users";
        this.setHtml(html);
        Ext.Viewport.add(this);
        this._visible = true;
    },

    hide: function() {
        Ext.Viewport.remove(this, false);
        this._visible = false;
    },

    _visible: false,
    _hideTimer: undefined
});
