# coding: utf-8
##############################################################################
from odoo import fields, models, api
from odoo.addons import decimal_precision as dp


class IslrRates(models.Model):

    """ The module to create the rates | the withholding concepts
    """
    _name = 'islr.rates'
    _description = 'Rates'


    #
    # def _get_name(self, field_name):
    #     """ Get the name of the withholding concept rate
    #     """
    #     res = {}
    #     for rate in self.browse():
    #         if rate.nature:
    #             if rate.residence:
    #                 name = 'Persona' + ' ' + 'Natural' + ' ' + 'Residente'
    #             else:
    #                 name = 'Persona' + ' ' + 'Natural' + ' ' + 'No Residente'
    #         else:
    #             if rate.residence:
    #                 name = 'Persona' + ' ' + 'Juridica' + ' ' + 'Domiciliada'
    #             else:
    #                 name = 'Persona' + ' ' + 'Juridica' + ' ' + \
    #                     'No Domiciliada'
    #         res[rate.id] = name
    #     return res


    name = fields.Char(string='Tasa',  size=256,
            help="Nombre de tasa de retención para los conceptos de la retención")
    code = fields.Char(
            'Código de concepto', size=3, required=True, help="Código Conceptual")
    base = fields.Float(
            'Sin importe de impuestos', required=True,
            help="Porcentaje de la cantidad sobre la cual aplicar la retención",
            digits=dp.get_precision('Withhold ISLR'))
    minimum= fields.Float(
            'Min. Cantidad', required=True,
            digits=dp.get_precision('Withhold ISLR'),
            help="Cantidad mínima, a partir de la cual determinará si esta"
                 "retenido")
    wh_perc= fields.Float(
            'Porcentaje de la Cantidad', required=True,
            digits=dp.get_precision('Withhold ISLR'),
            help="El porcentaje que se aplica a los ingresos imponibles sujetos a impuestos arroja la"
                 "cantidad a retener")
    subtract= fields.Float(
            'Sustracción en unidades impositivas', required=True,
            digits=dp.get_precision('Withhold ISLR'),
            help="Cantidad a restar de la cantidad total a retener "
                 "Cantidad Porcentaje de retención ..... Este sustraendo solamente"
                 "aplicado la primera vez que realiza una retención")
    residence= fields.Boolean(
            'Residencia',
            help="Indica si una persona es residente, en comparación con la "
                 "dirección de la empresa")
    nature =fields.Boolean(
            'Natural', help="Indica si una persona es natural o Juridica")
    concept_id= fields.Many2one(
            'islr.wh.concept', 'Withhold  Concept', required=False,
            ondelete='cascade',
            help="Concepto de retención asociado a esta tasa")
    rate2 = fields.Boolean(
            'Tasa 2', help='Tasa utilizada para entidades extranjeras')

    def _get_name(self):
        """ Get the name of the withholding concept rate
        """
        res = {}
        for rate in self:
            if rate.nature:
                if rate.residence:
                    name = 'Persona' + ' ' + 'Natural' + ' ' + 'Residente'
                else:
                    name = 'Persona' + ' ' + 'Natural' + ' ' + 'No Residente'
            else:
                if rate.residence:
                    name = 'Persona' + ' ' + 'Juridica' + ' ' + 'Domiciliada'
                else:
                    name = 'Persona' + ' ' + 'Juridica' + ' ' + \
                        'No Domiciliada'
            res[rate.id] = name
        return res
IslrRates()
