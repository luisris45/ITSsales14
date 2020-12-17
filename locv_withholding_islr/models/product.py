# coding: utf-8
##############################################################################

from odoo import fields, models, api
from odoo import exceptions
from odoo.tools.translate import _


class ProductTemplate(models.Model):

    _inherit = "product.template"


    concept_id= fields.Many2one(
            'islr.wh.concept', 'Withhold  Concept', required=False,
            help="Concept Income Withholding to apply to the service")



class ProductProduct(models.Model):

    _inherit = "product.product"

    @api.onchange('product_type', 'prd_type')
    def onchange_product_type(self):
        """ Add a default concept for products that are not service type,
        Returns false if the product type is not a service, and if the
        product is service, returns the first concept except 'No apply
        withholding'
        @param prd_type: product type new
        """
        concept_id = False
        if self.prd_type != 'service':
            concept_obj = self.env['islr.wh.concept']

            concept_id = concept_obj.search([('withholdable', '=', False)])
            concept_id = concept_id and concept_id[0] or False
            if not concept_id:
                raise exceptions.except_orm(
                    _('Invalid action !'),
                    _("Debe crear el concepto de retención de ingresos"))

        return {'value': {'concept_id': concept_id or False}}
