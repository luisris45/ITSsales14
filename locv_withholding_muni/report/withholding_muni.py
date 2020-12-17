# coding: utf-8
###########################################################################

import time

#from odoo.report import report_sxw
#from odoo.tools.translate import _
from odoo import models, api, _
from odoo.exceptions import UserError, Warning, ValidationError

class MuniReport(models.AbstractModel):
    _name = 'report.locv_withholding_muni.template_wh_muni2'

    @api.model
    def _get_report_values(self, docids, data=None):
        if not docids:
            raise UserError(_("Se necesita seleccionar la data a imprimir."))
        data = {'form': self.env['account.wh.munici'].browse(docids)}
        # company = data['form']['company']
        # company_id = self.env['res.company'].search([('id', '=', company)])
        res = dict()
        wh_muni = data['form']
        base_amount = []
        res_ali = []
        sum_total_compra = 0
        sum_monto_sujeto = 0
        sum_neto_pagado = 0
        sum_imp_retenido = 0
        if wh_muni and len(wh_muni) ==1 :
            if wh_muni.state == 'done':
               for line_muni in  wh_muni.munici_line_ids:

                    base_amount.append({'fecha_factura': line_muni.invoice_id.date,
                                        'nro_factura': line_muni.invoice_id.supplier_invoice_number,
                                        'nro_control': line_muni.invoice_id.nro_ctrl,
                                        'nro_debito' :'-',
                                        'nro_credito': '-',
                                        'fact_afec': '-',
                                        'total_compra': line_muni.invoice_id.amount_total,
                                        'monto_sujeto': '',
                                        'porc_ret': line_muni.wh_loc_rate,
                                        'neto_pagado': line_muni.invoice_amount,
                                        'imp_retenido': line_muni.amount,
                                        })
                    sum_total_compra += line_muni.invoice_id.amount_total
                    sum_monto_sujeto += line_muni.invoice_id.amount_total
                    sum_neto_pagado += line_muni.invoice_amount
                    sum_imp_retenido += line_muni.amount


            else:
                raise UserError(_("La Retencion Municipal debe estar en estado Confirmado para poder generar su Comprobante"))
        else:
            raise UserError(_("Solo puede seleccionar una Retencion de IVA a la vez, Por favor Seleccione una y proceda a Imprimir"))
        partner_id = data['form'].partner_id
        if partner_id.company_type == 'person':
            if partner_id.nationality == 'V' or partner_id.nationality == 'E':
                document = str(partner_id.nationality) + str(partner_id.identification_id)
            else:
                document = str(partner_id.identification_id)
        else:
            document = partner_id.vat
        sum_total_compra = self.separador_cifra(sum_total_compra)
        sum_monto_sujeto = self.separador_cifra(sum_monto_sujeto)
        sum_neto_pagado = self.separador_cifra(sum_neto_pagado)
        sum_imp_retenido = self.separador_cifra(sum_imp_retenido)
        hola = data['form']
        return {
            'data': hola,
            'model': self.env['report.locv_withholding_muni.template_wh_muni2'],
            'lines': res, #self.get_lines(data.get('form')),
            # 'company': company_id,
            'document': document,
            'number_comprobante': wh_muni.code if wh_muni else ' ',
            'base_amount': base_amount,
            'alicuota': res_ali,
            'sum_total_compra' :  sum_total_compra,
            'sum_monto_sujeto' :  sum_monto_sujeto,
            'b' :  sum_neto_pagado,
            'sum_imp_retenido' :  sum_imp_retenido,
        }

    def separador_cifra(self,valor):
        monto = '{0:,.2f}'.format(valor).replace('.', '-')
        monto = monto.replace(',', '.')
        monto = monto.replace('-', ',')
        return  monto

    def get_period(self, date):
        if not date:
            raise Warning (_("You need date."))
        split_date = (str(date).split('-'))
        return str(split_date[1]) + '/' + str(split_date[0])

    def get_date(self, date):
        if not date:
            raise Warning(_("You need date."))
        split_date = (str(date).split('-'))
        return str(split_date[2]) + '/' + (split_date[1]) + '/' + str(split_date[0])

    def get_direction(self, partner):
        direction = ''
        direction = ((partner.street and partner.street + ', ') or '') +\
                    ((partner.street2 and partner.street2 + ', ') or '') +\
                    ((partner.city and partner.city + ', ') or '') +\
                    ((partner.state_id.name and partner.state_id.name + ',')or '')+ \
                    ((partner.country_id.name and partner.country_id.name + '') or '')
        #if direction == '':
        #    raise ValidationError ("Debe ingresar los datos de direccion en el proveedor")
            #direction = 'Sin direccion'
        return direction

    def get_tipo_doc(self, tipo=None):
        if not tipo:
            return []
        types = {'out_invoice': '1', 'in_invoice': '1', 'out_refund': '2',
                 'in_refund': '2'}
        return types[tipo]

    def get_t_type(self, doc_type=None, name=None):
        tt = ''
        if doc_type:
            if doc_type == "out_refund" or doc_type == "in_refund":
                tt = '02-COMP'
            elif name and name.find('PAPELANULADO') >= 0:
                tt = '03-ANU'
            else:
                tt = '01-REG'
        return tt



