from odoo import _, api, fields, models


class DetailContact(models.TransientModel):
    _name = 'detail.contact'
    _description = 'Detail Contact'

    street_id = fields.Many2one('res.street', 'Đường')
    number_house = fields.Char('Số nhà')
    address_ward_district_show = fields.Html(string='Phường - Quận')
    contact = fields.Html('Liên hệ')
    job_profession_id = fields.Many2one('job.profession', string='Ngành nghề')
    source_image = fields.Selection([('newspaper', 'Báo'),
                                     ('survey', 'Khảo sát'),
                                     ('online', 'Online'),
                                     ('cooperate', 'Ký gửi/Hợp tác')],
                                    string='Nguồn tìm về', default='newspaper')
    source_estate_partner_ids = fields.Many2many(
        comodel_name='res.partner',
        relation='detail_contact_source_house_res_partner_rel',
        string='Nguồn nhà từ'
    )
    source_image_partner_ids = fields.Many2many(
        comodel_name='res.partner',
        relation='detail_contact_source_image_res_partner_rel',
        string='Nguồn hình từ')
    estate_id = fields.Many2one('real.estate', 'Nhà đất')
    partner_ids = fields.Many2many('res.partner', 'detail_contact_wz_res_partner_rel', string='Liên hệ')
    estate_ids = fields.Many2many('real.estate', 'detail_contact_wz_real_estate_rel', string='Căn nhà')

    def get_demand_estate_search_ids(self):
        estate = f"AND re.id = {self.estate_id.id}"
        query = f"""
           SELECT des.id

                from demand_estate_search des

                LEFT join demand_estate_search_real_estate_rel desrer on desrer.demand_estate_search_id = des.id
                LEFT join real_estate re on re.id = desrer.real_estate_id
            WHERE 1 = 1
            and des.partner_id is not NULL
            {estate}
        """
        self.env.cr.execute(query)
        demand_estate_search_ids = [result.get('id') for result in self.env.cr.dictfetchall()]
        return demand_estate_search_ids

    def get_offered_search_demand_ids(self):
        estate_condition = f"AND demand_id = {self.estate_id.id}"

        query = f"""
            SELECT search_demand_id
            FROM offering_estate
            WHERE 1 = 1
            {estate_condition}
        """
        self.env.cr.execute(query)

        # Sử dụng đúng tên cột 'search_demand_id'
        offered_search_demand_ids = [result.get('search_demand_id') for result in self.env.cr.dictfetchall()]

        return offered_search_demand_ids

    def action_greeting_customer_estate_views(self):
        demand_estate_search_ids = self.get_demand_estate_search_ids()
        offered_search_demand_ids = self.get_offered_search_demand_ids()
        search_demand_other = self.env['demand.estate.search'].search(
            [('id', 'not in', demand_estate_search_ids), ('partner_id', '!=', False),
             ('partner_id', '!=', None), ('id', 'not in', offered_search_demand_ids)])
        demand_estate_search_obj = self.env['demand.estate.search'].browse(demand_estate_search_ids)
        demand_estate_search_not_offered_obj = demand_estate_search_obj.filtered(
            lambda rec: rec.id not in offered_search_demand_ids)
        context = {
            'default_estate_id': self.estate_id.id,
            'default_search_demand_ids': demand_estate_search_not_offered_obj.ids if demand_estate_search_not_offered_obj else None,
            'default_offered_search_demand_ids': offered_search_demand_ids,
            'default_search_demand_other_ids': search_demand_other.ids if search_demand_other else None,
            'active_model': 'real.estate',
            'active_id': self.estate_id.id,
        }
        return {
            'name': "Chào nhà",
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'greeting.customer.estate',
            'view_id': self.env.ref('fs_real_estate.greeting_customer_estate_view_form').id,
            'target': 'new',
            'context': context,
        }
