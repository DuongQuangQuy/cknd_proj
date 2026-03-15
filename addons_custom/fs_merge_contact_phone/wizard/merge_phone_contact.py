from odoo import _, api, fields, models
import json
from datetime import datetime

from iteration_utilities import duplicates, unique_everseen


# from odoo.addons.sms.tools.sms_tools import sms_content_to_rendered_html



class MergePhoneContactWizard(models.TransientModel):
    _name = 'merge.phone.contact.wizard'
    _description = 'Merge Phone Contact Wizard'


    phone = fields.Char(string='Nhập số điện thoại cần tìm')
    partner_ids = fields.Many2many('res.partner', 'merge_phone_contact_wizard_partner_rel', string='Liên hệ')
    partner_data = fields.Text(compute='_compute_partner_data')
    preview_partner_data = fields.Text(compute='_compute_preview_partner_data')

    @api.depends('partner_ids')
    def _compute_partner_data(self):
        for record in self:
            if record.partner_ids:
                mobiles = record.partner_ids.mapped(lambda partner: partner.mobile or partner.mobile_2 or partner.mobile_3 or partner.mobile_4)
                line_vals = {mobile: [] for mobile in mobiles}
                for partner in record.partner_ids:
                    mobile = partner.mobile or partner.mobile_2 or partner.mobile_3 or partner.mobile_4
                    related_house_preview = []
                    for real_estate in partner.estate_ids:
                        related_house_preview.append(
                            f"<a href='/web#id={real_estate._origin.id}&amp;model=real.estate&amp;view_type=form' target='_blank' style='color: #337ab7'>{real_estate._get_address(house=1, street=1, district=1)}</a>"
                        )
                    line_vals[mobile].append((0, 0, {
                        'date_entry': f"<span class='text-danger'>{partner.date_entry.strftime('%d-%m-%Y')}</span><br/><span class='text-success'>Cách {(datetime.now() - partner.date_entry).days} ngày</span>",
                        'code': f"<a href='/web#id={partner._origin.id}&amp;model=res.partner&amp;view_type=form' target='_blank' style='color: #337ab7'>{partner.code}</a>" if partner.code else '',
                        'related_house_ids': related_house_preview,
                        'name': partner.display_name,
                        'demand': '',
                        'act': [record.id, partner._origin.id],
                        'orther': [record.id, partner._origin.id, (record.partner_ids.filtered(lambda p: p.mobile == mobile or p.mobile_2 == mobile or p.mobile_3 == mobile or p.mobile_4 == mobile) - partner).ids]
                    }))
                record.partner_data = json.dumps([{'mobile': mobile, 'line_ids': line_ids} for mobile, line_ids in line_vals.items()])
            else:
                record.partner_data = None
            

    @api.depends('partner_data')
    def _compute_preview_partner_data(self):
        for record in self:
            if record.partner_data:
                preview_columns = [
                    {'field': 'date_entry', 'label': _('Date')},
                    {'field': 'code', 'label': _('Code')},
                    {'field': 'related_house_ids', 'label': _('Nhà liên quan')},
                    {'field': 'name', 'label': _('Contact')},
                    {'field': 'demand', 'label': _('Nhu cầu')},
                    {'field': 'act', 'label': _('Hành động')},
                    {'field': 'orther', 'label': _('#')},
                    # {'field': 'phone', 'label': _('Phone')},
                    # {'field': 'debit', 'label': _('Debit'), 'class': 'text-right text-nowrap'},
                    # {'field': 'credit', 'label': _('Credit'), 'class': 'text-right text-nowrap'},
                ]

                partner_vals = json.loads(record.partner_data)
                preview_vals = []
                for partner_val in partner_vals:
                    preview_vals += [{
                        'group_name': f"<b># {partner_val['mobile']} - {len(partner_val['line_ids'])} liên hệ - <a href='https://www.google.com.vn/search?q={partner_val['mobile']}' target='_blank' style='color: #337ab7'>Tìm kiếm với google</a></b>",
                        'items_vals': partner_val['line_ids']
                    }]
                preview_discarded = 0

                record.preview_partner_data = json.dumps({
                    'groups_vals': preview_vals,
                    'options': {
                        'discarded_number': _("%d moves", preview_discarded) if preview_discarded else False,
                        'columns': preview_columns,
                    },
                })
            else:
                record.preview_partner_data = json.dumps({
                    'groups_vals': [],
                    'options': {
                        'discarded_number': False,
                        'columns': [],
                    },
                })

    def action_partners_top10_duplicate_phone(self):
        mobile_duplicates = self.env['res.partner'].search(['|', '|', '|',
                                                ('mobile', '!=', False),
                                                ('mobile_2', '!=', False),
                                                ('mobile_3', '!=', False),
                                                ('mobile_4', '!=', False),]).mapped(lambda partner: partner.mobile or partner.mobile_2 or partner.mobile_3 or partner.mobile_4)
        mobiles = list(unique_everseen(duplicates(mobile_duplicates)))[:10]
        partner_ids = []
        # mobiles = []
        # mobiles +=  [partner['mobile'] for partner in self.env['res.partner'].read_group([('mobile', '!=', False), ('mobile', 'not in', mobiles)], ['mobile'], ['mobile'], limit=10)]
        # if len(mobiles) < 10:
        #     mobiles +=  [partner['mobile_2'] for partner in self.env['res.partner'].read_group([('mobile_2', '!=', False), ('mobile_2', 'not in', mobiles)], ['mobile_2'], ['mobile_2'], limit=(10 - len(mobiles)))]
        # if len(mobiles) < 10:
        #     mobiles +=  [partner['mobile_3'] for partner in self.env['res.partner'].read_group([('mobile_3', '!=', False), ('mobile_3', 'not in', mobiles)], ['mobile_3'], ['mobile_3'], limit=(10 - len(mobiles)))]
        # if len(mobiles) < 10:
        #     mobiles +=  [partner['mobile_4'] for partner in self.env['res.partner'].read_group([('mobile_4', '!=', False), ('mobile_4', 'not in', mobiles)], ['mobile_4'], ['mobile_4'], limit=(10 - len(mobiles)))]
        # if len(mobiles) < 10:
        #         mobile = set(self.env['res.partner'].search([('mobile', '!=', False), ('mobile', 'not in', mobiles)]).mapped('mobile'))
        #         mobile_2 = set(self.env['res.partner'].search([('mobile_2', '!=', False), ('mobile_2', 'not in', mobiles)]).mapped('mobile_2'))
        #         mobile_3 = set(self.env['res.partner'].search([('mobile_3', '!=', False), ('mobile_3', 'not in', mobiles)]).mapped('mobile_3'))
        #         mobile_4 = set(self.env['res.partner'].search([('mobile_4', '!=', False), ('mobile_4', 'not in', mobiles)]).mapped('mobile_4'))
        #         duplicate_mobiles = (mobile | mobile_2 | mobile_3 | mobile_4) - (mobile ^ mobile_2 ^ mobile_3 ^ mobile_4)
        #         for dmoblie in duplicate_mobiles:
        #             if len(mobiles) < 10:
        #                 mobiles.append(dmoblie)
        #             else:
        #                 break
        for mobile in mobiles:
            partner_ids += self.env['res.partner'].search(['|', '|', '|',
                                                ('mobile', '=', mobile),
                                                ('mobile_2', '=', mobile),
                                                ('mobile_3', '=', mobile),
                                                ('mobile_4', '=', mobile)]).ids
        self.partner_ids = [(6, 0, partner_ids)]
        return {
            'name': _('Tìm điện thoại trùng'),
            'view_mode': 'form',
            'res_model': 'merge.phone.contact.wizard',
            'res_id': self.id,
            'type': 'ir.actions.act_window',
            'target': 'new',
        }

    def action_search_partner_by_phone(self):
        for record in self:
            if record.phone:
                partners = self.env['res.partner'].search(['|', '|', '|',
                                                    ('mobile', '=', record.phone),
                                                    ('mobile_2', '=', record.phone),
                                                    ('mobile_3', '=', record.phone),
                                                    ('mobile_4', '=', record.phone)])
                record.partner_ids = [(6, 0, partners.ids)]
            else:
                record.partner_ids = None

        return {
            'name': _('Tìm điện thoại trùng'),
            'view_mode': 'form',
            'res_model': 'merge.phone.contact.wizard',
            'res_id': self.id,
            'type': 'ir.actions.act_window',
            'target': 'new',
        }

    def remove_partner(self, partner_id):
        if self.partner_ids:
            self.partner_ids = [(2, partner_id, 0)]
            return self.preview_partner_data
    
    def merge_partner(self, partner_id, partner_remove_ids):
        partner = self.env['res.partner'].browse(partner_id)
        partners_remove = self.env['res.partner'].browse(partner_remove_ids)
        if partner and partners_remove:
            partner.estate_ids += partners_remove.estate_ids
            for pr in partners_remove:
                note = f"""\n_____________Gom theo thong tin_____________________
Code: {pr.code or ''}
Name: {pr.name or ''}
Mobile: {pr.mobile or pr.mobile_2 or pr.mobile_3 or pr.mobile_4}
____________________________________________________"""
                if partner.note:
                    partner.note += note
                else:
                    partner.note = note
                self.partner_ids = [(2, pr.id, 0)]
            return self.preview_partner_data
