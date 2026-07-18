from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import date, datetime, timedelta
import base64
from odoo.modules.module import get_module_resource
import json
import urllib.parse
import re


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
    total_price = fields.Float('Giá')
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
    number_house_parity = fields.Selection(
        [('even', 'Chẵn'), ('odd', 'Lẻ')],
        string='Số nhà chẵn/lẻ',
        compute='_compute_number_house_parity',
        store=True,
    )
    latitude = fields.Float('Vĩ độ', digits=(10, 7))
    longitude = fields.Float('Kinh độ', digits=(10, 7))
    not_found = fields.Boolean()
    url_map = fields.Text(string='Link chỉ định gg map')
    total_floor = fields.Integer(string='Tổng số tầng',)

    @api.onchange('structure_ids')
    def _onchange_structure_ids(self):
        for rec in self:
            if rec.structure_ids:
                rec.total_floor = max(rec.structure_ids.mapped('total_floor')) or 0
            else:
                rec.total_floor = 0

    def geocode_address_backup(self):
        import requests

        if not (self.number_house and self.street_id and self.district_id and self.city_id):
            return

        address_parts = []
        if self.number_house: address_parts.append(self.number_house)
        if self.street_id: address_parts.append(self.street_id.name)
        if self.ward_id: address_parts.append(self.ward_id.name)
        if self.district_id: address_parts.append(self.district_id.name)
        if self.city_id: address_parts.append(self.city_id.name)
        address_parts.append('Vietnam')

        address_str = ', '.join(address_parts)

        try:
            url = 'https://api.opencagedata.com/geocode/v1/json'
            params = {
                'q': address_str,
                'key': '3091d5a4339e4e69bb9c9d2f82f61ca2',
                'language': 'vi',
                'countrycode': 'vn',
                'limit': 1,
                'no_annotations': 1,
            }
            resp = requests.get(url, params=params, timeout=5)
            data = resp.json()
            results = data.get('results', [])
            if results:
                self.latitude = results[0]['geometry']['lat']
                self.longitude = results[0]['geometry']['lng']

            # else:
            #     self.not_found = True
        except Exception as e:
            pass
            # self.not_found = False

    def geocode_address(self):
        """Lấy tọa độ lat/lng từ địa chỉ dùng Maptiler Geocoding API"""
        import requests

        if not (self.number_house and self.street_id and self.district_id and self.city_id):
            return

        # Ghép địa chỉ
        address_parts = []
        if self.number_house:
            address_parts.append(self.number_house)
        if self.street_id:
            address_parts.append(self.street_id.name)
        if self.ward_id:
            address_parts.append(self.ward_id.name)
        if self.district_id:
            address_parts.append(self.district_id.name)
        if self.city_id:
            address_parts.append(self.city_id.name)
        address_parts.append('Vietnam')

        address_str = ', '.join(address_parts)

        try:
            url = f'https://api.maptiler.com/geocoding/{requests.utils.quote(address_str)}.json'
            params = {
                'key': 'ImjPn4h0t4FU8GPqW22o',  # ← thay bằng key Maptiler
                'language': 'vi',
                'country': 'vn',  # Giới hạn trong VN
                'limit': 1,
            }
            resp = requests.get(url, params=params, timeout=5)

            if resp.status_code == 200:
                data = resp.json()
                features = data.get('features', [])
                if features:
                    coords = features[0]['geometry']['coordinates']
                    self.longitude = coords[0]  # lng
                    self.latitude = coords[1]  # lat
                    # self.is_geocoded = True
                    print("✅ LAT:", self.latitude, "LNG:", self.longitude)
                else:
                    self.not_found= True
                    print("❌ Không tìm thấy:", address_str)
            else:
                self.not_found = True
                print("❌ Lỗi HTTP:", resp.status_code, resp.text)

        except Exception as e:
            self.not_found = True
            print("❌ Lỗi:", e)



    @api.onchange('number_house', 'street_id', 'ward_id', 'district_id', 'city_id')
    def _onchange_address_geocode(self):
        """Tự động geocode khi địa chỉ thay đổi"""
        if self.number_house and self.street_id and self.city_id:
            self.geocode_address()

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
    code_demand_secondary_show = fields.Html(string='Nhu cầu|Hình thức',
                                             compute='compute_code_demand_secondary_show', store=True)
    type_style_direction_show = fields.Html(string='Loại|Kiểu|Hướng', compute='compute_type_style_direction_show')
    address_ward_district_show = fields.Html(string='Phường - Quận', compute='compute_address_ward_district_show',
                                             store=True)
    horizontal_length_use_area_show = fields.Html(string='Dài|Rộng', compute='compute_horizontal_length_use_area',
                                                  store=True)

    status_advertising = fields.Selection([('not_post', 'Chưa đăng bài'),
                                           ('posted', 'Đã đăng'),
                                           ('stop_post', 'Ngưng đăng bài'),
                                           ], string='Trạng thái đăng bài', default='not_post')
    date_stop_post = fields.Date(string='Ngày ngưng đăng bài')
    date_not_post = fields.Date(string='Ngày chưa đăng bài', default=fields.Date.context_today)
    is_expired = fields.Boolean(string='Đã hết hạn', default=False, compute='compute_is_expired')

    image_avatar = fields.Binary(string='Ảnh', store=False)
    is_visiter = fields.Boolean(string='Là quyền cộng tác viên', compute='compute_is_visiter')
    old_id = fields.Integer(string='ID cũ')
    image_avatar_html = fields.Html(
        string='Ảnh',
        compute='_compute_image_avatar_html',
        store=True,
        sanitize=False
    )
    is_default = fields.Boolean(string='Default', default=True)
    date_last_modified = fields.Datetime(string='Ngày mới nhất', compute='_compute_date_last_modified', store=True,
                                         index=True)
    deposit_paid_display = fields.Text(string='Giá', compute='_compute_deposit_paid_display', store=False)

    address_str = fields.Char(string='địa chỉ str', compute='_compute_address_str', store=True)

    autofill_id = fields.Many2one('estate.autofill', string='Nguồn nhập liệu AI', readonly=True)

    @api.depends('number_house')
    def _compute_number_house_parity(self):
        # Chẵn/lẻ được xác định theo phần số ở ĐẦU number_house (VD: "12A" -> 12 -> chẵn),
        # cùng logic với regex '^[0-9]+' dùng trong real.estate.search.
        for rec in self:
            match = re.match(r'^(\d+)', rec.number_house or '')
            if not match:
                rec.number_house_parity = False
                continue
            rec.number_house_parity = 'even' if int(match.group(1)) % 2 == 0 else 'odd'

    @api.depends('number_house', 'street_id', 'ward_id', 'district_id', 'city_id')
    def _compute_address_str(self):
        for rec in self:
            parts = []

            # Số nhà + đường ghép trực tiếp, không có dấu phẩy
            if rec.number_house and rec.street_id:
                parts.append(f"{rec.number_house} {rec.street_id.name}")
            elif rec.number_house:
                parts.append(rec.number_house)
            elif rec.street_id:
                parts.append(rec.street_id.name)

            if rec.ward_id:
                parts.append(rec.ward_id.name)
            if rec.district_id:
                parts.append(rec.district_id.name)
            if rec.city_id:
                parts.append(rec.city_id.name)

            rec.address_str = ', '.join(parts) if parts else ''

    # @api.constrains('number_house', 'street_id', 'ward_id', 'district_id', 'city_id')
    # def _check_duplicate_address(self):
    #     # Kiểm tra trùng địa chỉ (số nhà -> thành phố), không phân biệt hoa/thường ở số nhà
    #     for rec in self:
    #         if not (rec.number_house and rec.street_id and rec.district_id and rec.city_id):
    #             continue

    #         domain = [
    #             ('id', '!=', rec.id),
    #             ('number_house', '=ilike', (rec.number_house or '').strip()),
    #             ('street_id', '=', rec.street_id.id),
    #             ('ward_id', '=', rec.ward_id.id),
    #             ('district_id', '=', rec.district_id.id),
    #             ('city_id', '=', rec.city_id.id),
    #         ]
    #         if rec.search_count(domain):
    #             raise ValidationError(_(
    #                 'Địa chỉ này đã tồn tại trong hệ thống (trùng Số nhà - Đường - Phường - Quận/Huyện - '
    #                 'Thành phố, không phân biệt hoa/thường). Vui lòng kiểm tra lại!'
    #             ))

    @api.onchange('horizontal', 'length')
    def _onchange_horizontal(self):
        for rec in self:
            rec.acreage_area = rec.horizontal * rec.length

    @api.depends('deposit', 'paid', 'fee', 'total_price')
    def _compute_deposit_paid_display(self):
        for record in self:
            lines = []
            if record.total_price:
                lines.append(f"Giá: {record.total_price}")
            if record.fee:
                lines.append(f"Phí: {record.fee}")
            record.deposit_paid_display = '\n'.join(lines)

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

    @api.depends('date_entry', 'date_updated', 'create_date', 'write_date')
    def _compute_date_last_modified(self):
        for rec in self:
            dates = [
                rec.date_entry,
                rec.date_updated,
                rec.create_date,
                rec.write_date
            ]
            # lọc bỏ giá trị None
            dates = [d for d in dates if d]

            rec.date_last_modified = max(dates) if dates else False

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
        self.is_default = False

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
        for rec in self:
            if rec.attachment_ids:
                data = rec.attachment_ids[0].datas

                # đảm bảo là string
                if isinstance(data, bytes):
                    data = data.decode()

                rec.image_avatar_html = f"""
                    <img src="data:image/png;base64,{data}"
                         style="width:60px;height:60px;object-fit:cover;border-radius:6px;"/>
                """
            else:
                rec.image_avatar_html = """
                    <img src="/fs_real_estate/static/img/logo.png"
                         style="width:60px;height:60px;opacity:0.5;"/>
                """

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

            horizontal_length_use_area_show += 'DTKV: %s<br/>' % (rec.acreage_area or '')

            horizontal_length_use_area_show += 'DTSD: %s<br/>' % (rec.acreage_use or '')
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

    def action_location(self):
        self.ensure_one()
        url = False

        if self.url_map:
            href_match = re.search(r'href=[\'"]([^\'"]+)[\'"]', self.url_map)
            if href_match:
                url = href_match.group(1)
            else:
                url_match = re.search(r'https?://[^\s<]+', self.url_map)
                url = url_match.group(0).rstrip('.,') if url_match else False

        if not url:
            # Chưa có link Google Maps -> tìm theo địa chỉ
            address = self._get_address(house=1, street=1, ward=1, district=1, city=1)
            if not address:
                raise UserError(_('Chưa có link Google Maps và không đủ thông tin địa chỉ để tìm kiếm.'))
            url = 'https://www.google.com/maps/search/?api=1&query=' + urllib.parse.quote(address)

        return {
            'type': 'ir.actions.act_url',
            'url': url.replace('&amp;', '&'),
            'target': 'new',
        }

    @api.model
    def action_open_ai_autofill(self):
        """Mở form nhập liệu bằng AI (Gemini) từ text tin rao."""
        return {
            'type': 'ir.actions.act_window',
            'name': _('Nhập liệu AI (Gemini)'),
            'res_model': 'estate.autofill',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_name': _('Nhập liệu AI')},
        }

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

    @api.model
    def search_estates_in_bounds(self, min_lat, max_lat, min_lng, max_lng, limit=100):
        """Tìm estates trong bounding box (cho map circle search)"""
        domain = [
            ('latitude', '>=', min_lat),
            ('latitude', '<=', max_lat),
            ('longitude', '>=', min_lng),
            ('longitude', '<=', max_lng),
            ('latitude', '!=', False),
            ('longitude', '!=', False),
        ]
        estates = self.search(domain, limit=limit)
        return estates.read([
            'id', 'code', 'note', 'latitude', 'longitude',
            'total_price', 'acreage_area', 'status_advertising',
            'number_house', 'street_id', 'ward_id', 'district_id', 'city_id',
        ])

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
