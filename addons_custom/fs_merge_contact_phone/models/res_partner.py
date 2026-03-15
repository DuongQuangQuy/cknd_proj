from odoo import _, api, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def unlink(self):
        print('---------')
        return super().unlink()
    