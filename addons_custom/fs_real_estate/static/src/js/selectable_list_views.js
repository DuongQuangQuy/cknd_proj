odoo.define('fs_real_estate.selectable_list_views', function (require) {
	"use strict";
    var core = require('web.core');
    var session = require('web.session');
    var Model = require('web.Model');
    var QWeb = core.qweb;
    var ListView = require('web.ListView');
    ListView.include({
    	init: function(parent, dataset, view_id, options) {
    		var self = this;
            self._super(parent, dataset, view_id, options);
    		self.options.selectable=true;

    		if ( self.options.selectable==true){
                $(".search_actions a[data-model='"+ this.model + "'].delete").click( function (e){
                	self.delete_by_client_action();
                });


    		}

        },

        delete_by_client_action: function(){
        	var self = this;
        	var ids = this.get_selected_ids();
        	if ( ids.length == 0  ) return;
        	var Mod = new Model(this.model );
        	Mod.call('unlink', [ids], {context: this.get_context()}).then(function (result) {
        		self.do_delete(ids);
        	});
        },

    });
});