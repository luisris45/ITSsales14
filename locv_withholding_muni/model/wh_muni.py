# -*- coding: utf-8 -*-
##############################################################################
#
#
##############################################################################

from odoo import api, models, fields, _, exceptions, time
from datetime import timedelta, date, datetime, time

class AccountWhMunici(models.Model):
    _name = "account.wh.munici"
    _description = "Retencion Muicipal form"


    @api.model
    def _get_type(self):
        """ Return invoice type
        """
        context = self._context
        tyype = context.get('number')
        return tyype

    def _get_journal(self):

            context = self._context
            type_inv = context.get('number','in_invoice')
            type2journal = {'out_invoice': 'mun_sale', 'in_invoice':
                'mun_purchase'}
            journal_obj = self.env['account.journal']
            res = journal_obj.search([('type', '=', type2journal.get(
                type_inv, 'mun_purchase'))], limit=1)
            if res:
                return res[0]
            else:
                return False

    def _get_currency(self):

        context = self._context
        company_id = context.get('allowed_company_ids')[0]
        company = self.env['res.company'].search([('id', '=', company_id)])
        currency = company.currency_id
        return currency

    def _get_company(self):
        context = self._context
        company_id = context.get('allowed_company_ids')[0]
        company = self.env['res.company'].search([('id', '=', company_id)])
        return company


    name = fields.Char('Descripcion', size=64, readonly=True,  states={'draft': [('readonly', False)]},
                       help="Descripcion de la Retención") #
    code = fields.Char('Numero de Comprobante Municipal', size=32, readonly=True,
                       help="Codigo de Retencion") #
    number = fields.Selection([('out_invoice', 'Factura de Cliente'),
                               ('in_invoice', 'Factura de Proveedor'), ],
                              string='Tipo', readonly=True,  help="Tipo de Retencion" , default=_get_type) #default=lambda s: s._get_type(),
    type = fields.Selection([('out_invoice', 'Customer Invoice'),
                             ('in_invoice', 'Supplier Invoice'), ],
                            string='Tipo', readonly=True, default=_get_type, help="Withholding type")
    state = fields.Selection([('draft', 'Borrador'),
                              ('confirmed', 'Confirmado'),
                              ('done', 'Realizado'),
                              ('cancel', 'Cancelado')],
                             string='Estado', readonly=True, default='draft', help="Estado del Comprobante")
    date_ret = fields.Date('Fecha de Comprobante', readonly=True, required=True, states={'draft': [('readonly', False)]},
                           help="Mantener vacío para usar la fecha actual") #
    date = fields.Date('Fecha', readonly=True, states={'draft': [('readonly', False)]}, help="Date", default=date.today())
    account_id = fields.Many2one('account.account', 'Cuenta', required=True, readonly=True,
                                 states={'draft': [('readonly', False)]},
                                 help="La cuenta de pago utilizada para esta retención.")

    currency_id = fields.Many2one('res.currency', 'Moneda', required=True, readonly=True, default=_get_currency,
                                  help="Moneda") #default=lambda s: s._get_currency(),
    partner_id = fields.Many2one('res.partner', 'Socio', readonly=True, required=True, states={'draft': [('readonly', False)]},
                                  help="Retención de cliente / proveedor")
    company_id = fields.Many2one('res.company', 'Compañia', required=True, default=_get_company,
                                 help="Compañia")

    journal_id = fields.Many2one('account.journal', 'Diario', required=True, readonly=True,
                                 states={'draft': [('readonly', False)]},
                                 help="Diario") #  default=lambda s: s._get_journal()
    munici_line_ids = fields.One2many('account.wh.munici.line', 'retention_id', 'Lineas de retencion',
                                       states={'draft': [('readonly', False)]},
                                      help="Las facturas se harán retenciones locales")
    amount = fields.Float('Monto Total', help="Cantidad retenida")
    move_id = fields.Many2one('account.move', 'Asiento Contable', help='asiento contable para la factura')

    def name_get(self):
        res = []
        for name in self:
            if name.code:
                res.append((name.id, 'RET. MUNICIPAL: %s' % (name.code)))
            else:
                res.append((name.id, 'RET. MUNICIPAL: '))
        return res

    # def action_cancel(self):
    #     #context = self._context or {}
    #     self.cancel_move()
    #     self.clear_munici_line_ids()
    #     self.state = 'cancel'
    #     return True

    def clear_wh_lines(self):
        """ Clear lines of current withholding document and delete wh document
        information from the invoice.
        """
        if self.ids:
            wil = self.env['account.wh.munici.line'].search([
                ('retention_id', 'in', self.ids)])

            wil_tax = self.env['account.wh.iva.line.tax'].search(
                [('wh_vat_line_id','=', wil.ids)])
            invoice = wil.mapped("invoice_id")
            if wil: wil.unlink()
            for wilt in wil_tax: wilt.unlink()
            if invoice: invoice.write({'wh_muni_id': False})

        return True

    def cancel_move(self):
        """ Delete move lines related with withholding vat and cancel
        """
        moves = []
        for ret in self:
            if ret.state == 'done':
                for ret_line in ret.munici_line_ids:
                    if ret_line.move_id:
                        ret_line.move_id._reverse_moves([{'date': fields.Date.today(), 'ref': _('Reversal of %s') % ret_line.move_id.name}], cancel=True)
            # second, set the withholding as cancelled
            ret.write({'state': 'cancel'})
        return True

    def get_reconciled_move(self):
        awil_obj = self.env['account.wh.munici.line']
        awil_brw = awil_obj.search([('retention_id', '=', self.id)])

        dominio = [('move_id', '=', awil_brw.move_id.id),
                   ('reconciled', '=', True)]
        obj_move_line = self.env['account.move.line'].search(dominio)

        if obj_move_line:
            raise exceptions.ValidationError(
                (
                    'El Comprobante ya tiene una aplicacion en la factura %s, debe desconciliar el comprobante para poder cancelar') % awil_brw.invoice_id.number)
        else:
            return True

    def action_cancel(self):
        """ Call cancel_move and return True
        """
        self.get_reconciled_move()
        self.cancel_move()
        self.clear_wh_lines()
        self.write({'state': 'cancel'})
        return True

    def action_draft(self):
        self.state = 'draft'
        
    '''-----------ORIGINAL-------------'''
    # def cancel_move(self):
    #     ret_brw = self.browse(self.ids)
    #     account_move_obj = self.env['account.move']
    #     for ret in ret_brw:
    #         if ret.state == 'done':
    #             for ret_line in ret.munici_line_ids:
    #                 if ret_line.move_id:
    #                     ret_line.move_id.write({'state': 'cancel'})
    #               #      account_move_obj.button_cancel([ret_line.move_id.id])
    #                     ret_line.move_id.unlink()
    #         self.write({'state': 'cancel'})
    #     return True


    def write(self, vals):
        #context = self._context or {}
        #ids = isinstance(self) and [self.ids] or self.ids

        loc_amt = self.calculate_wh_total()
        vals.update({'amount':loc_amt})
        res = super(AccountWhMunici, self).write(vals)
        self._update_check()
        return res

    @api.model
    def create(self,vals):
        """ Validate before create record
        """

        loc_amt = self.calculate_wh_total()
        vals.update({'amount':loc_amt})
        new_id = super(AccountWhMunici, self).create(vals)
        self._update_check()
        return new_id


    def calculate_wh_total(self):
        local_amount = 0.0
        for line in self.munici_line_ids:
            local_amount += line.amount
        return local_amount


    def clear_munici_line_ids(self):
        #context = self._context or {}
        wml_obj = self.env['account.wh.munici.line']
        ai_obj = self.env['account.move']
        lista = []
        if self.ids:
            wml_ids = wml_obj.search([('retention_id', 'in', self.ids)])
            ai_ids = wml_ids and [wml.invoice_id.id for wml in wml_ids]
            if ai_ids:
                ai_obj.write( {'wh_muni_id': False})
            if wml_ids:
                wml_obj.unlink()
        return True


    def action_confirm(self):
        #values = {}
        obj = self.browse(self.ids[0])
        total = 0.0
        for o in obj:
            for i in self.munici_line_ids:

                total += i.amount
        #self.amount = total
            o.write({'amount': total, 'state': 'confirmed'})
        return True

    def _get_sequence_code(self):
    # metodo que crea la secuencia del correlativo, si no esta creada crea una con el
    # nombre: 'number_comprobante_muni

        for a in self.munici_line_ids:
            a.invoice_id.ensure_one()
        SEQUENCE_CODE = 'number_comprobante_muni'
        company_id = self._get_company()
        IrSequence = self.env['ir.sequence'].with_context(force_company=company_id.id)
        self.code = IrSequence.next_by_code(SEQUENCE_CODE)
        return self.code

    def action_number(self):
        if self.number in ('in_refund', 'in_invoice'):
            if not self.code:
                self.code = self._get_sequence_code()
                self.write({'code': self.code})

        return True


    def action_done(self):
        """ The document is done
        """
        #if self._context is None:
        #    context = {}
        self.action_number()
        self.action_move_create()
        self.state = 'done'
        return True


    def action_move_create(self):
        """Queda pendiente revisar el punto referente al periodo, porque en el 11 hay un tema con respecto a esto"""
        inv_obj = self.env['account.move']
        ctx = dict(self._context, muni_wh=True,
                   company_id=self.env.user.company_id.id)
        for ret in self.with_context(ctx):
            #Busca si ya hay retenciones para esta factura
            for line in self.munici_line_ids:
                if line.move_id or line.invoice_id.wh_local:
                    raise exceptions.except_orm(_('Factura a retener!'), _(
                        "¡Debe omitir la siguiente factura") % (line.invoice_id.name,))

            acc_id = self.account_id
            if not self.date_ret:
                self.write({'date_ret':time.strftime('%Y-%m-%d')})
                ret = self.browse(ret.id)


            journal_id = ret.journal_id.id

            if ret.munici_line_ids:
                for line in ret.munici_line_ids:
                    writeoff_account_id = False
                    writeoff_journal_id = False
                    amount = line.amount
                    if ret.code and ret.code != False:
                        name = 'COMP. RET. MUN ' + ret.code
                    else:
                        raise exceptions.except_orm(
                            _("No existe un Secuencia creada para la Retencion Municipal"),
                            _("Por favor cree una secuencia para la Retencion Municipal, en los Ajustes, para poder continuar"))
                    self.with_context({'wh_county':'wh_county'})
                    ret_move = line.invoice_id.ret_and_reconcile(amount, acc_id, journal_id,
                                        writeoff_account_id, writeoff_journal_id,
                                        ret.date_ret, name, line, 'wh_muni')
                    # make the retencion line point to that move
                    ret_move.action_post()
                    rl = {'move_id': ret_move.id,}
                    lines = [(1, line.id, rl)]
                    self.write({'munici_line_ids': lines})
                    line.invoice_id.write({'wh_muni_id': ret.id})
        return True

    @api.onchange('type','partner_id')
    def onchange_partner_id(self):
        context = self._context or {}
        acc_id = False
        rp_obj = self.env['res.partner']
        if self.partner_id:
            acc_part_brw = rp_obj._find_accounting_partner(self.partner_id)
            if self._get_type() in ('out_invoice', 'out_refund'):
                acc_id = (acc_part_brw.property_account_receivable_id and
                          acc_part_brw.property_account_receivable_id.id or False)
            else:
                acc_id = (acc_part_brw.property_account_payable_id and
                          acc_part_brw.property_account_payable_id.id or False)
            if self.type and self.type == 'in_invoice' or 'in_refund':
                journal = self.env['account.journal'].search([('type','=','purchase')])
                journal1 = self.env['account.journal'].browse()
                journal_id = journal1
                if journal:
                    for journal_uni in journal:
                        if (journal_uni.name.find("Municipal") != -1) or (journal_uni.name.find("Municipal") != -1) or (journal_uni.name.find("MUNICIPAL") != -1) or (journal_uni.name.find("municipal") != -1):
                            journal_id = journal_uni
                            self.write({
                                'journal_id': journal_id
                            })
                    if journal_id == False:
                        raise exceptions.except_orm(
                            _("No existe un Diario para la Retencion Municipal"),
                            _("Por favor crear un Diario para la Retencion Municipal, para poder continuar"))


        result = {'value': {
            'account_id': acc_id}
        }
        return result

    def _update_check(self):


        #ids = isinstance((int)) and [self.ids] or self.ids
        rp_obj = self.env['res.partner']
        for awm_id in self.ids:
            inv_str = ''
            awm_brw = self.browse(awm_id)
            for line in awm_brw.munici_line_ids:
                acc_part_brw = rp_obj._find_accounting_partner(
                    line.invoice_id.partner_id)
                if acc_part_brw.id != awm_brw.partner_id.id:
                    inv_str += '%s' % '\n' + (
                        line.invoice_id.name or line.invoice_id.number or '')
            if inv_str:
                raise exceptions.except_orm(
                    _('Factura Incorrecta!'),
                    _("Las siguientes facturas no son del "
                      " partner seleccionado: %s " % (inv_str,)))

        return True


    def unlink(self):

        if self.state != 'cancel':
            raise exceptions.except_orm(
                _("Procedimiento Invalido!!"),
                _("El documento de retención debe estar en estado de cancelación"
                  "para poder ser eliminado."))
        return super(AccountWhMunici, self).unlink()
        #return True

    def confirm_check(self):

        #ids = isinstance(self.ids,int) and [self.ids] or self.ids

        if not self.check_wh_lines(self.ids):
            return False
        return True

    def check_wh_lines(self):
        #context = self._context or {}
        #ids = isinstance(self.ids, int) and [self.ids] or self.ids
        awm_brw = self.browse(self.ids)
        if not awm_brw.munici_line_ids:
            raise exceptions.except_orm(
                _("Valores faltantes !"),
                _("Faltan líneas de retención!"))
        self.state = 'confirmed'
        return True

