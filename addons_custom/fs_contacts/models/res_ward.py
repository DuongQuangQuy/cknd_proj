from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import date, datetime, timedelta


class ResWard(models.Model):
    _name = 'res.ward'
    _description = 'Res Ward'
    _rec_name = 'name_display'

    name = fields.Char(string='Tên',required=True)
    district_id = fields.Many2one('res.district', string='Quận/Huyện')
    street_ids = fields.Many2many(
        'res.street',  # Model liên kết
        'ward_street_rel',  # Tên bảng quan hệ
        'ward_id',  # Tên cột cho trường 'res.ward'
        'street_id',  # Tên cột cho trường 'res.street'
        string='Đường'
    )
    city_id = fields.Many2one('res.city', related='district_id.city_id', string='Thành phố', store=True)
    name_display = fields.Char(string='Tên hiển thị', compute='_compute_name_display', store=True)

    @api.depends("district_id.name", "district_id", "name")
    def _compute_name_display(self):
        for rec in self:
            if not rec.district_id:
                rec.name_display = rec.name
            else:
                rec.name_display = f'{rec.name} - {rec.district_id.name}'
    def add_street(self):
        return {
            'type': 'ir.actions.act_window',
            'name': self.name,
            'view_mode': 'form',
            'view_type': 'form',
            'res_model': 'res.ward',
            'view_id': self.env.ref('fs_contact.res_ward_view_form').id,
            'res_id': self.id,
            'target': 'new',
        }

    def update_name(self):
        for rec in self:
            rec._compute_name_display()