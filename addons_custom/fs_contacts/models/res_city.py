from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import date, datetime, timedelta


class ResCity(models.Model):
    _inherit = 'res.city'

    district_ids = fields.One2many('res.district','city_id',string='Quận/Huyện')
    country_id = fields.Many2one('res.country', string='Country', required=False)
