# coding: utf-8
##############################################################################
{
    "name": "Calcula la Retención del ISLR",
    "version": "0.3",
    "author": "Localizacion Venezolana",
    "license": "AGPL-3",
    "category": "Contabilidad, facturacion",
    #"website": "",
    "depends": [
        "account",
        "locv_account_fiscal_requirements",
        "locv_base_withholdings",
        'locv_grupo_localizacion',
    ],
    'demo': [

    ],
    "data": [
        'security/ir.model.access.csv',
         "data/l10n_ve_islr_withholding_data.xml",
         "data/sequence_withholding_islr.xml",
         "view/invoice_view.xml",
         "view/partner_view.xml",
         "view/res_company_view.xml",
         "view/islr_wh_doc_view.xml",
         "view/islr_wh_concept_view.xml",
         "view/product_view.xml",
         "view/islr_xml_wh.xml",
         "report/wh_islr_report.xml",
         #"report/islr_wh_report.xml"
    ],
    "installable": True,
    'application': True,
}
