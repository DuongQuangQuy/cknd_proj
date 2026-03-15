# -*- coding: utf-8 -*-

{
    "name": "Multi-selection for one2many fields",
    "version": "15.0.1.0.0",
    "author": "Nguynv",
    "summary": "This widget adds the capability for selecting multiple records in one2many fields"
               " and work on those records",
    "description": '''
        Description
        -----------
        Add widget="one2many_selectable"
        You can get the selected records in python function, a simple python function is as follows:
    ''',
    "category": "Web",
    "images": ["static/description/banner.jpg"],
    "depends": [
        'web', "sale",
    ],
    "data": [
    ],
    'images': ['static/description/banner.jpg'],
    'assets': {
        'web.assets_backend': [
            'fs_one2many_selection/static/src/js/widgets.js',
        ],
        'web.assets_qweb': [
            'fs_one2many_selection/static/src/xml/**/*',
        ],
    },
    "auto_install": False,
    "installable": True,
    'license': 'AGPL-3',
    "application": False,
}
