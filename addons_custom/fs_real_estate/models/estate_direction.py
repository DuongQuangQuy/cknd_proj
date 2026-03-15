from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import date, datetime, timedelta


class EstateDirection(models.Model):
    _name = 'estate.direction'
    _description = 'Estate Direction'
    _rec_name = 'name'

    name = fields.Char(string='Tên')