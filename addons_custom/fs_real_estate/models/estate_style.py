from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import date, datetime, timedelta


class EstateStyle(models.Model):
    _name = 'estate.style'
    _description = 'Estate Style'
    _rec_name = 'name'

    name = fields.Char(string='Tên')
    group_style_id = fields.Many2one('group.style', string='Nhóm kiểu')
