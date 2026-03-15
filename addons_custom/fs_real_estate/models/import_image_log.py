from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import date, datetime, timedelta


class ImportImageLog(models.Model):
    _name = 'import.image.log'
    _description = 'Import Image Log'

    old_id = fields.Char(string='Old ID', required=True)
    image_path = fields.Char(string='Image Path', required=True)
    