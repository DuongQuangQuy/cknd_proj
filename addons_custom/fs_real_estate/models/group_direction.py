from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import date, datetime, timedelta


class GroupDirection(models.Model):
    _name = 'group.direction'
    _description = 'Group Direction'
    _rec_name = 'name'

    name = fields.Char(string='Tên', required=True)
    direction_ids = fields.Many2many('estate.direction', 'group_estate_direction_rel', string='Hướng')
