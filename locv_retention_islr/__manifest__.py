# -*- coding: utf-8 -*-
{
    'name': "Retention ISLR",

    'summary': """Module_Retention_ISLR""",

    'description': """
      Generación de reportes por concepto de retención del ISLR, 
	reportes pdf y xls
    """,
    'version': '1.0',
    'author': 'Localizacion Venezolana',
    'category': 'Tools',

    # any module necessary for this one to work correctly
    'depends': ['base', 'account', 'locv_withholding_islr', 'locv_grupo_localizacion'],

    # always loaded
    'data': [
         'security/ir.model.access.csv',
        'wizard/wizard_retention_islr.xml',
        'report/report_retention_islr_pdf.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
    ],
    "installable": True,
    'application': True,

}
