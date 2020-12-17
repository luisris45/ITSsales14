# coding: utf-8

###############################################################################

from odoo.tools.translate import _
from odoo import models,fields, exceptions, _


class WizNroctrl(models.TransientModel):
    _name = 'wiz.nroctrl'
    _description = "Wizard que cambia el número de control de la factura."



    def set_noctrl(self):
        """ Change control number of the invoice
        """
        account_move = self.env['account.move'].search([])


        if not self.sure:
            raise exceptions.except_orm(
                _("Error!"),
                _("Confirme que desea hacer esto marcando la casilla "
                  " opción"))
        inv_obj = self.env['account.move']
        n_ctrl = self.name
        for noctrl in account_move :
            if noctrl.nro_ctrl ==  n_ctrl:
                raise exceptions.except_orm(
                    _("Error!"),
                    _("El Numero de Control ya Existe"))
        active_ids = self._context.get('active_ids', [])
        inv_obj.browse(active_ids).write({'nro_ctrl': n_ctrl})
        return {}


    name = fields.Char('Número de Control', required=True)
    sure = fields.Boolean('¿Estas seguro?')

WizNroctrl()
