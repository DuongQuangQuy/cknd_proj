from odoo import _, api, fields, models


class GreetingCustomerEstate(models.TransientModel):
    _name = 'greeting.customer.estate'
    _description = 'Greeting Customer Estate'

    partner_id = fields.Many2one("res.partner", string="Khách hàng")
    search_partner = fields.Char('Tìm kiếm thông tin khách hàng')
    estate_id = fields.Many2one("real.estate", string="Nhà đất")
    search_demand_ids = fields.Many2many('demand.estate.search', 'greeting_customer_estate_demand_estate_search_rel',
                                         string='Yêu cầu phù hợp')
    search_demand_other_ids = fields.Many2many('demand.estate.search',
                                               'other_greeting_customer_estate_demand_estate_search_rel',
                                               string='Yêu cầu khác')
    offered_search_demand_ids = fields.Many2many('demand.estate.search',
                                                 'offered_greeting_customer_estate_demand_estate_search_rel',
                                                 string='Yêu cầu đã chào')

    def search_partner_id(self):
        # Tách các từ khóa dựa trên dấu phẩy và loại bỏ khoảng trắng thừa
        keywords = [keyword.strip() for keyword in self.search_partner.split(',')]
        conditions = []
        for keyword in keywords:
            condition = f"""(
                name ILIKE '%{keyword}%'
                OR mobile ILIKE '%{keyword}%'
                OR mobile_2 ILIKE '%{keyword}%'
                OR mobile_3 ILIKE '%{keyword}%'
                OR mobile_4 ILIKE '%{keyword}%'
                OR code ILIKE '%{keyword}%'
            )"""
            conditions.append(condition)

        sql_conditions = " or ".join(conditions)

        query = f"""
            SELECT id
            FROM res_partner
            WHERE {sql_conditions}
        """

        # Thực thi truy vấn SQL
        self.env.cr.execute(query)
        return [result[0] for result in self.env.cr.fetchall()]

    def get_demand_estate_search_ids(self):
        estate = f"AND re.id = {self.estate_id.id}"
        search_partner = ''
        if self.search_partner:
            partner_ids = self.search_partner_id()
            if partner_ids:
                partners = self.env['res.partner'].browse(partner_ids)
                search_partner = f"AND rp.id in ({','.join(map(str, partners.ids))})"
            else:
                search_partner = f"AND false"
        query = f"""
           SELECT des.id

                from demand_estate_search des

                LEFT join demand_estate_search_real_estate_rel desrer on desrer.demand_estate_search_id = des.id
                LEFT join real_estate re on re.id = desrer.real_estate_id
                LEFT join res_partner rp on rp.id = des.partner_id
            WHERE 1 = 1
            and des.partner_id is not NULL
            {estate}
            {search_partner}
        """
        self.env.cr.execute(query)
        demand_estate_search_ids = [result.get('id') for result in self.env.cr.dictfetchall()]
        return demand_estate_search_ids

    def get_offered_search_demand_ids(self):
        estate = f"AND oe.demand_id = {self.estate_id.id}"
        search_partner = ''
        if self.search_partner:
            partner_ids = self.search_partner_id()
            if partner_ids:
                partners = self.env['res.partner'].browse(partner_ids)
                search_partner = f"AND rp.id in ({','.join(map(str, partners.ids))})"
            else:
                search_partner = f"AND false"

        query = f"""
                   SELECT oe.search_demand_id
                    from offering_estate oe 
                    left JOIN res_partner rp on rp.id = oe.customer_id

                    WHERE 1 = 1
                    {estate}
                    {search_partner}
                """
        self.env.cr.execute(query)
        offered_search_demand_ids = [result.get('id') for result in self.env.cr.dictfetchall()]
        return offered_search_demand_ids

    def button_search_infor_customer(self):
        demand_estate_search_ids = self.get_demand_estate_search_ids()
        offered_search_demand_ids = self.get_offered_search_demand_ids()
        search_demand_other = self.env['demand.estate.search'].search(
            [('id', 'not in', demand_estate_search_ids), ('partner_id', '!=', False),
             ('partner_id', '!=', None)])
        context = {
            'default_estate_id': self.estate_id.id,
            'default_search_demand_ids': demand_estate_search_ids,
            'default_offered_search_demand_ids': offered_search_demand_ids,
            'default_search_demand_other_ids': search_demand_other.ids if search_demand_other else None,
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
