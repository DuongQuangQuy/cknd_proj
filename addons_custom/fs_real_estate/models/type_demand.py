from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import date, datetime, timedelta


class TypeDemand(models.Model):
    _name = 'type.demand'
    _description = 'Type Demand'
    _rec_name = 'name'

    name = fields.Char(string="Tên")
