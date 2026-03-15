from odoo import _, api, fields, models
from odoo.exceptions import UserError


class RealEstatePricesConfig(models.Model):
    _name = 'real.estate.prices.config'

    group_id = fields.Many2one('res.groups', string='Vai trò', domain=lambda self: "[('category_id', '=', %s)]" % self.env.ref('fs_real_estate.category_real_estate').id, required=1)
    price_from = fields.Float(string='Giá từ', required=1)
    price_to = fields.Float(string='Giá đến', required=1)

    @api.constrains('price_from', 'price_to')
    def _constrains_price(self):
        for record in self:
            if record.price_from >= record.price_to:
                raise UserError(_('Giá đến phải lớn hơn giá từ'))