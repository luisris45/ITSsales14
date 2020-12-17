# coding: utf-8
###########################################################################
from odoo import api
from odoo import fields, models
from odoo import exceptions
from odoo.tools.translate import _


class AccountInvoice(models.Model):
    '''Esta clase es para crear en la factura el saldo de anticipo del cliente o proveedor'''
    _inherit = 'account.move'

    account_advance_ids = fields.One2many('account.advanced.payment','invoice_id')
    partner_id = fields.Many2one('res.partner')
    sum_amount_available = fields.Monetary('Anticipo Disponible')
    currency_id = fields.Many2one('res.currency', string='Currency')


    @api.onchange('partner_id')
    def _onchange_amount_available(self):
        '''Muestra el saldo disponible en los anticipos para clientes y proveedores'''
        self.sum_amount_available = 0
        advance_obj = self.env['account.advanced.payment']

        if self.type == 'out_invoice' or self.type == 'out_refund':
            advance_bw = advance_obj.search([('partner_id', '=', self.partner_id.id),
                                         ('state', '=', 'available'),
                                         ('is_customer','=',True)])

            for advance in advance_bw:
                self.sum_amount_available += advance.amount_available
        else:
            advance_bw = advance_obj.search([('partner_id', '=', self.partner_id.id),
                                             ('state', '=', 'available'),
                                             ('is_supplier', '=', True)])
            for advance in advance_bw:
                self.sum_amount_available += advance.amount_available
        return