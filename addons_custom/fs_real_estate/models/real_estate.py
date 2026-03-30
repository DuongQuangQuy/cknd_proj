from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import date, datetime, timedelta
import base64
from odoo.modules.module import get_module_resource
import json
import urllib.parse


# def _select_nextval(cr, seq_name):
#     cr.execute("SELECT nextval(%s)", [seq_name])
#     return cr.fetchone()


class RealEstate(models.Model):
    _name = 'real.estate'
    _description = 'Real Estate'

    # _rec_name = 'code'

    @api.model
    def default_get(self, fields):
        vals = super(RealEstate, self).default_get(fields)
        sequence = self.env['ir.sequence'].search([('code', '=', 'real.estate.sequence')])
        code_sequence = sequence.get_next_char(sequence.number_next_actual)
        vals['code'] = code_sequence
        return vals

    def default_is_visiter(self):
        if self.env.user.has_group('fs_real_estate.group_real_estate_vister') and not self.env.user.has_group(
                'fs_real_estate.group_real_estate_empoloyee'):
            return True
        else:
            return False

    code = fields.Char(string="Mã số")
    date_entry = fields.Datetime(string="Ngày nhập", default=lambda self: fields.Datetime.now())
    date_fix = fields.Datetime(string="Ngày sửa chữa")
    date_contract_exp = fields.Date(string="Ngày hết hạn HĐ")
    type_demand_id = fields.Many2one('type.demand', string='Nhu cầu Thuê/Bán')
    secondary_form_id = fields.Many2one('secondary.form', string='Hình thức phụ')
    date_receive = fields.Datetime(string="Ngày nhận nhà")
    date_advertisement = fields.Date(string="Ngày đăng quảng cáo")
    user_id = fields.Many2one('res.users', 'Người cập nhật')
    date_updated = fields.Datetime(string="Ngày cập nhật")
    attachment_ids = fields.Many2many(
        comodel_name='ir.attachment',
        relation='real_estate_ir_attachments_rel',
        string='Hình ảnh')
    source_image_partner_ids = fields.Many2many(
        comodel_name='res.partner',
        relation='real_estate_source_image_res_partner_rel',
        string='Nguồn hình từ')
    source_image = fields.Selection([('newspaper', 'Báo'),
                                     ('survey', 'Khảo sát'),
                                     ('online', 'Online'),
                                     ('cooperate', 'Ký gửi/ Hợp tác')],
                                    string='Nguồn tìm về', default='newspaper')
    job_profession_id = fields.Many2one('job.profession', string='Ngành nghề')
    source_estate_partner_ids = fields.Many2many(
        comodel_name='res.partner',
        relation='real_estate_source_house_res_partner_rel',
        string='Nguồn nhà từ'
    )

    # Real estate structure dimensions

    horizontal = fields.Float('Ngang')
    length = fields.Float('Dài')
    acreage_area = fields.Float('DTKV')
    acreage_use = fields.Float('DTSD')
    bedroom = fields.Integer('Phòng ngủ')
    boundary_line = fields.Float(string='Lộ giới')
    direction_id = fields.Many2one('estate.direction', string='Hướng')
    way_id = fields.Many2one('estate.way', string='Lối đi')
    stair_id = fields.Many2one('estate.stair', string='Cầu thang')
    kitchen = fields.Integer('Phòng bếp')
    type_estate_id = fields.Many2one('type.estate', 'Loại Nhà/MB', required=True)
    style_id = fields.Many2one('estate.style', 'Kiểu MT/Hẻm', required=True)
    structure_ids = fields.Many2many('estate.structure', string='Cấu trúc', required=True)
    bathroom = fields.Integer('Phòng vệ sinh')
    is_elevator = fields.Boolean('Thang máy')

    # Price
    total_price = fields.Float('Tổng tiền')
    currency_id = fields.Many2one('res.currency', 'Tiền tệ', default=lambda self: self.env.company.currency_id)
    fee = fields.Char('Phí')
    fee_unit = fields.Selection([
        ('percent', "%"),
        ('month', 'Tháng'),
        ('negotiate', 'TL'),
        ('million', 'Triệu'),
        ('usd', '$'),
        ('market', "Thị trường"),
    ], string="Đơn vị Phí")
    deposit = fields.Float('Tiền cọc')
    paid = fields.Float('Thanh toán', default=1)

    # Address
    street_id = fields.Many2one('res.street', 'Đường', required=True)
    ward_id = fields.Many2one('res.ward', 'Phường', required=True)
    district_id = fields.Many2one('res.district', 'Quận/Huyện', required=True)
    city_id = fields.Many2one('res.city', 'Thành phố', required=True)
    number_house = fields.Char('Số nhà', required=True)

    # Role Contact
    show_hide_table_role = fields.Boolean(string="Ẩn hiện vai trò")
    role_line_ids = fields.One2many('role.estate', 'estate_id', string='Vai trò')

    # Note
    note = fields.Text(string='Ghi chú')

    # Documents
    pink_book_attachment_ids = fields.Many2many('ir.attachment', 'real_estate_pink_book_attachment_rel',
                                                string='Sổ hồng')
    contract_attachment_ids = fields.Many2many('ir.attachment', 'real_estate_contract_attachment_rel',
                                               string='Hợp đồng')
    document_attachment_ids = fields.Many2many('ir.attachment', 'real_estate_document_attachment_rel',
                                               string='Tài liệu')

    # Secondary request
    parent_id = fields.Many2one('real.estate', string='Nhà đất chính')
    child_ids = fields.One2many('real.estate', 'parent_id', string='Chi tiết yêu cầu phụ')
    date_show = fields.Html(string='Ngày', compute='compute_date_show', store=False)
    code_demand_secondary_show = fields.Html(string='Code|Nhu cầu|Hình thức',
                                             compute='compute_code_demand_secondary_show', store=True)
    type_style_direction_show = fields.Html(string='Loại|Kiểu|Hướng', compute='compute_type_style_direction_show')
    address_ward_district_show = fields.Html(string='Phường - Quận', compute='compute_address_ward_district_show',
                                             store=True)
    horizontal_length_use_area_show = fields.Html(string='Dài|Rộng|KV|SD', compute='compute_horizontal_length_use_area',
                                                  store=True)

    status_advertising = fields.Selection([('not_post', 'Chưa đăng bài'),
                                           ('posted', 'Đã đăng'),
                                           ('stop_post', 'Ngưng đăng bài'),
                                           ], string='Trạng thái đăng bài', default='not_post')
    date_stop_post = fields.Date(string='Ngày ngưng đăng bài')
    date_not_post = fields.Date(string='Ngày chưa đăng bài', default=fields.Date.context_today)
    is_expired = fields.Boolean(string='Đã hết hạn', default=False, compute='compute_is_expired')

    image_avatar = fields.Binary(string='Ảnh', compute='_compute_image_avatar', store=False)
    is_visiter = fields.Boolean(string='Là quyền cộng tác viên', compute='compute_is_visiter')
    old_id = fields.Integer(string='ID cũ')
    image_avatar_html = fields.Html(string='Ảnh', store=True)
    is_default = fields.Boolean(string='Default', default=True)
    date_last_modified = fields.Datetime(string='Ngày mới nhất', compute='_compute_date_last_modified', store=True,
                                         index=True)

    @api.depends('attachment_ids')
    def _compute_image_avatar(self):
        for record in self:
            image_data = None
            # Check if there are attachments, use the first one if available
            if record.attachment_ids:
                image_data = record.attachment_ids[0].datas
            else:
                # Load default image from static folder if no attachments are found
                image_data = record._get_default_avatar()
            
            if image_data:
                # image_data is already a base64 string in Odoo, no need to decode
                if isinstance(image_data, bytes):
                    image_data = image_data.decode('utf-8')
                record.image_avatar = image_data
            else:
                record.image_avatar = False

    @api.depends('date_entry', 'date_updated')
    def _compute_date_last_modified(self):
        for rec in self:
            # Lấy ngày mới nhất giữa date_entry và date_updated
            if rec.date_updated and rec.date_entry:
                rec.date_last_modified = max(rec.date_entry, rec.date_updated)
            elif rec.date_updated:
                rec.date_last_modified = rec.date_updated
            elif rec.date_entry:
                rec.date_last_modified = rec.date_entry
            else:
                rec.date_last_modified = False

    def update_image(self):
        image_data = None
        # Check if there are attachments, use the first one if available
        if self.attachment_ids:
            image_data = self.attachment_ids[0].datas
        else:
            # Load default image from static folder if no attachments are found
            image_data = self._get_default_avatar()

        if image_data:
            # image_data is already a base64 string in Odoo, no need to decode
            if isinstance(image_data, bytes):
                image_data = image_data.decode('utf-8')
            self.image_avatar_html = f'<img src="data:image/png;base64,{image_data}" style="max-width: 100px; max-height: 100px;"/>'
        else:
            self.image_avatar_html = ''
        self.is_default= False

    def compute_is_visiter(self):
        for rec in self:
            if self.env.user.has_group('fs_real_estate.group_real_estate_admin'):
                rec.is_visiter = False
            elif self.env.user.has_group('fs_real_estate.group_real_estate_vister') and not self.env.user.has_group(
                    'fs_real_estate.group_real_estate_empoloyee') and self.env.user.partner_id not in rec.source_estate_partner_ids:
                rec.is_visiter = True
            else:
                rec.is_visiter = False

    @api.model
    def create(self, vals):

        result = super(RealEstate, self).create(vals)
        if not result.role_line_ids:
            raise UserError(_('Bạn cần nhập vai trò!'))
        self.env['ir.sequence'].next_by_code('real.estate.sequence')
        return result

    # def _compute_image_avatar(self):
    #     for record in self:
    #         # Check if there are attachments, use the first one if available
    #         if record.attachment_ids:
    #             record.image_avatar = record.attachment_ids[0].datas
    #         else:
    #             # Load default image from static folder if no attachments are found
    #             record.image_avatar = record._get_default_avatar()

    @api.depends('attachment_ids')
    def _compute_image_avatar_html(self):
        for record in self:
            image_data = None
            # Check if there are attachments, use the first one if available
            if record.attachment_ids:
                image_data = record.attachment_ids[0].datas
            else:
                # Load default image from static folder if no attachments are found
                image_data = record._get_default_avatar()

            if image_data:
                # image_data is already a base64 string in Odoo, no need to decode
                if isinstance(image_data, bytes):
                    image_data = image_data.decode('utf-8')
                record.image_avatar_html = f'<img src="data:image/png;base64,{image_data}" style="max-width: 100px; max-height: 100px;"/>'
            else:
                record.image_avatar_html = ''

    def _get_default_avatar(self):
        """Helper method to load a default image from static files"""
        image_path = get_module_resource('fs_real_estate', 'static/img', 'logo.png')
        try:
            with open(image_path, 'rb') as image_file:
                return base64.b64encode(image_file.read())
        except FileNotFoundError:
            # Handle the case where the image file is missing
            return False  # Or set a placeholder image or other default behavior

    def get_demand_estate_search_ids(self):
        estate = f"AND re.id = {self.id}"
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
        estate_condition = f"AND demand_id = {self.id}"

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
            'default_estate_id': self.id,
            'default_search_demand_ids': demand_estate_search_not_offered_obj.ids if demand_estate_search_not_offered_obj else None,
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

    def name_get(self):
        try:
            res = []
            for estate in self:
                # Tạo danh sách tên theo thứ tự ưu tiên
                name_parts = [
                    estate.number_house or "",
                    estate.street_id.name or "",
                    estate.ward_id.name or "",
                    estate.district_id.name or "",
                    estate.city_id.name or ""
                ]
                # Loại bỏ các giá trị rỗng
                name_parts = [part for part in name_parts if part]

                # Nếu không có thông tin, lấy `code` làm tên
                if not name_parts:
                    name = estate.code or "Unnamed"
                else:
                    # Ghép các thông tin lại bằng dấu phẩy
                    name = ", ".join(name_parts)

                res.append((estate.id, name))
            return res
        except Exception as e:
            raise ValidationError(_("An error occurred in name_get: %s") % str(e))

    @api.depends('date_contract_exp')
    def compute_is_expired(self):
        for rec in self:
            if rec.date_contract_exp:
                day = int(self.env["ir.config_parameter"].sudo().get_param("fs_real_estate.number_exp"))

                if (rec.date_contract_exp - datetime.now().date()).days < day:
                    rec.is_expired = True
                else:
                    rec.is_expired = False
            else:
                rec.is_expired = False
                rec.date_contract_exp = ''

    def action_update_date_entry(self):
        for rec in self:
            print(fields.Datetime.now())
            rec.write({
                'date_updated': datetime.now()
            })

    def action_not_post(self):
        for rec in self:
            rec.status_advertising = 'not_post'
            rec.date_not_post = fields.Date.context_today()

    def action_stop_post(self):
        for rec in self:
            rec.status_advertising = 'stop_post'
            rec.date_stop_post = fields.Date.context_today()

    def action_posted(self):
        for rec in self:
            rec.status_advertising = 'posted'
            rec.date_advertisement = fields.Date.context_today()

    @api.depends('horizontal', 'length', 'acreage_area', 'acreage_use')
    def compute_horizontal_length_use_area(self):
        for rec in self:
            horizontal_length_use_area_show = ''
            if rec.horizontal:
                horizontal_length_use_area_show += 'Ngang: %s<br/>' % (rec.horizontal)
            if rec.length:
                horizontal_length_use_area_show += 'Dài: %s<br/>' % (rec.length)
            if rec.acreage_area:
                horizontal_length_use_area_show += 'DTKV: %s<br/>' % (rec.acreage_area)
            if rec.acreage_use:
                horizontal_length_use_area_show += 'DTSD: %s<br/>' % (rec.acreage_use)
            rec.horizontal_length_use_area_show = horizontal_length_use_area_show

    @api.depends('ward_id', 'district_id')
    def compute_address_ward_district_show(self):
        for rec in self:
            address_show = ''
            # if rec.street_id:
            #     address_show += '%s - %s<br/>' % (rec.number_house if rec.number_house else '', rec.street_id.name)
            if rec.ward_id:
                address_show += '%s<br/>' % (rec.ward_id.name)
            if rec.district_id:
                address_show += '%s<br/>' % (rec.district_id.name)
            # if rec.city_id:
            #     address_show += '%s<br/>' % (rec.city_id.name)
            rec.address_ward_district_show = address_show

    @api.depends('type_estate_id', 'style_id', 'direction_id')
    def compute_type_style_direction_show(self):
        for rec in self:
            context = ''
            if rec.type_estate_id:
                context += '%s<br/>' % (rec.type_estate_id.name)
            if rec.style_id:
                context += '%s<br/>' % (rec.style_id.name)
            if rec.direction_id:
                context += '%s<br/>' % (rec.direction_id.name)
            rec.type_style_direction_show = context

    @api.depends('code', 'type_demand_id', 'secondary_form_id')
    def compute_code_demand_secondary_show(self):
        for rec in self:
            context = ''
            if rec.code:
                context += '%s<br/>' % (rec.code)
            if rec.type_demand_id:
                context += '%s<br/>' % (rec.type_demand_id.name)
            if rec.secondary_form_id:
                context += '%s<br/>' % (rec.secondary_form_id.name)
            rec.code_demand_secondary_show = context

    @api.depends('date_entry', 'date_updated', 'attachment_ids', 'status_advertising', 'date_not_post',
                 'date_stop_post', 'is_expired', 'date_contract_exp')
    def compute_date_show(self):
        for rec in self:
            date_show = ''

            # 1. Ngày nhập
            if rec.date_entry:
                date_show += '<span style="font-weight: bold; color: #333333;">%s</span><br/>' % (
                    rec.date_entry.strftime('%d-%m-%Y'))

            # 2. Số ngày còn hạn (hợp đồng)
            if rec.date_contract_exp:
                days_remaining = (rec.date_contract_exp - datetime.now().date()).days
                if days_remaining > 0:
                    date_show += '<span style="font-weight: bold; color: blue;">Còn %s ngày</span><br/>' % days_remaining
                elif days_remaining == 0:
                    date_show += '<span style="font-weight: bold; color: orange;">Hết hạn hôm nay</span><br/>'
                else:
                    date_show += '<span style="font-weight: bold; color: red;">Quá hạn %s ngày</span><br/>' % abs(
                        days_remaining)
            else:
                date_show += '<span style="font-weight: bold; color: #333333;">--- ngày</span><br/>'

            # 3. Số lượng hình
            if rec.attachment_ids:
                date_show += '<span style="font-weight: bold;color: blue;">Có %s hình</span><br/>' % (
                    str(len(rec.attachment_ids)))
            else:
                date_show += '<span style="font-weight: bold;color: #333333;">Có 0 hình</span><br/>'

            # 4. Trạng thái đăng tin
            if rec.status_advertising == 'not_post':
                date_show += '<span style="font-weight: bold; color: red;">Chưa đăng</span><br/>'
            elif rec.status_advertising == 'stop_post':
                date_show += '<span style="font-weight: bold; color: red;">Dừng đăng</span><br/>'
            else:
                date_show += '<span style="font-weight: bold; color: green;">Đã đăng</span><br/>'
            is_mt = rec.get_info_mt()
            if is_mt:
                date_show += '<span style="font-weight: bold; color: blue;">Môi giới</span><br/>'

            # 5. Ngày cập nhật
            if rec.date_updated:
                days_since_updated = (datetime.now().date() - rec.date_updated.date()).days
                if days_since_updated == 0:
                    date_show += '<span style="font-weight: bold; color: green;">Hôm nay</span><br/>'
                else:
                    date_show += '<span style="font-weight: bold; color: green;">%s ngày</span><br/>' % days_since_updated

            rec.date_show = date_show

    def get_info_mt(self):
        mt = self.role_line_ids.partner_id.mapped('type_contact')
        if 'agency' in mt:
            return True
        else:
            return False

    def show_role_line(self):
        for rec in self:
            rec.show_hide_table_role = not rec.show_hide_table_role

    def _get_address(self, house=0, street=0, ward=0, district=0, city=0):
        """Get full address of real estate with parameters are 1
        :param self: the real estate object
        :param house: boolean
        :param street: boolean
        :param ward: boolean
        :param district: boolean
        :param city: boolean
        :return: string address
        """
        for record in self:
            address = []
            if house:
                if record.number_house:
                    address.append(record.number_house)
            if street:
                if record.street_id:
                    if record.street_id.name:
                        address.append(record.street_id.name)
            if ward:
                if record.ward_id:
                    if record.ward_id.name:
                        address.append(record.ward_id.name)
            if district:
                if record.district_id:
                    if record.district_id.name:
                        address.append(record.district_id.name)
            if city:
                if record.city_id:
                    if record.city_id.name:
                        address.append(record.city_id.name)
        if address:
            return ", ".join(address)
        else:
            return ''

    def action_show_advertising_sample(self):
        return {
            'name': _(self._get_address(house=1, street=1, ward=1, district=1)),
            'view_mode': 'form',
            'res_model': 'advertising.sample.wizard',
            'type': 'ir.actions.act_window',
            'context': {'default_real_estate_id': self.id},
            'target': 'new',
        }

    def _get_prices_config(self):
        prices_config = self.env['real.estate.prices.config']
        if self.env.user.has_group('fs_real_estate.group_real_estate_admin'):
            prices_config = self.env['real.estate.prices.config'].search(
                [('group_id', '=', self.env.ref('fs_real_estate.group_real_estate_admin').id)], limit=1)
        elif self.env.user.has_group('fs_real_estate.group_real_estate_company'):
            prices_config = self.env['real.estate.prices.config'].search(
                [('group_id', '=', self.env.ref('fs_real_estate.group_real_estate_company').id)], limit=1)
        elif self.env.user.has_group('fs_real_estate.group_real_estate_manager'):
            prices_config = self.env['real.estate.prices.config'].search(
                [('group_id', '=', self.env.ref('fs_real_estate.group_real_estate_manager').id)], limit=1)
        elif self.env.user.has_group('fs_real_estate.group_real_estate_empoloyee'):
            prices_config = self.env['real.estate.prices.config'].search(
                [('group_id', '=', self.env.ref('fs_real_estate.group_real_estate_empoloyee').id)], limit=1)
        elif self.env.user.has_group('fs_real_estate.group_real_estate_vister'):
            prices_config = self.env['real.estate.prices.config'].search(
                [('group_id', '=', self.env.ref('fs_real_estate.group_real_estate_vister').id)], limit=1)
        return prices_config

    @api.model
    def web_search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        prices_config = self._get_prices_config()
        domain_prices = []
        if prices_config:
            domain_prices = [('total_price', '>=', prices_config.price_from),
                             ('total_price', '<=', prices_config.price_to)]
            if not domain:
                domain = domain_prices
            else:
                real_estate_ids = self.env['real.estate'].search(domain).filtered(
                    lambda record: prices_config.price_from <= record.total_price <= prices_config.price_to).ids
                domain = [('id', 'in', real_estate_ids)]
        return super(RealEstate, self).web_search_read(domain=domain, fields=fields, offset=offset, limit=limit,
                                                       order=None)

    # def read(self, fields=None, load='_classic_read'):
    #     result = []
    #     res = super(RealEstate, self).read(fields, load=load)
    #     prices_config = self._get_prices_config()
    #     for record in res:
    #         if record.get('total_price'):
    #             if prices_config.price_from <= record.get('total_price') <= prices_config.price_to:
    #                 result.append(record)
    #         else:
    #             result.append(record)
    #     return result

    def _generate_url_params(self, params):
        """Helper function to generate URL query string from params dictionary."""
        import urllib.parse
        return urllib.parse.urlencode(params)

    def get_contact_name(self):
        list_partner_name = ''
        partners = self.role_line_ids.mapped('partner_id')
        for partner in partners:
            estates = self.env['role.estate'].search([('partner_id', '=', partner.id)])
            if not estates:
                continue

                # Tìm id của action liên quan
            action = self.env.ref('fs_real_estate.real_estate_action').id

            # URL cơ bản
            base_url = '/web#'

            # Chuyển domain thành chuỗi JSON và mã hóa
            domain = json.dumps([('id', 'in', estates.estate_id.ids)])

            # Tạo các tham số URL
            params = {
                'model': 'real.estate',
                'view_type': 'list',
                'action': action,
                'domain': domain
            }
            url = f"{base_url}{self._generate_url_params(params)}"
            list_partner_name += '%s có  <a href="%s" target="_blank">%s căn nhà</a> <br/>' % (
                partner.display_name, url, str(len(estates)))
        return list_partner_name
        # list_partner_name.append({
        #     'partner_name': partner.display_name,
        #     'number_estate': len(estates)
        # })

        # for partner in self.role_line_ids.partner_id:
        #     if partner.name:
        #         list_partner_name.append(partner.name)

    def get_estate(self):
        estates = self.env['role.estate'].search([('partner_id', 'in', self.role_line_ids.partner_id.ids)])
        return estates.estate_id.ids

    def action_detail_contact_view(self):
        context = {
            'default_estate_id': self.id,
            'default_number_house': self.number_house,
            'default_address_ward_district_show': self.address_ward_district_show,
            'default_contact': self.get_contact_name(),
            'default_job_profession_id': self.job_profession_id.id if self.job_profession_id else None,
            'default_street_id': self.street_id.id if self.street_id else None,
            'default_source_image': self.source_image,
            'default_source_estate_partner_ids': self.source_estate_partner_ids.ids if self.source_estate_partner_ids else None,
            'default_source_image_partner_ids': self.source_image_partner_ids.ids if self.source_image_partner_ids else None,
            'default_partner_ids': self.role_line_ids.partner_id.ids if (
                    self.role_line_ids and self.role_line_ids.partner_id) else None,
            'default_estate_ids': self.get_estate()
        }
        return {
            'name': "Chi tiết liên hệ",
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'detail.contact',
            'view_id': self.env.ref('fs_real_estate.detail_contact_form').id,
            'target': 'new',
            'context': context,
        }
