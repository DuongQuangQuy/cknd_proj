from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import date, datetime, timedelta


class DemandEstateSearch(models.Model):
    _name = 'demand.estate.search'
    _description = 'Demand Estate Search'
    _rec_name = 'partner_id'

    date_request = fields.Datetime(string="Ngày nhận yêu cầu", default=lambda self: fields.Datetime.now())
    user_id = fields.Many2one('res.users', string='NV phụ trách')
    name = fields.Char(string='Yêu cầu')
    date_exp = fields.Date(string="Ngày hết hạn")
    evaluate = fields.Selection([
        ('friendly', 'Thân thiện'),
        ('potential', 'Tiềm năng'),
        ('order', 'Đặt hàng'),
    ], string="Đánh giá")
    partner_id = fields.Many2one('res.partner', string='Khách hàng')
    company_id = fields.Many2one('res.company', string='Dữ liệu thuộc về')

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

    source_estate_partner_id = fields.Many2one(
        comodel_name='res.partner',
        string='Nguồn nhà từ'
    )
    source_image = fields.Selection([('newspaper', 'Báo'),
                                     ('survey', 'Khảo sát'),
                                     ('online', 'Online'),
                                     ('cooperate', 'Ký gửi/Hợp tác')],
                                    string='Nguồn tìm về')
    type_estate_ids = fields.Many2many('type.estate', 'demand_estate_search_type_estate_rel', string='Loại')
    group_style_id = fields.Many2one('group.style', string='Nhóm kiểu')
    style_ids = fields.Many2many('estate.style', 'demand_estate_search_estate_style_rel', string='Kiểu')
    type_demand_ids = fields.Many2many('type.demand', 'demand_estate_search_type_demand_rel', string='Nhu cầu')
    secondary_form_ids = fields.Many2many('secondary.form', 'demand_estate_search_secondary_form_rel',
                                          string='Hình thức phụ')
    structure_ids = fields.Many2many('estate.structure', 'demand_estate_search_structure_rel', string='Cấu trúc')
    job_profession_ids = fields.Many2many('job.profession', 'demand_estate_search_job_profession_rel',
                                          string='Ngành nghề')
    group_direction_id = fields.Many2one('group.direction', string='Nhóm hướng')
    way_ids = fields.Many2many('estate.way', 'demand_estate_search_estate_way_rel', string='Lối đi')

    real_estate_ids = fields.Many2many('real.estate', 'demand_estate_search_real_estate_rel', string='Nhà đất')

    state = fields.Selection([('requesting', 'Đang yêu cầu'),
                              ('stop_request', 'Ngưng yêu cầu'),
                              ('support_complete', 'Hỗ trợ thành công')],
                             string="Trạng thái", default='requesting')
    note_customer = fields.Text('Ghi chú khách hàng')
    date_show = fields.Html(string='Ngày', compute='compute_date_show', store=True)
    date_call = fields.Datetime(string='Ngày gọi')
    dimension_info_show = fields.Html(string='Thông tin kích thước', compute='compute_dimension_info_show')
    offering_estate_ids = fields.One2many('offering.estate', 'search_demand_id', string='Lịch sử chào nhà')

    def get_real_estate(self):
        if self.env.context.get('active_model') == 'real.estate':
            real_estate = self.env['real.estate'].browse(int(self.env.context.get('active_id')))
        else:
            greeting_customer_estate = self.env['greeting.customer.estate'].browse(
                int(self.env.context.get('active_id')))
            real_estate = greeting_customer_estate.estate_id
        return real_estate

    def vals_offering_estate(self, real_estate):

        return {
            'customer_id': self.partner_id.id if self.partner_id else None,
            'demand_id': real_estate.id if real_estate else None,
            'search_demand_id': self.id,
        }

    def view_offering_estate(self):
        real_estate = self.get_real_estate()
        vals_offering_estate = self.vals_offering_estate(real_estate=real_estate)
        offering_estate = self.env['offering.estate'].create(vals_offering_estate)

        context = {
            'default_estate_id': real_estate.id if real_estate else None,
            'default_offering_estate_id': offering_estate.id,
            'default_customer_id':  self.partner_id.id if self.partner_id else None,
            'default_search_demand_id': self.id,
        }
        return {
            'name': "Chào nhà - Nhân viên dắt khách",
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'greeting.customer.employee',
            'view_id': self.env.ref('fs_real_estate.greeting_customer_employee_view_form').id,
            'target': 'new',
            'context': context,
        }


    @api.depends('horizontal_from', 'horizontal_to', 'acreage_area_from', 'acreage_area_to', 'length_from', 'length_to',
                 'acreage_use_from', 'acreage_use_to')
    def compute_dimension_info_show(self):
        for rec in self:
            dimension_info_show = ''
            if rec.horizontal_from != 0 and rec.horizontal_to != 0:
                dimension_info_show += '<span>Ngang:</span>%s - %s<br/>' % (rec.horizontal_from, rec.horizontal_to)
            elif rec.horizontal_from != 0 and not rec.horizontal_to:
                dimension_info_show += '<span>Ngang:</span> >= %s <br/>' % (rec.horizontal_from)

            elif not rec.horizontal_from  and  rec.horizontal_to != 0:

                dimension_info_show += '<span>Ngang:</span> <= %s <br/>' % (rec.horizontal_to)
            if rec.acreage_area_from != 0 and rec.acreage_area_to != 0:
                dimension_info_show += '<span>DTKV:</span>%s - %s<br/>' % (rec.acreage_area_from, rec.acreage_area_to)
            elif rec.acreage_area_from != 0 and not rec.acreage_area_to:
                dimension_info_show += '<span>DTKV:</span> >= %s <br/>' % (rec.acreage_area_from)

            elif not rec.acreage_area_from  and  rec.acreage_area_to != 0:

                dimension_info_show += '<span>DTKV:</span> <= %s <br/>' % (rec.acreage_area_to)
            if rec.length_from != 0 and rec.length_to != 0:
                dimension_info_show += '<span>Dài:</span>%s - %s<br/>' % (rec.length_from, rec.length_to)
            elif rec.length_from != 0 and not rec.length_to:
                dimension_info_show += '<span>Dài:</span> >= %s <br/>' % (rec.length_from)
            elif not rec.length_from and rec.length_to != 0:
                dimension_info_show += '<span>Dài:</span> <= %s <br/>' % (rec.length_to)
            if rec.acreage_use_from != 0 and rec.acreage_use_to != 0:
                dimension_info_show += '<span>DT sử dụng:</span>%s - %s<br/>' % (
                    rec.acreage_use_from, rec.acreage_use_to)

            elif rec.acreage_use_from != 0 and not rec.acreage_use_to:
                dimension_info_show += '<span>DT sử dụng:</span> >= %s <br/>' % (rec.acreage_use_from)
            elif not rec.acreage_use_from and rec.acreage_use_to != 0:
                dimension_info_show += '<span>DT sử dụng:</span> <= %s <br/>' % (rec.acreage_use_to)
            rec.dimension_info_show = dimension_info_show




    @api.depends('date_call', 'date_request', 'acreage_area_from')
    def compute_date_show(self):
        for rec in self:
            date_show = ''
            if rec.date_request:
                date_show += '<span style="font-weight: bold; color: black;">Ngày nhập:</span> %s <br/>' % (
                    rec.date_request.strftime('%d-%m-%Y'))
            if rec.date_call:
                date_show += '<span style="font-weight: bold; color: blue;"><i class="fa fa-phone" style="margin-right: 5px;"> Ngày gọi:</span> %s <br/>' % (
                    rec.date_call.strftime('%d-%m-%Y'))
            else:
                date_show += '<span style="font-weight: bold; color: red;">Chưa gọi</span>  <br/>'
            rec.date_show = date_show

    @api.model_create_multi
    def create(self, vals_list):
        records = super(DemandEstateSearch, self).create(vals_list)
        records.action_search_real_estate()
        return records

    def button_support_complete(self):
        for rec in self:
            rec.state = 'support_complete'

    def button_stop_request(self):
        for rec in self:
            rec.state = 'stop_request'

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
        number_house = ''
        if self.number_house:
            number_house = f"AND number_house ILIKE '{self.number_house}%'"
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
        """
        self.env.cr.execute(query)
        real_estate_ids = [result.get('id') for result in self.env.cr.dictfetchall()]
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


    def action_call(self):
        context = {
            'default_search_demand_id': self.id,
            'default_partner_id': self.partner_id.id,
        }
        action = self.env["ir.actions.actions"]._for_xml_id("fs_real_estate.call_sale_estate_action")
        action['target'] = 'new'
        action['views'] = [(False, 'form')]
        action['context'] = context
        return action

    def view_estate_greeted(self):
        action = {
            'type': 'ir.actions.act_window',
            "name": "Các căn nhà đã chào",
            "res_model": "res.partner",
            # "view_type": "form",
            "view_mode": "form",
            "view_id": self.env.ref("fs_real_estate.res_partner_estate_greeted_view_form").id,
            "res_id": self.partner_id.id,
            "target": "new",
            # "context": context,
        }
        return action
