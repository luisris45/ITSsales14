
# coding: utf-8
from odoo import models, fields, api
from odoo.tools.translate import _
from datetime import datetime,date
from dateutil import relativedelta


class AccountMoveInherit(models.Model):
    _inherit = 'account.move'


    ###################### -------------- Cliente ----#################################################
    nro_ctrl = fields.Char(
        'Número de Control', size=32,
        help="Número utilizado para gestionar facturas preimpresas, por ley "
             "Necesito poner aquí este número para poder declarar"
             "Informes fiscales correctamente.",copy=False, store=True, domain="['|',('type', '=', 'out_invoice'),('type', '=', 'out_refund')]")


    ###################### ---------- Funciones ----#################################################

    def _get_company(self):
        id = self.id
        res_company = self.env['res.company'].search([('id', '=', self.company_id.id)])
        return res_company


    def action_post(self):
        var = super(AccountMoveInherit, self).action_post()
        if self.type in ('out_invoice'):
            if not self.nro_ctrl:
                self.nro_ctrl = self._get_sequence_code()
                self.write({'nro_ctrl': self.nro_ctrl})
        if  self.type in ('out_refund'):
            if not self.nro_ctrl :
                name_factc = self.reversed_entry_id.display_name
                factc_affect = self.env['account.move'].search([('name','=',name_factc)])
                nro_ctrl = factc_affect.nro_ctrl
                self.write({'nro_ctrl': nro_ctrl})
        return var

    def _get_sequence_code(self):
        # metodo que crea la secuencia del número de control, si no esta creada crea una con el
        # nombre: 'l10n_nro_control

        self.ensure_one()
        SEQUENCE_CODE = 'l10n_nro_control_sale'
        company_id = self._get_company()
        IrSequence = self.env['ir.sequence'].with_context(force_company=company_id.id)
        self.nro_ctrl = IrSequence.next_by_code(SEQUENCE_CODE)
        return self.nro_ctrl


