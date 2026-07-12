import requests

from odoo import api, fields, models, _
from odoo.exceptions import UserError

from .estate_autofill import FALLBACK_MODELS, GEMINI_ENDPOINT


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    gemini_api_key = fields.Char(
        string='Gemini API Key',
        config_parameter='fs_real_estate.gemini_api_key',
        help='Lấy API Key miễn phí tại https://aistudio.google.com/apikey')
    gemini_model = fields.Char(
        string='Gemini Model',
        config_parameter='fs_real_estate.gemini_model',
        default='gemini-2.5-flash-lite',
        help='Tên model Gemini (bản free), ví dụ: gemini-2.5-flash-lite, gemini-2.5-flash. '
             'Dùng nút "Kiểm tra kết nối" bên dưới để xem model nào hoạt động với API Key của bạn.')

    @api.model
    def get_gemini_credentials(self):
        """Trả về (api_key, model) đã cấu hình cho tính năng nhập liệu AI."""
        params = self.env['ir.config_parameter'].sudo()
        api_key = params.get_param('fs_real_estate.gemini_api_key')
        model = params.get_param('fs_real_estate.gemini_model') or 'gemini-2.5-flash-lite'
        return api_key, model

    def action_test_gemini_connection(self):
        """Gửi 1 request cực nhỏ (không kèm master data/schema) tới từng model
        free-tier phổ biến để xác định CHÍNH XÁC model/API key nào dùng được,
        tách bạch lỗi do code (prompt quá lớn/token) với lỗi do tài khoản/API
        key (quota=0, sai loại key, chưa được cấp free tier...)."""
        self.ensure_one()
        api_key = self.gemini_api_key or self.env['ir.config_parameter'].sudo().get_param(
            'fs_real_estate.gemini_api_key')
        if not api_key:
            raise UserError(_('Vui lòng nhập Gemini API Key trước khi kiểm tra.'))

        models_to_test = [self.gemini_model] + [m for m in FALLBACK_MODELS if m != self.gemini_model] \
            if self.gemini_model else FALLBACK_MODELS
        payload = {
            'contents': [{'parts': [{'text': 'Trả lời đúng 1 chữ: OK'}]}],
            'generationConfig': {'maxOutputTokens': 5},
        }

        lines = []
        any_ok = False
        for candidate_model in models_to_test:
            url = GEMINI_ENDPOINT.format(model=candidate_model, api_key=api_key)
            try:
                resp = requests.post(url, json=payload, timeout=20)
            except requests.RequestException as e:
                lines.append('❌ %s: không kết nối được (%s)' % (candidate_model, e))
                continue
            if resp.status_code == 200:
                any_ok = True
                lines.append('✅ %s: OK' % candidate_model)
            else:
                lines.append('❌ %s: lỗi %s - %s' % (candidate_model, resp.status_code, resp.text[:200]))

        summary = _(
            'API Key CÓ dùng được (ít nhất 1 model trả lời thành công). Nếu tính năng "Nhập liệu AI" vẫn '
            'báo lỗi 429 dù test ở đây pass, khả năng prompt thực tế (kèm danh sách master data) đang vượt '
            'giới hạn TOKEN/PHÚT (TPM) của free tier chứ không phải giới hạn số request - hãy thử giảm bớt '
            'dữ liệu master (ít Đường/Phường hơn) hoặc đợi 1 phút giữa các lần bấm.'
        ) if any_ok else _(
            'API Key KHÔNG dùng được với TẤT CẢ model đã test, kể cả request tối thiểu. Đây là vấn đề của '
            'chính API key/project trên Google, không phải lỗi của phần mềm:\n'
            '- Kiểm tra key được tạo tại https://aistudio.google.com/apikey (không phải Cloud Console).\n'
            '- Thử tạo API key mới từ MỘT project/tài khoản Google khác (project cũ có thể bị chặn free '
            'tier, đặc biệt tài khoản Google Workspace của tổ chức).\n'
            '- Thử test trực tiếp key này ngay trong Google AI Studio (aistudio.google.com) xem có gọi '
            'được không - nếu ở đó cũng lỗi thì chắc chắn không phải do Odoo/phần mềm.'
        )

        raise UserError(_('Kết quả kiểm tra kết nối Gemini:\n\n%s\n\n%s') % ('\n'.join(lines), summary))
