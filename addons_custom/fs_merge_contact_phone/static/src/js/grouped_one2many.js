odoo.define('fs_merge_contact_phone.GroupedOne2Many', function (require) {
    'use strict';

    const { Component } = owl;
    const { useState } = owl.hooks;
    const { useEffect } = require('@web/core/utils/hooks');
    const AbstractFieldOwl = require('web.AbstractFieldOwl');
    const field_registry = require('web.field_registry_owl');
    var rpc = require('web.rpc');

    class ListOne2ManyItem extends Component { 
        unlink_partner (id, partnerId) {
            if (confirm("Bạn muốn xoá dữ liệu này!")) {
                return rpc.query({
                    model: 'merge.phone.contact.wizard',
                    method: 'remove_partner',
                    args: [id, partnerId],
                }).then(result => {
                    this.__owl__.parent.__owl__.parent._setValue(result);
                })
            }
        }

        merge_parner(id, partnerId, partnerRemoveId) {
            return rpc.query({
                model: 'merge.phone.contact.wizard',
                method: 'merge_partner',
                args: [id, partnerId, partnerRemoveId],
            }).then(result => {
                this.__owl__.parent.__owl__.parent._setValue(result);
            })
        }
    }
    ListOne2ManyItem.template = 'fs_merge_contact_phone.GroupedItemTemplate';
    ListOne2ManyItem.props = ["item_vals", "options"];

    class ListOne2ManyGroup extends Component { }
    ListOne2ManyGroup.template = 'fs_merge_contact_phone.GroupedItemsTemplate';
    ListOne2ManyGroup.components = { ListOne2ManyItem }
    ListOne2ManyGroup.props = ["group_vals", "options"];


    class ShowGroupedOne2ManyList extends AbstractFieldOwl {
        constructor(...args) {
            super(...args);
            this.data = this.value ? JSON.parse(this.value) : {
                groups_vals: [],
                options: {
                    discarded_number: '',
                    columns: [],
                },
            };
        }

        async willUpdateProps(nextProps) {
            await super.willUpdateProps(nextProps);
            Object.assign(this.data, JSON.parse(this.value));
        }
    }
    ShowGroupedOne2ManyList.template = 'fs_merge_contact_phone.GroupedListTemplate';
    ShowGroupedOne2ManyList.components = { ListOne2ManyGroup }
    
    field_registry.add('grouped_one2many_widget', ShowGroupedOne2ManyList);
    return ShowGroupedOne2ManyList;
})