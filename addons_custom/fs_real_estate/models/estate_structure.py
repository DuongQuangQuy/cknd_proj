from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import date, datetime, timedelta


class EstateStructure(models.Model):
    _name = 'estate.structure'
    _description = 'Estate Structure'
    _rec_name = 'name'

    name = fields.Char(string='Tên')
