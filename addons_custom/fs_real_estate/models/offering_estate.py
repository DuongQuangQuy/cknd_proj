from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import date, datetime, timedelta


class OfferingEstate(models.Model):
    _name = 'offering.estate'
    _description = 'Offering Estate'

    user_id = fields.Many2one('res.users', string='Nhân viên chào nhà')
    partner_id = fields.Many2one('res.partner', string='NV ghép nhà')
    customer_id = fields.Many2one('res.partner', string='Khách hàng')
    demand_id = fields.Many2one('real.estate', string='Nhà đất')
    search_demand_id = fields.Many2one('demand.estate.search', string='Yêu cầu tìm kiếm')
    employee_concierge_id = fields.Many2many('res.partner', 'offering_estate_res_partner_rel',
                                             string='Nhân viên dắt khách')
    state = fields.Selection([('draft', "Nháp"),
                              ('new', "Mới ghép"),
                              ('done', "Hoàn thành")], default="draft",
                             string="Trạng thái")
