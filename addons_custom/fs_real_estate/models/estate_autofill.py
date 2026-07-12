import base64
import hashlib
import json
import mimetypes
import re
import time
import unicodedata

import requests

from odoo import api, fields, models, _
from odoo.exceptions import UserError

GEMINI_ENDPOINT = 'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}'
GEMINI_CACHE_ENDPOINT = 'https://generativelanguage.googleapis.com/v1beta/cachedContents?key={api_key}'
# Thời gian sống của Gemini Explicit Context Cache (phần prompt tĩnh: hướng dẫn +
# danh sách master data). Chỉ là tối ưu token/độ trễ, KHÔNG ảnh hưởng giới hạn
# request/phút hay request/ngày.
GEMINI_CACHE_TTL_SECONDS = 1800
# Cache phía Odoo cho chuỗi master data (tránh query DB lại mỗi lần bấm trong
# vài phút liên tiếp).
MASTER_DATA_CACHE_TTL_SECONDS = 300
_MASTER_DATA_CACHE = {'text': None, 'built_at': 0.0}

# Giới hạn số Phường/Đường đưa vào prompt: danh sách Đường (kèm Phường liên kết)
# có thể rất lớn (hàng nghìn bản ghi), khiến prompt phình to và dễ dính giới hạn
# token/phút (TPM) của free tier dù request vẫn hợp lệ. Giữ ở mức vừa đủ để AI
# vẫn có dữ liệu tham chiếu hữu ích mà không làm prompt quá nặng.
MASTER_DATA_WARD_LIMIT = 800
MASTER_DATA_STREET_LIMIT = 1200

# Dùng để bỏ tiền tố hành chính phổ biến ("Phường"/"P."/"Quận"/"Q.") khi so khớp,
# vì dữ liệu thật trong Odoo có thể lưu viết tắt khác kiểu AI trả về (ví dụ DB
# lưu "P7" nhưng AI chuẩn hoá thành "Phường 7").
ADMIN_PREFIX_RE = re.compile(r'^(phuong|p|quan|q)\.?\s*')

# Model cấu hình trong Settings được thử trước; nếu bị lỗi 429 (quota = 0/hết quota cho
# riêng model đó) hoặc 404 (model đã bị gỡ/không hỗ trợ generateContent với API key này),
# lần lượt thử các model free-tier phổ biến khác trước khi báo lỗi cho người dùng.
# Ưu tiên các model flash/flash-lite mới (thường có hạn mức free tier rộng rãi hơn) trước
# gemini-2.0-flash, vì trên nhiều tài khoản model này bị giới hạn quota=0 dù các model khác
# vẫn dùng bình thường (xác nhận qua "Kiểm tra kết nối" trong Cài đặt).
FALLBACK_MODELS = ['gemini-2.5-flash-lite', 'gemini-2.5-flash', 'gemini-flash-latest', 'gemini-2.0-flash']

# 404/429: model này không dùng được với key hiện tại (vĩnh viễn) => bỏ qua, thử model khác ngay.
SKIP_STATUS_CODES = {404, 429}
# 500/502/503: lỗi tạm thời phía Google (quá tải) => thử lại chính model đó 1 lần trước khi bỏ qua.
TRANSIENT_STATUS_CODES = {500, 502, 503}

FEE_UNIT_SELECTION = [
    ('percent', "%"),
    ('month', 'Tháng'),
    ('negotiate', 'TL'),
    ('million', 'Triệu'),
    ('usd', '$'),
    ('market', "Thị trường"),
]

RESPONSE_SCHEMA = {
    'type': 'ARRAY',
    'items': {
        'type': 'OBJECT',
        'properties': {
            'raw_block': {'type': 'STRING'},
            'number_house': {'type': 'STRING'},
            'street_name': {'type': 'STRING'},
            'ward_name': {'type': 'STRING'},
            'district_name': {'type': 'STRING'},
            'city_name': {'type': 'STRING'},
            'horizontal': {'type': 'NUMBER'},
            'length': {'type': 'NUMBER'},
            'bedroom': {'type': 'INTEGER'},
            'bathroom': {'type': 'INTEGER'},
            'kitchen': {'type': 'INTEGER'},
            'structure_keywords': {'type': 'ARRAY', 'items': {'type': 'STRING'}},
            'type_estate_guess': {'type': 'STRING'},
            'style_guess': {'type': 'STRING'},
            'type_demand_guess': {'type': 'STRING', 'enum': ['sale', 'rent']},
            'total_price': {'type': 'NUMBER'},
            'fee': {'type': 'STRING'},
            'fee_unit_guess': {'type': 'STRING', 'enum': [code for code, label in FEE_UNIT_SELECTION]},
            'phone_numbers': {'type': 'ARRAY', 'items': {'type': 'STRING'}},
            'note': {'type': 'STRING'},
        },
        'required': ['raw_block', 'note'],
    },
}

# Schema cho lần gọi RIÊNG chỉ đọc địa chỉ trong ảnh (tách khỏi lần gọi tổng hợp
# dữ liệu từ text bên dưới - xem IMAGE_ADDRESS_PROMPT_TEMPLATE).
IMAGE_ADDRESS_RESPONSE_SCHEMA = {
    'type': 'OBJECT',
    'properties': {
        'found': {'type': 'BOOLEAN'},
        'number_house': {'type': 'STRING'},
        'street_name': {'type': 'STRING'},
        'ward_name': {'type': 'STRING'},
        'district_name': {'type': 'STRING'},
        'city_name': {'type': 'STRING'},
    },
    'required': ['found'],
}

