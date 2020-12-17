# coding: utf-8
###########################################################################

import time
from odoo.addons import decimal_precision as dp
from odoo import models, fields, api, exceptions, _
import logging
_logger = logging.getLogger(__name__)

class AccountMove(models.Model):
    _inherit = 'account.move'

    rela_wh_iva = fields.Many2one('account.wh.iva')

    wh_iva = fields.Boolean('¿Ya se ha retenido esta factura con el IVA?',
                            # compute='_compute_retenida',
                            copy=False ,help="Los movimientos de la cuenta de la factura han sido retenidos con "
                                 "movimientos de cuenta de los pagos.")
    wh_iva_id = fields.Many2one(
        'account.wh.iva', string='Documento de Retención de IVA',
        compute='_compute_wh_iva_id', store=True,
        help="Este es el documento de retención de IVA donde en esta factura "
             "está siendo retenida.")
    vat_apply = fields.Boolean(
        string='Excluir este documento de la retención del IVA',
        states={'draft': [('readonly', False)]},
        help="Esta selección indica si generar la factura "
             "documento de retención")
    consolidate_vat_wh = fields.Boolean(
        string='Group wh doc', readonly=True,
        states={'draft': [('readonly', False)]}, default=False,
        help="Esta selección indica agrupar esta factura en "
             "documento de retención")


    @api.depends('wh_iva_id.wh_lines')
    def _compute_wh_iva_id(self):
        for record in self:
            lines = self.env['account.wh.iva.line'].search([
                ('invoice_id', '=', record.id)])
            record.wh_iva_id = lines and lines[0].retention_id.id or False


    # @api.onchange('wh_iva')
    # def _compute_retenida(self):
    #     """ Verify whether withholding was applied to the invoice
    #     """
    #     for record in self:
    #         try:
    #             record.wh_iva = record.test_retenida()
    #         except:
    #             record.wh_iva = False


    def action_post(self):
        var = super(AccountMove, self).action_post()
        monto_tax = 0
        if self:
          #  self._compute_retenida()
            resul = self._withholdable_tax()
            for inv in self.line_ids:
                if len(self.line_ids.tax_ids) == 1:
                    for tax in inv.tax_ids:
                       if tax.amount == 0:
                           monto_tax = 2000



        if self.company_id.partner_id.wh_iva_agent and self.partner_id.wh_iva_agent and resul and monto_tax == 0:
            if self.state == 'posted':
                for ilids in self.invoice_line_ids:
                    self.check_document_date()
                    self.check_invoice_dates()
                    apply = self.check_wh_apply()
                    if apply == True:
                        self.check_withholdable()
                        self.action_wh_iva_supervisor()
                        self.action_wh_iva_create()
        return self


    def check_document_date(self):
        """
        check that the invoice in open state have the document date defined.
        @return True or raise an orm exception.
        """
        for inv_brw in self:
            if (inv_brw.type in ('in_invoice', 'in_refund', 'out_invoice', 'out_refund') and
                    inv_brw.state == 'posted' and not inv_brw.date):
                raise exceptions.except_orm(
                    _('Advertencia'),
                    _('La fecha del documento no puede estar vacía cuando la factura es '
                      'en estado publicado.'))
        return True


    def check_invoice_dates(self):
        """
        check that the date document is less or equal than the date invoice.
        @return True or raise and osv exception.
        """
        for inv_brw in self:
            if (inv_brw.type in ('in_invoice', 'in_refund', 'out_invoice', 'out_refund') and
                    inv_brw.date and
                    not inv_brw.date <= inv_brw.invoice_date):
                raise exceptions.except_orm(
                    _('Warning'),
                    _('The document date must be less or equal than the'
                      ' invoice date.'))
        return True



    # def copy(self, default=None):
    #     """ Initialized fields to the copy a register
    #     """
    #     if default is None:
    #         default = {}
    #     # TODO: PROPERLY CALL THE WH_IVA_RATE
    #     default.update({'wh_iva': False,
    #                     'wh_iva_id': False,
    #                     'vat_apply': False})
    #     return super(AccountMove, self).copy(default)


    def wh_iva_line_create(self):
        """ Creates line with iva withholding
        """
        wil_obj = self.env['account.wh.iva.line']
        partner = self.env['res.partner']
        values = {}
        for inv_brw in self:
            wh_iva_rate = (
                inv_brw.type in ('in_invoice', 'in_refund', 'out_refund', 'out_invoice') and
                partner._find_accounting_partner(
                    inv_brw.partner_id).wh_iva_rate or
                partner._find_accounting_partner(
                    inv_brw.company_id.partner_id).wh_iva_rate)
            values = {'name':_('IVA WH - ORIGIN %s' % (inv_brw.name)),
                      'invoice_id': inv_brw.id,
                      'wh_iva_rate': wh_iva_rate,
                      }

        return values and wil_obj.create(values)


    def action_wh_iva_supervisor(self):
        """ Validate the currencys are equal
        """
        for inv in self:
            if inv.amount_total == 0.0:
                raise exceptions.except_orm(
                    _('Acción Invalida!'),
                    _('Esta factura tiene una cantidad total% s% s verifique el '
                      'precio de los productos') % (inv.amount_total,
                                            inv.currency_id.symbol))
        return True


    def get_fortnight_wh_id(self):
        """ Returns the id of the acc.wh.iva in draft state that correspond to
        the invoice fortnight. If not exist return False.
        """
        wh_iva_obj = self.env['account.wh.iva']
        partner = self.env['res.partner']
        for inv_brw in self:
            invoice_date = inv_brw.invoice_date
            acc_part_id = partner._find_accounting_partner(inv_brw.partner_id)
            #inv_period, inv_fortnight = period.find_fortnight(invoice_date)
            ttype = (inv_brw.type in ["in_refund", "out_refund"])

            for wh_iva in wh_iva_obj.search([
                    ('state', '=', 'draft'), ('type', '=', ttype), '|',
                    ('partner_id', '=', acc_part_id.id),
                    ('partner_id', 'child_of', acc_part_id.id)]):
                    #('fortnight', '=', inv_fortnight):
                return wh_iva.id
        return False


    def create_new_wh_iva(self):
        """ Create a Withholding VAT document.
        @param ids: only one id.
        @return id of the new wh vat document created.
        """
        ret_iva = []
        wh_iva_obj = self.env['account.wh.iva']
        rp_obj = self.env['res.partner']
        values = {}
        for inv_brw in self:
            acc_part_id = rp_obj._find_accounting_partner(inv_brw.partner_id)
            if inv_brw.type in ('out_invoice', 'out_refund'):
                acc_id = acc_part_id.property_account_receivable_id.id
                wh_type = 'out_invoice'
            else:
                acc_id = acc_part_id.property_account_payable_id.id
                wh_type = 'in_invoice'
                if not acc_id:
                    raise exceptions.except_orm(
                        _('Accion Invalida'),
                        _('Se debe configurar el partner'
                          'Con las Cuentas Contables'))
            values = {'name': _('IVA WH - ORIGIN %s' % (inv_brw.name)),
                      'type': wh_type,
                      'account_id': acc_id,
                      'partner_id': acc_part_id.id,
                      }
                # 'date_ret': inv_brw.invoice_date,
                # 'period_id': inv_brw.invoice_date,
                # 'date': inv_brw.invoice_date,

            if inv_brw.company_id.propagate_invoice_date_to_vat_withholding:
                ret_iva['date'] = inv_brw.invoice_date
                ret_iva['date_ret'] = ret_iva['date']
                ret_iva['period_id'] = ret_iva['date']
        return values and wh_iva_obj.create(values)


    def action_wh_iva_create(self):
        """ Create withholding objects """
        ret_iva = []
        for inv in self:
            if inv.wh_iva_id:
                if inv.wh_iva_id.state == 'draft':
                    pass
                    #inv.wh_iva_id.compute_amount_wh()
                else:
                    raise exceptions.except_orm(
                        _('Advertencia!'),
                        _('Ya tiene un documento de retención asociado a '
                          'su factura, pero este documento de retención no está en'
                          'cancelar estado.'))
            else:
                # Create Lines Data
                ret_id = {}
                ret_line_id = inv.wh_iva_line_create()
                fortnight_wh_id = inv.get_fortnight_wh_id()
                # Add line to a WH DOC
                if inv.company_id.consolidate_vat_wh and fortnight_wh_id:
                    # Add to an exist WH Doc
                    ret_id = fortnight_wh_id
                    if not ret_id:
                        raise exceptions.except_orm(
                            _('Error!'),
                            _('No se puede encontrar el documento de retención'))
                    wh_iva = self.env['account.wh.iva'].browse(ret_id)
                    wh_iva.write({'wh_lines': [(4, ret_line_id.id)]})
                else:
                    # Create a New WH Doc and add line
                    wh_iva_obj = self.env['account.wh.iva']
                    rp_obj = self.env['res.partner']
                    values = {}
                    for inv_brw in self:
                        acc_part_id = rp_obj._find_accounting_partner(inv_brw.partner_id)
                        if inv_brw.type in ('out_invoice', 'out_refund'):
                            acc_id = acc_part_id.property_account_receivable_id.id
                            wh_type = 'out_invoice'
                            values = {'name': _('IVA WH CLIENTE - ORIGIN %s' % (inv_brw.name)),
                                      'type': wh_type,
                                      'account_id': acc_id,
                                      'partner_id': acc_part_id.id,
                                      'date_ret': inv_brw.invoice_date,
                                      'period_id': inv_brw.invoice_date,
                                      'date': inv_brw.invoice_date,
                                      }
                        else:
                            acc_id = acc_part_id.property_account_payable_id.id
                            wh_type = 'in_invoice'
                            if not acc_id:
                                raise exceptions.except_orm(
                                    _('Invalid Action !'),
                                    _('You need to configure the partner with'
                                      ' withholding accounts!'))
                            values = {'name': _('IVA WH - ORIGIN %s' % (inv_brw.name)),
                                      'type': wh_type,
                                      'account_id': acc_id,
                                      'partner_id': acc_part_id.id,
                                      'date_ret': inv_brw.invoice_date,
                                      'period_id': inv_brw.invoice_date,
                                      'date': inv_brw.invoice_date,
                                     }
                        if inv_brw.company_id.propagate_invoice_date_to_vat_withholding:
                            ret_iva['date'] = inv_brw.invoice_date
                            ret_iva['date_ret'] = ret_iva['date']
                            ret_iva['period_id'] = ret_iva['date']


                    ret_id =  wh_iva_obj.create(values)


                    ret_id.write({'wh_lines': [(4, ret_line_id.id)]})
                    if hasattr(ret_id, 'id'): ret_id = ret_id.id
                    if ret_id:
                        inv.write({'wh_iva_id': ret_id})
                        inv.wh_iva_id.compute_amount_wh()

        return True


    def button_reset_taxes_ret(self):
        """ Recalculate taxes in invoice
        """
        account_invoice_tax = self.env['account.tax']
        for inv in self:
            compute_taxes_ret = account_invoice_tax.compute_amount_ret(inv)
            for tax in account_invoice_tax.browse(compute_taxes_ret.keys()):
                tax.write(compute_taxes_ret[tax.id])
        return True


    def button_reset_taxes(self):
        """ It makes two function calls related taxes reset
        """
        res = super(AccountMove, self).button_reset_taxes()
        self.button_reset_taxes_ret()
        return res


    def _withholding_partner(self):
        """ I verify that the provider retains or not
        """
        # No VAT withholding Documents are created for customer invoice &
        # refunds
        for inv in self:
            if inv.type in ('in_invoice', 'in_refund', 'out_invoice', 'out_refund') and \
                    self.env['res.partner']._find_accounting_partner(
                        inv.company_id.partner_id).wh_iva_agent:
                return True
        return False


    def _withholdable_tax(self):
        """ Verify that existing withholding in invoice
        """
        is_withholdable = False
        for inv in self.line_ids:
            for tax in inv.tax_ids:
                if tax.type_tax == 'iva':
                    is_withholdable = True
        return is_withholdable
        #for inv in self:
        #    if inv.tax_line_ids.tax_id.type_tax == 'iva':
        #        return True
        #return False


    def check_withholdable(self):
        """ This will test for Refund invoice trying to find out
        if its regarding parent is in the same fortnight.

        return True if invoice is type 'in_invoice'
        return True if invoice is type 'in_refund' and parent_id invoice
                are both in the same fortnight.
        return False otherwise
        """
        #period = self.env['account.period']
        for inv in self:
            if inv.type == 'in_invoice':
                return True
            if inv.type == 'out_invoice':
                return True

            '''
            if inv.type == 'in_refund' and inv.parent_id:
                dt_refund = inv.invoice_date or time.strftime('%Y-%m-%d')
                dt_invoice = inv.parent_id.invoice_date
                return period.find_fortnight(dt_refund) == period.find_fortnight(dt_invoice)
            '''
        return False


    def check_wh_apply(self):
        """ Apply withholding to the invoice
        """
        wh_apply = []
        for inv in self:
            if inv.vat_apply or inv.sin_cred:
                return False
            wh_apply.append(inv._withholdable_tax())
            wh_apply.append(inv._withholding_partner())
        return all(wh_apply)


    def _get_move_lines1(self, to_wh, journal_id, writeoff_account_id, writeoff_journal_id,
                          date,name):
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

        # res = super(AccountMove, self)._get_move_lines(to_wh, journal_id, writeoff_account_id, writeoff_journal_id, date,name)
        res = []

        for invoice in self:
            acc_part_id = \
                self.env['res.partner']._find_accounting_partner(
                    invoice.partner_id)

            types = {'out_invoice': -1,
                     'in_invoice': 1,
                     'out_refund': 1,
                     'in_refund': -1}
            direction = types[invoice.type]
            print("to_wh: ",to_wh)
            for tax_brw in to_wh:
                if 'invoice' in invoice.type:
                    #acc = (tax_brw.tax_id.account_id and
                     #      tax_brw.tax_id.account_id.id or
                     #      False)
                    acc = (tax_brw.wh_vat_line_id.retention_id.journal_id.default_debit_account_id.id and
                           tax_brw.wh_vat_line_id.retention_id.journal_id.default_debit_account_id.id or
                          False)
                elif 'refund' in invoice.type:
                    acc = (tax_brw.wh_vat_line_id.retention_id.journal_id.default_debit_account_id.id and
                           tax_brw.wh_vat_line_id.retention_id.journal_id.default_debit_account_id.id or
                           False)
                if not acc:
                    raise exceptions.except_orm(
                        _('¡Falta una cuenta en impuestos!'),
                        _("El impuesto [% s] tiene una cuenta faltante. Por favor, complete el "
                          "campos faltantes") % (tax_brw.name))
                res.append((0, 0, {
                    'debit':
                    direction * tax_brw.amount_ret < 0 and
                    direction * tax_brw.amount_ret,
                    'credit':
                    direction * tax_brw.amount_ret > 0 and
                    direction * tax_brw.amount_ret,
                    'account_id': acc,
                    'partner_id': acc_part_id.id,
                    'ref': invoice.name,
                    'date': date,
                    'currency_id': False,
                    'name': name,
                    'amount_residual': direction * tax_brw.amount_ret
                }))
            #self.residual = self.residual - tax_brw.amount_ret
            #self.residual_company_signed = self.residual_company_signed - tax_brw.amount_ret
        return res


    def validate_wh_iva_done(self):
        """ Method that check if wh vat is validated in invoice refund.
        @params: ids: list of invoices.
        return: True: the wh vat is validated.
                False: the wh vat is not validated.
        """
        for inv in self:
            if inv.type in ('out_invoice', 'out_refund') and not inv.wh_iva_id:
                riva = True
            else:
                riva = (not inv.wh_iva_id and True or
                        inv.wh_iva_id.state in ('posted') and True or False)
                if not riva:
                    raise exceptions.except_orm(
                        _('Error !'),
                        _('¡La retención de IVA "% s" no está validada!' %
                          inv.wh_iva_id.code))
        return True


    def button_generate_wh_doc(self):
        context = dict(self._context)
        partner = self.env['res.partner']
        res = {}
        for inv in self:
            view_id = self.env['ir.ui.view'].search([
                ('name', '=', 'account.move._invoice,'
                              'wh.iva.customer')])
            context.update({
                'invoice_id': inv.id,
                'type': inv.type,
                'default_partner_id': partner._find_accounting_partner(
                    inv.partner_id).id,
                'default_name': inv.name or inv.number,
                'view_id': view_id.id,
                'date_ret': inv.invoice_date,
                'date': inv.date,
            })
            res = {
                'name': _('Withholding vat customer'),
                'type': 'ir.actions.act_window',
                'res_model': 'account.wh.iva',
                'view_type': 'form',
                'view_id': False,
                'view_mode': 'form',
                'nodestroy': True,
                'target': 'current',
                'domain': "[('type', '=', '" + inv.type + "')]",
                'context': context
            }
        return res


    def action_cancel(self):
        """ Verify first if the invoice have a non cancel withholding iva doc.
        If it has then raise a error message. """
        for inv in self:
            if ((not inv.wh_iva_id) or (
                    inv.wh_iva_id and
                    inv.wh_iva_id.state == 'cancel')):
                super(AccountMove, self).action_cancel()
            else:
                raise exceptions.except_orm(
                    _("Error!"),
                    _("No puede cancelar una factura que no se encuentra cancelado"
                      "el d0ocumento de retención. Primero debe cancelar la factura"
                      "documento de retención y luego puede cancelar esto"
                      "factura"))
        return True


class AccountTax(models.Model):
    _inherit = 'account.tax'

    amount_ret = fields.Float(
        string='Importe de retención',
        digits=dp.get_precision(' Withhold'),
        help="Importe de retención de IVA")
    base_ret = fields.Float(
        string='Amount',
        digits=dp.get_precision('Withhold'),
        help="Cantidad sin impuestos")


    @api.model
    def compute_amount_ret(self, invoice):
        """ Calculate withholding amount
        """
        res = {}
        partner = self.env['res.partner']
        acc_part_id = invoice.type in ['out_invoice', "out_refund"] and \
            partner._find_accounting_partner(invoice.company_id.partner_id) \
            or partner._find_accounting_partner(invoice.partner_id)
        wh_iva_rate = acc_part_id.wh_iva_rate

        for record in invoice.tax_line:
            amount_ret = 0.0
            if record.tax_id.ret:
                amount_ret = (wh_iva_rate and
                              record.tax_amount * wh_iva_rate / 100.0 or 0.00)
            res[record.id] = {'amount_ret': amount_ret,
                              'base_ret': record.base_amount}
        return res
