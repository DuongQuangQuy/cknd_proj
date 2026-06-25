from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import date, datetime, timedelta
import re


class ResCurrency(models.Model):
    _inherit = 'res.currency'

    name = fields.Char(string='Currency', size=1000, required=True, help="Currency Code (ISO 4217)")