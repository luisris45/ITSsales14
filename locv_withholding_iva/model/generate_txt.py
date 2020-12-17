# coding: utf-8
###########################################################################

import base64
import time

from odoo import models, fields, api, exceptions, _
from odoo.addons import decimal_precision as dp



class TxtIva(models.Model):
    _name = "txt.iva"
    _inherit = ['mail.thread']


    @api.model
    def _default_period_id(self):
        """ Return current period
        """
        fecha = time.strftime('%m/%Y')
        periods = self.env['account.period'].search([('code', '=', fecha)])
        return periods and periods[0].id or False



    name = fields.Char(
        string='Descripción', size=128, required=True, select=True,
        default=lambda self: 'Retención IVA ' + time.strftime('%m/%Y'),
        help="Description about statement of withholding income")
    company_id = fields.Many2one(
        'res.company', string='Compañia', required=True,
        states={'draft': [('readonly', False)]}, help='Company',
        default=lambda self: self.env['res.company']._company_default_get())
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('confirmed', 'Confirmado'),
        ('done', 'Realizado'),
        ('cancel', 'Cancelado')
        ], string='Estado', select=True, readonly=True, default='draft',
        help="proof status")
    period_id = fields.Date(string='Periodo')
    type = fields.Boolean(
        string='Retención de Proveedores?', required=True,
        states={'draft': [('readonly', False)]}, default=True,
        help="Select the type of retention to make")
    date_start = fields.Date(
        string='Fecha de Inicio', required=True,
        states={'draft': [('readonly', False)]},
        help="Fecha de inicio del período")
    date_end = fields.Date(
        string='Fecha Fin', required=True,
        states={'draft': [('readonly', False)]},
        help="Fecha de Fin del período")
    txt_ids = fields.One2many(
        'txt.iva.line', 'txt_id',
        states={'draft': [('readonly', False)]},
        help='Txt líneas de campo de ar requeridas por SENIAT para '
        'Retención de IVA')
    amount_total_ret = fields.Float(
        string='Monto Total Retenido',
     #   compute='_get_amount_total',
        help="Monto Total Retenido")
    amount_total_base = fields.Float(
        string='Total de la Base Imponible',
     #   compute='_get_amount_total_base',
        help="Total de la Base Imponible")
    txt_name = fields.Char('Nombre Archivo')
    txt_file = fields.Binary('Descargar TXT', states={'done': [('invisible', False)]} )

    def _get_amount_total(self):
        """ Return total amount withheld of each selected bill
        """
        res = {}

        for txt in self.browse(self.ids):
            res[txt.id] = 0.0
            if txt.create_date != False:
                for txt_line in txt.txt_ids:
                    if txt_line.invoice_id.type in ['out_refund', 'in_refund']:
                        res[txt.id] -= txt_line.amount_withheld
                    else:
                        res[txt.id] += txt_line.amount_withheld
        return res

    def _get_amount_total_base(self):
        """ Return total amount base of each selected bill
        """
        res = {}
        for txt in self.browse(self.ids):
            res[txt.id] = 0.0
            if txt.create_date != False:
                for txt_line in txt.txt_ids:
                    if txt_line.invoice_id.type in ['out_refund', 'in_refund']:
                        res[txt.id] -= txt_line.untaxed
                    else:
                        res[txt.id] += txt_line.untaxed
        return res


    def name_get(self):
        """ Return a list with id and name of the current register
        """
        res = [(r.id, r.name) for r in self]
        return res

    
    def action_anular(self):
        """ Return document state to draft
        """
        self.write({'state': 'draft'})
        return True

    
    def check_txt_ids(self): #, cr, uid, ids, context=None
        """ Check that txt_iva has lines to process."""
        for awi in self:
            if not awi.txt_ids:
                raise exceptions.except_orm(
                    _("Valores faltantes!"),
                    _("Faltan líneas TXT de IVA !!!"))
        return True

    
    def action_confirm(self):
        """ Transfers the document status to confirmed
        """
        self.check_txt_ids()
        self.write({'state': 'confirmed'})
        return True


    
    def action_generate_lines_txt(self):
        """ Current lines are cleaned and rebuilt
        """
        rp_obj = self.env['res.partner']
        voucher_obj = self.env['account.wh.iva']
        txt_iva_obj = self.env['txt.iva.line']
        vouchers = []
        txt_brw = self.browse(self.ids)
        txt_ids = txt_iva_obj.search([('txt_id', '=', txt_brw.id)])
        if txt_ids:
            for txt in txt_ids: txt.unlink()

        if txt_brw.type:
            vouchers = voucher_obj.search([
                ('date_ret', '>=', txt_brw.date_start),
                ('date_ret', '<=', txt_brw.date_end),
                #('period_id', '=', txt_brw.period_id.id),
                ('state', '=', 'done'),
                ('type', 'in', ['in_invoice', 'in_refund'])])
        else:
            vouchers = voucher_obj.search([
                ('date_ret', '>=', txt_brw.date_start),
                ('date_ret', '<=', txt_brw.date_end),
                #('period_id', '=', txt_brw.period_id.id),
                ('state', '=', 'done'),
                ('type', 'in', ['out_invoice', 'out_refund'])])
        amount_total =0
        base_total = 0
        amount_exento = 0
        amount = 0
        base = 0
        for voucher in vouchers:

            acc_part_id = rp_obj._find_accounting_partner(voucher.partner_id)
            for voucher_lines in voucher.wh_lines:
                for voucher_tax_line in voucher_lines.tax_line:
                    amount_total += voucher_tax_line.amount_ret
                    amount = voucher_tax_line.amount_ret
                    base = voucher_tax_line.base
                    base_total += voucher_tax_line.base
                    if voucher_tax_line.wh_vat_line_id.invoice_id.type == 'in_invoice' or voucher_tax_line.wh_vat_line_id.invoice_id.type == 'in_refund':
                        type = 'purchase'
                    else:
                        type = 'sale'
                    busq = self.env['account.tax'].search([('id','=', voucher_tax_line.id_tax),('type_tax_use','=', type)])
                    if voucher_tax_line.amount == 0 and voucher_tax_line.amount_ret == 0:
                        amount_exento = voucher_tax_line.base

                    txt_iva_obj.create(
                        {'partner_id': acc_part_id.id,
                         'voucher_id': voucher.id,
                         'invoice_id': voucher_lines.invoice_id.id,
                         'txt_id': txt_brw.id,
                         # 'untaxed': voucher_tax_line.base,
                         'untaxed': base,#voucher_lines.base_ret,
                         'amount_withheld': amount,#voucher_lines.amount_tax_ret,
                         'amount_sdcf': amount_exento,  # self.get_amount_scdf(voucher_lines),
                         'tax_wh_iva_id': busq.name if busq else '',
                         })
                    busq = {}
                    # else:
                    #     # for voucher_tax_line in voucher_lines.tax_line:
                    #     txt_iva_obj.create(
                    #         {'partner_id': acc_part_id.id,
                    #          'voucher_id': voucher.id,
                    #          'invoice_id': voucher_lines.invoice_id.id,
                    #          'txt_id': txt_brw.id,
                    #          'untaxed': voucher_tax_line.base,
                    #          'amount_withheld': voucher_tax_line.amount_ret,
                    #          'tax_wh_iva_id': voucher_tax_line.id,
                    #
                    #          })
                self.update({'amount_total_ret': amount_total,
                             'amount_total_base': base_total})
                if voucher_lines.invoice_id.state not in ['posted']:
                    pass
                # if len(voucher_lines.tax_line) > 1:
                #     txt_iva_obj.create(
                #         {'partner_id': acc_part_id.id,
                #          'voucher_id': voucher.id,
                #          'invoice_id': voucher_lines.invoice_id.id,
                #          'txt_id': txt_brw.id,
                #          #'untaxed': voucher_tax_line.base,
                #          'untaxed': voucher_lines.base_ret,
                #          'amount_withheld': voucher_lines.amount_tax_ret,
                #          'amount_sdcf': amount_exento, #self.get_amount_scdf(voucher_lines),
                #          'tax_wh_iva_id': self.get_alicuota_iva(voucher_lines),
                #          })


                # else:
                #
                #         self.update({'amount_total_ret': amount_total,
                #                      'amount_total_base': base_total})

        return True
    # @api.model
    # def get_amount_scdf(self,voucher_lines):
    #     amount_sdcf = 0.0
    #     line_tax_obj = self.env['account.wh.iva.line.tax']
    #     line_tax_bw = line_tax_obj.search([('wh_vat_line_id', '=', voucher_lines.id)])
    #
    #     for line_tax in line_tax_bw:
    #         if line_tax.name in ['Exento','Exento (compras)','exento','exento (compras)','Exento (Compras)']:
    #             amount_sdcf = line_tax.base
    #     return amount_sdcf
    @api.model
    def get_alicuota_iva(self,voucher_lines):
        line_tax_obj = self.env['account.wh.iva.line.tax']
        line_tax_bw = line_tax_obj.search([('wh_vat_line_id', '=', voucher_lines.id)])

        for line_tax in line_tax_bw:
            if line_tax.amount != 0.0:
                tax_id = line_tax.id
        return tax_id

    @api.model
    def get_buyer_vendor(self, txt, txt_line):
        """ Return the buyer and vendor of the sale or purchase invoice
        @param txt: current txt document
        @param txt_line: One line of the current txt document
        """
        rp_obj = self.env['res.partner']
        vat_company = txt.company_id.partner_id.vat
        vat_partner = txt_line.partner_id.vat
        if vat_partner == False:
            nationality= txt_line.partner_id.nationality
            cedula = txt_line.partner_id.identification_id
            if nationality and cedula:
                if nationality == 'V' or nationality == 'E':
                    vat_partner = str(nationality) + str(cedula)
                else:
                    vat_partner = str(cedula)
        if txt_line.invoice_id.type in ['out_invoice', 'out_refund']:
            vendor = vat_company
            buyer = vat_partner
        else:
            buyer = vat_company
            vendor = vat_partner
        return (vendor, buyer)

    @api.model
    def get_document_affected(self, txt_line):
        """ Return the reference or number depending of the case
        @param txt_line: line of the current document
        """
        number = '0'
        if txt_line.invoice_id.type in ['out_refund', 'in_refund'] and txt_line.invoice_id.name.find("ND") != -1 or txt_line.invoice_id.name.find("nd") != -1\
                or txt_line.invoice_id.name.find("NC") != -1 or txt_line.invoice_id.name.find("nc") != -1:
            number = txt_line.invoice_id.supplier_invoice_number
        elif txt_line.invoice_id:
             number = '0'
        return number

    @api.model
    def get_number(self, number, inv_type, max_size):
        """ Return a list of number for document number
        @param number: list of characters from number or reference of the bill
        @param inv_type: invoice type
        @param long: max size oh the number
        """
        if not number:
            return '0'
        result = ''
        for i in number:
            if inv_type == 'vou_number' and i.isdigit():
                if len(result) < max_size:
                    result = i + result
            elif i.isalnum():
                if len(result) < max_size:
                    result = i + result
        return result[::-1].strip()

    @api.model
    def get_document_number(self, txt_line, inv_type):
        """ Return the number o reference of the invoice into txt line
        @param txt_line: One line of the current txt document
        @param inv_type: invoice type into txt line
        """
        number = 0
        if txt_line.invoice_id.type in ['in_invoice', 'in_refund']:
            if not txt_line.invoice_id.supplier_invoice_number:
                raise exceptions.except_orm(
                    _('Acción Invalida!'),
                    _("No se puede hacer el archivo txt porque la factura no tiene "
                      "número de referencia gratis!"))
            else:
                number = self.get_number(
                    txt_line.invoice_id.supplier_invoice_number.strip(),
                    inv_type, 20)
        elif txt_line.invoice_id.number:
            number = self.get_number(
                txt_line.invoice_id.number.strip(), inv_type, 20)
        return number

    @api.model
    def get_type_document(self, txt_line):
        """ Return the document type
        @param txt_line: line of the current document
        """
        inv_type = '03'
        if txt_line.invoice_id.type in ['out_invoice', 'in_invoice'] and txt_line.invoice_id.partner_id.people_type_company != 'pjnd' :
            inv_type = '01'
        elif txt_line.invoice_id.type in ['out_invoice', 'in_invoice'] and \
                txt_line.invoice_id.name:
            inv_type = '02'
        if txt_line.invoice_id.partner_id.company_type == 'company' and txt_line.invoice_id.partner_id.people_type_company == 'pjnd':
            inv_type = '05'

        return inv_type

    @api.model
    def get_max_aliquot(self, txt_line):
        """Get maximum aliquot per invoice"""
        res = []
        # for tax_line in txt_line.invoice_id.tax_line_ids:
        #     res.append(int(tax_line.tax_id.amount * 100))
        return (res)

    @api.model
    def get_amount_line(self, txt_line, amount_exempt):
        """Method to compute total amount"""
        ali_max = 0
        exempt = 0

        alic_porc = 0
        busq = self.env['account.tax'].search([('name', '=', txt_line.tax_wh_iva_id)])
        if busq:
            alic_porc = busq.amount
        if ali_max == alic_porc:
            exempt = amount_exempt

        total = (txt_line.untaxed + txt_line.amount_withheld +
                     exempt)

        return total, exempt

    @api.model
    def get_amount_exempt_document(self, txt_line):
        """ Return total amount not entitled to tax credit and the remaining
        amounts
        @param txt_line: One line of the current txt document
        """
        tax = 0
        amount_doc = 0
        for tax_lines in txt_line.voucher_id.wh_lines.tax_line:
            if 'Exento (compras)' in tax_lines.name or (tax_lines.base and not tax_lines.amount):
                tax = tax_lines.base + tax
            else:
                amount_doc = tax_lines.base + amount_doc
        return (tax, amount_doc)

    @api.model
    def get_alicuota(self, txt_line):
        """ Return aliquot of the withholding into line
        @param txt_line: One line of the current txt document
        """
        busq = self.env['account.tax'].search([('name','=', txt_line.tax_wh_iva_id)])

        alic_porc = 0
        if busq:
            alic_porc = busq.amount

        return int(alic_porc)

    def get_period(self, date):
        split_date = str(date).split('-')

        return str(split_date[0]) + str(split_date[1])

    
    def generate_txt(self):
        """ Return string with data of the current document
        """
        txt_string = ''
        rp_obj = self.env['res.partner']
        for txt in self:
            expediente = '0'
            vat = txt.company_id.partner_id.vat
            vat = vat
            amount_total11 =0
            for txt_line in txt.txt_ids:
                vendor, buyer = self.get_buyer_vendor(txt, txt_line)
                if txt_line.invoice_id.type in ['out_invoice','out_refund']:
                    if vendor:
                        vendor = vendor.replace("-", "")
                    else:
                        vendor = ''
                    if txt_line.partner_id.company_type == 'person':
                        buyer = buyer
                    else:
                        if buyer:
                            buyer = buyer.replace("-", "")
                        else:
                            buyer = ''
                else:
                    if buyer:
                        buyer = buyer.replace("-", "")
                    else:
                        buyer = ' '
                    if txt_line.partner_id.company_type == 'person':
                        vendor = vendor
                    else:
                        if vendor:
                            vendor = vendor.replace("-", "")
                        else:
                            vendor = ''

                period = self.get_period(txt.date_start)
                # TODO: use the start date of the period to get the period2
                # with the 'YYYYmm'
                operation_type = ('V' if txt_line.invoice_id.type in
                                  ['out_invoice', 'out_refund'] else 'C')
                document_type = self.get_type_document(txt_line)
                document_number = self.get_document_number(
                    txt_line, 'inv_number')
                control_number = self.get_number(
                    txt_line.invoice_id.nro_ctrl, 'inv_ctrl', 20)
                document_affected = self.get_document_affected(txt_line)
                document_affected = document_affected.replace("-","") if document_affected else '0'
                voucher_number = self.get_number(
                    txt_line.voucher_id.number, 'vou_number', 14)
                amount_exempt, amount_untaxed = \
                    self.get_amount_exempt_document(txt_line)

                alicuota = float(self.get_alicuota(txt_line))
                amount_total, amount_exempt = self.get_amount_line(
                    txt_line, amount_exempt)
                if txt_line.voucher_id == txt_line.invoice_id.wh_iva_id:
                    amount_total11 = txt_line.invoice_id.amount_total
                    amount_total2 = str(round(amount_total11, 2))
                    amount_untaxed = txt_line.untaxed
                else:
                    amount_total2 = str(round(amount_total, 2))
                    amount_untaxed = amount_untaxed
                txt_line.untaxed2 = str(round(txt_line.untaxed, 2))
                txt_line.amount_withheld2 = str(round(txt_line.amount_withheld, 2))
                amount_exempt2 = str(round(amount_exempt, 2))
                alicuota2 = alicuota
                if document_type == '05':
                    expediente = str(txt_line.invoice_id.nro_expediente_impor)
                txt_string = (
                    txt_string + buyer + '\t' + period + '\t'
                    + (str(txt_line.invoice_id.date)) + '\t' + operation_type +
                    '\t' + document_type + '\t' + vendor + '\t' +
                    document_number + '\t' + control_number + '\t' +
                    self.formato_cifras(amount_total2) + '\t' +
                    #self.formato_cifras(txt_line.untaxed2) + '\t' +
                    self.formato_cifras(amount_untaxed) + '\t' +
                    self.formato_cifras(txt_line.amount_withheld2) + '\t' +
                    document_affected
                    + '\t' + voucher_number + '\t' +
                    self.formato_cifras(amount_exempt2) + '\t' + self.formato_cifras(alicuota2)
                    + '\t' + expediente + '\n')
        return txt_string

    
    def _write_attachment(self, root):
        """ Encrypt txt, save it to the db and view it on the client as an
        attachment
        @param root: location to save document
        """
        fecha = time.strftime('%Y_%m_%d_%H%M%S')
        name = 'IVA_' + fecha + '.' + 'txt'