class Accountwhmuniciline(models.Model):
    _name = "account.wh.munici.line"
    _description = "Línea de retención Muni"

    # @api.model
    # def _default_partner(self):
    #     if self.retention_id.partner_id:
    #         return self.retention_id.partner_id
    #     return False

    name = fields.Char('Descripción', size=64, required=True,help="Local Withholding line Description")
    partner_id = fields.Many2one('res.partner', 'Socio',
                            help="Retención de cliente / proveedor") #
    retention_id = fields.Many2one('account.wh.munici', 'Retencion Municipal', ondelete='cascade',help="Retención Municipal")
    invoice_id = fields.Many2one('account.move', 'Factura',help="Factura de retención", required=True,  domain="[('partner_id', '=', partner_id),('type','in',('in_invoice','in_refund')),('state','=','posted')]") #   ondelete='set null'
    amount = fields.Float('Monto',help='Monto de la Retención')
    invoice_amount = fields.Float('Monto Factura', help='Monto de la Factura')
    move_id = fields.Many2one('account.move', 'Asiento contable', readonly=True,help="Asiento Contable")
    wh_loc_rate = fields.Float('Tasa', help="Tasa de retención Municipal")
    concepto_id = fields.Integer('Concepto', size=3, default=1,help="Concepto de Retencion Municipal")

    _sql_constraints = [
        ('munici_fact_uniq', 'unique (invoice_id)',
         'La factura ya se ha asignado a la retención municipal,'
         ' no se puede asignar dos veces!')
    ]



    # @api.model
    # def defauld_get(self,field_list):
    #     if self._context is None:
    #         context = {}
    #     data = super(Accountwhmuniciline, self).default_get(field_list)
    #     self.munici_context = context
    #     return data


    @api.onchange('invoice_id','wh_loc_rate')
    def onchange_invoice_id(self):
        #if self._context is None:
        #    context = {}
        if self.retention_id.partner_id:
            self.partner_id = self.retention_id.partner_id
        else:
            self.partner_id = False
        if not self.invoice_id:
            self.invoice_amount = 0.0

            self.amount =  0.0
            self.wh_loc_rate = 0.0
        else:
            amount_total = 0
            invoice = self.env['account.move'].browse(self.invoice_id.id)
            for lines in invoice.invoice_line_ids:
                for tax in lines.tax_ids:
                    if tax.type_tax == 'municipal':
                        amount_total = lines.price_subtotal

            self.env.cr.execute('select retention_id '
                       'from account_wh_munici_line '
                       'where invoice_id=%s',
                       ([self.invoice_id.id]))
            ret_ids = self._cr.fetchone()
            if bool(ret_ids):
                ret = self.env[
                    'account.wh.munici'].browse(ret_ids[0])
                raise exceptions.except_orm(
                    _('Factura asignada!'),
                    "La factura ya se ha asignado en la retención Municipal."
                    " code: '%s' !" % (ret.code,))
            if self.partner_id.wh_muni:
                self.wh_loc_rate = self.partner_id.wh_muni
            else:
                self.wh_loc_rate = 0
            total = amount_total * (self.wh_loc_rate / 100.0)
            self.amount = total
            self.invoice_amount = amount_total
            #return {'value': {'amount': total,
             #                 'wh_loc_rate': self.wh_loc_rate}}
    #@api.multi
    #def unlink(self):
    #    whm_obj = self.env['account.wh.munici']
    #    loc_state = whm_obj.search([('id', '=',self.retention_id)]).state
    #    if loc_state != 'cancel':
    #        raise exceptions.except_orm(
    #            _("Invalid Procedure!!"),
    #            _("The withholding document needs to be in cancel state"
    #            " to be deleted."))
    #    return super(Accountwhmuniciline, self).unlink()