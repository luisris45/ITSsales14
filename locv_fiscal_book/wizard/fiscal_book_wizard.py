# coding: utf-8
##############################################################################

###############################################################################
import time

from odoo import fields, models, api, exceptions, _
from odoo.exceptions import ValidationError
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT as DATETIME_FORMAT
from datetime import datetime, date, timedelta
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT

class FiscalBookWizard(models.TransientModel):

    """
    Sales book wizard implemented using the osv_memory wizard system
    """
    _name = "fiscal.book.wizard"

    TYPE = [("sale", _("Venta")),
            ("purchase", _("Compra")),
        ]


    @api.model
    def default_get(self, field_list):


        fiscal_book_obj = self.env['fiscal.book']
        fiscal_book = fiscal_book_obj.browse(self._context['active_id'])
        res = super(FiscalBookWizard, self).default_get(field_list)
        local_period = fiscal_book_obj.get_time_period(fiscal_book.time_period, fiscal_book)
        res.update({'type': fiscal_book.type})
        res.update({'date_start': local_period.get('dt_from', '')})
        res.update({'date_end': local_period.get('dt_to', '')})
        if fiscal_book.fortnight == 'first':
            date_obj = local_period.get('dt_to', '').split('-')
            res.update({'date_end': "%0004d-%02d-15" % (int(date_obj[0]), int(date_obj[1]))})
        elif fiscal_book.fortnight == 'second':
            date_obj = local_period.get('dt_to', '').split('-')
            res.update({'date_start': "%0004d-%02d-16" % (int(date_obj[0]), int(date_obj[1]))})
        return res


    def check_report(self):
       if self.type == 'purchase':
            if self.date_start and self.date_end:
                fecha_inicio = self.date_start
                fecha_fin = self.date_end
                book_id = self.env.context['active_id']


                purchase_book_obj = self.env['account.move']
                purchase_book_ids = purchase_book_obj.search(
                    [('invoice_date', '>=', fecha_inicio), ('invoice_date', '<=', fecha_fin)])
                if purchase_book_ids:
                    ids = []
                    for id in purchase_book_ids:
                        ids.append(id.id)
            #        datas = self.read(self.id)[0]
                    data = {
                        'ids': ids,
                        'model': 'report.locv_fiscal_book.report_fiscal_purchase_book',
                        'form': {
                    #        'datas': datas,
                            'date_from': self.date_start,
                            'date_to': self.date_end,
                            'book_id': book_id,
                        },
                      #  'context': self._context
                    }
                    return self.env.ref('locv_fiscal_book.report_purchase_book').report_action(self, data=data) #, config=False
                else:
                    raise ValidationError('Advertencia! No existen facturas entre las fechas seleccionadas')
       else:
            if self.date_start and self.date_end:
                fecha_inicio = self.date_start
                fecha_fin = self.date_end
                book_id = self.env.context['active_id']
                # tabla_report_z = self.env['datos.zeta.diario']
                # domain = ['|',
                #           ('fecha_ultimo_reporte_z', '>=', fecha_inicio),
                #           ('fecha_ultimo_reporte_z', '<=', fecha_fin),
                #           ('numero_ultimo_reporte_z', '>', '0')
                #           ]
                #
                # report_z_ids = tabla_report_z.search(domain, order='fecha_ultimo_reporte_z asc')
                #
                # if report_z_ids:
                #     ids = []
                #     for id in report_z_ids:
                #         ids.append(id.id)
                purchase_book_obj = self.env['account.move']
                purchase_book_ids = purchase_book_obj.search(
                    [('invoice_date', '>=', fecha_inicio), ('invoice_date', '<=', fecha_fin)])
                if purchase_book_ids:
                    ids = []
                    for id in purchase_book_ids:
                        ids.append(id.id)

               #     datas = self.read(self.ids)[0]
                    data = {
                        'ids': ids,
                        'model': 'report.locv_fiscal_book.report_fiscal_sale_book',
                        'form': {
                          #  'datas': datas,
                            'date_from': self.date_start,
                            'date_to': self.date_end,
                            'book_id': book_id,
                        },
                  #      'context': self._context
                    }
                    return self.env.ref('locv_fiscal_book.report_sale_book').report_action(self, data=data, config=False)
                else:
                    raise ValidationError('Advertencia! No existen facturas entre las fechas seleccionadas')


    date_start = fields.Date("Fecha de Inicio", required=True, default=time.strftime('%Y-%m-%d'))
    date_end = fields.Date("Fecha Fin", required=True, default=time.strftime('%Y-%m-%d'))
    control_start = fields.Integer("Control Start")
    control_end = fields.Integer("Control End")
    type = fields.Selection(TYPE, "Tipo", required=True)
