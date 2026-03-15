# -*- coding: utf-8 -*-
{
    'name': "FS Real Estate",

    'summary': """
        FS Real Estate """,

    'description': """
        FS Real Estate
    """,

    'author': "FS",
    'website': "",

    'category': '',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': [
        'base', 'mail','fs_contacts', 'fs_one2many_selection','web'
    ],

    # always loaded
    'data': [
        # data
        'data/ir_sequence_data.xml',
        # security
        'security/real_estate_groups.xml',
        'security/ir.model.access.csv',
        # views
        'views/type_demand_view.xml',
        'views/estate_way_view.xml',
        'views/secondary_form_view.xml',
        'views/estate_direction_view.xml',
        'views/estate_stair_view.xml',
        'views/type_estate_view.xml',
        'views/estate_style_view.xml',
        'views/group_style_view.xml',
        'views/estate_structure_view.xml',
        'views/real_estate_view.xml',
        'views/role_detail_view.xml',
        'views/res_partner_view.xml',
        'views/group_direction_view.xml',
        'views/real_estate_search_view.xml',
        'views/demand_estate_search_view.xml',
        'views/res_config_settings_views.xml',
        'views/real_estate_search_expired_view.xml',
        'views/search_demand_estate_customer_view.xml',
        'views/real_estate_prices_config_views.xml',
        'views/real_estate_advertising_template_views.xml',

        'views/call_sale_estate_view.xml',
        'views/offering_history_view.xml',
        'views/real_estate_favorite.xml',
        'views/estate_category_views.xml',




        #wizard
        'wizard/update_address_view.xml',

        'wizard/advertising_sample_views.xml',
        'wizard/greeting_customer_estate_views.xml',
        'wizard/greeting_customer_employee_view.xml',
        'wizard/detail_contact_view.xml',

        'views/menus.xml',

    ],
    'assets': {
        'web.assets_backend': [
            'fs_real_estate/static/src/js/real_estate_advertising_template.js',
            'fs_real_estate/static/src/js/dropdown_hover.js',
            # 'fs_real_estate/static/src/js/real_estate_favorite.js',
            # 'fs_real_estate/static/src/js/real_estate_pagination.js',
            'fs_real_estate/static/src/css/custom_form_view.scss',
            'fs_real_estate/static/src/css/custom_size_form_view.css',
        ],
    },
    'application': True,
}
