# -*- coding: utf-8 -*-
"""
GIẢI PHÁP TỐI ƯU CỰC MẠNH cho real_estate_search
Áp dụng khi có 33,800+ records và indexes vẫn chậm

CHIẾN LƯỢC:
1. Filter theo thứ tự: MẠNH → YẾU (giảm rows sớm)
2. Chỉ SELECT id (không load data thừa)
3. LIMIT ngay từ đầu
4. Dùng CTE (Common Table Expression) để tối ưu
"""

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import date, datetime, timedelta
import logging

_logger = logging.getLogger(__name__)


class RealEstateSearchOptimized(models.Model):
    _inherit = 'real.estate.search'
    
    @api.model
    def default_get(self, fields_list):
        """
        Override để:
        1. COUNT tổng số records (hiển thị đúng total_count)
        2. KHÔNG load data (để trống real_estate_ids)
        → User thấy tổng số nhưng phải click Search để load data
        """
        vals = super(RealEstateSearchOptimized, self).default_get(fields_list)
        
        # COUNT tổng số records (nhanh - chỉ đếm)
        total_count = self.env['real.estate'].search_count([])
        vals['total_count'] = total_count
        
        # KHÔNG load data - để trống
        recent_estates = self.env['real.estate'].search([], order='date_last_modified desc', limit=40)
        vals['real_estate_ids'] = [(6, 0, recent_estates.ids)]
        
        return vals
    
    # Pagination fields - Hỗ trợ phân trang thông minh
    page = fields.Integer(
        string='Trang hiện tại',
        default=1,
        help='Trang hiện tại đang xem'
    )
    page_size = fields.Selection([
        ('50', '50 kết quả/trang'),
        ('100', '100 kết quả/trang'),
        ('200', '200 kết quả/trang'),
        ('500', '500 kết quả/trang'),
        ('1000', '1000 kết quả/trang'),
        ('0', 'Tất cả (không phân trang)'),
    ], string='Số kết quả mỗi trang', default='100')
    
    total_count = fields.Integer(
        string='Tổng số kết quả',
        readonly=True,
        help='Tổng số nhà đất tìm thấy (không tính phân trang)'
    )
    
    total_pages = fields.Integer(
        string='Tổng số trang',
        compute='_compute_total_pages',
        store=False
    )
    
    @api.depends('total_count', 'page_size')
    def _compute_total_pages(self):
        """Tính tổng số trang"""
        for rec in self:
            page_size_int = int(rec.page_size) if rec.page_size else 100
            if page_size_int > 0 and rec.total_count > 0:
                rec.total_pages = (rec.total_count + page_size_int - 1) // page_size_int
            else:
                rec.total_pages = 1
    
    def action_first_page(self):
        """Chuyển về trang đầu"""
        self.page = 1
        self.action_search_real_estate()
    
    def action_prev_page(self):
        """Trang trước"""
        if self.page > 1:
            self.page -= 1
            self.action_search_real_estate()
    
    def action_next_page(self):
        """Trang sau"""
        if self.page < self.total_pages:
            self.page += 1
            self.action_search_real_estate()
    
    def action_last_page(self):
        """Chuyển đến trang cuối"""
        self.page = self.total_pages if self.total_pages > 0 else 1
        self.action_search_real_estate()
    
    @api.onchange('page_size')
    def _onchange_page_size(self):
        """Reset về trang 1 khi thay đổi page_size"""
        self.page = 1
    
    @api.model
    def _cron_refresh_materialized_view(self):
        """
        Cron job: Refresh materialized view mỗi 5 phút
        Chạy CONCURRENTLY để không block queries
        """
        try:
            self.env.cr.execute("REFRESH MATERIALIZED VIEW CONCURRENTLY mv_real_estate_search_cache")
            _logger.info('✓ Materialized view refreshed successfully')
        except Exception as e:
            _logger.error(f'✗ Failed to refresh materialized view: {str(e)}')
    
    @api.model
    def _cron_cleanup_expired_cache(self):
        """
        Cron job: Cleanup cache đã expire mỗi 1 giờ
        """
        try:
            self.env.cr.execute("SELECT cleanup_expired_search_cache()")
            _logger.info('✓ Expired cache cleaned up successfully')
        except Exception as e:
            _logger.error(f'✗ Failed to cleanup cache: {str(e)}')
    
    def get_real_estate_ids(self):
        """
        TỐI ƯU CỰC MẠNH - Query theo thứ tự ưu tiên
        
        THỨ TỰ FILTER (từ MẠNH → YẾU):
        1. Địa chỉ (district, ward, street) - Thường filter mạnh nhất
        2. Loại hình (type_estate, style) - Filter mạnh
        3. Giá (total_price) - Filter trung bình
        4. Kích thước (horizontal, length, acreage) - Filter yếu
        5. Ngày tháng - Filter yếu nhất
        """
        
        # ============================================
        # BƯỚC 1: XÂY DỰNG ĐIỀU KIỆN THEO ƯU TIÊN
        # ============================================
        
        conditions = []
        params = {}
        
        # === PRIORITY 1: ĐỊA CHỈ (Filter mạnh nhất) ===
        if self.district_ids:
            conditions.append("district_id = ANY(%(district_ids)s)")
            params['district_ids'] = self.district_ids.ids
        
        if self.ward_ids:
            conditions.append("ward_id = ANY(%(ward_ids)s)")
            params['ward_ids'] = self.ward_ids.ids
        
        if self.street_ids:
            conditions.append("street_id = ANY(%(street_ids)s)")
            params['street_ids'] = self.street_ids.ids
        
        if self.city_ids:
            conditions.append("city_id = ANY(%(city_ids)s)")
            params['city_ids'] = self.city_ids.ids
        
        # === PRIORITY 2: LOẠI HÌNH (Filter mạnh) ===
        if self.type_estate_ids:
            conditions.append("type_estate_id = ANY(%(type_estate_ids)s)")
            params['type_estate_ids'] = self.type_estate_ids.ids
        
        if self.style_ids:
            conditions.append("style_id = ANY(%(style_ids)s)")
            params['style_ids'] = self.style_ids.ids
        elif self.group_style_id and self.group_style_id.style_ids:
            conditions.append("style_id = ANY(%(group_style_ids)s)")
            params['group_style_ids'] = self.group_style_id.style_ids.ids
        
        if self.direction_ids:
            conditions.append("direction_id = ANY(%(direction_ids)s)")
            params['direction_ids'] = self.direction_ids.ids
        elif self.group_direction_id and self.group_direction_id.direction_ids:
            conditions.append("direction_id = ANY(%(group_direction_ids)s)")
            params['group_direction_ids'] = self.group_direction_id.direction_ids.ids
        
        if self.type_demand_ids:
            conditions.append("type_demand_id = ANY(%(type_demand_ids)s)")
            params['type_demand_ids'] = self.type_demand_ids.ids
        
        if self.secondary_form_ids:
            conditions.append("secondary_form_id = ANY(%(secondary_form_ids)s)")
            params['secondary_form_ids'] = self.secondary_form_ids.ids
        
        # === PRIORITY 3: GIÁ (Filter trung bình) ===
        if self.total_price_from and self.total_price_to:
            conditions.append("total_price BETWEEN %(price_from)s AND %(price_to)s")
            params['price_from'] = self.total_price_from
            params['price_to'] = self.total_price_to
        elif self.total_price_from:
            conditions.append("total_price >= %(price_from)s")
            params['price_from'] = self.total_price_from
        elif self.total_price_to:
            conditions.append("total_price <= %(price_to)s")
            params['price_to'] = self.total_price_to
        
        # === PRIORITY 4: KÍCH THƯỚC (Filter yếu) ===
        if self.horizontal_from and self.horizontal_to:
            conditions.append("horizontal BETWEEN %(horizontal_from)s AND %(horizontal_to)s")
            params['horizontal_from'] = self.horizontal_from
            params['horizontal_to'] = self.horizontal_to
        elif self.horizontal_from:
            conditions.append("horizontal >= %(horizontal_from)s")
            params['horizontal_from'] = self.horizontal_from
        elif self.horizontal_to:
            conditions.append("horizontal <= %(horizontal_to)s")
            params['horizontal_to'] = self.horizontal_to
        
        if self.length_from and self.length_to:
            conditions.append("length BETWEEN %(length_from)s AND %(length_to)s")
            params['length_from'] = self.length_from
            params['length_to'] = self.length_to
        elif self.length_from:
            conditions.append("length >= %(length_from)s")
            params['length_from'] = self.length_from
        elif self.length_to:
            conditions.append("length <= %(length_to)s")
            params['length_to'] = self.length_to
        
        if self.acreage_area_from and self.acreage_area_to:
            conditions.append("acreage_area BETWEEN %(acreage_area_from)s AND %(acreage_area_to)s")
            params['acreage_area_from'] = self.acreage_area_from
            params['acreage_area_to'] = self.acreage_area_to
        elif self.acreage_area_from:
            conditions.append("acreage_area >= %(acreage_area_from)s")
            params['acreage_area_from'] = self.acreage_area_from
        elif self.acreage_area_to:
            conditions.append("acreage_area <= %(acreage_area_to)s")
            params['acreage_area_to'] = self.acreage_area_to
        
        if self.acreage_use_from and self.acreage_use_to:
            conditions.append("acreage_use BETWEEN %(acreage_use_from)s AND %(acreage_use_to)s")
            params['acreage_use_from'] = self.acreage_use_from
            params['acreage_use_to'] = self.acreage_use_to
        elif self.acreage_use_from:
            conditions.append("acreage_use >= %(acreage_use_from)s")
            params['acreage_use_from'] = self.acreage_use_from
        elif self.acreage_use_to:
            conditions.append("acreage_use <= %(acreage_use_to)s")
            params['acreage_use_to'] = self.acreage_use_to
        
        # === PRIORITY 5: NGÀY THÁNG (Filter yếu nhất) ===
        if self.date_entry_from:
            conditions.append("date_entry >= %(date_entry_from)s")
            params['date_entry_from'] = self.date_entry_from
        if self.date_entry_to:
            conditions.append("date_entry <= %(date_entry_to)s")
            params['date_entry_to'] = self.date_entry_to
        
        if self.date_updated_from:
            conditions.append("date_updated >= %(date_updated_from)s")
            params['date_updated_from'] = self.date_updated_from
        if self.date_updated_to:
            conditions.append("date_updated <= %(date_updated_to)s")
            params['date_updated_to'] = self.date_updated_to
        
        if self.date_contract_exp_from:
            conditions.append("date_contract_exp >= %(date_contract_exp_from)s")
            params['date_contract_exp_from'] = self.date_contract_exp_from
        if self.date_contract_exp_to:
            conditions.append("date_contract_exp <= %(date_contract_exp_to)s")
            params['date_contract_exp_to'] = self.date_contract_exp_to
        
        # === PRIORITY 6: CÁC ĐIỀU KIỆN ĐẶC BIỆT ===
        if self.code:
            conditions.append("code ILIKE %(code)s")
            params['code'] = f"{self.code}%"
        
        if self.note:
            conditions.append("note ILIKE %(note)s")
            params['note'] = f"%{self.note}%"
        
        if self.number_house:
            conditions.append("number_house ILIKE %(number_house)s")
            params['number_house'] = f"{self.number_house}%"
        
        if self.source_image:
            conditions.append("source_image = %(source_image)s")
            params['source_image'] = self.source_image
        
        if self.source_estate_partner_id:
            conditions.append("""
                EXISTS (
                    SELECT 1
                    FROM real_estate_source_house_res_partner_rel rel
                    WHERE rel.real_estate_id = real_estate.id
                    AND rel.res_partner_id = %(source_partner_id)s
                )
            """)
            params['source_partner_id'] = self.source_estate_partner_id.id
        
        if self.way_ids:
            conditions.append("way_id = ANY(%(way_ids)s)")
            params['way_ids'] = self.way_ids.ids
        
        if self.job_profession_ids:
            conditions.append("job_profession_id = ANY(%(job_profession_ids)s)")
            params['job_profession_ids'] = self.job_profession_ids.ids
        
        # Structure (Many2many)
        if self.structure_ids:
            conditions.append("""
                EXISTS (
                    SELECT 1
                    FROM estate_structure_real_estate_rel esrl
                    WHERE esrl.real_estate_id = real_estate.id
                    AND esrl.estate_structure_id = ANY(%(structure_ids)s)
                )
            """)
            params['structure_ids'] = self.structure_ids.ids
        
        # Contact (phức tạp - để cuối)
        if self.contact:
            keywords = [kw.strip().replace("'", "''") for kw in self.contact.split(',')]
            partner_conditions = []
            for i, keyword in enumerate(keywords):
                key = f'contact_kw_{i}'
                partner_conditions.append(f"""(
                    rp.name ILIKE %(${key})s
                    OR rp.mobile ILIKE %(${key})s
                    OR rp.mobile_2 ILIKE %(${key})s
                    OR rp.mobile_3 ILIKE %(${key})s
                    OR rp.mobile_4 ILIKE %(${key})s
                )""")
                params[key] = f'%{keyword}%'
            
            conditions.append(f"""
                EXISTS (
                    SELECT 1
                    FROM role_estate re
                    INNER JOIN res_partner rp ON rp.id = re.partner_id
                    WHERE re.estate_id = real_estate.id
                    AND ({' OR '.join(partner_conditions)})
                )
            """)
        
        # ============================================
        # BƯỚC 2: XÂY DỰNG QUERY TỐI ƯU VỚI PAGINATION
        # ============================================
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        # BƯỚC 2.1: COUNT query - Đếm tổng số records (NHANH - chỉ count, không load data)
        count_query = f"""
            SELECT COUNT(id)
            FROM real_estate
            WHERE {where_clause}
        """
        
        self.env.cr.execute(count_query, params)
        total_count = self.env.cr.fetchone()[0]
        
        # Cập nhật total_count để hiển thị trong pager
        self.total_count = total_count
        
        # BƯỚC 2.2: Data query - Chỉ load 1 trang data (NHANH - có LIMIT)
        # Convert page_size từ string sang int
        page_size_int = int(self.page_size) if self.page_size else 100
        
        # Tính OFFSET dựa trên page hiện tại
        offset = 0
        limit_clause = ""
        
        if page_size_int > 0:
            # Có phân trang
            offset = (self.page - 1) * page_size_int
            limit_clause = f"LIMIT {page_size_int} OFFSET {offset}"
        # Nếu page_size = 0 → Lấy tất cả (không LIMIT)
        
        # Query data với LIMIT và OFFSET
        data_query = f"""
            SELECT id
            FROM real_estate
            WHERE {where_clause}
            ORDER BY date_last_modified DESC NULLS LAST
            {limit_clause}
        """
        
        # Execute data query
        self.env.cr.execute(data_query, params)
        real_estate_ids = [row[0] for row in self.env.cr.fetchall()]
        
        # Favorite filter (nếu có)
        if self.favorite_id and self.show_favorite and real_estate_ids:
            favorite_ids = set(self.favorite_id.estate_ids.ids)
            real_estate_ids = [rid for rid in real_estate_ids if rid in favorite_ids]
        
        return real_estate_ids
