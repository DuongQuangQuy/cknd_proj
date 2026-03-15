# -*- coding: utf-8 -*-
{
    'name': "FS Contact",

    'summary': """
        FS Contact """,

    'description': """
        FS Contact
    """,

    'author': "FS",
    'website': "",

    'category': '',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': [
        'base', 'mail','base_address_city','sms','account'
    ],

    # always loaded
    'data': [
        # data
        'data/sequence.xml',
        # security
        'security/ir.model.access.csv',
        # views
        'views/job_profession_view.xml',
        'views/res_street_view.xml',
        'views/res_ward_view.xml',
        'views/res_district_view.xml',
        'views/res_city_view.xml',
        'views/res_partner_view.xml',

        # wizard
        # 'wizard/goods_delivery_wizard_views.xml',
    ],
    'application': True,
}
