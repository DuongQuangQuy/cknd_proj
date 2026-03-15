from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import date, datetime, timedelta


class RoleDetail(models.Model):
    _name = 'role.detail'
    _description = 'Role Detail'
    _rec_name = 'name'

    name = fields.Char(string='Tên', required=True)

