# coding: utf-8
###########################################################################

from odoo import models, fields, api


class res_partner(models.Model):
    '''Se crea dos campos para agregar a la ficha del cliente y proveedor las cuentas
     contables de anticipo a cliente y proveedor'''

    _inherit = 'res.partner'
    es_cliente = fields.Boolean(string='Es un cliente', default=False,
                                help="Chequea si el usuario es un cliente, en caso contrario es proveedor")
    tipo_usuario = fields.Selection(string='Cliente o proveedor',
                                    selection=[('cliente', 'Cliente'), ('proveedor', 'Proveedor')],
                                    compute='_compute_cliente_type', inverse='_write_cliente_type')
    account_advance_payment_purchase_id = fields.Many2one('account.account','Cuenta de Anticipos de Compras')
    account_advance_payment_sales_id = fields.Many2one('account.account','Cuenta de Anticipos de Ventas')
    journal_advanced_id = fields.Many2one('account.journal','Diario de Anticipos')

    @api.depends('es_cliente')
    def _compute_cliente_type(self):
        for partner in self:
            partner.tipo_usuario = 'cliente' if partner.es_cliente else 'proveedor'

    def _write_cliente_type(self):
        for partner in self:
            partner.es_cliente = partner.tipo_usuario == 'cliente'

    @api.onchange('tipo_usuario')
    def onchange_company_type(self):
        self.es_cliente = (self.tipo_usuario == 'cliente')
