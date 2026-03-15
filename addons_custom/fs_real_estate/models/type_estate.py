from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import date, datetime, timedelta


class TypeEstate(models.Model):
    _name = 'type.estate'
    _description = 'Type Estate'
    _rec_name = 'name'

    name = fields.Char(string="Tên")
    color = fields.Char(string="Màu")
    note = fields.Text(string="Ghi chú")
