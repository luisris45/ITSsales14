# coding: utf-8
###############################################################################

from odoo import models, fields


class ResCompany(models.Model):
    _inherit = "res.company"

    consolidate_vat_wh = fields.Boolean(
        string="Consolidar Quincena de Retencion de IVA", default=False,
        help='Si se establece, las retenciones en IVA generadas en una misma'
        ' noche se agruparán en un recibo de retención')
    allow_vat_wh_outdated = fields.Boolean(
        string="Permitir retención de IVA",
        help="Permite confirmar comprobantes de retención para anteriores o futuras "
        " fechas.")
    propagate_invoice_date_to_vat_withholding = fields.Boolean(
        string='Propagar fecha de factura a retención de IVA', default=False,
        help='Propague la fecha de la factura a la retención de IVA. Por defecto está en '
        'Falso.')
