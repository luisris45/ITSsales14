# coding: utf-8
###########################################################################

##############################################################################
{
    "name": "Facturacion-validaciones y correcciones; números de control automaticos Clientes-Proveedores",
    "version": "1.0",
    "author": "Localizacion Venezolana",
    "license": "AGPL-3",
    "category": "facturacion",
    #"website": "",
    "colaborador":"Maria Carreño",
    "depends": [
        "account",
        "base",
        "base_vat",
        "locv_validation_res_partner",
        "locv_validation_rif_res_company"
    ],
    'demo': [
    ],
    "data": [
        'security/ir.model.access.csv',
        'view/invoice_view.xml',
    ],
    'test': [

    ],
    "installable": True,
    'application': True,
}