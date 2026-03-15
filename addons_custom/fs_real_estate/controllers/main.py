from odoo import http, _
from odoo.http import request

class AdvertisingSampleController(http.Controller):

    @http.route('/advertising_sample/copy', auth='user', type='json')
    def delete_lines(self, content):
        return request.env['advertising.sample.wizard'].copy_sample(content)