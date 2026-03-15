from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import date, datetime, timedelta


class CallSaleEstate(models.Model):
    _name = 'call.sale.estate'
    _description = 'Call Sale Estate'

    user_id = fields.Many2one('res.users', string='Người gọi', default=lambda self: self.env.user)
    company_id = fields.Many2one('res.company', string='Company', readonly=True,
                                 default=lambda self: self.env.company)
    search_demand_id = fields.Many2one('demand.estate.search', string='Yêu cầu tìm kiếm')
    partner_id = fields.Many2one('res.partner', string='Người liên lạc', readonly=True)
    note = fields.Text('Ghi chú')

    def action_call(self):
        pass