#         self.env['ir.attachment'].create({
#             'name': name,
#             'datas': base64.encodestring(root),
#             'datas_fname': name,
#             'res_model': 'txt.iva',
#             'res_id': self.ids[0],
#         })
        txt_name = name
        txt_file = root.encode('utf-8')
        txt_file = base64.encodestring(txt_file)
        self.write({'txt_name': txt_name, 'txt_file': txt_file})
        msg = _("File TXT %s generated.") % (name)
        self.message_post(body=msg)

    
    def action_done(self):
        """ Transfer the document status to done
        """
        root = self.generate_txt()
        self._write_attachment(root)
        self.write({'state': 'done'})

        return True

    def formato_cifras(self,monto):
        cds = '0'
        monto = str(monto)
        if monto =='0':
            monto = '0.00'
        for i in range(0, len(monto)):
            if (monto[i] == '.'):
                cds = monto[i + 1:]
        if len(cds) == 2:
            imprimir0 = ''
        else:
            imprimir0 = '0'
        montofinal = monto + imprimir0
        return montofinal

class TxtIvaLine(models.Model):
    _name = "txt.iva.line"

    partner_id = fields.Many2one(
        'res.partner', string='Comprador/Vendedor', readonly=True,
        help="Persona natural o jurídica que genera la Factura,"
        "Nota de crédito, nota de débito o certificación (vendedor)")
    invoice_id = fields.Many2one(
        'account.move', 'Factura/ND/NC', readonly=True,
        help="Fecha de factura, nota de crédito, nota de débito o certificado, "
        "Declaración de Importación")
    voucher_id = fields.Many2one(
        'account.wh.iva', string='Impuesto de Retención', readonly=True,
        help="Retencion de impuesto del valor agregado(IVA)")
    amount_withheld = fields.Float(
        string='Cantidad retenida', readonly=True, help='Cantidad retenida')
    amount_sdcf = fields.Float(
        string='Monto SDCF', readonly=True, help='Monto SDCF')
    untaxed = fields.Float(
        string='Base de la Retención', readonly=True, help='Base de la Retención')
    txt_id = fields.Many2one(
        'txt.iva', string='Generar-Documento TXT IVA', readonly=True,
        help='Lineas de Retención')
    # tax_wh_iva_id = fields.Many2one(
    #     'account.wh.iva.line.tax', string='Líneas de impuesto de Retención de IVA')
    tax_wh_iva_id = fields.Char(
              string='Líneas de impuesto de Retención de IVA', readonly=True)

    _rec_name = 'partner_id'
