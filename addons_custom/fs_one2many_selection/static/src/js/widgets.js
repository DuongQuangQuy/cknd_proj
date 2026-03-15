odoo.define('fs_web_one2many_selectable.form_widgets', function (require) {
	"use strict";

	var core = require('web.core');
	var utils = require('web.utils');
	var _t = core._t;
	var QWeb = core.qweb;
	var fieldRegistry = require('web.field_registry');
	var ListRenderer = require('web.ListRenderer');
	var rpc = require('web.rpc');
	var FieldOne2Many = require('web.relational_fields').FieldOne2Many;

	ListRenderer.include({

		// Override this method to get delete button appear,disappear logic
		_updateSelection: function () {
	        this.selection = [];
	        var self = this;
	        var $inputs = this.$('tbody .o_list_record_selector input:visible:not(:disabled)');
	        var allChecked = $inputs.length > 0;
	        $inputs.each(function (index, input) {
	            if (input.checked) {
	                self.selection.push($(input).closest('tr').data('id'));
	            } else {
	                allChecked = false;
	            }
	        });
	        if(this.selection.length > 0){
	        	$('.button_delete_lines').show();
	        	$('.button_favorite_lines').show();
	        }else{
	        	$('.button_delete_lines').hide();
	        	$('.button_favorite_lines').hide();
	        }
	        this.$('thead .o_list_record_selector input').prop('checked', allChecked);
	        this.trigger_up('selection_changed', { selection: this.selection });
	        this._updateFooter();
	    },
	})


	var One2ManySelectable = FieldOne2Many.extend({
		template: 'One2ManySelectable',
		events: {
			"click .button_delete_lines": "action_selected_lines",
			"click .button_favorite_lines": "action_favorite_lines",
		},
		start: function()
	    {
	    	this._super.apply(this, arguments);
			var self=this;
	   },
		//passing ids to function
		action_selected_lines: function()
		{
			var self=this;
			var selected_ids = self.get_selected_ids_one2many();
			if (selected_ids.length === 0)
			{
				this.do_warn(_t("You must choose at least one record."));
				return false;
			}
			rpc.query({
				route: '/one2many_selection/delete_lines',
				params: {
					model: this.field.relation,
					selected_ids: selected_ids,
				},
			}).then(function(result){
                self.trigger_up('reload');
            });
		},

		// Add favorite functionality
		action_favorite_lines: function() {
    var self = this;
    var selected_ids = self.get_selected_ids_one2many();
    if (selected_ids.length === 0) {
        this.do_warn(_t("You must choose at least one record."));
        return false;
    }

    // First check if there are any existing favorite records
    rpc.query({
        model: 'real.estate.favorite',
        method: 'search',
        args: [[]],
        limit: 1,
    }).then(function(favorite_ids) {
        if (favorite_ids && favorite_ids.length > 0) {
            // Existing record found, add selected items to it
            var favorite_id = favorite_ids[0];

            // Tạo danh sách các lệnh để thêm từng ID riêng lẻ
            var commands = [];
            selected_ids.forEach(function(id) {
                commands.push([4, id, 0]); // Command 4: add existing record
            });

            rpc.query({
                model: 'real.estate.favorite',
                method: 'write',
                args: [favorite_id, {
                    'estate_ids': commands
                }],
            }).then(function() {
                // Hiển thị thông báo thành công
                self.displayNotification({
                    title: _t("Success"),
                    message: _t("Selected properties added to existing favorites"),
                    type: 'success'
                });

                // Bỏ chọn tất cả các checkbox
                self._clearSelection();
            }).catch(function(error) {
                console.error("Error adding to favorites:", error);
                self.do_warn(_t("Error"), _t("Failed to add to favorites. Please try again."));
            });
        } else {
            // No existing record, create a new one
            self.do_action({
                name: _t("Add to Favorites"),
                type: "ir.actions.act_window",
                res_model: "real.estate.favorite",
                views: [[false, "form"]],
                target: "new",
                context: {
                    "default_estate_ids": selected_ids,
                    "default_name": _t("Favorites ") + new Date().toLocaleString()
                }
            }, {
                on_close: function() {
                    // Bỏ chọn tất cả các checkbox khi form đóng (dù lưu hay hủy)
                    self._clearSelection();
                }
            });
        }
    }).catch(function(error) {
        console.error("Error checking favorites:", error);
        self.do_warn(_t("Error"), _t("Failed to check existing favorites. Please try again."));
    });
},

// Thêm hàm mới để xóa selection
_clearSelection: function() {
    // Bỏ chọn tất cả các checkbox
    this.$('tbody .o_list_record_selector input:checked').prop('checked', false);
    this.$('thead .o_list_record_selector input').prop('checked', false);

    // Cập nhật selection và làm mới giao diện
    this.renderer._updateSelection();
    this.trigger_up('reload');
},

		_getRenderer: function () {
            if (this.view.arch.tag === 'kanban') {
                return One2ManyKanbanRenderer;
            }
            if (this.view.arch.tag === 'tree') {
                return ListRenderer.extend({
                    init: function (parent, state, params) {
                        this._super.apply(this, arguments);
                        this.hasSelectors = true;
                    },
                });
            }
            return this._super.apply(this, arguments);
        },
		//collecting the selected IDS from one2manay list
		get_selected_ids_one2many: function () {
            var self=this;
            var ids =[];
            this.$el.find('td.o_list_record_selector input:checked')
                    .closest('tr').each(function () {
                        ids.push(parseInt(self._getResId($(this).data('id'))));
            });
            return ids;
        },

        _getResId: function (recordId) {
            var record;
            utils.traverse_records(this.recordData[this.name], function (r) {
                if (r.id === recordId) {
                    record = r;
                }
            });
            return record.res_id;
        },

	});
	// register unique widget, because Odoo does not know anything about it
	//you can use <field name="One2many_ids" widget="x2many_selectable"> for call this widget
	fieldRegistry.add('one2many_selectable', One2ManySelectable);
});

