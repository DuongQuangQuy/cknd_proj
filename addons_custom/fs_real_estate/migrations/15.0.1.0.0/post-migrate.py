# -*- coding: utf-8 -*-
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """
    Migration script để thêm indexes cho bảng real_estate
    Mục đích: Tối ưu performance search với 33,800+ records
    
    KHÔNG thay đổi logic, chỉ thêm indexes để query nhanh hơn
    """
    _logger.info('=' * 80)
    _logger.info('Starting migration: Adding indexes to real_estate table')
    _logger.info('=' * 80)
    
    # 1. Single column indexes - Các trường hay dùng trong WHERE clause
    single_indexes = [
        # Kích thước (horizontal, length, acreage_area, acreage_use)
        ('idx_real_estate_horizontal', 'real_estate', 'horizontal', 'horizontal IS NOT NULL'),
        ('idx_real_estate_length', 'real_estate', 'length', 'length IS NOT NULL'),
        ('idx_real_estate_acreage_area', 'real_estate', 'acreage_area', 'acreage_area IS NOT NULL'),
        ('idx_real_estate_acreage_use', 'real_estate', 'acreage_use', 'acreage_use IS NOT NULL'),
        
        # Giá
        ('idx_real_estate_total_price', 'real_estate', 'total_price', 'total_price IS NOT NULL'),
        
        # Địa chỉ
        ('idx_real_estate_street_id', 'real_estate', 'street_id', None),
        ('idx_real_estate_ward_id', 'real_estate', 'ward_id', None),
        ('idx_real_estate_district_id', 'real_estate', 'district_id', None),
        ('idx_real_estate_city_id', 'real_estate', 'city_id', None),
        
        # Loại hình
        ('idx_real_estate_type_estate_id', 'real_estate', 'type_estate_id', None),
        ('idx_real_estate_style_id', 'real_estate', 'style_id', None),
        ('idx_real_estate_direction_id', 'real_estate', 'direction_id', None),
        ('idx_real_estate_way_id', 'real_estate', 'way_id', None),
        ('idx_real_estate_type_demand_id', 'real_estate', 'type_demand_id', None),
        ('idx_real_estate_secondary_form_id', 'real_estate', 'secondary_form_id', None),
        ('idx_real_estate_job_profession_id', 'real_estate', 'job_profession_id', None),
        
        # Ngày tháng
        ('idx_real_estate_date_entry', 'real_estate', 'date_entry', None),
        ('idx_real_estate_date_updated', 'real_estate', 'date_updated', None),
        ('idx_real_estate_date_contract_exp', 'real_estate', 'date_contract_exp', None),
        ('idx_real_estate_date_last_modified', 'real_estate', 'date_last_modified', None),
        
        # Mã code
        ('idx_real_estate_code', 'real_estate', 'code', None),
        
        # Nguồn
        ('idx_real_estate_source_image', 'real_estate', 'source_image', None),
    ]
    
    _logger.info('Creating single column indexes...')
    for idx_name, table, column, where_clause in single_indexes:
        try:
            where_sql = f" WHERE {where_clause}" if where_clause else ""
            cr.execute(f"""
                CREATE INDEX IF NOT EXISTS {idx_name} 
                ON {table}({column}){where_sql}
            """)
            _logger.info(f'  ✓ Created index: {idx_name} on {table}({column})')
        except Exception as e:
            _logger.warning(f'  ✗ Failed to create index {idx_name}: {str(e)}')
    
    # 2. Composite indexes - Các tổ hợp trường hay search cùng nhau
    composite_indexes = [
        # Địa chỉ (district + ward + street) - Search theo khu vực
        ('idx_real_estate_location', 'real_estate', 'district_id, ward_id, street_id'),
        
        # Giá + Diện tích - Search theo giá và diện tích
        ('idx_real_estate_price_area', 'real_estate', 'total_price, acreage_area'),
        
        # Loại + Kiểu - Search theo loại nhà và kiểu
        ('idx_real_estate_type_style', 'real_estate', 'type_estate_id, style_id'),
        
        # Quận + Giá - Search theo quận và giá
        ('idx_real_estate_district_price', 'real_estate', 'district_id, total_price'),
        
        # Ngày cập nhật + Trạng thái đăng bài
        ('idx_real_estate_date_status', 'real_estate', 'date_last_modified, status_advertising'),
    ]
    
    _logger.info('Creating composite indexes...')
    for idx_name, table, columns in composite_indexes:
        try:
            cr.execute(f"""
                CREATE INDEX IF NOT EXISTS {idx_name} 
                ON {table}({columns})
            """)
            _logger.info(f'  ✓ Created composite index: {idx_name} on {table}({columns})')
        except Exception as e:
            _logger.warning(f'  ✗ Failed to create composite index {idx_name}: {str(e)}')
    
    # 3. Analyze table để PostgreSQL update statistics
    _logger.info('Analyzing real_estate table to update statistics...')
    try:
        cr.execute("ANALYZE real_estate")
        _logger.info('  ✓ Table analyzed successfully')
    except Exception as e:
        _logger.warning(f'  ✗ Failed to analyze table: {str(e)}')
    
    _logger.info('=' * 80)
    _logger.info('Migration completed successfully!')
    _logger.info('All indexes have been created for real_estate table')
    _logger.info('Performance should improve significantly for search operations')
    _logger.info('=' * 80)
