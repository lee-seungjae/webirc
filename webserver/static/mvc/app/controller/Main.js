Ext.define('WebIRC.controller.Main', {
    extend: 'Ext.app.Controller',
    config: {
    //refs: {},
    //control: {}
    },

    init: function() {
        console.log("init function called");
        Ext.get("divLoad").setHtml("Constructing components....");
    },

    launch: function() {
        console.log("control launch function called");
        Ext.get("divLoad").setHtml("Loading initial log....");
        connection.init(this.connEstablished, this.logUpdate, this.initFailed);
    },

    connEstablished: function() {
        Ext.get("divLoad").destroy();
    },

    initFailed: function() {
        Ext.get("divLoad").setHtml("connection failed! refresh page please.");
    },

    logUpdate: function() {
        console.log("updated");
    }
});