#
class PurchaseBook(models.AbstractModel):

    _name = 'report.locv_fiscal_book.report_fiscal_purchase_book'


    @api.model
    def _get_report_values(self, docids, data=None):
        format_new = "%d/%m/%Y"
        date_start = datetime.strptime(data['form']['date_from'], DATE_FORMAT)
        date_end = datetime.strptime(data['form']['date_to'], DATE_FORMAT)
        datos_compras = []
        purchasebook_ids = self.env['fiscal.book.line'].search(
            [('fb_id','=',data['form']['book_id']), ('accounting_date', '>=', date_start.strftime(DATETIME_FORMAT)), ('accounting_date', '<=', date_end.strftime(DATETIME_FORMAT))])
        emission_date = ' '
        sum_compras_credit = 0
        sum_total_with_iva = 0
        sum_vat_general_base = 0
        sum_vat_general_tax = 0
        sum_vat_reduced_base = 0
        sum_vat_reduced_tax = 0
        sum_vat_additional_base = 0
        sum_vat_additional_tax = 0
        sum_get_wh_vat = 0
        suma_vat_exempt = 0

        vat_reduced_base = 0
        vat_reduced_rate = 0
        vat_reduced_tax = 0
        vat_additional_base = 0
        vat_additional_rate = 0
        vat_additional_tax = 0


        ''' COMPRAS DE IMPORTACIONES'''

        sum_total_with_iva_importaciones = 0
        sum_vat_general_base_importaciones = 0
        suma_base_general_importaciones = 0
        sum_base_general_tax_importaciones = 0
        sum_vat_general_tax_importaciones = 0
        sum_vat_reduced_base_importaciones = 0
        sum_vat_reduced_tax_importaciones = 0
        sum_vat_additional_base_importaciones = 0
        sum_vat_additional_tax_importaciones = 0

        hola = 0
        #######################################
        compras_credit = 0
        origin = 0
        number = 0

        for h in purchasebook_ids:
            h_vat_general_base = 0.0
            h_vat_general_rate = 0.0
            h_vat_general_tax = 0.0
            vat_general_base_importaciones = 0
            vat_general_rate_importaciones = 0
            vat_general_general_rate_importaciones = 0
            vat_general_tax_importaciones = 0
            vat_reduced_base_importaciones = 0
            vat_reduced_rate_importaciones = 0
            vat_reduced_tax_importaciones = 0
            vat_additional_tax_importaciones = 0
            vat_additional_rate_importaciones = 0
            vat_additional_base_importaciones = 0
            vat_reduced_base = 0
            vat_reduced_rate = 0
            vat_reduced_tax = 0
            vat_additional_base = 0
            vat_additional_rate = 0
            vat_additional_tax = 0
            get_wh_vat = 0

            if h.type == 'ntp':
                compras_credit = h.invoice_id.amount_untaxed

            if h.doc_type == 'N/DB':
                origin = h.affected_invoice
                if h.invoice_id:
                    if  h.invoice_id.nro_ctrl:
                        busq1 = self.env['account.move'].search([('nro_ctrl', '=',h.invoice_id.nro_ctrl)])
                        if busq1:
                            for busq2 in busq1:
                                if busq2.type == 'in_invoice':
                                    number = busq2.name or ''


            sum_compras_credit += compras_credit
            suma_vat_exempt += h.vat_exempt
            planilla = ''
            expediente = ''
            total = 0
            partner = self.env['res.partner'].search([('name','=', h.partner_name)])
            if (partner.company_type == 'company' or  partner.company_type == 'person') and (partner.people_type_company or partner.people_type_individual) and  (partner.people_type_company == 'pjdo' or partner.people_type_individual == 'pnre' or  partner.people_type_individual == 'pnnr'):
                '####################### NO ES PROVEDOR INTERNACIONAL########################################################3'
                if h.invoice_id:
                    if h.doc_type == 'N/DB':
                        total = (h.invoice_id.amount_total)*-1
                    else:
                        total = (h.invoice_id.amount_total)
                    sum_vat_reduced_base += h.vat_reduced_base  # Base Imponible de alicuota Reducida
                    sum_vat_reduced_tax += h.vat_reduced_tax  # Impuesto de IVA alicuota reducida
                    sum_vat_additional_base += h.vat_additional_base  # BASE IMPONIBLE ALICUOTA ADICIONAL

                    sum_vat_additional_tax += h.vat_additional_tax  # IMPUESTO DE IVA ALICUOTA ADICIONAL
                    if h.doc_type == 'N/DB':
                        sum_total_with_iva -= total  # Total monto con IVA
                    else:
                        sum_total_with_iva += total
                     # Total monto con IVA
                    sum_vat_general_base += h.vat_general_base # Base Imponible Alicuota general
                    sum_vat_general_tax += h.vat_general_tax   # Impuesto de IVA
                    h_vat_general_base = h.vat_general_base
                    h_vat_general_rate = int(h.vat_general_base and h.vat_general_tax * 100 / h.vat_general_base) if h.vat_general_base else 0.0
                    h_vat_general_tax = h.vat_general_tax if h.vat_general_tax else 0.0
                    vat_reduced_base = h.vat_reduced_base
                    vat_reduced_rate = int(h.vat_reduced_base and h.vat_reduced_tax * 100 / h.vat_reduced_base)
                    vat_reduced_tax = h.vat_reduced_tax
                    vat_additional_base = h.vat_additional_base
                    vat_additional_rate = int(h.vat_additional_base and h.vat_additional_tax * 100 / h.vat_additional_base)
                    vat_additional_tax = h.vat_additional_tax
                    get_wh_vat = h.get_wh_vat

                    emission_date = datetime.strftime(datetime.strptime(str(h.emission_date), DEFAULT_SERVER_DATE_FORMAT),
                                                       format_new)
                if h.iwdl_id.invoice_id:
                    if h.doc_type == 'N/DB':
                        total = (h.iwdl_id.invoice_id.amount_total)*-1
                    else:
                        total = (h.iwdl_id.invoice_id.amount_total)
                    sum_vat_reduced_base += h.vat_reduced_base  # Base Imponible de alicuota Reducida
                    sum_vat_reduced_tax += h.vat_reduced_tax
                    # Impuesto de IVA alicuota reducida

                    sum_vat_additional_base += h.vat_additional_base  # BASE IMPONIBLE ALICUOTA ADICIONAL

                    sum_vat_additional_tax += h.vat_additional_tax  # IMPUESTO DE IVA ALICUOTA ADICIONAL
                    if h.doc_type == 'N/DB':
                        sum_total_with_iva -= total  # Total monto con IVA
                    else:
                        sum_total_with_iva += total
                    sum_vat_general_base += h.vat_general_base  # Base Imponible Alicuota general
                    sum_vat_general_tax += h.vat_general_tax  # Impuesto de IVA
                    h_vat_general_base = h.vat_general_base
                    h_vat_general_rate = int(h.vat_general_base and h.vat_general_tax * 100 / h.vat_general_base) if h.vat_general_base else 0.0
                    h_vat_general_tax = h.vat_general_tax if h.vat_general_tax else 0.0
                    vat_reduced_base = h.vat_reduced_base
                    vat_reduced_rate = int(h.vat_reduced_base and h.vat_reduced_tax * 100 / h.vat_reduced_base)
                    vat_reduced_tax = h.vat_reduced_tax
                    vat_additional_base = h.vat_additional_base
                    vat_additional_rate = int(h.vat_additional_base and h.vat_additional_tax * 100 / h.vat_additional_base)
                    vat_additional_tax = h.vat_additional_tax
                    get_wh_vat = h.get_wh_vat

                    emission_date = datetime.strftime(
                        datetime.strptime(str(h.emission_date), DEFAULT_SERVER_DATE_FORMAT),
                        format_new)

            if (partner.company_type == 'company' or  partner.company_type == 'person') and (partner.people_type_company or partner.people_type_individual) and  partner.people_type_company == 'pjnd':
                '############## ES UN PROVEEDOR INTERNACIONAL ##############################################'

                if h.invoice_id:
                    if h.invoice_id.fecha_importacion:
                        date_impor = h.invoice_id.fecha_importacion
                        emission_date = datetime.strftime(datetime.strptime(str(date_impor), DEFAULT_SERVER_DATE_FORMAT),
                                                       format_new)
                        total = h.invoice_id.amount_total
                    else:
                        date_impor =  h.invoice_id.invoice_date
                        emission_date = datetime.strftime(
                            datetime.strptime(str(date_impor), DEFAULT_SERVER_DATE_FORMAT),
                            format_new)

                    planilla = h.invoice_id.nro_planilla_impor
                    expediente = h.invoice_id.nro_expediente_impor
                else:
                    date_impor = h.iwdl_id.invoice_id.fecha_importacion
                    emission_date = datetime.strftime(datetime.strptime(str(date_impor), DEFAULT_SERVER_DATE_FORMAT),
                                                      format_new)
                    planilla = h.iwdl_id.invoice_id.nro_planilla_impor
                    expediente = h.iwdl_id.invoice_id.nro_expediente_impor
                    total = h.iwdl_id.invoice_id.amount_total
                get_wh_vat = 0.0
                vat_reduced_base = 0
                vat_reduced_rate = 0
                vat_reduced_tax = 0
                vat_additional_base = 0
                vat_additional_rate = 0
                vat_additional_tax = 0
                'ALICUOTA GENERAL IMPORTACIONES'
                vat_general_base_importaciones = h.vat_general_base
                vat_general_rate_importaciones = int(h.vat_general_base and h.vat_general_tax * 100 / h.vat_general_base)
                vat_general_tax_importaciones = h.vat_general_tax
                'ALICUOTA REDUCIDA IMPORTACIONES'
                vat_reduced_base_importaciones = h.vat_reduced_base
                vat_reduced_rate_importaciones = int(h.vat_reduced_base and h.vat_reduced_tax * 100 / h.vat_reduced_base)
                vat_reduced_tax_importaciones = h.vat_reduced_tax
                'ALICUOTA ADICIONAL IMPORTACIONES'
                vat_additional_base_importaciones = h.vat_additional_base
                vat_additional_rate_importaciones = int(h.vat_additional_base and h.vat_additional_tax * 100 / h.vat_additional_base)
                vat_additional_tax_importaciones = h.vat_additional_tax
                'Suma total compras con IVA'
                if h.doc_type == 'N/DB':
                    sum_total_with_iva -= total  # Total monto con IVA
                else:
                    sum_total_with_iva += total
                 # Total monto con IVA
                'SUMA TOTAL DE TODAS LAS ALICUOTAS PARA LAS IMPORTACIONES'
                sum_vat_general_base_importaciones += h.vat_general_base + h.vat_reduced_base + h.vat_additional_base # Base Imponible Alicuota general
                sum_vat_general_tax_importaciones += h.vat_general_tax + h.vat_additional_tax + h.vat_reduced_tax  # Impuesto de IVA

                'Suma total de Alicuota General'
                suma_base_general_importaciones += h.vat_general_base
                sum_base_general_tax_importaciones += h.vat_general_tax

                ' Suma total de Alicuota Reducida'
                sum_vat_reduced_base_importaciones += h.vat_reduced_base  # Base Imponible de alicuota Reducida
                sum_vat_reduced_tax_importaciones += h.vat_reduced_tax  # Impuesto de IVA alicuota reducida
                'Suma total de Alicuota Adicional'
                sum_vat_additional_base_importaciones += h.vat_additional_base  # BASE IMPONIBLE ALICUOTA ADICIONAL
                sum_vat_additional_tax_importaciones += h.vat_additional_tax  # IMPUESTO DE IVA ALICUOTA ADICIONAL

                get_wh_vat = h.get_wh_vat
            sum_get_wh_vat += h.get_wh_vat  # IVA RETENIDO

            if h_vat_general_base != 0:
                valor_base_imponible = h.vat_general_base
                valor_alic_general = h_vat_general_rate
                valor_iva = h_vat_general_tax
            else:
                valor_base_imponible = 0
                valor_alic_general = 0
                valor_iva = 0

            if get_wh_vat != 0:
                hola = get_wh_vat
            else:
                hola = 0

            if h.vat_exempt != 0 :
                vat_exempt = h.vat_exempt

            else:
                vat_exempt = 0




            'Para las diferentes alicuotas que pueda tener el proveedor  internacional'
            'todas son mayor a 0'
            if vat_general_rate_importaciones > 0 and vat_reduced_rate_importaciones > 0 and vat_additional_rate_importaciones > 0:
                vat_general_general_rate_importaciones = str(vat_general_rate_importaciones) + ',' + ' ' + str(vat_reduced_rate_importaciones) + ',' + ' ' + str(vat_additional_rate_importaciones) + ' '
            'todas son cero'
            if vat_general_rate_importaciones == 0 and vat_reduced_rate_importaciones == 0 and vat_additional_rate_importaciones == 0:
                vat_general_general_rate_importaciones = 0
            'Existe reducida y adicional'
            if vat_general_rate_importaciones == 0 and vat_reduced_rate_importaciones > 0 and vat_additional_rate_importaciones > 0:
                vat_general_general_rate_importaciones = str(vat_reduced_rate_importaciones) + ',' + ' ' + str(vat_additional_rate_importaciones) + ' '
            'Existe general y adicional'
            if   vat_general_rate_importaciones >  0 and vat_reduced_rate_importaciones == 0 and vat_additional_rate_importaciones > 0:
                vat_general_general_rate_importaciones = str(vat_general_rate_importaciones) + ','+ ' ' + str(vat_additional_rate_importaciones) + ' '
            'Existe general y reducida'
            if  vat_general_rate_importaciones >  0 and vat_reduced_rate_importaciones > 0 and vat_additional_rate_importaciones == 0:
                vat_general_general_rate_importaciones = str(vat_general_rate_importaciones) + ',' +  ' ' + str(vat_reduced_rate_importaciones) + ' '
            'Existe solo la general'
            if vat_general_rate_importaciones > 0 and vat_reduced_rate_importaciones == 0 and vat_additional_rate_importaciones == 0:
                vat_general_general_rate_importaciones = str(vat_general_rate_importaciones)
            'Existe solo la reducida'
            if vat_general_rate_importaciones == 0 and vat_reduced_rate_importaciones > 0 and vat_additional_rate_importaciones == 0:
                vat_general_general_rate_importaciones = str(vat_reduced_rate_importaciones)
            'Existe solo la adicional'
            if vat_general_rate_importaciones == 0 and vat_reduced_rate_importaciones == 0 and vat_additional_rate_importaciones > 0:
                vat_general_general_rate_importaciones = str(vat_additional_rate_importaciones)

            datos_compras.append({

                'emission_date': emission_date if emission_date else ' ',
                'partner_vat': h.partner_vat if h.partner_vat else ' ',
                'partner_name': h.partner_name,
                'people_type': h.people_type,
                'wh_number': h.wh_number if h.wh_number else ' ',
                'invoice_number': h.invoice_number,
                'affected_invoice': h.affected_invoice,
                'ctrl_number': h.ctrl_number,
                'debit_affected': number if h.doc_type == 'N/DB' else '',
                'credit_affected': h.invoice_number if h.doc_type == 'N/CR' else '',# h.credit_affected,
                'type': h.void_form,
                'doc_type': h.doc_type,
                'origin': origin,
                'number': number,
                'total_with_iva': total,
                'vat_exempt': vat_exempt,
                'compras_credit': compras_credit,
                'vat_general_base': valor_base_imponible,
                'vat_general_rate': valor_alic_general,
                'vat_general_tax': valor_iva,
                'vat_reduced_base': vat_reduced_base,
                'vat_reduced_rate': vat_reduced_rate,
                'vat_reduced_tax': vat_reduced_tax,
                'vat_additional_base': vat_additional_base,
                'vat_additional_rate': vat_additional_rate ,
                'vat_additional_tax':  vat_additional_tax,
                'get_wh_vat': hola,
                'vat_general_base_importaciones' : vat_general_base_importaciones + vat_additional_base_importaciones + vat_reduced_base_importaciones,
                'vat_general_rate_importaciones' : vat_general_general_rate_importaciones,
                'vat_general_tax_importaciones' : vat_general_tax_importaciones + vat_reduced_tax_importaciones + vat_additional_tax_importaciones,
                'nro_planilla': planilla,
                'nro_expediente': expediente,
            })
        'SUMA TOTAL DE ALICUOTA ADICIONAL BASE'
        if sum_vat_additional_base != 0 and sum_vat_additional_base_importaciones > 0:
            sum_ali_gene_addi =  sum_vat_additional_base
            sum_vat_additional_base = sum_vat_additional_base
        else:
            sum_ali_gene_addi = sum_vat_additional_base
        'SUMA TOTAL DE ALICUOTA ADICIONAL TAX'
        if sum_vat_additional_tax != 0 and sum_vat_additional_tax_importaciones > 0:
            sum_ali_gene_addi_credit = sum_vat_additional_tax
            sum_vat_additional_tax = sum_vat_additional_tax
        else:
            sum_ali_gene_addi_credit = sum_vat_additional_tax
        'SUMA TOTAL DE ALICUOTA GENERAL BASE'
        if sum_vat_general_base != 0 and suma_base_general_importaciones > 0:
            sum_vat_general_base = sum_vat_general_base
            sum_vat_general_tax =  sum_vat_general_tax
        'SUMA TOTAL DE ALICUOTA REDUCIDA BASE'
        if sum_vat_reduced_base != 0 and sum_vat_reduced_base_importaciones > 0:
            sum_vat_reduced_base = sum_vat_reduced_base
            sum_vat_reduced_tax = sum_vat_reduced_tax


        ' IMPORTACIONES ALICUOTA GENERAL + ALICUOTA ADICIONAL'
        if sum_vat_additional_base_importaciones != 0:
            sum_ali_gene_addi_importaciones = sum_vat_additional_base_importaciones
        else:
            sum_ali_gene_addi_importaciones = sum_vat_additional_base_importaciones

        if sum_vat_additional_tax_importaciones != 0:
            sum_ali_gene_addi_credit_importaciones = sum_vat_additional_tax_importaciones
        else:
            sum_ali_gene_addi_credit_importaciones = sum_vat_additional_tax_importaciones



        total_compras_base_imponible = sum_vat_general_base + sum_ali_gene_addi + sum_vat_reduced_base + suma_base_general_importaciones + sum_ali_gene_addi_importaciones + sum_vat_reduced_base_importaciones + suma_vat_exempt
        total_compras_credit_fiscal = sum_vat_general_tax + sum_ali_gene_addi_credit + sum_vat_reduced_tax + sum_base_general_tax_importaciones + sum_ali_gene_addi_credit_importaciones + sum_vat_reduced_tax_importaciones



        date_start = datetime.strftime(datetime.strptime(data['form']['date_from'], DEFAULT_SERVER_DATE_FORMAT), format_new)
        date_end = datetime.strftime(datetime.strptime(data['form']['date_to'], DEFAULT_SERVER_DATE_FORMAT), format_new)

        if purchasebook_ids.env.company and purchasebook_ids.env.company.street :
            street = str(purchasebook_ids.env.company.street) +','
        else:
            street = ' '
        return {
            'doc_ids': data['ids'],
            'doc_model': data['model'],
            'date_start': date_start,
            'date_end': date_end,
            'a': 0.00,
            'street': street,
            'company': purchasebook_ids.env.company,
            'datos_compras': datos_compras,
            'sum_compras_credit': sum_compras_credit,
            'sum_total_with_iva': sum_total_with_iva,
            'suma_vat_exempt': suma_vat_exempt,
            'sum_vat_general_base' : sum_vat_general_base,
            'sum_vat_general_tax': sum_vat_general_tax,
            'sum_vat_reduced_base': sum_vat_reduced_base,
            'sum_vat_reduced_tax': sum_vat_reduced_tax,
            'sum_vat_additional_base': sum_vat_additional_base,
            'sum_vat_additional_tax': sum_vat_additional_tax,
            'sum_get_wh_vat': sum_get_wh_vat,
            'sum_ali_gene_addi': sum_ali_gene_addi,
            'sum_ali_gene_addi_credit': sum_ali_gene_addi_credit,
            'suma_base_general_importaciones': suma_base_general_importaciones,
            'sum_base_general_tax_importaciones': sum_base_general_tax_importaciones,
            'sum_vat_general_base_importaciones' : sum_vat_general_base_importaciones,
            'sum_vat_general_tax_importaciones' : sum_vat_general_tax_importaciones,
            'sum_ali_gene_addi_importaciones': sum_ali_gene_addi_importaciones,
            'sum_ali_gene_addi_credit_importaciones': sum_ali_gene_addi_credit_importaciones,
            'sum_vat_reduced_base_importaciones': sum_vat_reduced_base_importaciones,
            'sum_vat_reduced_tax_importaciones': sum_vat_reduced_tax_importaciones,
            'total_compras_base_imponible': total_compras_base_imponible,
            'total_compras_credit_fiscal': total_compras_credit_fiscal,

        }
