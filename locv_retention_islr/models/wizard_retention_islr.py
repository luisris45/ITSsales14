# -*- coding: utf-8 -*-
import locale
from odoo import models, fields, api
from odoo.exceptions import UserError
from datetime import timedelta, date, datetime
from io import BytesIO
import xlwt, base64
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT

class RetentionISLR(models.Model):
    _name = 'account.retention.islr'
    _description = 'Open Retention ISLR'

    company = fields.Many2one('res.company', required=True)
    start_date = fields.Date(required=True, default=fields.Datetime.now)
    end_date = fields.Date(required=True, default=fields.Datetime.now)
    supplier = fields.Boolean(default=False)
    customer = fields.Boolean(default=False)
    partner_id = fields.Many2one('res.partner')
    clientes = fields.Many2one('res.partner')
    concepto = fields.Boolean(default=True)
    todos = fields.Boolean(default=True)
    concept = fields.Many2many('islr.wh.concept')

    state = fields.Selection([('choose', 'choose'), ('get', 'get')], default='choose')
    report = fields.Binary('Descargar xls', filters='.xls', readonly=True)
    name = fields.Char('File Name', size=32)



    def generate_retention_islr_xls(self):
        hoy = date.today()
        format_new = "%d/%m/%Y"
        hoy_date = datetime.strftime(hoy, format_new)
        start_date = datetime.strftime(datetime.strptime(str(self.start_date), DEFAULT_SERVER_DATE_FORMAT), format_new)
        end_date = datetime.strftime(datetime.strptime(str(self.end_date), DEFAULT_SERVER_DATE_FORMAT), format_new)
        locale.setlocale(locale.LC_ALL, '')

        self.ensure_one()
        fp = BytesIO()
        wb = xlwt.Workbook(encoding='utf-8')
        writer = wb.add_sheet('Nombre de hoja')

        islr_concept = []
        retention_islr = []
        pnre = []
        unico = []
        repetido = []
        retention_islr_asc = []
        pnre_asc = []
        partner = []
        concept_id = []
        lista_nueva_partner = []
        suma_base = 0
        suma_imp_ret = 0
        suma_total_base = 0
        suma_total_imp_ret = 0
        concept = self.concept.id
        if self.todos == True:
            concepts = self.env['islr.wh.concept'].search([('id', '!=', 0)])
            concept = []
            for i in concepts:
                concept.append(i.id)
        if self.supplier == True and self.customer == False:
            islr_concept_id = self.env['islr.wh.doc'].search([('company_id', '=',self.company.id),
                                                              ('partner_id', '=', self.partner_id.id),
                                                              ('type', '=', 'in_invoice'),
                                                              ('state', '=', 'done'),
                                                              ('date_ret', '>=', self.start_date),
                                                              ('date_ret', '<=', self.end_date)])

        if self.supplier == False and self.customer == True:
            islr_concept_id = self.env['islr.wh.doc'].search([('company_id', '=', self.company.id),
                                                              ('partner_id', '=', self.clientes.id),
                                                              ('type', '=', 'out_invoice'),
                                                              ('state', '=', 'done'),
                                                              ('date_ret', '>=', self.start_date),
                                                              ('date_ret', '<=', self.end_date)])

        if self.supplier == False and self.customer == False:
            todo_supplier = self.env['res.partner'].search(['|',('customer_rank', '>', 0),('supplier_rank', '>', 0)])
            for y in todo_supplier:
                partner.append(y.id)

            for i in partner:
                if i not in lista_nueva_partner:
                    lista_nueva_partner.append(i)
            type = ['out_invoice', 'in_invoice']


            islr_concept_id = self.env['islr.wh.doc'].search([('company_id', '=', self.company.id),
                                                              ('partner_id', 'in', lista_nueva_partner),
                                                              ('type', 'in', type),
                                                              ('state', '=', 'done'),
                                                              ('date_ret', '>=', self.start_date),
                                                              ('date_ret', '<=', self.end_date)])


        for a in islr_concept_id:
            islr_concept.append(a.id)

        islr_concept_line = self.env['islr.wh.doc.line'].search([('concept_id', '=', concept),
                                                                 ('islr_wh_doc_id', '=', islr_concept)])
        if islr_concept_line:
            for i in islr_concept_line:
                concept_id.append(i.concept_id.name)
            concept_id.sort()
        else:
            raise UserError('No hay retenciones en estado Hecho')


        header_content_style = xlwt.easyxf("font: name Helvetica size 80 px, bold 1, height 200;")
        sub_header_style = xlwt.easyxf("font: name Helvetica size 10 px, bold 1, height 170; borders: left thin, right thin, top thin, bottom thin;")
        sub_header_style_bold = xlwt.easyxf("font: name Helvetica size 10 px, bold 1, height 170;")
        sub_header_content_style = xlwt.easyxf("font: name Helvetica size 10 px, height 170;")
        line_content_style = xlwt.easyxf("font: name Helvetica, height 170; align: horiz right;")
        line_content_style_totales = xlwt.easyxf("font: name Helvetica size 10 px, bold 1, height 170; borders: left thin, right thin, top thin, bottom thin; align: horiz right;")
        line_content_style_2 = xlwt.easyxf("font: name Helvetica, height 170;")


        row = 1
        col = 0

        # writer.write_merge(row, row, 0, header_cols, "Información de contactos",)

        writer.write_merge(row, row, 1, 2, str(self.company.name), sub_header_content_style)
        writer.write_merge(row, row, 11, 12, "Fecha de Impresión:", sub_header_style_bold)
        writer.write_merge(row, row, 13, 13, hoy_date, sub_header_content_style)
        row += 1

        writer.write_merge(row, row, 1, 2, "R.I.F:", sub_header_style_bold)
        writer.write_merge(row, row, 3, 4, str(self.company.vat), sub_header_content_style)
        row += 1

        writer.write_merge(row, row, 1, 6, "*RELACIÓN DETALLADA DE I.S.L.R. RETENIDO - NUEVO FORMATO*", sub_header_style_bold)
        row += 1

        writer.write_merge(row, row, 1, 2, "Fecha Desde:", sub_header_style_bold)
        writer.write_merge(row, row, 3, 3, start_date, sub_header_content_style)
        writer.write_merge(row, row, 5, 6, "Fecha Hasta:", sub_header_style_bold)
        writer.write_merge(row, row, 7, 7, end_date, sub_header_content_style)
        row += 1

        #/////////////////////ENCABEZADO DEL REPORTE///////////////////////////////
        writer.write_merge(row, row, 1, 1, "FECHA", sub_header_style_bold)
        writer.write_merge(row, row, 2,3,  "PROVEEDOR", sub_header_style_bold)
        writer.write_merge(row, row, 4, 4, "RIF:", sub_header_style_bold)
        writer.write_merge(row, row, 5, 5, "FACTURA:", sub_header_style_bold)
        writer.write_merge(row, row, 6, 6, "CONTROL:", sub_header_style_bold)
        writer.write_merge(row, row, 7, 7, "CONCEPTO", sub_header_style_bold)
        writer.write_merge(row, row, 8, 8, "CODIGO CONCEPTO", sub_header_style_bold)
        writer.write_merge(row, row, 9, 9, "MONTO SUJETO A RETENCION", sub_header_style_bold)
        writer.write_merge(row, row, 10, 10, "TASA PORC", sub_header_style_bold)
        writer.write_merge(row, row, 11, 11, "IMPUESTO RETENIDO", sub_header_style_bold)
        row += 1
        #/////////////////////////////////////////////////////////////////////////////
        #///////////////////////////CUERPO DEL REPORTE DE XLS/////////////////////////

        for concept_line in islr_concept_line:
            if concept_line.invoice_id.nro_ctrl:
                nro_control = concept_line.invoice_id.nro_ctrl
            else:
                nro_control = concept_line.invoice_id.nro_ctrl
            fecha = concept_line.invoice_id.date
            fecha_inicio = fecha.strftime('%d-%m-%Y')
            for cod in concept_line.concept_id.rate_ids:
                if cod.wh_perc == concept_line.retencion_islr:
                    cod_concepto = cod.code
            writer.write_merge(row, row, 1, 1,   fecha_inicio, line_content_style_2)
            writer.write_merge(row, row, 2,3,    concept_line.invoice_id.partner_id.name, line_content_style_2)
            writer.write_merge(row, row, 4, 4,   concept_line.invoice_id.partner_id.vat, line_content_style_2)
            writer.write_merge(row, row, 5, 5,   concept_line.invoice_id.name, line_content_style_2)
            writer.write_merge(row, row, 6, 6,   nro_control, line_content_style_2)
            writer.write_merge(row, row, 7, 7,   concept_line.concept_id.display_name, line_content_style_2)
            writer.write_merge(row, row, 8, 8,  cod_concepto, line_content_style_2)
            writer.write_merge(row, row, 9, 9,  self.separador_cifra(concept_line.base_amount), line_content_style)
            writer.write_merge(row, row, 10, 10,  concept_line.retencion_islr, line_content_style)
            writer.write_merge(row, row, 11, 11, self.separador_cifra(concept_line.amount), line_content_style)
            row += 1



        col = 1

        wb.save(fp)

        out = base64.encodestring(fp.getvalue())
        self.write({'state': 'get', 'report': out, 'name': 'Detalle_De_Ret_de_ISLR.xls'})

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.retention.islr',
            'view_mode': 'form',
            'view_type': 'form',
            'res_id': self.id,
            'views': [(False, 'form')],
            'target': 'new',
        }


    def generate_retention_islr_pdf(self):
        b = []
        name = []
        for a in self.concept:
            b.append(a.id)
            name.append(a.name)
        data = {
            'ids': self.ids,
            'model': 'report.locv_retention_islr.report_retention_islr1',
            'form': {
                'date_start': self.start_date,
                'date_stop': self.end_date,
                'company': self.company.id,
                'supplier': self.supplier,
                'partner_id': self.partner_id.id,
                'customer': self.customer,
                'clientes': self.clientes.id,
                'concept': b,
                'concept_name': name,
                'todos': self.todos,
            },
        }

        return self.env.ref('locv_retention_islr.action_report_retention_islr').report_action(self, data=data)

    def separador_cifra(self, valor):
        monto = '{0:,.2f}'.format(valor).replace('.', '-')
        monto = monto.replace(',', '.')
        monto = monto.replace('-', ',')
        return monto

