# coding: utf-8
######################################

from odoo import models, fields


class AccountTax(models.Model):
    _inherit = 'account.tax'

    ret = fields.Boolean(
        string='Retenido?',
        help="Indique si el impuesto debe ser retenido")

    wh_vat_collected_account_id = fields.Many2one(
        'account.account',
        string="Cuenta de retención de IVA de factura",
        help="Esta cuenta se utilizará al aplicar una retención a una Factura")

    wh_vat_paid_account_id = fields.Many2one(
        'account.account',
        string="Cuenta de Devolucion de la retención de IVA",
        help="Esta cuenta se utilizará al aplicar una retención a un Reembolso")

    type_tax = fields.Selection([('iva', 'IVA'),
        						('islr', 'ISLR'),
        						('responsability','Responsabilidad social'),
        						('municipal', 'Municipal'),
        						('fiscal', 'Timbre fiscal')],required=True,help="Selecione el Tipo de Impuesto",string="Tipo de Impuesto")