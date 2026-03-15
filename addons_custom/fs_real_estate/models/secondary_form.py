from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import date, datetime, timedelta


class SecondaryForm(models.Model):
    _name = 'secondary.form'
    _description = 'Secondary Form'
    _rec_name = 'name'

    name = fields.Char(string="Tên")