//odoo.define('fs_web_one2many_selectable.form_widgets', function (require) {
//	"use strict";
//
//	var core = require('web.core');
//	var utils = require('web.utils');
//	var _t = core._t;
//	var QWeb = core.qweb;
//	var fieldRegistry = require('web.field_registry');
//	var ListRenderer = require('web.ListRenderer');
//	var rpc = require('web.rpc');
//	var FieldOne2Many = require('web.relational_fields').FieldOne2Many;
//
//	ListRenderer.include({
//
//		// Override this method to get delete button appear,disappear logic
//		_updateSelection: function () {
//	        this.selection = [];
//	        var self = this;
//	        var $inputs = this.$('tbody .o_list_record_selector input:visible:not(:disabled)');
//	        var allChecked = $inputs.length > 0;
//	        $inputs.each(function (index, input) {
//	            if (input.checked) {
//	                self.selection.push($(input).closest('tr').data('id'));
//	            } else {
//	                allChecked = false;
//	            }
//	        });
//	        if(this.selection.length > 0){
//	        	$('.button_delete_lines').show();
//	        	$('.button_favorite_lines').show();
//	        }else{
//	        	$('.button_delete_lines').hide();
//	        	$('.button_favorite_lines').hide();
//	        }
//	        this.$('thead .o_list_record_selector input').prop('checked', allChecked);
//	        this.trigger_up('selection_changed', { selection: this.selection });
//	        this._updateFooter();
//	    },
//	})
//
//
//	var One2ManySelectable = FieldOne2Many.extend({
//		template: 'One2ManySelectable',
//		events: {
//			"click .button_delete_lines": "action_selected_lines",
//			"click .button_favorite_lines": "action_favorite_lines",
//		},
//		start: function()
//	    {
//	    	this._super.apply(this, arguments);
//			var self=this;
//	   },
//		//passing ids to function
//		action_selected_lines: function()
//		{
//			var self=this;
//			var selected_ids = self.get_selected_ids_one2many();
//			if (selected_ids.length === 0)
//			{
//				this.do_warn(_t("You must choose at least one record."));
//				return false;
//			}
//			rpc.query({
//				route: '/one2many_selection/delete_lines',
//				params: {
//					model: this.field.relation,
//					selected_ids: selected_ids,
//				},
//			}).then(function(result){
//                self.trigger_up('reload');
//            });
//		},
//
//		// Add favorite functionality
//		action_favorite_lines: function() {
//			var self = this;
//			var selected_ids = self.get_selected_ids_one2many();
//			if (selected_ids.length === 0) {
//				this.do_warn(_t("You must choose at least one record."));
//				return false;
//			}
//
//			// Open the favorite form with selected IDs
//			self.do_action({
//				name: _t("Add to Favorites"),
//				type: "ir.actions.act_window",
//				res_model: "real.estate.favorite",
//				views: [[false, "form"]],
//				target: "new",
//				context: {
//					"default_estate_ids": selected_ids,
//					"default_name": _t("Favorites ") + new Date().toLocaleString()
//				}
//			});
//		},
//
//		_getRenderer: function () {
//            if (this.view.arch.tag === 'kanban') {
//                return One2ManyKanbanRenderer;
//            }
//            if (this.view.arch.tag === 'tree') {
//                return ListRenderer.extend({
//                    init: function (parent, state, params) {
//                        this._super.apply(this, arguments);
//                        this.hasSelectors = true;
//                    },
//                });
//            }
//            return this._super.apply(this, arguments);
//        },
//		//collecting the selected IDS from one2manay list
//		get_selected_ids_one2many: function () {
//            var self=this;
//            var ids =[];
//            this.$el.find('td.o_list_record_selector input:checked')
//                    .closest('tr').each(function () {
//                        ids.push(parseInt(self._getResId($(this).data('id'))));
//            });
//            return ids;
//        },
//
//        _getResId: function (recordId) {
//            var record;
//            utils.traverse_records(this.recordData[this.name], function (r) {
//                if (r.id === recordId) {
//                    record = r;
//                }
//            });
//            return record.res_id;
//        },
//
//	});
//	// register unique widget, because Odoo does not know anything about it
//	//you can use <field name="One2many_ids" widget="x2many_selectable"> for call this widget
//	fieldRegistry.add('one2many_selectable', One2ManySelectable);
//});