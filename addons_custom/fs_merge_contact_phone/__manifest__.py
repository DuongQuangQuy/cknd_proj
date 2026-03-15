# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Merge Contact Phone',
    'version': '1.0',
    'category': 'Merge Contact Phone',
    'summary': 'Merge Contact Phone Number',
    "author": "nguynv",
    'description': """
    This module merge contact phone number
    """,
    'depends': [
        'base',
        'web',
        'fs_real_estate'
    ],
    'data': [
        'security/ir.model.access.csv',
        'wizard/merge_phone_contact_views.xml',
    ],

    'assets': {
        'web.assets_backend': [
            'fs_merge_contact_phone/static/src/js/grouped_one2many.js',
            'fs_merge_contact_phone/static/src/scss/grouped_one2many.scss',
        ],
        'web.assets_qweb': [
            'fs_merge_contact_phone/static/src/xml/**/*',
        ],
    },
    'installable': True,
    'auto_install': False,
}
