odoo.define('fs_real_estate.real_estate_advertising_template', function (require) {
    "use strict";

    var FormController = require('web.FormController');
    var rpc = require('web.rpc');

    FormController.include({
        events: _.extend({}, FormController.prototype.events, {
            'click .copy_advertising_template': '_copyAdvertisingTemplate',
        }),

        _copyAdvertisingTemplate: function(evt) {
            return rpc.query({
				route: '/advertising_sample/copy',
				params: {
					content: this.initialState.data[evt.currentTarget.id],
				},
			})
        }
    })
})