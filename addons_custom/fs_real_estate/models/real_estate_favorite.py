# models/real_estate_favorite.py
from odoo import models, fields, api, _
from datetime import datetime

class RealEstateFavorite(models.Model):
    _name = 'real.estate.favorite'
    _description = 'Real Estate Favorites'

    name = fields.Char(string='Name', required=True)
    user_id = fields.Many2one('res.users', string='User', default=lambda self: self.env.user.id, required=True)
    date_added = fields.Datetime(string='Date Added', default=fields.Datetime.now)
    estate_ids = fields.Many2many('real.estate', string='Properties')

    def save_favorites(self):
        return {'type': 'ir.actions.act_window_close'}