# coding: utf-8
##############################################################################

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'


    automatic_income_wh= fields.Boolean(
            'Retención Automática de Ingresos', default=False,
            help='Cuando sea cierto, la retención de ingresos del proveedor se'
                 'validara automáticamente')
    propagate_invoice_date_to_income_withholding= fields.Boolean(
            'Propague la fecha de la factura a la retención de ingresos', default = False,
            help='Propague la fecha de la factura a la retención de ingresos. Por defecto es'
                 'en falso')

