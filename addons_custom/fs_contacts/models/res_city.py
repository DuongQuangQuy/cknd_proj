from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import date, datetime, timedelta


class ResCity(models.Model):
    _inherit = 'res.city'

    district_ids = fields.One2many('res.district','city_id',string='Quận/Huyện')
    country_id = fields.Many2one('res.country', string='Country', required=False)
    is_prioritize = fields.Boolean(string='Ưu tiên tìm kiếm', default=False, help='Đánh dấu các thành phố ưu tiên hiển thị trên website')
