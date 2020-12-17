# -*- coding: utf-8 -*-
##############################################################################
#
#
##############################################################################
from odoo import  api, fields, models, _,exceptions

class AccountInvoice(models.Model):
    _inherit = 'account.move'


    # def copy(self, default=None):
    #     """ Initialized fields to the copy a register
    #             """
    #     # NOTE: use ids argument instead of id for fix the pylint error W0622.
    #     # Redefining built-in 'id'
    #     default = default or {}
    #     default = default.copy()
    #     default.update({'wh_local': False, 'wh_muni_id': False})
    #     return super(AccountInvoice, self).copy(default)

    def _get_move_lines3(self,to_wh, journal_id, writeoff_account_id, writeoff_journal_id,date,name):
        """ Generate move lines in corresponding account
        @param to_wh: whether or not withheld
        @param period_id: Period
        @param pay_journal_id: pay journal of the invoice
        @param writeoff_acc_id: account where canceled
        @param writeoff_period_id: period where canceled
        @param writeoff_journal_id: journal where canceled
        @param date: current date
        @param name: description
        """
        context = self._context or {}
        # res = super(AccountInvoice, self)._get_move_lines(to_wh, journal_id, writeoff_account_id, writeoff_journal_id,date,name)
        res = []
        rp_obj = self.env['res.partner']

        if to_wh and to_wh != []:
            invoice = self.browse(to_wh.invoice_id.id)
            acc_part_brw = rp_obj._find_accounting_partner(
                to_wh.invoice_id.partner_id)
            types = {
                'out_invoice': -1,
                'in_invoice': 1,
                'out_refund': 1,
                'in_refund': -1
            }
            direction = types[invoice.type]
            if invoice.type == 'in_invoice':
                acc = acc_part_brw.property_county_wh_payable and \
                    acc_part_brw.property_county_wh_payable.id or False
            else:
                acc = acc_part_brw.property_county_wh_receivable and \
                    acc_part_brw.property_county_wh_receivable.id or False
            if not acc:
                raise exceptions.except_orm(
                    _('¡Falta una cuenta local en el socio!'),
                    _("Al Proveedor [% s] le falta una cuenta local. Por favor llene"
                      " el campo faltante") % (acc_part_brw.name,))
            res.append((0, 0, {
                'debit': direction * to_wh.amount < 0 and
                (-direction * to_wh.amount),
                'credit': direction * to_wh.amount > 0 and
                direction * to_wh.amount,
                'partner_id': acc_part_brw.id,
                'ref': name,
                'date': date,
                'currency_id': False,
                'name': name,
                'account_id': acc,
            }))
            self.residual = self.amount_residual + direction * to_wh.amount
         #   self.residual_company_signed = self.residual_company_signed + direction * to_wh.amount
        return res

    def _retenida_munici(self):

        context = self._context or {}
        res = {}
        for inv_id in self.ids:
            res[inv_id] = self.test_retenida_muni()
        return res

    def _get_inv_munici_from_line(self):
        context = self._context or {}
        move = {}
        aml_brw = self.env['account.move.line'].browse(self)
        for line in aml_brw:
            if line.reconcile_partial_id:
                for line2 in line.reconcile_partial_id.line_partial_ids:
                    move[line2.move_id.id] = True
            if line.reconcile_id:
                for line2 in line.reconcile_id.line_id:
                    move[line2.move_id.id] = True
        invoice_ids = []
        if move:
            invoice_ids = self.pool.get('account.move').search(self,
                 [('move_id', 'in', move.keys())], context=context)
        return invoice_ids

    def _get_inv_munici_from_reconcile(self):
        context = self._context or {}
        move = {}
        amr_brws = self.env['account.move.reconcile'].browse(self)
        for amr_brw in amr_brws:
            for line in amr_brw.line_partial_ids:
                move[line.move_id.id] = True
            for line in amr_brw.line_id:
                move[line.move_id.id] = True

        invoice_ids = []
        if move:
            invoice_ids = self.env['account.move'].search(
                self, [('move_id', 'in', move.keys())], context=context)
        return invoice_ids

    def test_retenida_muni(self):
        type2journal = {'out_invoice': 'mun_sale',
                        'out_refund': 'mun_sale',
                        'in_invoice': 'mun_purchase',
                        'in_refund': 'mun_purchase'}
        type_inv = self.browse().type
        type_journal = type2journal.get(type_inv, 'mun_purchase')
        res = self.ret_payment_get()
        if not res:
            return False
        ok = True

        self.env.cr.execute('select l.id'
                   ' from account_move_line l'
                   ' inner join account_journal j on (j.id=l.journal_id)'
                   ' where l.id in (' + ','.join(
                       [str(item) for item in res]) + ') and j.type=' +
                   '\'' + type_journal + '\'')
        ok = ok and bool(self.env.cr.fetchone())
        return ok

    def action_cancel(self):
        """ Verify first if the invoice have a non cancel local withholding doc.
        If it has then raise a error message. """
        context = self._context or {}
        for inv_brw in self.browse():
            if not inv_brw.wh_muni_id:
                super(AccountInvoice, self).action_cancel()
            else:
                raise exceptions.except_orm(
                    _("Error!"),
                    _("No puede cancelar una factura que no tiene"
                      "Documento de retención municipal. Primero se debe cancelar la"
                      "factura el documento de retención municipal y luego puedes"
                      "cancelar esta factura."))
        return True

    # @api.onchange('invoice_line_ids')
    # def _compute_invoice_mount_wh_muni(self):
    #     new = self.invoice_line_ids
    #     if new:
    #            # taxes_group = self.get_taxes_values()
    #             for tax in new:
    #                 if "Impuesto Municipal" in tax.values():
    #                     account = self._origin
    #                     #amount_total = self.env['account.move'].browse(self.id).amount_tax
    #                     #self.amount_muni = self.amount_tax #Metodo 1
    #
    #                     amount_wh_muni = tax.get('amount') #Metodo2
    #                     self.amount_muni = amount_wh_muni
    #                 else:
    #                     return None
    #             return

    wh_local = fields.Boolean(string='Local Withholding', compute='_retenida_munici', store=True,
                              help="The account moves of the invoice have been withheld with \account moves of the payment(s).")
    wh_muni_id = fields.Many2one('account.wh.munici', 'Wh. Municipality', readonly=True, help="Withholding muni.")

    amount_muni = fields.Monetary(string='Impuesto Municipal', store=True, readonly=True,)
                                  #compute='_compute_invoice_mount_wh_muni')

