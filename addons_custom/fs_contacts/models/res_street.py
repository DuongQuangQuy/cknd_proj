from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import date, datetime, timedelta


class ResStreet(models.Model):
    _name = 'res.street'
    _description = 'Res Street'
    _rec_name = 'name'

    name = fields.Char(string="Tên",required=False)
    # ward_ids = fields.Many2many('res.ward','res_street_res_ward_rel','street_id',  # Tên cột cho trường 'res.street'
    #     'ward_id','Phường')
    ward_ids = fields.Many2many(
        'res.ward',  # Model liên kết
        'street_ward_rel',  # Tên bảng quan hệ
        'street_id',  # Tên cột cho trường 'res.street'
        'ward_id',  # Tên cột cho trường 'res.ward'
        string='Phường'
    )