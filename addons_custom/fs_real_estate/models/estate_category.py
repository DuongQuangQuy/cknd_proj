from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import date, datetime, timedelta


class EstateCategory(models.Model):
    _name = 'estate.category'
    _description = 'Estate Category'
    _rec_name = 'name'

    name = fields.Char('Tên')
    style_ids = fields.Many2many('estate.style', 'estate_category_style_rel', string='Kiểu MT/Hẻm')
    direction_ids = fields.Many2many('estate.direction', string='Hướng')
    ward_ids = fields.Many2many('res.ward', string='Phường')
    district_ids = fields.Many2many('res.district', string='Quận/Huyện')
