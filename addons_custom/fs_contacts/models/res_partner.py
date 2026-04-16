from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import date, datetime, timedelta


class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.model
    def default_get(self, fields):
        vals = super(ResPartner, self).default_get(fields)
        sequence = self.env['ir.sequence'].search([('code', '=', 'res.partner.sequence')])
        code_sequence = f"LH-{sequence.get_next_char(sequence.number_next_actual)}"
        vals['code'] = code_sequence
        return vals

    _sql_constraints = [
        ('check_name', "CHECK(1=1)", 'Contacts require a name')
    ]

    mobile_2 = fields.Char(string='Di động 2')
    mobile_3 = fields.Char(string='Di động 3')
    mobile_4 = fields.Char(string='Di động 4')
    date_entry = fields.Datetime(string="Ngày nhập", default=lambda self: fields.Datetime.now())
    date_updated = fields.Datetime(string="Ngày cập nhật")
    user_update_id = fields.Many2one('res.users', 'Người cập nhật')
    source_customer_partner_ids = fields.Many2many(
        comodel_name='res.partner',
        relation='source_customer_res_partner_rel',
        column1='source_id',  # first field in the relation table
        column2='partner_id',  # second field in the relation table
        string='Nguồn tìm về'
    )
    name_company = fields.Char(string='Tên công ty')
    customer_care = fields.Selection([
        ('new', 'Mới'),
        ('assigned', 'Đã phân khách'),
        ('done', 'Đã được chăm sóc'),
    ], string="Tình trạng chia khách")
    evaluate = fields.Selection([
        ('friendly', 'Thân thiện'),
        ('hard', 'Chịu khó'),
        ('potential', 'Tiềm năng'),
        ('normal', 'Bình thường'),
        ('enthusiasm', 'Nhiệt tình'),
    ], string="Đánh giá")

    street_id = fields.Many2one('res.street', 'Đường')
    ward_id = fields.Many2one('res.ward', 'Phường')
    district_id = fields.Many2one('res.district', 'Quận/Huyện')
    city_id = fields.Many2one('res.city', 'Thành phố')
    number_house = fields.Char('Số nhà')
    type_contact = fields.Selection([
        ('contact', 'Liên hệ'),
        ('customer', 'Khách hàng'),
        ('agency', 'Môi giới'),
    ], string="Loại khách hàng")
    job_profession_id = fields.Many2one('job.profession', string='Ngành nghề')
    note = fields.Text(string='Ghi chú nội bộ')
    code = fields.Char(string='Mã khách hàng')
    name = fields.Char(index=True, required=False)
    property_account_payable_id = fields.Many2one('account.account', company_dependent=True,
                                                  string="Account Payable",
                                                  domain="[('internal_type', '=', 'payable'), ('deprecated', '=', False), ('company_id', '=', current_company_id)]",
                                                  help="This account will be used instead of the default one as the payable account for the current partner",
                                                  required=False)
    property_account_receivable_id = fields.Many2one('account.account', company_dependent=True,
                                                     string="Account Receivable",
                                                     domain="[('internal_type', '=', 'receivable'), ('deprecated', '=', False), ('company_id', '=', current_company_id)]",
                                                     help="This account will be used instead of the default one as the receivable account for the current partner",
                                                     required=False)

    @api.onchange('type_contact')
    def onchange_type_contact(self):
        if self.type_contact:
            # Lấy tiền tố mới dựa trên type_contact
            prefix_map = {
                'customer': 'KH',
                'contact': 'LH',
                'agency': 'MG'
            }
            new_prefix = prefix_map.get(self.type_contact, '')

            # Kiểm tra nếu đã có giá trị trong trường code
            if self.code:
                # Thay thế 2 ký tự đầu bằng tiền tố mới
                self.code = f"{new_prefix}{self.code[2:]}"
            else:
                # Nếu chưa có code, gán giá trị mặc định
                sequence = self.env['ir.sequence'].search([('code', '=', 'res.partner.sequence')])

                self.code = f"{new_prefix}-{sequence.get_next_char(sequence.number_next_actual)}"

    @api.model
    def create(self, vals):
        # Xử lý tách số điện thoại và tên từ trường name
        if vals.get('name'):
            import re
            name_value = vals['name'].strip()
            
            # Pattern: số điện thoại 10 số ở đầu, có thể có dấu cách, sau đó là tên
            # VD: "0832629295 A Quý" hoặc "0832629295"
            phone_pattern = r'^(\d{10})(\s+(.+))?$'
            match = re.match(phone_pattern, name_value)
            
            if match:
                phone_number = match.group(1)  # Số điện thoại 10 số
                remaining_name = match.group(3)  # Phần tên sau dấu cách (nếu có)
                
                # Gán số điện thoại vào mobile (nếu chưa có)
                if not vals.get('mobile'):
                    vals['mobile'] = phone_number
                
                # Xử lý tên
                if remaining_name:
                    # Có tên sau số điện thoại → giữ lại tên
                    vals['name'] = remaining_name.strip()
                else:
                    # Chỉ có số điện thoại → đặt tên mặc định
                    vals['name'] = 'No Name'
        
        # Xử lý sequence theo type_contact
        if vals.get('type_contact') == 'contact':
            self.env['ir.sequence'].next_by_code('res.partner.contact.sequence')
        elif vals.get('type_contact') == 'customer':
            self.env['ir.sequence'].next_by_code('res.partner.customer.sequence')
        elif vals.get('type_contact') == 'agency':
            self.env['ir.sequence'].next_by_code('res.partner.agency.sequence')
        
        result = super(ResPartner, self).create(vals)
        return result
    
    def action_migrate_phone_from_name(self):
        """
        Hàm migrate dữ liệu cũ: Tìm các partner có số điện thoại trong tên và tách ra
        Có thể gọi từ button hoặc chạy thủ công
        """
        import re
        
        # Tìm tất cả partners có name chứa số điện thoại 10 số ở đầu
        all_partners = self.env['res.partner'].search([
            ('name', '!=', False),
            ('name', '!=', 'No Name')
        ])
        
        updated_count = 0
        phone_pattern = r'^(\d{10})(\s+(.+))?$'
        
        for partner in all_partners:
            if not partner.name:
                continue
                
            name_value = partner.name.strip()
            match = re.match(phone_pattern, name_value)
            
            if match:
                phone_number = match.group(1)  # Số điện thoại 10 số
                remaining_name = match.group(3)  # Phần tên sau dấu cách (nếu có)
                
                # Chuẩn bị dữ liệu update
                update_vals = {}
                
                # Chỉ update mobile nếu chưa có hoặc khác với số điện thoại tìm thấy
                if not partner.mobile or partner.mobile != phone_number:
                    update_vals['mobile'] = phone_number
                
                # Update tên
                if remaining_name:
                    # Có tên sau số điện thoại → giữ lại tên
                    update_vals['name'] = remaining_name.strip()
                else:
                    # Chỉ có số điện thoại → đặt tên mặc định
                    update_vals['name'] = 'No Name'
                
                # Thực hiện update
                if update_vals:
                    partner.write(update_vals)
                    updated_count += 1
        
        # Trả về thông báo
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Migration Complete'),
                'message': _('Đã cập nhật %s partners: tách số điện thoại từ tên sang mobile.') % updated_count,
                'type': 'success',
                'sticky': False,
            }
        }
