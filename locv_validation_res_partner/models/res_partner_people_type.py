# -*- coding: utf-8 -*-
import locale
from odoo import api, exceptions, fields, models, _
from odoo.tools import float_is_zero, float_compare, pycompat

class ResPartner(models.Model):
    _inherit = 'res.partner'

    people_type_individual = fields.Selection([
        ('pnre', 'PNRE    Persona Natural Residente'),
        ('pnnr', 'PNNR    Persona Natural No Residente')
        ], 'Tipo de Persona')

    people_type_company = fields.Selection([
        ('pjdo', 'PJDO    Persona Jurídica Domiciliada'),
        ('pjnd', 'PJND    Persona Jurídica No Domiciliada')], 'Tipo de Persona')



    @api.onchange('company_type')
    def change_country_id_partner(self):
        if self.company_type and self.company_type == 'person':
            self.country_id = 238
        elif self.company_type == 'company':
            self.country_id = False