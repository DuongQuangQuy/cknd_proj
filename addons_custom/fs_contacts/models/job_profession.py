from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import date, datetime, timedelta


class JobProfession(models.Model):
    _name = 'job.profession'
    _description = 'Job Profession'
    _rec_name = 'name'

    name = fields.Char(string="Tên")
