import base64
import io

from odoo import api, models

try:
    from PIL import Image
except ImportError:  # Pillow không có sẵn -> bỏ qua tối ưu, không chặn upload
    Image = None

# Chỉ tối ưu ảnh đính kèm của 2 model hay bị upload ảnh nặng (ảnh nhà đất/ảnh OCR
# địa chỉ) - không đụng tới attachment của các model khác trong hệ thống để tránh
# ảnh hưởng ngoài ý muốn (icon module, mail attachment, report...).
OPTIMIZE_RES_MODELS = {'real.estate', 'estate.autofill'}

# Nếu sau khi tối ưu lossless mà ảnh vẫn vượt 1 trong 2 ngưỡng này thì mới resize
# xuống (đánh đổi 1 phần chất lượng không nhận ra bằng mắt thường, đổi lấy giảm
# dung lượng đáng kể cho các ảnh chụp điện thoại độ phân giải rất cao).
RESIZE_MAX_DIMENSION = 2000
RESIZE_SIZE_THRESHOLD = 2 * 1024 * 1024

# Định dạng ảnh hỗ trợ tối ưu; định dạng khác (gif, webp, pdf...) giữ nguyên.
OPTIMIZABLE_FORMATS = ('JPEG', 'PNG')


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._optimize_image_vals(vals)
        return super().create(vals_list)

    def write(self, vals):
        if vals.get('datas') and Image is not None and self and \
                all(rec.res_model in OPTIMIZE_RES_MODELS for rec in self):
            self._optimize_image_vals(vals)
        return super().write(vals)

    def _optimize_image_vals(self, vals):
        """Tối ưu dung lượng ảnh (nếu có) trong vals trước khi lưu: luôn tối ưu
        lossless (gỡ metadata thừa + nén lại không mất chất lượng hiển thị), chỉ
        resize (mất 1 phần chất lượng) nếu ảnh vẫn quá nặng sau bước lossless.
        Mọi lỗi đọc/xử lý ảnh đều bị nuốt và giữ nguyên dữ liệu gốc - đây chỉ là
        tối ưu, không được phép làm hỏng/chặn việc lưu file.
        """
        if Image is None or not vals.get('datas'):
            return
        res_model = vals.get('res_model')
        if res_model not in OPTIMIZE_RES_MODELS:
            return
        try:
            raw = base64.b64decode(vals['datas'])
            optimized = self._optimize_image_bytes(raw)
        except Exception:
            return
        if optimized and len(optimized) < len(raw):
            vals['datas'] = base64.b64encode(optimized)

    @api.model
    def _optimize_image_bytes(self, raw):
        img = Image.open(io.BytesIO(raw))
        img_format = (img.format or '').upper()
        if img_format not in OPTIMIZABLE_FORMATS:
            return None

        buffer = io.BytesIO()
        if img_format == 'JPEG':
            # quality='keep' giữ nguyên hệ số DCT gốc (không giảm chất lượng),
            # chỉ nén lại Huffman table tối ưu hơn + bỏ EXIF/metadata thừa.
            img.save(buffer, format='JPEG', quality='keep', optimize=True)
        else:
            # PNG vốn là định dạng nén không mất dữ liệu, optimize=True chỉ nén
            # nhiều hơn (chậm hơn) chứ không đổi điểm ảnh nào.
            img.save(buffer, format='PNG', optimize=True)
        lossless = buffer.getvalue()

        if max(img.size) <= RESIZE_MAX_DIMENSION and len(lossless) <= RESIZE_SIZE_THRESHOLD:
            return lossless

        ratio = RESIZE_MAX_DIMENSION / max(img.size)
        if ratio < 1:
            new_size = (round(img.width * ratio), round(img.height * ratio))
            img = img.resize(new_size, Image.LANCZOS)

        buffer = io.BytesIO()
        if img_format == 'JPEG':
            img.save(buffer, format='JPEG', quality=90, optimize=True)
        else:
            img.save(buffer, format='PNG', optimize=True)
        resized = buffer.getvalue()
        return resized if len(resized) < len(lossless) else lossless
