{
    "name": "Retencion Municipal Venezuela",
    "version": "0.2",
    "author": "Localizacion Venezolana",
    "category": 'Generic Modules/Accounting',
    "depends": ["base_vat","base","account",'locv_account_fiscal_requirements', 'locv_base_withholdings'],
  #  'test': [
  #      'test/awm_customer.yml',
  #      'test/awm_supplier.yml',
  #  ],
    'data': [
  #      'security/wh_muni_security.xml',
        'security/ir.model.access.csv',
  #      'data/wh_muni_sequence.xml',
        'view/account_invoice_view.xml',
        'view/partner_view.xml',
        'view/wh_muni_view.xml',
        'report/withholding_muni_report.xml',

    ],

    'installable': True,
}