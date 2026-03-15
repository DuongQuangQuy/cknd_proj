from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import date, datetime, timedelta


class GroupStyle(models.Model):
    _name = 'group.style'
    _description = 'Group Style'
    _rec_name = 'name'

    name = fields.Char(string='Tên')
    style_ids = fields.Many2many('estate.style', 'group_estate_style_rel', string='Kiểu')
