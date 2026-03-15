from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import date, datetime, timedelta


class EstateStair(models.Model):
    _name = 'estate.stair'
    _description = 'Estate Stair'
    _rec_name = 'name'

    name = fields.Char(string='Tên')