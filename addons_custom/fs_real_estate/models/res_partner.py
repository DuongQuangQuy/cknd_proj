from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import date, datetime, timedelta


class ResPartner(models.Model):
    _inherit = 'res.partner'

    estate_ids = fields.Many2many('real.estate', 'role_estate', 'partner_id', 'estate_id', string='Nhà đất')
    demand_estate_search_ids = fields.One2many('demand.estate.search', 'partner_id',
                                               string='Yêu cầu tìm kiếm khách hàng')
    offering_estate_ids = fields.One2many('offering.estate', 'customer_id', string='Các căn đã chào')
    is_employee = fields.Boolean(default=False, compute='_compute_is_employee')
    is_vip = fields.Boolean(string='Khách VIP', default=False)
    is_hide_mobile = fields.Boolean(string='Ẩn sdt', default=False, compute='_compute_is_hide_mobile')

    def _compute_is_employee(self):
        for record in self:
            record.is_employee =  self.env.user.has_group('fs_real_estate.group_real_estate_empoloyee')
            
    @api.depends('type_contact', 'name', 'mobile', 'is_employee')
    def _compute_display_name(self):
        result = []
        acronym_contact_type = {
            'contact': 'LH',
            'customer': 'KH',
            'agency': 'MG'
        }
        for record in self:
            record.display_name = f"{acronym_contact_type[record.type] if record.type else ''} {record.name or ''} {'( ' + record.mobile + ' )' if record.mobile else ''}"

    @api.depends('is_vip', 'type_contact')
    def _compute_is_hide_mobile(self):
        is_manager = self.env.user.has_group('fs_real_estate.group_real_estate_manager') or self.env.user.has_group('fs_real_estate.group_real_estate_import_data')
        is_employee = self.env.user.has_group('fs_real_estate.group_real_estate_empoloyee') or self.env.user.has_group('fs_real_estate.group_real_estate_import_data')
        for record in self:
            record.is_hide_mobile = (record.is_vip and not is_manager) or (record.type_contact == 'agency' and not is_employee)

    # def name_get(self):
    #     result = []
    #     for record in self:
    #         name = ''
    #         result.append(record.id, name)
    #     return name

    def read(self, fields=None, load='_classic_read'):
        res = super(ResPartner, self).read(fields, load=load)
        prices_config = self.env['real.estate']._get_prices_config()
        if prices_config:
            for record in res:
                if record.get('estate_ids'):
                    real_estates = self.env['real.estate'].browse(record.get('estate_ids'))
                    record['estate_ids'] = real_estates.filtered(lambda estate: prices_config.price_from <= estate.total_price <= prices_config.price_to).ids
        return res

    def button_add_demand_estate_search(self):
        for rec in self:
            context = {
                'default_partner_id': rec.id,
            }
            return {
                'name': "Nhu cầu tìm kiếm nhà đất",
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'demand.estate.search',
                'view_id': self.env.ref('fs_real_estate.demand_estate_search_view_form').id,
                'target': 'new',
                'context': context,
            }