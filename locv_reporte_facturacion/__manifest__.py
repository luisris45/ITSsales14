# -*- coding: utf-8 -*-
{
    'name': "Reporte de Factura cliente-proveedor",

    'summary': """Reporte de Factura""",

    'description': """
       Reporte para facturas y facturas sin pago en Facturas de Clientes y Proveedores.
       Elaborado por: Ing. Maria Carreno
    """,
    'version': '1.0',
    'author': 'Localizacion Venezolana',
    'category': 'Tools',

    # any module necessary for this one to work correctly
    'depends': ['base', 'account'],

    # always loaded
    'data': [
        'report/reporte_facturacion.xml',

    ],
    # only loaded in demonstration mode
    'demo': [
        #'demo/demo.xml',
    ],
    'application': True,
}
