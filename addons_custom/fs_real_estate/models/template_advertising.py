from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import date, datetime, timedelta


class TemplateAdvertising(models.Model):
    _name = 'template.advertising'
    _description = 'Template Advertising'

    name = fields.Char(string='Name', required=True)
    content = fields.Text('Nội dung quảng cáo')
