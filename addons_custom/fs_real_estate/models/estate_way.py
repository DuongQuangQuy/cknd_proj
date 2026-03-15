from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import date, datetime, timedelta


class EstateWay(models.Model):
    _name = 'estate.way'
    _description = 'Estate Way'
    _rec_name = 'name'

    name = fields.Char(string='Tên')