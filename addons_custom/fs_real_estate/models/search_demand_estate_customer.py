from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import date, datetime, timedelta


class SearchDemandEstateCustomer(models.Model):
    _name = 'search.demand.estate.customer'
    _description = 'Search Demand Estate Customer'

    user_id = fields.Many2one('res.users',string='NV phụ trách')
    evaluate = fields.Selection([
        ('friendly', 'Thân thiện'),
        ('potential', 'Tiềm năng'),
        ('order', 'Đặt hàng'),
    ], string="Đánh giá")


    code = fields.Char(string="Mã số")
    contact = fields.Char(string="Liên hệ")
    note = fields.Text(string="Ghi chú")
    date_entry_from = fields.Datetime(string="Ngày nhập từ")
    date_entry_to = fields.Datetime(string="Ngày nhập đến")
    date_contract_exp_from = fields.Date(string="Ngày hết hạn HĐ từ")
    date_contract_exp_to = fields.Date(string="Ngày hết hạn HĐ đến")
    date_updated_from = fields.Datetime(string="Ngày cập nhật từ")
    date_updated_to = fields.Datetime(string="Ngày cập nhật đến")

    # Address
    street_ids = fields.Many2many('res.street', string='Đường')
    ward_ids = fields.Many2many('res.ward', string='Phường')
    district_ids = fields.Many2many('res.district', string='Quận/Huyện')
    city_ids = fields.Many2many('res.city', string='Thành phố')
    number_house = fields.Char('Số nhà')

    # Real estate structure dimensions
    horizontal_from = fields.Float('Ngang từ')
    horizontal_to = fields.Float('Ngang đến')
    acreage_area_from = fields.Float('DTKV từ')
    acreage_area_to = fields.Float('DTKV đến')
    length_from = fields.Float('Dài từ')
    length_to = fields.Float('Dài đến')
    acreage_use_from = fields.Float('DTSD từ')
    acreage_use_to = fields.Float('DTSD đến')

    # Price
    total_price_from = fields.Float('Giá từ')
    total_price_to = fields.Float('Giá đến')

    # source_estate_partner_id = fields.Many2one(
    #     comodel_name='res.partner',
    #     string='Nguồn nhà từ'
    # )
    # source_image = fields.Selection([('newspaper', 'Báo'),
    #                                  ('survey', 'Khảo sát'),
    #                                  ('online', 'Online'),
    #                                  ('cooperate', 'Ký gửi/Hợp tác')],
    #                                 string='Nguồn tìm về')
    type_estate_ids = fields.Many2many('type.estate', 'search_demand_estate_customer_type_estate_rel', string='Loại')
    group_style_id = fields.Many2one('group.style', string='Nhóm kiểu')
    style_ids = fields.Many2many('estate.style', 'search_demand_estate_customer_estate_style_rel', string='Kiểu')
    type_demand_ids = fields.Many2many('type.demand', 'search_demand_estate_customer_type_demand_rel', string='Nhu cầu')
    secondary_form_ids = fields.Many2many('secondary.form', 'search_demand_estate_customer_secondary_form_rel',
                                          string='Hình thức phụ')
    structure_ids = fields.Many2many('estate.structure', 'search_demand_estate_customer_structure_rel', string='Cấu trúc')
    job_profession_ids = fields.Many2many('job.profession', 'search_demand_estate_customer_job_profession_rel',
                                          string='Ngành nghề')
    group_direction_id = fields.Many2one('group.direction', string='Nhóm hướng')
    way_ids = fields.Many2many('estate.way', 'search_demand_estate_customer_estate_way_rel', string='Lối đi')

    demand_estate_search_ids = fields.Many2many('demand.estate.search', 'search_demand_estate_customer_demand_estate_search_rel', string='Nhu cầu khách hàng')

    # state = fields.Selection([('requesting', 'Đang yêu cầu'),
    #                           ('stop_request', 'Ngưng yêu cầu'),
    #                           ('support_complete', 'Hỗ trợ thành công')],
    #                          string="Trạng thái", default='requesting')
    # note_customer = fields.Text('Ghi chú khách hàng')

    def action_search_real_estate(self):
        for record in self:
            record.demand_estate_search_ids = [(6, 0, record.get_real_estate_ids())]

    def get_real_estate_ids(self):
        note = ''
        if self.note:
            note = f"AND note ILIKE '{self.note}%'"

        code = ''
        if self.code:
            code = f"AND code ILIKE '{self.code}%'"
        contact = ''
        if self.contact:
            partners = self.search_partner()
            if partners:
                contact = f"AND partner_id IN ({','.join(map(str, partners))})"
            else:
                contact = "AND false"
        user = ''
        if self.user_id:
            user = f"AND user_id = {self.user_id.id}"
        evaluate = ''
        if self.evaluate:
            evaluate = f"AND evaluate = '{self.evaluate}'"
        street = ''
        if self.street_ids:
            street_ids = ','.join(map(str, self.street_ids.ids))
            # Thêm JOIN để xử lý quan hệ many2many
            street = f"""
            AND EXISTS (
                SELECT 1
                FROM demand_estate_search_res_street_rel AS rel
                WHERE rel.demand_estate_search_id = demand_estate_search.id
                AND rel.res_street_id IN ({street_ids})
            )
        """
        ward = ''
        if self.ward_ids:
            ward_ids = ','.join(map(str, self.ward_ids.ids))
            # Thêm JOIN để xử lý quan hệ many2many
            ward = f"""
                        AND EXISTS (
                            SELECT 1
                            FROM demand_estate_search_res_ward_rel AS rel
                            WHERE rel.demand_estate_search_id = demand_estate_search.id
                            AND rel.res_ward_id IN ({ward_ids})
                        )
                    """
        district = ''
        if self.district_ids:
            district_ids = ','.join(map(str, self.district_ids.ids))
            # Thêm JOIN để xử lý quan hệ many2many
            district = f"""
                                    AND EXISTS (
                                        SELECT 1
                                        FROM demand_estate_search_res_district_rel AS rel
                                        WHERE rel.demand_estate_search_id = demand_estate_search.id
                                        AND rel.res_district_id IN ({district_ids})
                                    )
                                """
        city = ''
        if self.city_ids:
            city_ids = ','.join(map(str, self.city_ids.ids))
            # Thêm JOIN để xử lý quan hệ many2many
            city = f"""
                                                AND EXISTS (
                                                    SELECT 1
                                                    FROM demand_estate_search_res_city_rel AS rel
                                                    WHERE rel.demand_estate_search_id = demand_estate_search.id
                                                    AND rel.res_city_id IN ({city_ids})
                                                )
                                            """
        number_house = ''
        if self.number_house:
            number_house = f"AND number_house ILIKE '{self.number_house}%'"
        group_direction = ''
        if self.group_direction_id:
            group_direction = f"AND group_direction_id = {self.group_direction_id.id}"
        group_style = ''
        if self.group_style_id:
            group_style = f"AND group_style_id = {self.group_style_id.id}"
        way_condition = ''
        if self.way_ids:
            way_ids = ','.join(map(str, self.way_ids.ids))
            # Sử dụng EXISTS để kiểm tra sự tồn tại của bản ghi trong bảng liên kết
            way_condition = f"""
                    AND EXISTS (
                        SELECT 1
                        FROM demand_estate_search_estate_way_rel AS rel
                        WHERE rel.demand_estate_search_id = demand_estate_search.id
                        AND rel.estate_way_id IN ({way_ids})
                    )
                """
        type_estate_condition = ''
        if self.type_estate_ids:
            type_estate_ids = ','.join(map(str, self.type_estate_ids.ids))
            # Sử dụng EXISTS để kiểm tra sự tồn tại của bản ghi trong bảng liên kết
            type_estate_condition = f"""
                    AND EXISTS (
                        SELECT 1
                        FROM demand_estate_search_type_estate_rel AS rel
                        WHERE rel.demand_estate_search_id = demand_estate_search.id
                        AND rel.type_estate_id IN ({type_estate_ids})
                    )
                """
        style_condition = ''
        if self.style_ids:
            style_ids = ','.join(map(str, self.style_ids.ids))
            # Sử dụng EXISTS để kiểm tra sự tồn tại của bản ghi trong bảng liên kết
            style_condition = f"""
                    AND EXISTS (
                        SELECT 1
                        FROM demand_estate_search_estate_style_rel AS rel
                        WHERE rel.demand_estate_search_id = demand_estate_search.id
                        AND rel.estate_style_id IN ({style_ids})
                    )
                """
        type_demand_condition = ''
        if self.type_demand_ids:
            type_demand_ids = ','.join(map(str, self.type_demand_ids.ids))
            # Sử dụng EXISTS để kiểm tra sự tồn tại của bản ghi trong bảng liên kết
            type_demand_condition = f"""
                    AND EXISTS (
                        SELECT 1
                        FROM demand_estate_search_type_demand_rel AS rel
                        WHERE rel.demand_estate_search_id = demand_estate_search.id
                        AND rel.type_demand_id IN ({type_demand_ids})
                    )
                """
        secondary_form_condition = ''
        if self.secondary_form_ids:
            secondary_form_ids = ','.join(map(str, self.secondary_form_ids.ids))
            # Sử dụng EXISTS để kiểm tra sự tồn tại của bản ghi trong bảng liên kết
            secondary_form_condition = f"""
                    AND EXISTS (
                        SELECT 1
                        FROM demand_estate_search_secondary_form_rel AS rel
                        WHERE rel.demand_estate_search_id = demand_estate_search.id
                        AND rel.secondary_form_id IN ({secondary_form_ids})
                    )
                """
        structure_condition = ''
        if self.structure_ids:
            structure_ids = ','.join(map(str, self.structure_ids.ids))
            # Sử dụng EXISTS để kiểm tra sự tồn tại của bản ghi trong bảng liên kết
            structure_condition = f"""
                    AND EXISTS (
                        SELECT 1
                        FROM demand_estate_search_structure_rel AS rel
                        WHERE rel.demand_estate_search_id = demand_estate_search.id
                        AND rel.estate_structure_id IN ({structure_ids})
                    )
                """
        job_profession_condition = ''
        if self.job_profession_ids:
            job_profession_ids = ','.join(map(str, self.job_profession_ids.ids))
            # Sử dụng EXISTS để kiểm tra sự tồn tại của bản ghi trong bảng liên kết
            job_profession_condition = f"""
                    AND EXISTS (
                        SELECT 1
                        FROM demand_estate_search_job_profession_rel AS rel
                        WHERE rel.demand_estate_search_id = demand_estate_search.id
                        AND rel.job_profession_id IN ({job_profession_ids})
                    )
                """
        # Điều kiện cho date_entry_from và date_entry_to
        date_entry_condition = ''
        if self.date_entry_from:
            date_entry_condition += f"AND date_entry_from >= '{self.date_entry_from}'"
        if self.date_entry_to:
            date_entry_condition += f"AND date_entry_to <= '{self.date_entry_to}'"
        # Điều kiện cho ngày hết hạn hợp đồng
        date_contract_condition = ''
        if self.date_contract_exp_from:
            date_contract_condition += f"AND date_contract_exp_from >= '{self.date_contract_exp_from}'"
        if self.date_contract_exp_to:
            date_contract_condition += f"AND date_contract_exp_to <= '{self.date_contract_exp_to}'"
        # Điều kiện cho ngày cập nhật
        date_updated_condition = ''
        if self.date_updated_from:
            date_updated_condition += f"AND date_updated_from >= '{self.date_updated_from}'"
        if self.date_updated_to:
            date_updated_condition += f"AND date_updated_to <= '{self.date_updated_to}'"
        # Điều kiện cho ngang từ và ngang đến
        horizontal_condition = ''
        if self.horizontal_from:
            horizontal_condition += f"AND horizontal_from >= {self.horizontal_from}"
        if self.horizontal_to:
            horizontal_condition += f"AND horizontal_to <= {self.horizontal_to}"
        # Điều kiện cho diện tích đất từ và đến
        acreage_area_condition = ''
        if self.acreage_area_from:
            acreage_area_condition += f"AND acreage_area_from >= {self.acreage_area_from}"
        if self.acreage_area_to:
            acreage_area_condition += f"AND acreage_area_to <= {self.acreage_area_to}"
        # Điều kiện cho chiều dài từ và đến
        length_condition = ''
        if self.length_from:
            length_condition += f"AND length_from >= {self.length_from}"
        if self.length_to:
            length_condition += f"AND length_to <= {self.length_to}"
        # Điều kiện cho diện tích sử dụng từ và đến
        acreage_use_condition = ''
        if self.acreage_use_from:
            acreage_use_condition += f"AND acreage_use_from >= {self.acreage_use_from}"
        if self.acreage_use_to:
            acreage_use_condition += f"AND acreage_use_to <= {self.acreage_use_to}"
        # Điều kiện cho giá từ và đến
        total_price_condition = ''
        if self.total_price_from:
            total_price_condition += f"AND total_price_from >= {self.total_price_from}"
        if self.total_price_to:
            total_price_condition += f"AND total_price_to <= {self.total_price_to}"
        query = f"""
                SELECT id
                FROM demand_estate_search
                WHERE 1 = 1
                {note}
                {code}
                {contact}
                {user}
                {evaluate}
                {street}
                {ward}
                {district}
                {city}
                {number_house}
                {group_direction}
                {group_style}
                {way_condition}
                {type_estate_condition}
                {style_condition}
                {type_demand_condition}
                {secondary_form_condition}
                {structure_condition}
                {job_profession_condition}
                {date_entry_condition}
                {date_contract_condition}
                {date_updated_condition}
                {horizontal_condition}
                {acreage_area_condition}
                {length_condition}
                {acreage_use_condition}
                {total_price_condition}
            """
        self.env.cr.execute(query)
        demand_estate_search_ids = [result.get('id') for result in self.env.cr.dictfetchall()]
        return demand_estate_search_ids

    def search_partner(self):
        # Tách các từ khóa dựa trên dấu phẩy và loại bỏ khoảng trắng thừa
        keywords = [keyword.strip() for keyword in self.contact.split(',')]
        conditions = []
        for keyword in keywords:
            condition = f"""(
                    name ILIKE '%{keyword}%'
                    OR mobile ILIKE '%{keyword}%'
                    OR mobile_2 ILIKE '%{keyword}%'
                    OR mobile_3 ILIKE '%{keyword}%'
                    OR mobile_4 ILIKE '%{keyword}%'
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