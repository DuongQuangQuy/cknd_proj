from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import date, datetime, timedelta


class RealEstateSearch(models.Model):
    _name = 'real.estate.search'
    _description = 'Real Estate Search'

    @api.model
    def default_get(self, fields):
        vals = super(RealEstateSearch, self).default_get(fields)
        recent_estates = self.env['real.estate'].search([], limit=40)
        vals['real_estate_ids'] = [(6, 0, recent_estates.ids)]
        return vals

    code = fields.Char(string="Mã số")
    contact = fields.Char(string="Liên hệ")
    note = fields.Char(string="Ghi chú")
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
    number_house_from = fields.Char('Số nhà từ')
    number_house_to = fields.Char('Số nhà đến')
    number_house = fields.Char('Số nhà(Cố định)')

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

    source_estate_partner_id = fields.Many2one(
        comodel_name='res.partner',
        string='Nguồn nhà từ'
    )
    source_image = fields.Selection([('newspaper', 'Báo'),
                                     ('survey', 'Khảo sát'),
                                     ('online', 'Online'),
                                     ('cooperate', 'Ký gửi/Hợp tác')],
                                    string='Nguồn tìm về')
    type_estate_ids = fields.Many2many('type.estate', 'real_estate_search_type_estate_rel', string='Loại Nhà/MB')
    group_style_id = fields.Many2one('group.style', string='Nhóm kiểu')
    style_ids = fields.Many2many('estate.style', 'real_estate_search_estate_style_rel', string='Kiểu MT/Hẻm')
    type_demand_ids = fields.Many2many('type.demand', 'real_estate_search_type_demand_rel', string='Nhu cầu Thuê/Bán')
    secondary_form_ids = fields.Many2many('secondary.form', 'real_estate_search_secondary_form_rel',
                                          string='Hình thức phụ')
    structure_ids = fields.Many2many('estate.structure', 'real_estate_search_estate_structure_rel', string='Cấu trúc')
    job_profession_ids = fields.Many2many('job.profession', 'real_estate_search_job_profession_rel',
                                          string='Ngành nghề')
    group_direction_id = fields.Many2one('group.direction', string='Nhóm hướng')
    way_ids = fields.Many2many('estate.way', 'real_estate_search_estate_way_rel', string='Lối đi')

    real_estate_ids = fields.Many2many('real.estate', 'real_estate_search_real_estate_rel', string='Nhà đất')
    type_number = fields.Selection([('even_number', 'Số chẵn'),
                                    ('odd_number', 'Số lẽ')], string='Kiểu số nhà')
    is_visiter = fields.Boolean(string='Là quyền cộng tác viên', compute='compute_is_visiter')
    favorite_id = fields.Many2one('real.estate.favorite', string='Favorite List')
    show_favorite = fields.Boolean(string='Show Favorite Field', default=False)
    bsearch = fields.Boolean(string=u"Search options", default="1")
    category_ids = fields.Many2many('estate.category', string='Định danh nhóm')
    direction_ids = fields.Many2many('estate.direction', string='Hướng')

    @api.onchange('category_ids')
    def onchange_category_ids(self):
        for rec in self:
            for category_id in rec.category_ids:
                if category_id.style_ids:
                    rec.style_ids = [(4, style_id.id) for style_id in category_id.style_ids]
                if category_id.direction_ids:
                    rec.direction_ids = [(4, direction_id.id) for direction_id in category_id.direction_ids]
                if category_id.ward_ids:
                    rec.ward_ids = [(4, ward_id.id) for ward_id in category_id.ward_ids]
                if category_id.district_ids:
                    rec.district_ids = [(4, district_id.id) for district_id in category_id.district_ids]

    def action_pager_next(self):
        for rec in self:
            rec.action_search_real_estate()

    def toggle_favorite_field(self):
        """
        Toggle hiển thị/ẩn trường favorite_id
        """
        for record in self:
            record.show_favorite = not record.show_favorite

    def compute_is_visiter(self):
        for rec in self:
            if self.env.user.has_group('fs_real_estate.group_real_estate_vister') and not self.env.user.has_group(
                    'fs_real_estate.group_real_estate_empoloyee') and self.env.user.partner_id not in rec.source_estate_partner_ids:
                rec.is_visiter = True
            else:
                rec.is_visiter = False

    def action_search_real_estate(self):
        for record in self:
            record.real_estate_ids = [(6, 0, record.get_real_estate_ids())]

    def get_real_estate_ids(self):
        note = ''
        if self.note:
            note = f"AND note ILIKE '{self.note}%'"

        code = ''
        if self.code:
            code = f"AND code ILIKE '{self.code}%'"
        ######## Horizontal #########
        horizontal = ''
        if self.horizontal_from and self.horizontal_to:
            horizontal = f"AND horizontal >= {self.horizontal_from} AND horizontal <= {self.horizontal_to}"
        elif self.horizontal_from:
            horizontal = f"AND horizontal >= {self.horizontal_from}"
        elif self.horizontal_to:
            horizontal = f"AND horizontal <= {self.horizontal_to}"
        #################
        ######## Length #########
        length = ''
        if self.length_from and self.length_to:
            length = f"AND length >= {self.length_from} AND length <= {self.length_to}"
        elif self.length_from:
            length = f"AND length >= {self.length_from}"
        elif self.length_to:
            length = f"AND length <= {self.length_to}"
        #################
        ######## acreage_area #########
        acreage_area = ''
        if self.acreage_area_from and self.acreage_area_to:
            acreage_area = f"AND acreage_area >= {self.acreage_area_from} AND acreage_area <= {self.acreage_area_to}"
        elif self.acreage_area_from:
            acreage_area = f"AND acreage_area >= {self.acreage_area_from}"
        elif self.acreage_area_to:
            acreage_area = f"AND acreage_area <= {self.acreage_area_to}"
        #################
        ######## acreage_use #########
        acreage_use = ''
        if self.acreage_use_from and self.acreage_use_to:
            acreage_use = f"AND acreage_use >= {self.acreage_use_from} AND acreage_use <= {self.acreage_use_to}"
        elif self.acreage_use_from:
            acreage_use = f"AND acreage_use >= {self.acreage_use_from}"
        elif self.acreage_use_to:
            acreage_use = f"AND acreage_use <= {self.acreage_use_to}"
        #################
        ######## total_price #########
        total_price = ''
        if self.total_price_from and self.total_price_to:
            total_price = f"AND total_price >= {self.total_price_from} AND total_price <= {self.total_price_to}"
        elif self.total_price_from:
            total_price = f"AND total_price >= {self.total_price_from}"
        elif self.total_price_to:
            total_price = f"AND total_price <= {self.total_price_to}"
        #################
        ######## date_entry #########
        date_entry = ''
        if self.date_entry_from and self.date_entry_to:
            date_entry = f"AND date_entry >= '{self.date_entry_from}' AND date_entry <= '{self.date_entry_to}'"
        elif self.date_entry_from:
            date_entry = f"AND date_entry >= '{self.date_entry_from}'"
        elif self.date_entry_to:
            date_entry = f"AND date_entry <= '{self.date_entry_to}'"
        #################
        ######## date_contract_exp #########
        date_contract_exp = ''
        if self.date_contract_exp_from and self.date_contract_exp_to:
            date_contract_exp = f"AND date_contract_exp >= '{self.date_contract_exp_from}' AND date_contract_exp <= '{self.date_contract_exp_to}'"
        elif self.date_contract_exp_from:
            date_contract_exp = f"AND date_contract_exp >= '{self.date_contract_exp_from}'"
        elif self.date_contract_exp_to:
            date_contract_exp = f"AND date_contract_exp <= '{self.date_contract_exp_to}'"
        #################
        ######## date_updated #########
        date_updated = ''
        if self.date_updated_from and self.date_updated_to:
            date_updated = f"AND date_updated >= '{self.date_updated_from}' AND date_updated <= '{self.date_updated_to}'"
        elif self.date_updated_from:
            date_updated = f"AND date_updated >= '{self.date_updated_from}'"
        elif self.date_updated_to:
            date_updated = f"AND date_updated <= '{self.date_updated_to}'"
        #################
        ######## address #########
        street = ''
        if self.street_ids:
            street = f"AND street_id IN ({','.join(map(str, self.street_ids.ids))})"
        ward = ''
        if self.ward_ids:
            ward = f"AND ward_id IN ({','.join(map(str, self.ward_ids.ids))})"
        district = ''
        if self.district_ids:
            district = f"AND district_id IN ({','.join(map(str, self.district_ids.ids))})"
        city = ''
        if self.city_ids:
            city = f"AND city_id IN ({','.join(map(str, self.city_ids.ids))})"

        #################
        ######## Source Estate Partner #########
        source_estate_partner = ''
        if self.source_estate_partner_id:
            source_estate_partner = f"""
                   AND EXISTS (
                       SELECT 1
                       FROM real_estate_source_house_res_partner_rel AS rel
                       WHERE rel.real_estate_id = real_estate.id
                       AND rel.res_partner_id = {self.source_estate_partner_id.id}
                   )
               """
        #################
        source_image = ''
        if self.source_image:
            source_image = f"AND source_image = '{self.source_image}'"

        type_estate = ''
        if self.type_estate_ids:
            type_estate = f"AND type_estate_id IN ({','.join(map(str, self.type_estate_ids.ids))})"
        group_style = ''
        if self.group_style_id:
            if self.group_style_id.style_ids:
                group_style = f"AND style_id IN ({','.join(map(str, self.group_style_id.style_ids.ids))})"
            else:
                group_style = "AND false"

        style = ''
        if self.style_ids:
            style = f"AND style_id in ({','.join(map(str, self.style_ids.ids))})"

        direction = ''
        if self.direction_ids:
            direction = f"AND direction_id in ({','.join(map(str, self.direction_ids.ids))})"

        structure = ''
        if self.structure_ids:
            structure = f"""AND EXISTS (
                SELECT 1
                FROM estate_structure_real_estate_rel AS esrl
                WHERE esrl.real_estate_id = real_estate.id
                AND esrl.estate_structure_id IN ({','.join(map(str, self.structure_ids.ids))})
            )"""

        type_demand = ''
        if self.type_demand_ids:
            style = f"AND type_demand_id in ({','.join(map(str, self.type_demand_ids.ids))})"

        secondary_form = ''
        if self.secondary_form_ids:
            secondary_form = f"AND secondary_form_id in ({','.join(map(str, self.secondary_form_ids.ids))})"
        job_profession = ''
        if self.job_profession_ids:
            job_profession = f"AND job_profession_id in ({','.join(map(str, self.job_profession_ids.ids))})"

        group_direction = ''
        if self.group_direction_id:
            if self.group_direction_id.direction_ids:
                group_direction = f"AND direction_id IN ({','.join(map(str, self.group_direction_id.direction_ids.ids))})"
            else:
                group_direction = "AND false"
        way_id = ''
        if self.way_ids:
            way_id = f"AND way_id in ({','.join(map(str, self.way_ids.ids))})"
        contact = ''
        if self.contact:
            partners = self.search_partner()
            if partners:
                role_estate = self.env['role.estate'].search([('partner_id', 'in', partners)])
                if role_estate:
                    contact = f"AND id IN ({','.join(map(str, role_estate.estate_id.ids))})"
                else:
                    contact = "AND false"
            else:
                contact = "AND false"
        number_house_exact = ''
        if self.number_house:
            number_house_exact = f"AND number_house ILIKE '{self.number_house}%'"
        
        number_house = ''
        if self.number_house_from or self.number_house_to:
            conditions = []
            if self.number_house_from:
                conditions.append(
                    f"number_house ~ '^[0-9]+' AND CAST(substring(number_house FROM '^[0-9]+') AS INTEGER) >= {self.number_house_from}")
            if self.number_house_to:
                conditions.append(
                    f"number_house ~ '^[0-9]+' AND CAST(substring(number_house FROM '^[0-9]+') AS INTEGER) <= {self.number_house_to}")

            # Kết hợp các điều kiện
            number_house = f"AND ({' AND '.join(conditions)})"

        type_number_condition = ''
        if self.type_number:
            if self.type_number == 'even_number':
                type_number_condition = """
                    AND number_house ~ '^[0-9]+'
                    AND CAST(substring(number_house FROM '^[0-9]+') AS INTEGER) % 2 = 0
                """
            elif self.type_number == 'odd_number':
                type_number_condition = """
                    AND number_house ~ '^[0-9]+'
                    AND CAST(substring(number_house FROM '^[0-9]+') AS INTEGER) % 2 = 1
                """

        query = f"""
            SELECT id
            FROM real_estate
            WHERE 1 = 1
            {code}
            {horizontal}
            {length}
            {acreage_area}
            {acreage_use}
            {total_price}
            {date_entry}
            {date_contract_exp}
            {date_updated}
            {note}
            {street}
            {ward}
            {district}
            {city}
            {number_house_exact}
            {number_house}
            {source_estate_partner}
            {source_image}
            {type_estate}
            {group_style}
            {style}
            {structure}
            {type_demand}
            {secondary_form}
            {job_profession}
            {group_direction}
            {way_id}
            {contact}
            {type_number_condition}
            {direction}
        """
        self.env.cr.execute(query)
        real_estate_ids = [result.get('id') for result in self.env.cr.dictfetchall()]

        if self.favorite_id and self.show_favorite:
            favorite_estate_ids = self.favorite_id.estate_ids.ids
            if favorite_estate_ids:
                # Chỉ giữ lại các ID có trong cả danh sách kết quả tìm kiếm và danh sách yêu thích
                real_estate_ids = list(set(real_estate_ids).intersection(set(favorite_estate_ids)))
        return real_estate_ids

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
