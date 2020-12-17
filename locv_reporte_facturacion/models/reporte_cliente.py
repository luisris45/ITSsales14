from odoo import models, api, _, exceptions, fields
from odoo.exceptions import UserError, Warning
from datetime import datetime, date, timedelta


class ReportInvoiceCliente(models.AbstractModel):
    _name = 'report.locv_reporte_facturacion.template_cliente'

    @api.model
    def _get_report_values(self, docids, data):
        if docids:
            data = {'form': self.env['account.move'].browse(docids)}
            var = data['form']
        else:
            var = self.env['account.move'].search([('id', '=', data['id'])])

        for inv in var:
            res = dict()
            name_document = ' '
            ident = ''
            n_factura = ''
            docs = []
            info = []
            monto_base_exento = 0
            if inv.date:
                fecha = inv.date
            else:
                fecha = inv.date_invoice
            fecha = datetime.strptime(str(fecha), '%Y-%m-%d')
            fecha = fecha.strftime('%d/%m/%Y')
            if inv.type == 'out_invoice' or 'out_refund':
                n_factura = inv.name
            elif inv.type == 'in_invoice' or 'in_refund':
                n_factura = inv.supplier_invoice_number
     #       n_cliente = inv.partner_id.num_cliente
            razon = inv.partner_id.name
            if inv.partner_id.company_type == 'person':
                name_document = 'DOCUMENTO DE IDENTIDAD'
                if inv.partner_id.nationality != 'P':
                    ident = str(inv.partner_id.nationality) + str(inv.partner_id.identification_id)
                else:
                    ident = str(inv.partner_id.identification_id)
            else:
                name_document = 'RIF'
                ident =  inv.partner_id.vat

            direccion = inv.partner_id.street
            telefono = inv.partner_id.phone
         #   forma_pago = inv.pago_transfe.name
           # banco = inv.tipo_banco.name
            cont = 0
            total = 0


            if inv.invoice_origin:
                origen = 'REC'
            else:
                origen = 'FAC'
            nota_cred = inv.name
            origin_number = inv.name
            info.append({
                'fecha':fecha,
                'n_factura': n_factura,
                'nro_ctrl': inv.nro_ctrl if inv.nro_ctrl else ' ',
                'razon': razon,
                'name_document': name_document,
                'rif': ident,
                'direccion': direccion,
                'telefono': telefono,
             #   'forma_pago': forma_pago,
              #  'banco': banco
            })
            base = 0
            for lin in inv.invoice_line_ids:
                monto_base_exento = 0
                monto_base = 0
                name_tax = 0
                name_taxo = ' '
                name_taxd = ' '
                name_taxe = ' '
                name_taxt = ' '
                cont += 1

                monto_base = lin.price_total - lin.price_subtotal
                base += lin.price_total - lin.price_subtotal
                if monto_base == 0:
                    monto_base_exento = lin.price_subtotal
                else:
                    monto_base_exento = 0
                for tax in lin.tax_ids:
                    if tax and tax.amount != 0 and tax.amount == 16.0:
                        name_tax = tax.amount
                        name_taxd =  str(name_tax)[:2]  + '%'

                    if tax and tax.amount != 0 and tax.amount == 8.0:
                        name_tax = tax.amount
                        name_taxo = str(name_tax)[:1]  + '%'
                    if tax and tax.amount != 0 and tax.amount == 31.0:
                        name_tax = tax.amount
                        name_taxt = str(name_tax)[:2]  + '%'
                    if tax and tax.amount == 0:
                        name_taxe = 'Exento'
                docs.append({
                    'n': cont,
                    'cod': lin.product_id.default_code,
                    'cant': lin.quantity,
                    'um': lin.product_uom_id.name,
                    'descripcion': lin.name,
                    'name_taxo' : str(name_taxo),
                    'name_taxd' : str(name_taxd),
                    'name_taxt' : str(name_taxt),
                    'name_taxe' : str(name_taxe),
                #    'lote': numero_lote,
                    'precio_unitario': self.formato_cifras(lin.price_unit),
                    'precio_total': self.formato_cifras(lin.price_subtotal),
                })
                total += lin.price_subtotal


            if docs:
                docs.append({
                    'n': ' ',
                    'cod': ' ',
                    'cant': ' ',
                    'um': ' ',
                    'descripcion': ' ',
                    'name_taxd': ' ',
                    'name_taxo' : ' ',
                    'name_taxt': ' ',
                    'name_taxe': ' ',
                    'precio_unitario': ' ',
                    'precio_total': ' ',
                })
            if inv.env.company and inv.env.company.street :
                street = str(inv.env.company.street) +','
            else:
                street = ' '
            if inv.env.company and inv.env.company.zip:
                zip_code = str(inv.env.company.zip) + ','
            else:
                zip_code = ' '
            if inv.env.company and inv.env.company.city:
                city = str(inv.env.company.city) + ','
            else:
                city = ' '
            return {
                'data': inv,
                'model': self.env['report.locv_reporte_facturacion.template_cliente'],
                'lines': res,  # self.get_lines(data.get('form')),
                # date.partner_id
                'docs': docs,
                'infos': info,
                'total': self.formato_cifras(total),
                'total_total': self.formato_cifras(inv.amount_total),
                'monto_iva': self.formato_cifras(inv.amount_tax),
                'base': self.formato_cifras(base),
                'monto_base_exento': self.formato_cifras(monto_base_exento),
                'cifra_total': self.numero_to_letras(inv.amount_total),
                'company': inv.env.company,
                'street' : street,
                'zip_code': zip_code,
                'city': city,
                'origin_check': origen,
                'nota_cred': nota_cred,
                'origin_number': origin_number,

            }

    def formato_cifras(self, valor):
        monto = '{0:,.2f}'.format(valor).replace('.', '-')
        monto = monto.replace(',', '.')
        monto = monto.replace('-', ',')
        return monto

    def numero_to_letras(self,numero):
        indicador = [("", ""), ("MIL", "MIL"), ("MILLON", "MILLONES"), ("MIL", "MIL"), ("BILLON", "BILLONES")]
        entero = int(numero)
        decimal = int(round((numero - entero) * 100))
        # print 'decimal : ',decimal
        contador = 0
        numero_letras = ""
        while entero > 0:
            a = entero % 1000
            if contador == 0:
                en_letras = self.convierte_cifra(a, 1).strip()
            else:
                en_letras = self.convierte_cifra(a, 0).strip()
            if a == 0:
                numero_letras = en_letras + " " + numero_letras
            elif a == 1:
                if contador in (1, 3):
                    numero_letras = indicador[contador][0] + " " + numero_letras
                else:
                    numero_letras = en_letras + " " + indicador[contador][0] + " " + numero_letras
            else:
                numero_letras = en_letras + " " + indicador[contador][1] + " " + numero_letras
            numero_letras = numero_letras.strip()
            contador = contador + 1
            entero = int(entero / 1000)
        numero_letras = numero_letras
        return numero_letras

    def convierte_cifra(self,numero, sw):
        lista_centana = ["", ("CIEN", "CIENTO"), "DOSCIENTOS", "TRESCIENTOS", "CUATROCIENTOS", "QUINIENTOS",
                         "SEISCIENTOS", "SETECIENTOS", "OCHOCIENTOS", "NOVECIENTOS"]
        lista_decena = ["", (
        "DIEZ", "ONCE", "DOCE", "TRECE", "CATORCE", "QUINCE", "DIECISEIS", "DIECISIETE", "DIECIOCHO", "DIECINUEVE"),
                        ("VEINTE", "VEINTI"), ("TREINTA", "TREINTA Y "), ("CUARENTA", "CUARENTA Y "),
                        ("CINCUENTA", "CINCUENTA Y "), ("SESENTA", "SESENTA Y "),
                        ("SETENTA", "SETENTA Y "), ("OCHENTA", "OCHENTA Y "),
                        ("NOVENTA", "NOVENTA Y ")
                        ]
        lista_unidad = ["", ("UN", "UNO"), "DOS", "TRES", "CUATRO", "CINCO", "SEIS", "SIETE", "OCHO", "NUEVE"]
        centena = int(numero / 100)
        decena = int((numero - (centena * 100)) / 10)
        unidad = int(numero - (centena * 100 + decena * 10))
        # print "centena: ",centena, "decena: ",decena,'unidad: ',unidad

        texto_centena = ""
        texto_decena = ""
        texto_unidad = ""

        # Validad las centenas
        texto_centena = lista_centana[centena]
        if centena == 1:
            if (decena + unidad) != 0:
                texto_centena = texto_centena[1]
            else:
                texto_centena = texto_centena[0]

        # Valida las decenas
        texto_decena = lista_decena[decena]
        if decena == 1:
            texto_decena = texto_decena[unidad]
        elif decena > 1:
            if unidad != 0:
                texto_decena = texto_decena[1]
            else:
                texto_decena = texto_decena[0]
        # Validar las unidades
        # print "texto_unidad: ",texto_unidad
        if decena != 1:
            texto_unidad = lista_unidad[unidad]
            if unidad == 1:
                texto_unidad = texto_unidad[sw]

        return "%s %s %s" % (texto_centena, texto_decena, texto_unidad)