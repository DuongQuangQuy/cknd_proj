from odoo import _, api, fields, models


class RealEstateAdvertisingTemplate(models.Model):
    _name = 'real.estate.advertising.template'

    name = fields.Char(string='Name')
    advertising_template = fields.Text(string='Text template')

    @api.model
    def create(self, vals):
        res = super(RealEstateAdvertisingTemplate, self).create(vals)
        self.env['ir.model.fields'].create({
                    'model_id': self.env['ir.model']._get_id('advertising.sample.wizard'),
                    'name': f"x_advertising_template_{res.id}",
                    'ttype': 'html',
                    'compute': f"for record in self: record['x_advertising_template_{res.id}'] = record._compute_advertising_template()",
                    'depends': 'real_estate_id',
                    'store': False
                })
        return res

    def unlink(self):
        for record in self:
            field = self.env['ir.model.fields']._get('advertising.sample.wizard', f"x_advertising_template_{record.id}")
            field.unlink()
        return super(RealEstateAdvertisingTemplate, self).unlink()