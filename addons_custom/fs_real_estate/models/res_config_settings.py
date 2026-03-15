from odoo import api, fields, models, _


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    number_exp = fields.Integer(string='Số ngày tính hạn',
                          config_parameter='fs_real_estate.number_exp')

