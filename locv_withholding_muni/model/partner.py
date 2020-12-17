# -*- coding: utf-8 -*-
##############################################################################
#
#    autor: Tysamnca.
#
##############################################################################

from odoo import fields, models

class ResParther(models.Model):
    _inherit = 'res.partner'

    property_county_wh_payable = fields.Many2one('account.account',
                                                 company_dependent=True,
                                                 string="Cuenta de Compra para Impuesto Municipal",
                                                 oldname="property_county_wh_payable",
                                                 help="This account will be used debit local withholding amount",
                                                )

    property_county_wh_receivable = fields.Many2one('account.account',
                                                    company_dependent=True,
                                                    string="Cuenta de Venta para Impuesto Municipal",
                                                    oldname="property_county_wh_receivable",
                                                    help="This account will be used credit local withholding amount",
                                                   )

    wh_muni_agent = fields.Boolean('Se le Aplica Impuesto Municipal?')
    wh_muni = fields.Float('Porcentaje de Retencion')