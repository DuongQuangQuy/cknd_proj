from odoo import _, api, fields, models


class GreetingCustomerEmployee(models.TransientModel):
    _name = 'greeting.customer.employee'
    _description = 'Greeting Customer Employee'

    customer_id = fields.Many2one("res.partner", string="Khách hàng")
    partner_id = fields.Many2one('res.partner', string='NV ghép nhà')
    estate_id = fields.Many2one("real.estate", string="Nhà đất")
    search_demand_id = fields.Many2one('demand.estate.search', string='Yêu cầu tìm kiếm')
    offering_estate_id = fields.Many2one('offering.estate', string='Chào khách')

    def vals_offering_history(self):
        return {
            'customer_id': self.customer_id.id if self.customer_id else None,
            'demand_id': self.estate_id.id,
            'search_demand_id': self.id,
            'state': 'new',
            'offering_id': self.offering_estate_id.id,
            'partner_id': self.partner_id.id
        }

    def button_done_greeted(self):
        self.offering_estate_id.write({
            'state': 'new'
        })
        vals_offering_history = self.vals_offering_history()
        offering_estate = self.env['offering.history'].create(vals_offering_history)
