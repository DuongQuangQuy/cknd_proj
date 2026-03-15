from odoo import http, _
from odoo.http import request

class One2manySelectionController(http.Controller):

    @http.route('/one2many_selection/delete_lines', auth='user', type='json')
    def delete_lines(self, model, selected_ids):
        lines = request.env[model].sudo().browse(selected_ids)
        for line in lines:
            line.unlink()
        return True