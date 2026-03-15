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
        if vals.get('type_contact') == 'contact':
            self.env['ir.sequence'].next_by_code('res.partner.contact.sequence')
        elif vals.get('type_contact') == 'customer':
            self.env['ir.sequence'].next_by_code('res.partner.customer.sequence')
        elif vals.get('type_contact') == 'agency':
            self.env['ir.sequence'].next_by_code('res.partner.agency.sequence')
        result = super(ResPartner, self).create(vals)
        return result
