# -*- coding: utf-8 -*-
"""
GIẢI PHÁP CẤP 2: MATERIALIZED VIEW
Tạo bảng tạm lưu kết quả search phổ biến

ƯU ĐIỂM:
- Query SIÊU NHANH (đã tính toán sẵn)
- Giảm load database
- Phù hợp với search patterns lặp lại

NHƯỢC ĐIỂM:
- Cần refresh định kỳ
- Tốn thêm disk space
"""

import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """
    Tạo Materialized View cho search nhanh
    """
    _logger.info('=' * 80)
    _logger.info('Creating Materialized View for real_estate search optimization')
    _logger.info('=' * 80)
    
    # 1. Tạo Materialized View - Lưu kết quả search phổ biến
    try:
        _logger.info('Creating materialized view: mv_real_estate_search_cache...')
        cr.execute("""
            CREATE MATERIALIZED VIEW IF NOT EXISTS mv_real_estate_search_cache AS
            SELECT 
                id,
                code,
                district_id,
                ward_id,
                street_id,
                city_id,
                type_estate_id,
                style_id,
                direction_id,
                total_price,
                horizontal,
                length,
                acreage_area,
                acreage_use,
                date_last_modified,
                status_advertising
            FROM real_estate
            WHERE status_advertising != 'stop_post'  -- Chỉ lấy nhà đang active
            ORDER BY date_last_modified DESC
        """)
        _logger.info('  ✓ Materialized view created successfully')
        
        # 2. Tạo indexes cho Materialized View
        _logger.info('Creating indexes on materialized view...')
        
        mv_indexes = [
            ('idx_mv_district_id', 'mv_real_estate_search_cache', 'district_id'),
            ('idx_mv_ward_id', 'mv_real_estate_search_cache', 'ward_id'),
            ('idx_mv_street_id', 'mv_real_estate_search_cache', 'street_id'),
            ('idx_mv_type_estate_id', 'mv_real_estate_search_cache', 'type_estate_id'),
            ('idx_mv_style_id', 'mv_real_estate_search_cache', 'style_id'),
            ('idx_mv_total_price', 'mv_real_estate_search_cache', 'total_price'),
            ('idx_mv_date_last_modified', 'mv_real_estate_search_cache', 'date_last_modified'),
            ('idx_mv_location', 'mv_real_estate_search_cache', 'district_id, ward_id, street_id'),
            ('idx_mv_price_area', 'mv_real_estate_search_cache', 'total_price, acreage_area'),
        ]
        
        for idx_name, table, columns in mv_indexes:
            cr.execute(f"""
                CREATE INDEX IF NOT EXISTS {idx_name} 
                ON {table}({columns})
            """)
            _logger.info(f'  ✓ Created index: {idx_name}')
        
        # 3. Tạo function để refresh materialized view
        _logger.info('Creating refresh function...')
        cr.execute("""
            CREATE OR REPLACE FUNCTION refresh_real_estate_search_cache()
            RETURNS void AS $$
            BEGIN
                REFRESH MATERIALIZED VIEW CONCURRENTLY mv_real_estate_search_cache;
            END;
            $$ LANGUAGE plpgsql;
        """)
        _logger.info('  ✓ Refresh function created')
        
        # 4. Refresh lần đầu
        _logger.info('Initial refresh of materialized view...')
        cr.execute("REFRESH MATERIALIZED VIEW mv_real_estate_search_cache")
        _logger.info('  ✓ Initial refresh completed')
        
    except Exception as e:
        _logger.warning(f'  ✗ Failed to create materialized view: {str(e)}')
    
    # 5. Tạo bảng cache cho search results (Redis alternative)
    try:
        _logger.info('Creating search cache table...')
        cr.execute("""
            CREATE TABLE IF NOT EXISTS real_estate_search_cache (
                id SERIAL PRIMARY KEY,
                search_key VARCHAR(255) UNIQUE NOT NULL,
                result_ids INTEGER[],
                created_at TIMESTAMP DEFAULT NOW(),
                expires_at TIMESTAMP DEFAULT NOW() + INTERVAL '1 hour'
            )
        """)
        
        cr.execute("""
            CREATE INDEX IF NOT EXISTS idx_search_cache_key 
            ON real_estate_search_cache(search_key)
        """)
        
        cr.execute("""
            CREATE INDEX IF NOT EXISTS idx_search_cache_expires 
            ON real_estate_search_cache(expires_at)
        """)
        
        _logger.info('  ✓ Search cache table created')
        
    except Exception as e:
        _logger.warning(f'  ✗ Failed to create cache table: {str(e)}')
    
    # 6. Tạo function cleanup cache cũ
    try:
        _logger.info('Creating cache cleanup function...')
        cr.execute("""
            CREATE OR REPLACE FUNCTION cleanup_expired_search_cache()
            RETURNS void AS $$
            BEGIN
                DELETE FROM real_estate_search_cache
                WHERE expires_at < NOW();
            END;
            $$ LANGUAGE plpgsql;
        """)
        _logger.info('  ✓ Cleanup function created')
        
    except Exception as e:
        _logger.warning(f'  ✗ Failed to create cleanup function: {str(e)}')
    
    _logger.info('=' * 80)
    _logger.info('Materialized View migration completed!')
    _logger.info('To refresh view manually: SELECT refresh_real_estate_search_cache();')
    _logger.info('To cleanup cache: SELECT cleanup_expired_search_cache();')
    _logger.info('=' * 80)
