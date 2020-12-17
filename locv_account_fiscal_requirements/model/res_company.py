# coding: utf-8

from odoo import fields,models,api


class Company(models.Model):
    _inherit = 'res.company'

    jour_id = fields.Many2one(
            'account.journal', 'Diario', required=False,
            help="Diario predeterminado para facturas dañadas")

    acc_id = fields.Many2one(
            'account.account', 'Cuenta', required=False,
            help="Cuenta predeterminada utilizada para facturas y líneas dañadas "
                 " facturas")

    printer_fiscal = fields.Boolean(
            'Manages fiscal printer',
            help='Indica que la compañía puede operar una impresora fiscal')

    fax=fields.Char( string="Fax", size=13)

    @api.model
    def create(self, vals):
        """ To create a new record,
        adds a Boolean field to true
        indicates that the partner is a company
        """
        if self._context is None:
            context = {}
        context = dict(self._context)
        context.update({'create_company': True})
        return super(Company, self).create(vals)

    def write(self, values):
        """ To write a new record,
        adds a Boolean field to true
        indicates that the partner is a company
        """
        context = dict(self._context or {})
        context.update({'create_company': True})
        return super(Company, self).write(values)

Company()