class ReportRetentionISLR(models.AbstractModel):
    _name = 'report.locv_retention_islr.report_retention_islr1'

    @api.model
    def _get_report_values(self, docids, data=None):
        date_start = data['form']['date_start']
        end_date = data['form']['date_stop']
        company_id = data['form']['company']
        supplier = data['form']['supplier']
        partner_id = data['form']['partner_id']
        customer = data['form']['customer']
        clientes = data['form']['clientes']
        concept = data['form']['concept']
        concept_name = data['form']['concept_name']
        todos = data['form']['todos']
        today = date.today()
        cod_concepto = ' '
        islr_concept = []
        retention_islr = []
        pnre = []
        unico = []
        repetido = []
        retention_islr_asc = []
        pnre_asc = []
        concept_id = []
        partner = []
        lista_nueva_partner = []
        if todos == True:
            concepts = self.env['islr.wh.concept'].search([('id', '!=', 0)])
            concept = []
            for i in concepts:
                concept.append(i.id)

        company = self.env['res.company'].search([('id', '=', company_id)])

        if supplier == True and customer == False:
            islr_concept_id = self.env['islr.wh.doc'].search([('company_id', '=', company_id),
                                                              ('partner_id', '=', partner_id),
                                                              ('type', '=', 'in_invoice'),
                                                              ('state', '=', 'done'),
                                                              ('date_ret', '>=', date_start),
                                                              ('date_ret', '<=', end_date)])

        if supplier == False and customer == True:
            islr_concept_id = self.env['islr.wh.doc'].search([('company_id', '=', company_id),
                                                              ('partner_id', '=', clientes),
                                                              ('type', '=', 'out_invoice'),
                                                              ('state', '=', 'done'),
                                                              ('date_ret', '>=', date_start),
                                                              ('date_ret', '<=', end_date)])

        if supplier == True and customer == True:
            type = ['out_invoice', 'in_invoice']
            islr_concept_id = self.env['islr.wh.doc'].search([('company_id', '=', company_id),
                                                              ('partner_id', 'in', [clientes, partner_id]),
                                                              ('type', '=', type),
                                                              ('state', '=', 'done'),
                                                              ('date_ret', '>=', date_start),
                                                              ('date_ret', '<=', end_date)])

        if supplier == False and customer == False:
            todo_supplier = self.env['res.partner'].search(['|', ('customer_rank', '>', 0),('supplier_rank', '>', 0)])
            for y in todo_supplier:
                partner.append(y.id)


            for i in partner:
                if i not in lista_nueva_partner:
                    lista_nueva_partner.append(i)
            type = ['out_invoice', 'in_invoice']
            date_ret1 = datetime.strptime(date_start, '%Y-%m-%d').date()
            date_ret2 = datetime.strptime(end_date, '%Y-%m-%d').date()

            islr_concept_id = self.env['islr.wh.doc'].search([('company_id', '=', company_id),
                                                              ('partner_id', 'in', lista_nueva_partner),
                                                              ('type', 'in', type),
                                                              ('state', '=', 'done'),
                                                              ('date_ret', '>=', date_ret1),
                                                              ('date_ret', '<=', date_ret2)
                                                              ])


        for a in islr_concept_id:
            islr_concept.append(a.id)

        islr_concept_line = self.env['islr.wh.doc.line'].search([('concept_id', '=', concept),
                                                                 ('islr_wh_doc_id', '=', islr_concept)])

        if islr_concept_line:
            for i in islr_concept_line:
                concept_id.append(i.concept_id.name)
            concept_id.sort()
        else:
            raise UserError('No hay retenciones en estado Hecho')

        '''concepts_people_type = self.env['islr.rates'].search([('concept_id', '=', concept)])
        for concept_line in concepts_people_type:

            pnre.append({
                'name': concept_line.concept_id.name,
                'residence': concept_line.residence,
                'nature': concept_line.nature,
                'porcentaconcept_linee': concept_line.wh_perc,
            })'''

        docs = []
        for concept_line in islr_concept_line:
            if concept_line.invoice_id:
                if concept_line.invoice_id.nro_ctrl:
                    nro_control = concept_line.invoice_id.nro_ctrl
                else:
                    nro_control = concept_line.invoice_id.nro_ctrl
                fecha = concept_line.invoice_id.date
                fecha_inicio = fecha.strftime('%d-%m-%Y')
                for cod in concept_line.concept_id.rate_ids:
                    if cod.wh_perc == concept_line.retencion_islr:
                        cod_concepto = cod.code
                if  concept_line.invoice_id.partner_id.company_type == 'person':
                    if concept_line.invoice_id.partner_id.nationality == 'V' or concept_line.invoice_id.partner_id.nationality == 'E':
                        document = str(concept_line.invoice_id.partner_id.nationality) + str(concept_line.invoice_id.partner_id.identification_id)
                    else:
                        document = str(concept_line.invoice_id.partner_id.identification_id)
                else:
                    document = concept_line.invoice_id.partner_id.vat
                docs.append({
                    'fecha' : fecha_inicio,
                    'name': concept_line.concept_id.display_name,
                    'proveedor': concept_line.invoice_id.partner_id.name,
                    'rif': document,
                    'factura': concept_line.invoice_id.name,
                    'control': nro_control,
                    'cod_concepto': cod_concepto,
                    'monto_suj_retencion': self.separador_cifra(concept_line.base_amount),
                    'tasa_porc': concept_line.retencion_islr,
                    'impusto_retenido': self.separador_cifra(concept_line.amount),
                })


        return {
            'doc_ids': data['ids'],
            'doc_model': data['model'],
            'end_date': end_date,
            'start_date': date_start,
            'today': today,
            'company': company,
            'docs': docs,
            }

    def separador_cifra(self, valor):
        monto = '{0:,.2f}'.format(valor).replace('.', '-')
        monto = monto.replace(',', '.')
        monto = monto.replace('-', ',')
        return monto