#
class FiscalBookSaleReport(models.AbstractModel):
    _name = 'report.locv_fiscal_book.report_fiscal_sale_book'

    @api.model
    def _get_report_values(self, docids, data=None):
        format_new = "%d/%m/%Y"

        # date_start =(data['form']['date_from'])
        # date_end =(data['form']['date_to'])

        fb_id = data['form']['book_id']
        busq = self.env['fiscal.book'].search([('id','=',fb_id)])
        date_start = datetime.strptime(data['form']['date_from'], DATE_FORMAT).date()
        date_end = datetime.strptime(data['form']['date_to'], DATE_FORMAT).date()
        # date_start = busq.period_start
        # date_end = busq.period_end
        fbl_obj = self.env['fiscal.book.line'].search(
            [('fb_id','=',busq.id),('accounting_date', '>=', date_start)
             ])

        docs = []
        suma_total_w_iva = 0
        suma_no_taxe_sale = 0
        suma_vat_general_base = 0
        suma_total_vat_general_base = 0
        suma_total_vat_general_tax = 0
        suma_total_vat_reduced_base = 0
        suma_total_vat_reduced_tax = 0
        suma_total_vat_additional_base = 0
        suma_total_vat_additional_tax = 0
        suma_vat_general_tax = 0
        suma_vat_reduced_base = 0
        suma_vat_reduced_tax = 0
        suma_vat_additional_base = 0
        suma_vat_additional_tax = 0
        suma_get_wh_vat = 0
        suma_ali_gene_addi = 0
        suma_ali_gene_addi_debit = 0
        total_ventas_base_imponible = 0
        total_ventas_debit_fiscal = 0

        suma_amount_tax = 0

        for line in fbl_obj:
            if line.vat_general_base != 0 or line.vat_reduced_base != 0 or line.vat_additional_base != 0 or line.vat_exempt != 0:
                vat_general_base = 0
                vat_general_rate =  0
                vat_general_tax =  0
                vat_reduced_base = 0
                vat_additional_base =0
                vat_additional_rate = 0
                vat_additional_tax = 0
                vat_reduced_rate = 0
                vat_reduced_tax = 0


                if line.type == 'ntp':
                    no_taxe_sale = line.vat_general_base
                else:
                    no_taxe_sale = 0.0

                if line.vat_reduced_base and  line.vat_reduced_base != 0:
                    vat_reduced_base = line.vat_reduced_base
                    vat_reduced_rate = int(line.vat_reduced_base and line.vat_reduced_tax * 100 / line.vat_reduced_base)
                    vat_reduced_tax = line.vat_reduced_tax
                    suma_vat_reduced_base += line.vat_reduced_base
                    suma_vat_reduced_tax += line.vat_reduced_tax

                if line.vat_additional_base and line.vat_additional_base != 0:
                    vat_additional_base = line.vat_additional_base
                    vat_additional_rate = int(line.vat_additional_base and line.vat_additional_tax * 100 / line.vat_additional_base)
                    vat_additional_tax = line.vat_additional_tax
                    suma_vat_additional_base += line.vat_additional_base
                    suma_vat_additional_tax += line.vat_additional_tax

                if line.vat_general_base  and line.vat_general_base != 0:
                    vat_general_base = line.vat_general_base
                    vat_general_rate = int(line.vat_general_base and line.vat_general_tax * 100 / line.vat_general_base)
                    vat_general_tax = line.vat_general_tax
                    suma_vat_general_base += line.vat_general_base
                    suma_vat_general_tax += line.vat_general_tax



                if line.get_wh_vat:
                 suma_get_wh_vat += line.get_wh_vat
                if vat_reduced_rate == 0:
                    vat_reduced_rate = ''
                else:
                    vat_reduced_rate = str(vat_reduced_rate)
                if vat_additional_rate == 0:
                    vat_additional_rate = ''
                else:
                    vat_additional_rate = str(vat_additional_rate)
                if vat_general_rate == 0:
                    vat_general_rate = ''

                if  vat_general_rate == '' and vat_reduced_rate == '' and vat_additional_rate == '':
                    vat_general_rate = 0
                docs.append({
                    'rannk': line.rank,
                    'emission_date': datetime.strftime(datetime.strptime(str(line.emission_date), DEFAULT_SERVER_DATE_FORMAT), format_new),
                    'partner_vat': line.partner_vat if line.partner_vat else ' ',
                    'partner_name': line.partner_name,
                    'people_type': line.people_type if line.people_type else ' ',
                    'report_z': line.z_report,
                    'export_form': '',
                    'wh_number': line.wh_number,
                    'date_wh_number': line.iwdl_id.retention_id.date_ret if line.wh_number != '' else '',
                    'invoice_number': line.invoice_number,
                    'n_ultima_factZ': line.n_ultima_factZ,
                    'ctrl_number': line.ctrl_number,
                    'debit_note': '',
                    'credit_note': line.invoice_number if line.doc_type == 'N/CR' else '',
                    'type': line.void_form,
                    'affected_invoice': line.affected_invoice if line.affected_invoice else ' ',
                    'total_w_iva': line.total_with_iva if line.total_with_iva else 0,
                    'no_taxe_sale': line.vat_exempt,
                    'export_sale': '',
                    'vat_general_base': vat_general_base, # + vat_reduced_base + vat_additional_base,
                    'vat_general_rate': str(vat_general_rate), #+ '  ' + str(vat_reduced_rate) + ' ' + str(vat_additional_rate) + '  ',
                    'vat_general_tax': vat_general_tax, #+ vat_reduced_tax + vat_additional_tax,
                    'vat_reduced_base': line.vat_reduced_base,
                    'vat_reduced_rate': str(vat_reduced_rate),
                    'vat_reduced_tax': vat_reduced_tax,
                    'vat_additional_base': vat_additional_base,
                    'vat_additional_rate': str(vat_additional_rate),
                    'vat_additional_tax': vat_additional_tax,
                    'get_wh_vat': line.get_wh_vat,
                })

                suma_total_w_iva += line.total_with_iva
                suma_no_taxe_sale += line.vat_exempt
                suma_total_vat_general_base += line.vat_general_base
                suma_total_vat_general_tax +=  line.vat_general_tax
                suma_total_vat_reduced_base +=  line.vat_reduced_base
                suma_total_vat_reduced_tax += line.vat_reduced_tax
                suma_total_vat_additional_base += line.vat_additional_base
                suma_total_vat_additional_tax += line.vat_additional_tax

                #RESUMEN LIBRO DE VENTAS


               # suma_ali_gene_addi =  suma_vat_additional_base if line.vat_additional_base else 0.0
                #suma_ali_gene_addi_debit = suma_vat_additional_tax if line.vat_additional_tax else 0.0
                total_ventas_base_imponible = suma_vat_general_base + suma_vat_additional_base + suma_vat_reduced_base + suma_no_taxe_sale
                total_ventas_debit_fiscal = suma_vat_general_tax + suma_vat_additional_tax + suma_vat_reduced_tax

        date_start = datetime.strftime(datetime.strptime(data['form']['date_from'], DEFAULT_SERVER_DATE_FORMAT),
                                       format_new)
        date_end = datetime.strftime(datetime.strptime(data['form']['date_to'], DEFAULT_SERVER_DATE_FORMAT), format_new)


        if fbl_obj.env.company and fbl_obj.env.company.street :
            street = str(fbl_obj.env.company.street) +','
        else:
            street = ' '


        return {
            'doc_ids': data['ids'],
            'doc_model': data['model'],
            'date_start':date_start,
            'date_end': date_end,
            'docs': docs,
            'a': 0.00,
            'street':street,
            'company': fbl_obj.env.company,
            'suma_total_w_iva': suma_total_w_iva,
            'suma_no_taxe_sale': suma_no_taxe_sale,
            'suma_total_vat_general_base': suma_total_vat_general_base,
            'suma_total_vat_general_tax': suma_total_vat_general_tax,
            'suma_vat_general_base': suma_vat_general_base,
            'suma_vat_general_tax': suma_vat_general_tax,
            'suma_total_vat_reduced_base' : suma_total_vat_reduced_base,
            'suma_total_vat_reduced_tax' : suma_total_vat_reduced_tax,
            'suma_total_vat_additional_base': suma_total_vat_additional_base,
            'suma_total_vat_additional_tax' : suma_total_vat_additional_tax,
            'suma_vat_reduced_base': suma_vat_reduced_base,
            'suma_vat_reduced_tax': suma_vat_reduced_tax,
            'suma_vat_additional_base': suma_vat_additional_base,
            'suma_vat_additional_tax': suma_vat_additional_tax,
            'suma_get_wh_vat': suma_get_wh_vat,
            'suma_ali_gene_addi': suma_vat_additional_base,
            'suma_ali_gene_addi_debit': suma_vat_additional_tax,
            'total_ventas_base_imponible': total_ventas_base_imponible,
            'total_ventas_debit_fiscal': total_ventas_debit_fiscal,
        }
#
#
# FiscalBookWizard()
