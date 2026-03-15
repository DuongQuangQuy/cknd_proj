from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import date, datetime, timedelta


class RoleEstate(models.Model):
    _name = 'role.estate'
    _description = 'Role Estate'
    _rec_name = 'name'

    name = fields.Char(string='Tên',related='role_detail_id.name',store=True)
    partner_id = fields.Many2one('res.partner', 'Liên hệ',required=False)
    estate_id = fields.Many2one('real.estate', 'Nhà đất')
    role_detail_id = fields.Many2one('role.detail', 'Vai trò')

    # @api.model_create_multi
    # def create(self, vals_list):
    #     records = super(RoleEstate, self).create(vals_list)
    #     if records.partner_id:
    #         records.partner_id.estate_ids = [(4, records.estate_id.id)]
    #     return records
    #
    # def write(self, vals):
    #     for rec in self:
    #         old_partner_id = rec.partner_id.id  # Lưu giá trị partner_id trước khi cập nhật
    #
    #         # Gọi hàm ghi cập nhật các giá trị mới
    #         result = super(RoleEstate, rec).write(vals)
    #
    #         # Kiểm tra nếu partner_id bị xóa hoặc thay đổi
    #         if 'partner_id' in vals:
    #             new_partner_id = vals.get('partner_id')
    #             estate_id = rec.estate_id.id
    #
    #             # Nếu partner_id bị xóa, xóa estate_id khỏi partner cũ
    #             if not new_partner_id and old_partner_id:
    #                 self.env['res.partner'].browse(old_partner_id).estate_ids = [(3, estate_id)]
    #
    #             # Nếu partner_id thay đổi, cập nhật lại ở cả partner cũ và mới
    #             elif new_partner_id and old_partner_id != new_partner_id:
    #                 self.env['res.partner'].browse(old_partner_id).estate_ids = [(3, estate_id)]
    #                 self.env['res.partner'].browse(new_partner_id).estate_ids = [(4, estate_id)]
    #         return result
    #
    # def unlink(self):
    #     for rec in self:
    #         rec.partner_id.estate_ids = [(3, rec.estate_id.id)]
    #         res = super(RoleEstate, self).unlink()
    #         return res

