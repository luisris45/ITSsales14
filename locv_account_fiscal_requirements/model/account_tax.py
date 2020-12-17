# coding: utf-8


from odoo import fields,models


class AccountTax(models.Model):
    _inherit = 'account.tax'

    appl_type = fields.Selection(
            [('exento', 'Exento'),
             ('sdcf', 'No tiene derecho a crédito fiscal'),
             ('general', 'Alicuota General'),
             ('reducido', 'Alicuota Reducida'),
             ('adicional', 'Alicuota General + Adicional')],
            'Tipo de Alicuota',
            required=False,
            help='Especifique el tipo de alícuota para el impuesto para que pueda procesarse '
                 'según el libro de compra / venta generado')
