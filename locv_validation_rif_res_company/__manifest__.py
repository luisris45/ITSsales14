# -*- coding: UTF-8 -*-

{
    "name": "RIF Company-Res_partner Validaciones y agregación de campos sobre la compañia",
    "version": "1.0",
    "author": "Localizacion Venezolana",
    'depends' : [
                 "base","base_vat","locv_validation_res_partner"],
    "data": [
        'security/ir.model.access.csv',
        'views/locv_validation_res_company_rif.xml',
	    'views/locv_validation_res_partner.xml',
             ],
    'category': 'company',
    "description": """
    Modifica campo y realiza validaciones al vat(nif) y al email de la compañia; Modifica campo y realiza validaciones al vat(nif) y al email del partner cliente-proveedor.
    """,
    'installable': True,
    'application': True,
}
