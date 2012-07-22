Ext.application({
    name: 'WebIRC',
    models: ['Log'],
    views: ['Main'],
    controllers: ['Main'],
    //stores: [],
    //profiles: [], // pc, ipad, iphone, android

    launch: function() {
        console.log("launch function called");
        Ext.create('WebIRC.view.Main');
    }
});