# Prompt RIÊNG cho lần gọi chỉ đọc địa chỉ trong ảnh (OCR) - tách biệt khỏi prompt
# tổng hợp dữ liệu từ text (PROMPT_PREFIX_TEMPLATE bên dưới) để model không bị
# "loãng" bởi hàng chục quy tắc không liên quan (giá, hoa hồng, kết cấu...) khi
# phải vừa đọc ảnh vừa tuân thủ toàn bộ quy tắc đó cùng lúc.
IMAGE_ADDRESS_PROMPT_TEMPLATE = """Bạn là trợ lý đọc địa chỉ nhà đất từ ảnh (OCR) cho phần mềm quản lý môi
giới bất động sản tại Việt Nam. Ảnh đính kèm có thể là ảnh chụp/scan địa chỉ: bản đồ, sổ hồng, biển số nhà,
tin rao viết tay/in...

Hãy ĐỌC kỹ toàn bộ chữ trong ảnh và trích xuất địa chỉ (nếu có) thành: number_house (số nhà, có thể dạng
"61/19" kiểu số nhà trong hẻm), street_name (tên đường), ward_name (Phường/Xã), district_name (Quận/Huyện),
city_name (Thành phố). Nếu ảnh KHÔNG chứa thông tin địa chỉ nào, hoặc chữ quá mờ không đọc được, đặt
found=false và để tất cả các trường còn lại là chuỗi rỗng - TUYỆT ĐỐI KHÔNG bịa đặt địa chỉ.

DANH SÁCH DỮ LIỆU ĐÃ CÓ SẴN TRONG HỆ THỐNG - ưu tiên hàng đầu là chọn giá trị KHỚP CHÍNH XÁC (copy nguyên văn,
đúng chữ hoa/thường và dấu) từ danh sách dưới đây cho city_name, district_name, ward_name, street_name. Chỉ khi
không có giá trị nào phù hợp thì mới tự chuẩn hoá theo quy tắc viết tắt bên dưới:
{master_data}

Quy ước viết tắt thường gặp (áp dụng khi địa chỉ trong ảnh viết tắt, không khớp thẳng danh sách trên):
- Quận theo số: "Q.10", "Q10", "Q 10", "q10" => district_name = "Quận 10".
- Quận theo tên chữ (TP.HCM): "Q.Tân Bình", "QTB", hoặc chỉ ghi "Tân Bình" => district_name = "Quận Tân Bình".
  Áp dụng tương tự: Bình Thạnh, Phú Nhuận, Tân Phú, Gò Vấp, Bình Tân, Nhà Bè, Bình Chánh, Hóc Môn, Củ Chi, Cần
  Giờ. Riêng "Thủ Đức"/"TP.Thủ Đức" => district_name = "Thành phố Thủ Đức".
- Phường theo số: "P.15", "P15", "p6" => ward_name = "Phường 15"/"Phường 6".
- Phường theo tên chữ: "P.Tân Định", "PTĐ" => ward_name = "Phường Tân Định".
- Nếu không thấy tên thành phố trong ảnh, mặc định city_name = "Hồ Chí Minh".

Chỉ trả về JSON đúng theo schema đã cho, không thêm giải thích.
"""

# Phần TĨNH của prompt (hướng dẫn + danh sách master data) - giống hệt nhau giữa
# các lần gọi miễn là master data chưa đổi, nên đây là phần được đưa vào Gemini
# Explicit Context Cache khi khả dụng, thay vì gửi lại toàn bộ mỗi lần.
PROMPT_PREFIX_TEMPLATE = """Bạn là trợ lý nhập liệu cho phần mềm quản lý môi giới bất động sản tại Việt Nam.
Người dùng dán vào một đoạn văn bản có thể chứa MỘT hoặc NHIỀU tin rao nhà đất viết theo văn phong tốc ký
của môi giới (mỗi tin thường có 3 dòng: địa chỉ / kích thước-kết cấu / giá-phí-số điện thoại). Các tin có
thể cách nhau bằng dòng trống hoặc dấu phẩy. Hãy TÁCH từng tin và trích xuất dữ liệu có cấu trúc cho từng tin.

DANH SÁCH DỮ LIỆU ĐÃ CÓ SẴN TRONG HỆ THỐNG - ưu tiên hàng đầu là chọn giá trị KHỚP CHÍNH XÁC (copy nguyên
văn, đúng chữ hoa/thường và dấu) từ danh sách dưới đây cho các trường city_name, district_name, ward_name,
street_name, type_estate_guess, style_guess, và từng phần tử trong structure_keywords. Chỉ khi không có giá
trị nào trong danh sách phù hợp thì mới tự chuẩn hoá theo các quy tắc bên dưới. Danh sách "Đường" có ghi kèm
(các) Phường mà đường đó thuộc về trong dấu ngoặc vuông [...] - hãy DÙNG THÔNG TIN NÀY để suy luận/kiểm tra
chéo ward_name và district_name khi tin rao chỉ ghi tên đường mà không ghi rõ (hoặc ghi mơ hồ) Phường/Quận:
{master_data}

Quy ước viết tắt thường gặp:
- Tên Quận/Phường trong tin rao được viết tắt rất đa dạng: có/không dấu chấm, có/không dấu cách, viết
  hoa/thường lẫn lộn, có/không dấu tiếng Việt. Hãy CHUẨN HOÁ về dạng đầy đủ, không phân biệt các biến thể sau:
  * Quận theo số: "Q.10", "Q10", "Q 10", "q10", "quan 10" => district_name = "Quận 10".
  * Quận theo tên chữ (TP.HCM): "Q.Tân Bình", "QTB", "Q Tân Bình", hoặc chỉ ghi "Tân Bình" (không có tiền
    tố Q.) => district_name = "Quận Tân Bình". Áp dụng tương tự cho: Bình Thạnh, Phú Nhuận, Tân Phú, Gò Vấp,
    Bình Tân, Nhà Bè, Bình Chánh, Hóc Môn, Củ Chi, Cần Giờ. Riêng "Thủ Đức"/"TP.Thủ Đức"/"Tp Thủ Đức"
    => district_name = "Thành phố Thủ Đức".
  * Phường theo số: "P.15", "P15", "P.6", "p6", "phuong 15" => ward_name = "Phường 15".
  * Phường theo tên chữ: "P.Tân Định", "P Tân Định", "PTĐ" => ward_name = "Phường Tân Định" (áp dụng
    tương tự với các phường có tên chữ khác).
  * Nếu địa chỉ chỉ liệt kê các số/tên cách nhau bằng dấu phẩy mà không ghi rõ "P."/"Q." (ví dụ
    "..., 15, Q.10" hoặc "..., 15, 10"), số/tên đứng NGAY TRƯỚC quận thường là phường, hãy suy luận
    ward_name và district_name theo thứ tự đó.
- Nếu không thấy tên thành phố, mặc định city_name = "Hồ Chí Minh" (vì đây là dữ liệu môi giới TP.HCM).
- "3x10m", "3x10", "4x26" là ngang x dài (mét) => horizontal, length.
- "trệt", "lầu", "lửng", "suốt", "gác", "sân thượng", "ST" là các từ khoá kết cấu => đưa từng từ (viết hoa
  chữ cái đầu) vào mảng structure_keywords, ví dụ "trệt 2 lầu lửng" => ["Trệt", "Lầu", "Lửng"].
- "pn" = phòng ngủ (bedroom), "wc" = toilet/phòng vệ sinh (bathroom). "3pn 2wc" => bedroom=3, bathroom=2.
- total_price: LẤY NGUYÊN SỐ đã viết trong tin, KHÔNG quy đổi/KHÔNG tự thêm số 0 theo đơn vị "tr"/"tỷ" - đơn vị
  "tr"/"tỷ" chỉ để tham khảo văn phong, không dùng để nhân giá trị. Ví dụ "12tr" => total_price=12, "5.5 tỷ" =>
  total_price=5.5, "150" (không ghi đơn vị) => total_price=150.
- "hhtt" = hoa hồng thoả thuận => fee="TT", fee_unit_guess="negotiate".
- "hh1/2" hoặc "hh 1/2" = hoa hồng nửa tháng => fee="1/2", fee_unit_guess="month".
- "hh1th"/"hh 1 tháng" => fee="1", fee_unit_guess="month". "hh1%" => fee="1", fee_unit_guess="percent".
  Nếu không có thông tin hoa hồng thì để fee rỗng và không có fee_unit_guess.
- Các dãy số 9-11 chữ số là số điện thoại Việt Nam => đưa vào mảng phone_numbers (có thể nhiều số).
- type_demand_guess: nếu văn phong cho thấy đây là tin CHO THUÊ (giá vài chục triệu, có hoa hồng theo
  tháng/thoả thuận) => "rent"; nếu giá rất lớn (hàng tỷ, kiểu giá bán đứt) => "sale". Mặc định "rent" nếu
  không chắc chắn với các tin có giá dạng "xx tr".
- style_guess: điền "Mặt tiền" nếu có từ "MT"/"mặt tiền"; điền "Hẻm" nếu có từ "hẻm" HOẶC nếu number_house có
  dạng "số/số" (ví dụ "61/19", "12/3/5" - quy ước số nhà trong hẻm ở Việt Nam); nếu không có dấu hiệu nào thì
  để rỗng, KHÔNG đoán bừa.
- type_estate_guess: nếu không có thông tin cụ thể về loại hình, mặc định "Nhà phố".
- raw_block: chép lại nguyên văn đoạn text gốc tương ứng với tin đó.
- note: tóm tắt ngắn gọn các chi tiết KHÔNG có field riêng ở trên (ví dụ "lửng suốt", "ST", ghi chú khác).

Chỉ trả về JSON đúng theo schema đã cho, không thêm giải thích.
"""

