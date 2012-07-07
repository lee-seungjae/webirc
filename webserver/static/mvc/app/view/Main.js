Ext.define('WebIRC.view.Main', {
    extend: 'Ext.Panel',

    config: {
        html: 'this is a view',
        fullscreen: true,
        layout: { type: 'vbox', align: 'stretch'},
        items: [
        // carousel for chat log
        {
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
    }
});

