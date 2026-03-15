from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import date, datetime, timedelta


class ResDistrict(models.Model):
    _name = 'res.district'
    _description = 'Res District'
    _rec_name = 'name_display'

    name = fields.Char(string='Tên',required=True)
    name_display = fields.Char(string='Tên hiển thị', compute='_compute_name_display', store=True)
    city_id = fields.Many2one('res.city', string='Thành phố')
    ward_ids = fields.One2many('res.ward', 'district_id', string='Phường')

    @api.depends("city_id.name","city_id", "name")
    def _compute_name_display(self):
        for rec in self:
            if not rec.city_id:
                rec.name_display = rec.name
            else:
                rec.name_display = f'{rec.name} - {rec.city_id.name}'

    def update_name(self):
        for rec in self:
            rec._compute_name_display()


    def add_ward(self):
        return {
            'type': 'ir.actions.act_window',
            'name': self.name,
            'view_mode': 'form',
            'view_type': 'form',
            'res_model': 'res.district',
            'view_id': self.env.ref('fs_contact.res_district_view_form').id,
            'res_id': self.id,
            'target': 'new',
        }