# Phần THAY ĐỔI mỗi lần gọi (nội dung tin đăng người dùng vừa dán) - luôn được
# gửi mới, không nằm trong cache.
PROMPT_SUFFIX_TEMPLATE = """Dữ liệu đầu vào:
---
{raw_text}
---
"""


class EstateAutofill(models.Model):
    _name = 'estate.autofill'
    _description = 'Nhập liệu nhà đất bằng AI (Gemini)'
    _order = 'create_date desc'

    name = fields.Char(string='Tiêu đề', default=lambda self: _('Nhập liệu AI'), required=True)
    raw_text = fields.Text(string='Nội dung tin đăng (dán vào đây)', required=True)
    state = fields.Selection([('draft', 'Chưa xử lý'), ('done', 'Đã xử lý')], default='draft', readonly=True)
    result_log = fields.Text(string='Kết quả xử lý', readonly=True)
    ai_response_log = fields.Text(string='Log JSON trả về từ AI (debug)', readonly=True)
    estate_ids = fields.One2many('real.estate', 'autofill_id', string='Tin đã tạo', readonly=True)
    estate_count = fields.Integer(string='Số tin đã tạo', compute='_compute_estate_count')
    image = fields.Binary(string='Ảnh địa chỉ')
    image_name = fields.Char(string='Tên file ảnh')
    attachment_ids = fields.Many2many(
        comodel_name='ir.attachment',
        relation='estate_autofill_ir_attachments_rel',
        string='Hình ảnh')

    @api.depends('estate_ids')
    def _compute_estate_count(self):
        for rec in self:
            rec.estate_count = len(rec.estate_ids)

    def action_view_estates(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Tin đã tạo'),
            'res_model': 'real.estate',
            'view_mode': 'tree,form',
            'domain': [('autofill_id', '=', self.id)],
        }

    def action_process(self):
        self.ensure_one()
        if not self.raw_text or not self.raw_text.strip():
            raise UserError(_('Vui lòng nhập nội dung tin đăng.'))

        items = self._call_gemini(self.raw_text)
        if not items:
            raise UserError(_(
                'AI không trích xuất được tin nào từ nội dung đã nhập. Vui lòng kiểm tra lại nội dung.'))

        created = self.env['real.estate']
        logs = []
        for idx, item in enumerate(items, start=1):
            try:
                with self.env.cr.savepoint():
                    estate = self._create_real_estate(item)
                created += estate
                logs.append(_('✅ Tin %s: đã tạo %s') % (idx, estate.display_name))
            except Exception as e:
                logs.append(_('❌ Tin %s (%s): %s') % (
                    idx, (item.get('raw_block') or '')[:40].replace('\n', ' '), str(e)))

        self.write({
            'state': 'done',
            'result_log': '\n'.join(logs),
        })

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Nhập liệu AI'),
                'message': _('Đã tạo %s / %s tin. Xem chi tiết ở "Kết quả xử lý".') % (len(created), len(items)),
                'type': 'success' if created else 'warning',
                'sticky': True,
            },
        }

    # ------------------------------------------------------------------
    # Gemini call
    # ------------------------------------------------------------------
    def _call_gemini(self, raw_text):
        api_key, model = self.env['res.config.settings'].sudo().get_gemini_credentials()
        if not api_key:
            raise UserError(_(
                'Chưa cấu hình Gemini API Key. Vào Cài đặt > Real Estate để nhập API Key '
                '(lấy miễn phí tại https://aistudio.google.com/apikey).'))

        # Nếu có ảnh: gọi AI RIÊNG 1 lần chỉ để đọc địa chỉ trong ảnh (OCR), tách
        # biệt khỏi lần gọi tổng hợp dữ liệu từ text bên dưới - giúp model không bị
        # "loãng" bởi hàng chục quy tắc không liên quan (giá, hoa hồng, kết cấu...)
        # khi phải xử lý đồng thời cả ảnh lẫn toàn bộ quy tắc đó. Việc ưu tiên địa
        # chỉ từ ảnh (nếu đọc được) so với địa chỉ trong text được quyết định bằng
        # CODE (xem _apply_image_address) thay vì nhờ AI tự phân xử.
        image_part = self._get_image_part()
        image_debug = self._describe_image_part(image_part)
        image_address = None
        if image_part:
            image_address, address_debug = self._extract_address_from_image(image_part, api_key, model)
            image_debug = '%s\n%s' % (image_debug, address_debug)

        prefix_text = PROMPT_PREFIX_TEMPLATE.format(master_data=self._get_master_data_text())
        suffix_text = PROMPT_SUFFIX_TEMPLATE.format(raw_text=raw_text)
        generation_config = {
            'temperature': 0.1,
            'responseMimeType': 'application/json',
            'responseSchema': RESPONSE_SCHEMA,
        }

        # Best-effort: dùng Gemini Explicit Context Cache cho phần prompt tĩnh
        # (hướng dẫn + master data) của model đã cấu hình, để KHÔNG phải gửi lại
        # toàn bộ đoạn đó mỗi lần gọi (giảm token/độ trễ). Đây chỉ là tối ưu, nếu
        # cache không tạo được/không hợp lệ thì tự động rơi xuống nhánh gửi
        # prompt đầy đủ bên dưới như trước, không ảnh hưởng kết quả.
        cache_name = self._get_or_create_gemini_cache(model, api_key, prefix_text)
        if cache_name:
            resp = self._post_gemini(model, api_key, {
                'contents': [{'parts': [{'text': suffix_text}]}],
                'cachedContent': cache_name,
                'generationConfig': generation_config,
            })
            if resp.status_code == 200:
                items = self._parse_gemini_response(
                    resp, '%s\n[DEBUG] model=%s (dùng cache)' % (image_debug, model))
                return self._apply_image_address(items, image_address)
            if resp.status_code in (400, 404):
                # Cache hết hạn/không hợp lệ phía Google -> xoá cache đã lưu và
                # tiếp tục bằng nhánh gửi prompt đầy đủ bên dưới.
                self.env['ir.config_parameter'].sudo().set_param('fs_real_estate.gemini_cache_name', '')

        payload = {
            'contents': [{'parts': [{'text': prefix_text + suffix_text}]}],
            'generationConfig': generation_config,
        }
        resp, used_model = self._post_gemini_with_fallback(model, api_key, payload)
        items = self._parse_gemini_response(
            resp, '%s\n[DEBUG] model=%s (không dùng cache)' % (image_debug, used_model))
        return self._apply_image_address(items, image_address)

    def _post_gemini_with_fallback(self, model, api_key, payload):
        """Thử model cấu hình trước; nếu lỗi thì lần lượt thử các model dự phòng
        (xem FALLBACK_MODELS). Trả về (resp, model_đã_trả_lời) khi có response
        200, raise UserError khi tất cả model đã thử đều lỗi.

        Some Gemini free API keys/projects have quota = 0 on a given model
        (HTTP 429, "limit: 0"), some model ids get deprecated/removed over time
        (HTTP 404, "is not found ... or is not supported for generateContent"),
        Google's servers occasionally return transient overload errors
        (HTTP 500/502/503, "high demand"/"UNAVAILABLE"), and the free tier also
        enforces a per-minute rate limit shared across models (HTTP 429,
        "RESOURCE_EXHAUSTED") that is transient and resets within seconds - it
        is NOT the same as the daily quota shown on the usage dashboard. Retry
        transient/rate-limit errors once (respecting Google's suggested
        retryDelay when given), then move on to the next free-tier model
        instead of failing on the first one configured.
        """
        models_to_try = [model] + [m for m in FALLBACK_MODELS if m != model]
        skip_errors = []
        for idx, candidate_model in enumerate(models_to_try):
            resp = self._post_gemini(candidate_model, api_key, payload)
            if resp.status_code in TRANSIENT_STATUS_CODES:
                time.sleep(2)
                resp = self._post_gemini(candidate_model, api_key, payload)
            elif resp.status_code == 429 and idx == 0:
                # Chỉ chờ-và-thử-lại ở model đầu tiên (thường do rate limit theo
                # phút, không phải quota=0 riêng model) để tránh cộng dồn thời
                # gian chờ quá lâu khi phải lần lượt qua nhiều model dự phòng.
                time.sleep(self._extract_retry_delay(resp))
                resp = self._post_gemini(candidate_model, api_key, payload)
            if resp.status_code == 200:
                return resp, candidate_model
            if resp.status_code in SKIP_STATUS_CODES or resp.status_code in TRANSIENT_STATUS_CODES:
                skip_errors.append('%s (%s): %s' % (candidate_model, resp.status_code, resp.text[:300]))
                continue
            raise UserError(_('Gemini API lỗi (%s) với model %s: %s') % (
                resp.status_code, candidate_model, resp.text[:500]))

        raise UserError(_(
            'Tất cả model Gemini đã thử đều lỗi (không tồn tại, hết hạn mức, hoặc server đang quá tải):\n'
            '%s\n\n'
            'Nếu là lỗi 429 "RESOURCE_EXHAUSTED"/"exceeded your current quota" mà trên trang '
            'https://ai.dev/rate-limit vẫn còn nhiều lượt trong ngày: đây thường KHÔNG phải hết quota theo '
            'ngày, mà là giới hạn số request MỖI PHÚT (RPM) của free tier - giới hạn này dùng chung cho '
            'các model, gọi liên tiếp nhiều model/nhiều tin trong thời gian ngắn sẽ dễ dính lỗi này. Hệ '
            'thống đã tự đợi và thử lại nhưng vẫn chưa qua được, hãy đợi khoảng 1 phút rồi bấm "Phân tích & '
            'Tạo tin đăng" lại (không cần đổi gì).\n\n'
            'Các nguyên nhân khác có thể gặp:\n'
            '- API Key không phải tạo từ https://aistudio.google.com/apikey (Cloud Console key có thể '
            'không có free tier hoặc không hỗ trợ các model này).\n'
            '- Project/API Key chưa được cấp hạn mức free tier cho các model trên (đôi khi cần vài phút '
            'sau khi tạo key).\n'
            '- Server Gemini đang quá tải tạm thời (503) cho tất cả model đã thử, hãy thử lại sau ít phút.\n'
            'Bạn có thể vào https://ai.google.dev để xem danh sách model khả dụng với key của bạn, rồi '
            'nhập đúng tên model đó vào Cài đặt > Real Estate.') % '\n'.join(skip_errors))

    def _extract_address_from_image(self, image_part, api_key, model):
        """Gọi Gemini RIÊNG chỉ để đọc địa chỉ trong ảnh, KHÔNG kèm theo toàn bộ
        quy tắc trích xuất dữ liệu từ text. Trả về (address_dict_hoặc_None,
        debug_message). Mọi lỗi đều bị nuốt (trả về None) để không chặn luồng
        trích xuất dữ liệu từ text bên dưới - đọc ảnh chỉ là bổ sung."""
        prompt = IMAGE_ADDRESS_PROMPT_TEMPLATE.format(master_data=self._get_master_data_text())
        payload = {
            'contents': [{'parts': [image_part, {'text': prompt}]}],
            'generationConfig': {
                'temperature': 0.1,
                'responseMimeType': 'application/json',
                'responseSchema': IMAGE_ADDRESS_RESPONSE_SCHEMA,
            },
        }
        try:
            resp, used_model = self._post_gemini_with_fallback(model, api_key, payload)
            data = json.loads(resp.json()['candidates'][0]['content']['parts'][0]['text'])
        except UserError as e:
            return None, '[DEBUG] Lỗi khi gọi AI đọc địa chỉ từ ảnh: %s' % e
        except Exception as e:
            return None, '[DEBUG] Không đọc được phản hồi AI khi đọc địa chỉ từ ảnh: %s' % e

        if not data.get('found'):
            return None, '[DEBUG] AI (model=%s) đọc ảnh nhưng KHÔNG tìm thấy địa chỉ trong ảnh.' % used_model

        address_str = ', '.join(filter(None, [
            data.get('number_house'), data.get('street_name'), data.get('ward_name'),
            data.get('district_name'), data.get('city_name'),
        ]))
        return data, '[DEBUG] AI (model=%s) đọc được địa chỉ từ ảnh: %s' % (used_model, address_str or '(rỗng)')

    def _apply_image_address(self, items, image_address):
        """Ưu tiên địa chỉ đọc được từ ảnh (nếu có) cho MỌI tin trích xuất từ
        text - ghi đè từng trường address riêng lẻ, chỉ khi ảnh thực sự đọc
        được giá trị đó (không ghi đè bằng chuỗi rỗng)."""
        if not image_address:
            return items
        for item in items:
            for field in ('number_house', 'street_name', 'ward_name', 'district_name', 'city_name'):
                value = image_address.get(field)
                if value:
                    item[field] = value
        return items

    def _get_image_part(self):
        """Trả về part ảnh (inline_data) cho Gemini nếu bản ghi có đính kèm ảnh
        địa chỉ, None nếu không có ảnh."""
        self.ensure_one()
        if not self.image:
            return None
        data = self.image.decode('ascii') if isinstance(self.image, bytes) else self.image
        return {'inline_data': {'mime_type': self._guess_image_mime_type(data), 'data': data}}

    def _describe_image_part(self, image_part):
        """Dòng debug ghi vào ai_response_log để xác nhận ảnh có thực sự được
        gửi lên Gemini hay không (mime type/kích thước), tách biệt việc "ảnh
        không được gửi" (lỗi phía Odoo) với "Gemini nhận ảnh nhưng không đọc
        được thông tin" (hạn chế của model/ảnh mờ/không có địa chỉ trong ảnh)."""
        if not image_part:
            return '[DEBUG] Không có ảnh đính kèm khi gọi AI (field "image" đang rỗng lúc xử lý).'
        data = image_part['inline_data']['data']
        mime = image_part['inline_data']['mime_type']
        size_kb = len(data) * 3 / 4 / 1024
        return '[DEBUG] Đã gửi ảnh cho AI: mime_type=%s, dung lượng ~%.1f KB.' % (mime, size_kb)

    def _guess_image_mime_type(self, base64_data):
        """Đoán mime type ảnh qua magic bytes (đáng tin cậy hơn đuôi file, vì
        người dùng có thể đổi tên file), fallback về đuôi file rồi về jpeg."""
        chunk = (base64_data or '')[:64]
        chunk += '=' * (-len(chunk) % 4)
        try:
            header = base64.b64decode(chunk)
        except (ValueError, TypeError):
            header = b''
        if header.startswith(b'\x89PNG'):
            return 'image/png'
        if header.startswith(b'\xff\xd8\xff'):
            return 'image/jpeg'
        if header.startswith(b'GIF87a') or header.startswith(b'GIF89a'):
            return 'image/gif'
        if header[:4] == b'RIFF' and header[8:12] == b'WEBP':
            return 'image/webp'
        # HEIC/HEIF: định dạng mặc định của camera iPhone (rất phổ biến khi môi
        # giới chụp ảnh địa chỉ) - không nhận diện được sẽ fallback sai về jpeg
        # khiến Gemini không giải mã được ảnh (đọc được 0 thông tin, không báo lỗi).
        if header[4:8] == b'ftyp' and header[8:12] in (
                b'heic', b'heix', b'hevc', b'hevx', b'mif1', b'msf1', b'heif'):
            return 'image/heic'
        guessed = mimetypes.guess_type(self.image_name or '')[0]
        return guessed if guessed and guessed.startswith('image/') else 'image/jpeg'

    def _post_gemini(self, model, api_key, payload):
        url = GEMINI_ENDPOINT.format(model=model, api_key=api_key)
        try:
            return requests.post(url, json=payload, timeout=60)
        except requests.RequestException as e:
            raise UserError(_('Không thể kết nối tới Gemini API: %s') % e)

    def _extract_retry_delay(self, resp, default=3.0, cap=20.0):
        """Đọc gợi ý retryDelay Google trả về trong lỗi 429 (nếu có), giới hạn
        thời gian chờ tối đa để không treo request Odoo quá lâu."""
        try:
            data = resp.json()
            for detail in (data.get('error') or {}).get('details') or []:
                delay = detail.get('retryDelay')
                if delay:
                    return min(float(str(delay).rstrip('s')), cap)
        except (ValueError, AttributeError):
            pass
        return default

    def _get_or_create_gemini_cache(self, model, api_key, prefix_text):
        """Best-effort tạo/tái sử dụng Gemini Explicit Context Cache cho phần
        prompt tĩnh (hướng dẫn + master data), lưu tham chiếu qua ir.config_parameter
        để dùng lại giữa các lần gọi/các worker khác nhau.

        Đây CHỈ là tối ưu token/độ trễ - không làm giảm số request tính vào giới
        hạn RPM/RPD. Có thể không khả dụng (free tier không hỗ trợ, model không
        hỗ trợ cache, nội dung chưa đủ số token tối thiểu...) nên mọi lỗi ở đây
        đều bị nuốt, trả về None để _call_gemini tự dùng lại prompt đầy đủ.
        """
        ICP = self.env['ir.config_parameter'].sudo()
        fingerprint = hashlib.md5(('%s::%s' % (model, prefix_text)).encode('utf-8')).hexdigest()

        cached_name = ICP.get_param('fs_real_estate.gemini_cache_name')
        if cached_name and ICP.get_param('fs_real_estate.gemini_cache_fingerprint') == fingerprint:
            try:
                if float(ICP.get_param('fs_real_estate.gemini_cache_expire') or 0) - 60 > time.time():
                    return cached_name
            except ValueError:
                pass

        try:
            resp = requests.post(
                GEMINI_CACHE_ENDPOINT.format(api_key=api_key),
                json={
                    'model': 'models/%s' % model,
                    'contents': [{'role': 'user', 'parts': [{'text': prefix_text}]}],
                    'ttl': '%ss' % GEMINI_CACHE_TTL_SECONDS,
                },
                timeout=30,
            )
            if resp.status_code not in (200, 201):
                return None
            name = resp.json().get('name')
            if not name:
                return None
            ICP.set_param('fs_real_estate.gemini_cache_name', name)
            ICP.set_param('fs_real_estate.gemini_cache_fingerprint', fingerprint)
            ICP.set_param('fs_real_estate.gemini_cache_expire', str(time.time() + GEMINI_CACHE_TTL_SECONDS))
            return name
        except (requests.RequestException, ValueError):
            return None

    def _get_master_data_text(self):
        """Cache phía Odoo (vài phút) cho chuỗi master data, tránh phải query lại
        city/district/ward/street/... mỗi lần bấm liên tiếp trong thời gian ngắn."""
        now = time.time()
        if _MASTER_DATA_CACHE['text'] is not None and \
                (now - _MASTER_DATA_CACHE['built_at']) < MASTER_DATA_CACHE_TTL_SECONDS:
            return _MASTER_DATA_CACHE['text']
        text = self._build_master_data_block()
        _MASTER_DATA_CACHE['text'] = text
        _MASTER_DATA_CACHE['built_at'] = now
        return text

    def _build_master_data_block(self):
        """Trích xuất danh sách dữ liệu master hiện có để AI ưu tiên khớp chính xác
        thay vì tự đoán mù (đặc biệt là Phường/Quận vốn có nhiều cách viết tắt)."""

        def names(model_name, domain=None, limit=1000):
            recs = self.env[model_name].search(domain or [], limit=limit)
            return sorted({rec.name for rec in recs if rec.name})

        def fmt(label, values):
            return '- %s: %s' % (label, ', '.join(values) if values else '(chưa có dữ liệu)')

        def fmt_ward(w):
            return '%s (%s)' % (w.name, w.district_id.name) if w.district_id else w.name

        # Ưu tiên phạm vi các Thành phố đánh dấu is_prioritize=True (khu vực kinh
        # doanh chính, ví dụ Hồ Chí Minh) rồi lấy Quận -> Phường -> Đường (qua
        # ward_ids) đi xuống theo đúng phạm vi đó. Nhờ vậy danh sách gửi cho AI
        # luôn ĐẦY ĐỦ và ĐÚNG TÊN THẬT đang lưu (ví dụ "P5" chứ không tự suy đoán
        # thành "Phường 5"), thay vì bị cắt bớt ngẫu nhiên khi giới hạn limit trên
        # toàn bộ dữ liệu hệ thống. Nếu chưa đánh dấu thành phố nào, dùng lại toàn
        # bộ dữ liệu (có giới hạn) như trước để không phá vỡ các cài đặt khác.
        city_recs = self.env['res.city'].search([('is_prioritize', '=', True)])
        if not city_recs:
            city_recs = self.env['res.city'].search([], limit=1000)
        cities = sorted({c.name for c in city_recs if c.name})

        if city_recs:
            district_recs = self.env['res.district'].search([('city_id', 'in', city_recs.ids)])
        else:
            district_recs = self.env['res.district'].search([], limit=1000)
        districts = sorted({d.name for d in district_recs if d.name})

        if district_recs:
            ward_recs = self.env['res.ward'].search(
                [('district_id', 'in', district_recs.ids)], limit=MASTER_DATA_WARD_LIMIT)
        else:
            ward_recs = self.env['res.ward'].search([], limit=MASTER_DATA_WARD_LIMIT)
        wards = sorted({fmt_ward(w) for w in ward_recs if w.name})

        # Đường gắn kèm (các) Phường mà nó thuộc về, giúp AI đối chiếu chéo giữa
        # street_name và ward_name/district_name thay vì chỉ so tên đường trơ trọi.
        if ward_recs:
            street_recs = self.env['res.street'].search(
                [('ward_ids', 'in', ward_recs.ids)], limit=MASTER_DATA_STREET_LIMIT)
        else:
            street_recs = self.env['res.street'].search([], limit=MASTER_DATA_STREET_LIMIT)
        streets = sorted({
            '%s [%s]' % (s.name, '; '.join(sorted({fmt_ward(w) for w in s.ward_ids if w.name})))
            if s.ward_ids else s.name
            for s in street_recs if s.name
        })

        type_estates = names('type.estate')
        styles = names('estate.style')
        structures = names('estate.structure')

        return '\n'.join([
            fmt('Thành phố', cities),
            fmt('Quận/Huyện', districts),
            fmt('Phường/Xã (định dạng "Tên (Quận)")', wards),
            fmt('Đường (định dạng "Tên đường [Phường liên kết]")', streets),
            fmt('Loại Nhà/MB', type_estates),
            fmt('Kiểu MT/Hẻm', styles),
            fmt('Cấu trúc', structures),
        ])

    def _parse_gemini_response(self, resp, image_debug=''):
        data = resp.json()
        try:
            text = data['candidates'][0]['content']['parts'][0]['text']
        except (KeyError, IndexError) as e:
            raise UserError(_('Không đọc được kết quả trả về từ Gemini: %s') % e)

        # Lưu lại nguyên văn JSON AI trả về (kể cả khi parse JSON lỗi ở bước sau)
        # để có thể xem lại/debug khi AI đọc sai/không đọc được thông tin trong ảnh.
        self.ai_response_log = ('%s\n\n%s' % (image_debug, text)) if image_debug else text

        try:
            items = json.loads(text)
        except ValueError as e:
            raise UserError(_('Không đọc được kết quả trả về từ Gemini: %s') % e)

        if isinstance(items, dict):
            items = [items]
        return items or []

    # ------------------------------------------------------------------
    # Master-data matching helpers
    # ------------------------------------------------------------------
    @api.model
    def _strip_accents(self, text):
        if not text:
            return ''
        text = unicodedata.normalize('NFKD', str(text))
        return ''.join(c for c in text if not unicodedata.combining(c)).lower().strip()

    @api.model
    def _match_many2one(self, model_name, text, extra_domain=None):
        """Best-effort resolve a free-text name to an existing master-data record.

        Never creates records: an unresolved value is simply left blank (the
        listing is then skipped with a clear reason in result_log).
        """
        text = (text or '').strip()
        if not text:
            return self.env[model_name]
        domain = list(extra_domain or [])
        Model = self.env[model_name]

        rec = Model.search(domain + [('name', 'ilike', text)], limit=1)
        if rec:
            return rec

        target = self._strip_accents(text)
        candidates = Model.search(domain, limit=500)
        for cand in candidates:
            if self._strip_accents(cand.name) == target:
                return cand
        for cand in candidates:
            cname = self._strip_accents(cand.name)
            if cname and (target in cname or cname in target):
                return cand

        # Fallback cuối: bỏ tiền tố hành chính ("Phường"/"P."/"Quận"/"Q.") ở CẢ
        # HAI phía rồi so khớp phần lõi còn lại (thường là số hoặc tên riêng).
        # Xử lý đúng trường hợp dữ liệu thật lưu viết tắt khác kiểu AI trả về,
        # ví dụ DB lưu "P7" nhưng AI chuẩn hoá thành "Phường 7" (hoặc ngược lại).
        target_core = ADMIN_PREFIX_RE.sub('', target, count=1).strip()
        if target_core:
            for cand in candidates:
                cand_core = ADMIN_PREFIX_RE.sub('', self._strip_accents(cand.name), count=1).strip()
                if cand_core and cand_core == target_core:
                    return cand
        return self.env[model_name]

    @api.model
    def _normalize_phone(self, raw):
        """Chuẩn hoá về đúng 10 chữ số kiểu di động VN (bắt buộc bởi
        res.partner.mobile - required=True + constrains 10 chữ số). Trả về
        None nếu không thể chuẩn hoá được (số không hợp lệ)."""
        digits = re.sub(r'\D', '', raw or '')
        if digits.startswith('84') and len(digits) == 11:
            digits = '0' + digits[2:]
        if len(digits) == 10 and digits.startswith('0'):
            return digits
        return None

    def _get_or_create_partner(self, phone):
        """phone phải là số đã chuẩn hoá (đúng 10 chữ số), vì res.partner.create()
        yêu cầu 'mobile' bắt buộc và đúng định dạng 10 chữ số."""
        partner = self.env['res.partner'].search(
            ['|', ('mobile', '=', phone), ('phone', '=', phone)], limit=1)
        if partner:
            return partner
        return self.env['res.partner'].create({
            'name': _('Chủ nhà %s') % phone,
            'mobile': phone,
            'type_contact': 'contact',
        })

    def _match_many2one_or_default(self, model_name, text, extra_domain=None):
        """Như _match_many2one, nhưng nếu không khớp thì lấy đại bản ghi đầu
        tiên hiện có thay vì để trống - dùng cho các field required=True thật
        sự trên real.estate (type_estate_id/style_id) để không chặn tạo tin chỉ
        vì AI đoán sai phân loại; người dùng có thể sửa lại sau khi tạo."""
        rec = self._match_many2one(model_name, text, extra_domain)
        if rec:
            return rec, False
        rec = self.env[model_name].search(extra_domain or [], limit=1)
        return rec, True

    # ------------------------------------------------------------------
    # AI item -> real.estate
    # ------------------------------------------------------------------
    def _create_real_estate(self, item):
        self.ensure_one()

        # Địa chỉ (Thành phố/Quận/Phường/Đường) chỉ được khớp với dữ liệu đã có sẵn,
        # KHÔNG tự tạo mới => tin nào không khớp được sẽ bị bỏ qua (xem result_log).
        city = self._match_many2one('res.city', item.get('city_name') or 'Hồ Chí Minh')
        district = self._match_many2one(
            'res.district', item.get('district_name'), [('city_id', '=', city.id)] if city else None)
        ward = self._match_many2one(
            'res.ward', item.get('ward_name'), [('district_id', '=', district.id)] if district else None)
        street = self._match_many2one('res.street', item.get('street_name'))

        number_house = item.get('number_house') or ''
        # "61/19" kiểu số/số gần như luôn là địa chỉ trong hẻm (số hẻm/số nhà) ở VN.
        style_guess = item.get('style_guess') or ('Hẻm' if '/' in number_house else '')

        # Loại nhà/Kiểu MT-hẻm là danh mục phân loại cố định, KHÔNG tự tạo mới,
        # nhưng cũng KHÔNG bắt buộc khớp đúng: nếu AI đoán sai/không đoán được,
        # tự lấy tạm bản ghi đầu tiên hiện có để không chặn tạo tin - người dùng
        # có thể sửa lại phân loại sau khi tin đã được tạo.
        type_estate, type_estate_defaulted = self._match_many2one_or_default(
            'type.estate', item.get('type_estate_guess'))
        style, style_defaulted = self._match_many2one_or_default('estate.style', style_guess)
        type_demand_label = 'Cho thuê' if item.get('type_demand_guess') == 'rent' else 'Bán'
        type_demand = self._match_many2one('type.demand', type_demand_label)

        structure_ids = []
        for kw in item.get('structure_keywords') or []:
            rec = self._match_many2one('estate.structure', kw)
            if rec:
                structure_ids.append(rec.id)

        # Chuẩn hoá số điện thoại (bắt buộc đúng 10 chữ số vì res.partner.mobile
        # required=True + constrains định dạng) và tìm/tạo partner tương ứng để
        # gắn vào role_line_ids - MỌI role_line đều phải có partner có số điện
        # thoại hợp lệ (không tạo role_line trống nữa).
        phones = []
        for raw in item.get('phone_numbers') or []:
            for part in re.split(r'[,/\s]+', raw):
                normalized = self._normalize_phone(part)
                if normalized and normalized not in phones:
                    phones.append(normalized)

        # Chỉ bắt buộc: địa chỉ đủ để tạo real.estate, và có ít nhất 1 số điện
        # thoại hợp lệ để tạo/gắn liên hệ (chủ nhà) vào role_line_ids.
        missing = []
        if not number_house:
            missing.append('Số nhà')
        if not street:
            missing.append('Đường (%s)' % (item.get('street_name') or '?'))
        if not ward:
            missing.append('Phường (%s)' % (item.get('ward_name') or '?'))
        if not district:
            missing.append('Quận/Huyện (%s)' % (item.get('district_name') or '?'))
        if not city:
            missing.append('Thành phố (%s)' % (item.get('city_name') or '?'))
        if not phones:
            missing.append('Số điện thoại (%s)' % (', '.join(item.get('phone_numbers') or []) or '?'))
        if missing:
            raise UserError(_('Thiếu/không khớp dữ liệu bắt buộc: %s') % '; '.join(missing))

        horizontal = item.get('horizontal') or 0
        length = item.get('length') or 0

        role_vals = []
        role_detail = self.env['role.detail'].search([('name', 'ilike', 'chủ')], limit=1)
        for phone in phones:
            partner = self._get_or_create_partner(phone)
            role_vals.append((0, 0, {
                'partner_id': partner.id,
                'role_detail_id': role_detail.id if role_detail else False,
            }))

        sequence = self.env['ir.sequence'].search([('code', '=', 'real.estate.sequence')], limit=1)
        code = sequence.get_next_char(sequence.number_next_actual) if sequence else False

        note = item.get('note') or ''
        defaulted_labels = []
        if type_estate_defaulted:
            defaulted_labels.append('Loại Nhà/MB')
        if style_defaulted:
            defaulted_labels.append('Kiểu MT/Hẻm')
        if defaulted_labels:
            note = ('[AI không xác định được: %s - đã tự chọn tạm, vui lòng kiểm tra lại] %s' % (
                ', '.join(defaulted_labels), note)).strip()

        vals = {
            'code': code,
            'autofill_id': self.id,
            'number_house': number_house,
            'street_id': street.id,
            'ward_id': ward.id,
            'district_id': district.id,
            'city_id': city.id,
            'horizontal': horizontal,
            'length': length,
            'acreage_area': horizontal * length,
            'bedroom': item.get('bedroom') or 0,
            'bathroom': item.get('bathroom') or 0,
            'kitchen': item.get('kitchen') or 0,
            'structure_ids': [(6, 0, structure_ids)],
            'type_estate_id': type_estate.id,
            'style_id': style.id,
            'type_demand_id': type_demand.id if type_demand else False,
            'total_price': item.get('total_price') or 0,
            'fee': item.get('fee') or '',
            'fee_unit': item.get('fee_unit_guess') or False,
            'note': note,
            'source_image': 'online',
            'role_line_ids': role_vals,
            'attachment_ids': [(6, 0, self.attachment_ids.ids)],
        }
        return self.env['real.estate'].create(vals)
