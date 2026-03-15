from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import date, datetime, timedelta


class OfferingHistory(models.Model):
    _name = 'offering.history'
    _description = 'Offering History'

    offering_id = fields.Many2one('offering.estate', string='Chào nhà')
    partner_id = fields.Many2one('res.partner', string='NV ghép nhà')
    customer_id = fields.Many2one('res.partner', string='Khách hàng')
    demand_id = fields.Many2one('real.estate', string='Nhà đất')
    search_demand_id = fields.Many2one('demand.estate.search', string='Yêu cầu tìm kiếm')
    # employee_concierge_id = fields.Many2many('res.partner', 'offering_estate_res_partner_rel',
    #                                          string='Nhân viên dắt khách')
    state = fields.Selection([('draft', "Nháp"),
                              ('new', "Mới ghép"),
                              ('done', "Hoàn thành")], default="draft",
                             string="Trạng thái")
    date = fields.Datetime(string="Ngày dắt khách",  default=fields.Datetime.now )