import time
from odoo import fields, models, api, exceptions, _
from odoo.exceptions import UserError

from odoo.addons import decimal_precision as dp

from datetime import timedelta, datetime, date
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT


class FiscalBook(models.Model):
    FORNIGHT = [('first', "First Fortnight"), ('second', "Second Fortnight")]

    STATES = [('draft', 'Preparándose'),
              ('confirmed', 'Aprobado por el Responsable'),
              ('done', 'Enviado al Seniat'),
              ('cancel', 'Cancelar')]

    TYPES = [('sale', 'Libro de Venta'),
             ('purchase', 'Libro de Compra')]

    TIME_PERIODS = [('this_month', 'Este mes'),
                    ('this_quarter', 'Esta Trimestre'),
                    ('this_year', 'Este año Fiscal'),
                    ('last_month', 'Último mes'),
                    ('last_quarter', 'Último Trimestre'),
                 #   ('last_year', 'Último año Fiscal'),
                    ('custom', 'Personalizado')]

    @api.model
    def _get_type(self):
        context = self._context or {}
        return context.get('type', 'purchase')

    
    def _get_article_number(self):
        context = self._context or {}
        company_brw = self.env['res.users'].browse().company_id
        if context.get('type') == 'sale':
            return company_brw.printer_fiscal and '78' or '76'
        else:
            return '75'

    
    def _get_article_number_types(self):

        company_brw = self.env['res.users'].browse().company_id
        if self._context.get('type') == 'sale':
		#
            if company_brw.printer_fiscal:
                return [('77', 'Article 77'), ('78', 'Article 78')]
            else:
                return [('76', 'Article 76')]
        else:
            return [('75', 'Article 75')]

    
    def _get_partner_addr(self):
        """ It returns Partner address in printable format for the fiscal book
        report.
        @param field_name: field [get_partner_addr]
        """

        rp_obj = self.env['res.partner']
        res = {}.fromkeys(self.ids, 'NO HAY DIRECCION FISCAL DEFINIDA')
        # TODO: ASK: what company, fisal.book.company_id?
        ru_obj = self.env['res.users']
        rc_brw = ru_obj.browse().company_id
        addr = rp_obj._find_accounting_partner(rc_brw.partner_id)
        for fb_id in self.ids:
            if addr:
                res[fb_id] = (addr.street or '') + \
                             ' ' + (addr.street2 or '') + ' ' + (addr.zip or '') + ' ' \
                             + (addr.city or '') + ' ' + \
                             (addr.country_id and addr.country_id.name or '') + \
                             ', TELF.:' + (addr.phone or '') or \
                             'NO HAY DIRECCION FISCAL DEFINIDA'
        return res

    
    def _get_month_year(self):
        """ It returns an string with the information of the the year and month
        of the fiscal book.
        @param field_name: field [get_month_year]
        """

        months = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
                  "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre",
                  "Diciembre"]
        res = {}.fromkeys(self.ids, '')
        for fb_brw in self.browse(self.ids):
            month = months[time.strptime(fb_brw.date_start, "%Y-%m-%d")[1] - 1]
            year = time.strptime(fb_brw.date_start, "%Y-%m-%d")[0]
            res[fb_brw.id] = ("Correspodiente al Mes de " + str(month) +
                              " del año " + str(year))
        return res

    
    def _get_total_with_iva_sum(self, field_names=None):
        """ It returns sum of of all columns total with iva of the fiscal book
        lines.
        @param field_name: ['get_total_with_iva_sum',
                            'get_total_with_iva_imex_sum',
                            'get_total_with_iva_do_sum',
                            'get_total_with_iva_tp_sum',
                            'get_total_with_iva_ntp_sum',
                            ]"""
        res = {}
        if field_names:
            res = {}.fromkeys(self.ids, {}.fromkeys(field_names, 0.0))
        op_types = ["imex", "do", "tp", "ntp"]
        for fb_brw in self.browse():
            for fbl_brw in fb_brw.fbl_ids:
                # TODO LINEA ORIGINAL SE COMENTA POR SU RELACION CON EL MODELO customs.form DEL MODULO l10n_ve_imex
                # if fbl_brw.invoice_id or fbl_brw.cf_id:
                # TODO SI SE UTILIZA LA LINEA ANTERIOR SE DEBE COMENTAR LA SIGUIENTE
                if fbl_brw.invoice_id:
                    fbl_op_type = fbl_brw.type in ['im', 'ex'] and 'imex' \
                                  or fbl_brw.type
                    fbl_index = "get_total_with_iva_" + fbl_op_type + "_sum"
                    res[fb_brw.id][fbl_index] += fbl_brw.total_with_iva

            res[fb_brw.id]['get_total_with_iva_sum'] = \
                sum([res[fb_brw.id]["get_total_with_iva_" + optype + "_sum"]
                     for optype in op_types])
        return res

    
    def _get_vat_sdcf_sum(self):
        """ It returns the SDCF sumation of purchase (imported, domestic) or
        sale (Exports, tax payer, Non-Tax Payer) operations types.
        @param field_name: field ['get_vat_sdcf_sum'] """

        res = {}.fromkeys(self.ids, 0.0)
        for fb_brw in self.browse():
            res[fb_brw.id] = fb_brw.type == 'purchase' \
                             and (fb_brw.imex_sdcf_vat_sum + fb_brw.do_sdcf_vat_sum) \
                             or (fb_brw.imex_sdcf_vat_sum + fb_brw.tp_sdcf_vat_sum +
                                 fb_brw.ntp_sdcf_vat_sum)
        return res

    
    def _get_total_tax_credit_debit(self, field_names):
        """ It returns sum of of all data in the fiscal book summary table.
        @param field_name: ['get_total_tax_credit_debit_base_sum',
                            'get_total_tax_credit_debit_tax_sum']
        """
        # TODO: summations of all taxes types? only ret types?
        res = {}.fromkeys(self.ids, {}.fromkeys(field_names, 0.0))
        for fb_brw in self.browse():
            op_types = fb_brw.type == 'purchase' and ['imex', 'do'] \
                       or ['imex', 'tp', 'ntp']
            tax_types = ['reduced', 'general', 'additional']

            res[fb_brw.id]['get_total_tax_credit_debit_base_sum'] += \
                sum([getattr(fb_brw, op + '_' + ttax + '_vat_base_sum')
                     for ttax in tax_types
                     for op in op_types])

            res[fb_brw.id]['get_total_tax_credit_debit_tax_sum'] += \
                sum([getattr(fb_brw, op + '_' + ttax + '_vat_tax_sum')
                     for ttax in tax_types
                     for op in op_types])
        return res

    
    def _get_wh(self, field_names):
        """ It returns sum of all data in the withholding summary table.
        @param field_name: ['get_total_wh_sum', 'get_previous_wh_sum',
                            'get_wh_sum']"""
        # TODO: this works if its ensuring that that emmision date is always
        # set and and all periods for every past dates are created.
        res = {}.fromkeys(self.ids, {}.fromkeys(field_names, 0.0))

        for fb_brw in self.browse():
            for fbl_brw in fb_brw.fbl_ids:
                if fbl_brw.iwdl_id:
                    # TODO revisar este metodo
                    # emission_period = period_obj.find(fbl_brw.emission_date)
                    local_period = self.get_time_period(self.time_period)
                    if local_period.get('dt_from') <= fb_brw.emission_date <= local_period.get('dt_to'):
                        res[fb_brw.id]['get_wh_sum'] += \
                            fbl_brw.iwdl_id.amount_tax_ret
                        res[fb_brw.id]['get_wh_debit_credit_sum'] += \
                            fbl_brw.get_wh_debit_credit
                    else:
                        res[fb_brw.id]['get_previous_wh_sum'] += \
                            fbl_brw.iwdl_id.amount_tax_ret
            res[fb_brw.id]['get_total_wh_sum'] = \
                res[fb_brw.id]['get_wh_sum'] + \
                res[fb_brw.id]['get_previous_wh_sum']
        return res

    
    def _get_do_adjustment_vat_tax_sum(self):
        res = {}
        for fb_brw in self.browse():
            avts = 0
            for fbl_brw in fb_brw.fbl_ids:
                if fbl_brw.doc_type == 'AJST':
                    avts += fbl_brw._get_wh_vat(fb_brw.id)
            res[fb_brw.id] = avts
        return res

    def _get_default_company(self):
        for inv in self.issue_invoice_ids:
            res_company = self.env['res.company'].search([('id', '=', inv.company_id.id)])
            if not res_company:
                res_company = self.env.company
            return res_company
    # def _get_company(self):
    #     user = self.env['res.users'].browse(self.uid)
    #     return user.company_id.id

    _description = "Venezuela's Sale & Purchase Fiscal Books"
    _name = 'fiscal.book'
    _inherit = ['mail.thread']

    name = fields.Char('Descripción', size=256, required=True)
    company_id = fields.Many2one(
        'res.company', string='Compañia',
        default=_get_default_company,  # lambda self: self.env.company.id,
        help="Compañia", required=True)
   # company_id = fields.Many2one('res.company', 'Compañia', help='Company', )
    # period_id = fields.Many2one('account.period', string='Period', required=True,
    #        help="Book's Fiscal Period. The periods listed are thouse how are "
    #             "regular periods, i.e. not opening/closing periods.")
    currency_id = fields.Many2one('res.currency', string='Moneda')
    period_start = fields.Date('Periodo de Inicio')
    period_end = fields.Date('Periodo Fin')
    fortnight = fields.Selection(FORNIGHT, string="Quincena", default=None,
                                 help="Fortnight that applies to the current book.")
    state = fields.Selection(STATES, string='Status', required=True, readonly=True, default='draft')
    type = fields.Selection(TYPES, help="Select Sale for Customers and Purchase for Suppliers",
                            string='Tipo de libro', required=True, default=lambda s: s._get_type())
    base_amount = fields.Float('Base imponible', help='Cantidad utilizada como base imponible')
    tax_amount = fields.Float('Cantidad gravada', help='Cantidad gravada sobre la base imponible')
    fbl_ids = fields.One2many('fiscal.book.line', 'fb_id', 'Lineas de libros',
                              help='Lines being recorded in the book')
    fbt_ids = fields.One2many('fiscal.book.taxes', 'fb_id', 'Lineas de Impuestos',
                              help='Taxes being recorded in the book')
    fbts_ids = fields.One2many('fiscal.book.taxes.summary', 'fb_id', 'Resumen de Impuestos')
    invoice_ids = fields.One2many('account.move', 'fb_id', 'Facturas', help="Las facturas se registran en un "
                                                                               "Libro fiscal")
    issue_invoice_ids = fields.One2many('account.move', 'issue_fb_id', 'Emitir facturas',
                                        help="Las facturas que están en estado pendiente cancelan o se borran")
    iwdl_ids = fields.One2many('account.wh.iva.line', 'fb_id', 'Retenciones de IVA',
                               help="Retenciones de IVA registradas en un libro fiscal")
    # TODO CAMPO RELACIONADO CON MODULO DE IMPUESTOS DE 9MPORTACION Y EXPORTACION (l10n_ve_imex)
    # cf_ids = fields.One2many('customs.form', 'fb_id', 'Customs Form',
    #                            help="Customs Form being recorded in the Fiscal Book")
    # TODO FALTA RESOLVER ERROR: invf = comodel._fields[self.inverse_name]
    # abl_ids = fields.One2many('adjustment.book.line', 'fb_id', 'Adjustment Lines',
    #                            help="Adjustment Lines being recorded in a Fiscal Book")
    note = fields.Text('Note')
    # TODO covert function _get_article_number_types() & _get_article_number() to ODOO 11 and check parameters
    article_number = fields.Selection(_get_article_number_types, string="Número de artículo",
                                      required=True, default=lambda s: s._get_article_number(),
                                      help="Número de artículo que describe las características especiales del libro fiscal "
                                           "De acuerdo con la declaración venezolana RLIVA para fiscal"
                                           "libros de contabilidad. Opciones:"
                                           "- Art. 75: Libro de compra"
                                           "- Art. 76: Libro de ventas. Refleja cada operación individual"
                                           "detalle"
                                           "- Art. 77: Libro de ventas. Agrupa operaciones de contribuyentes no tributarios en"
                                           " uno "
                                           "línea consolidada. Solo facturación fiscal"
                                           "- Art. 78: Libro de venta. Híbrido para el artículo 76 y 77. Mostrar"
                                           "operaciones automáticas y mecanizadas de manera individual, y"
                                           "agrupa las operaciones de facturación fiscal en una consolidada"
                                           "línea.")
    # Withholding fields
    get_wh_sum = fields.Float(compute='_get_wh',
                              method=True, store=True, #multi="get_wh",
                              string="Retención del período actual",
                              help="Usado en"
                                   " 1. Fila de totalización en el bloque de la línea del libro fiscal en la retención"
                                   " Columna de -iva"
                                   " 2. Second row at the Withholding Summary block ")
    get_previous_wh_sum = fields.Float( compute='_get_wh',
                                       method=True, store=True, #multi="get_wh",
                                       string="Retención del período anterior",
                                       help="Primera fila en el bloque Resumen de retención")
    get_total_wh_sum = fields.Float(compute='_get_wh',
                                    method=True, store=True, #multi="get_wh",
                                    string="Suma de retención de IVA",
                                    help="Fila de totalización en el bloque Resumen de retención")
    get_wh_debit_credit_sum = fields.Float(compute='_get_wh',
                                           method=True, store=True, #multi="get_wh",
                                           string="Suma de débito fiscal basado",
                                           help="Fila de totalización en el bloque de la línea del libro fiscal en "
                                                "Columna de débito fiscal basado")

    # Printable report data
    get_partner_addr = fields.Char(compute='_get_partner_addr',
                                   type="text", method=True,
                                   help='Partner address printable format')
    get_month_year = fields.Char(compute='_get_month_year',
                                 type="text", method=True,
                                 help='Year and Month ot the Fiscal book period')

    # Totalization fields for all type of transactions
    get_total_with_iva_sum = fields.Float(compute='_get_total_with_iva_sum',
                                          method=True, store=True,
                                          multi="get_total_with_iva",
                                          string='Importe total con IVA',
                                          help="Total con suma de IVA (importación / exportación, nacional, contribuyente y "
                                               "Pagador no tributario")
    get_vat_sdcf_sum = fields.Float(compute='_get_vat_sdcf_sum',
                                    method=True, store=True,
                                    string="Exento y suma de impuestos SDCF",
                                    help="Exentos y sin derecho a la totalización del crédito fiscal. La suma de"
                                         "SDCF y columnas de totalización de impuestos exentos para todas las transacciones"
                                         "tipos")
    get_total_tax_credit_debit_base_sum = fields.Float(compute='_get_total_tax_credit_debit',
                                                       method=True, store=True,
                                                  #     multi="get_total_tax_credit_debit",
                                                       string="Monto base total del crédito fiscal",
                                                       help="Usos en 1. compra: fila total en el resumen de impuestos "
                                                            "2. ventas: fila en el resumen de impuestos")
    get_total_tax_credit_debit_tax_sum = fields.Float(compute='_get_total_tax_credit_debit',
                                                      method=True, store=True,
                                                   #   multi="get_total_tax_credit_debit",
                                                      string="Crédito fiscal Monto total de impuestos")
    do_sdcf_and_exempt_sum = fields.Float(digits=dp.get_precision('Account'),
                                          string="Suma de IVA interno no gravado",
                                          help="SDCF y Exempt sum para domestict transanctions "
                                               "En la venta, el libro representa la suma del contribuyente y el no contribuyente")

    # Totalization fields for international transactions
    get_total_with_iva_imex_sum = fields.Float(compute='_get_total_with_iva_sum',
                                               method=True, store=True,
                                            #   multi="get_total_with_iva",
                                               string="Importe total con IVA",
                                               help="Total importado / exportado con totalización del IVA")
    imex_vat_base_sum = fields.Float(#digits=dp.get_precision('Account'),
                                     string="Monto imponible internacional",
                                     help="Suma de importes de base impositiva internacional (reducida, general "
                                          "y adicional). Utilizado en la segunda fila en el resumen del libro de ventas"
                                          "con el título de ventas de exportación")
    imex_exempt_vat_sum = fields.Float(#digits=dp.get_precision('Account'),
                                       string="Impuesto exento",
                                       help="Totalización de impuestos exentos de importación / exportación: suma de exentos "
                                            "columna para transacciones internacionales")
    imex_sdcf_vat_sum = fields.Float(#digits=dp.get_precision('Account'),
                                     string="Impuesto SDCF",
                                     help="Importación / Exportación Totalización de impuestos SDCF: Suma de la columna SDCF "
                                          "para transacciones internacionales")
    imex_general_vat_base_sum = fields.Float(#digits=dp.get_precision('Account'),
                                             string="Importe imponible general del IVA",
                                             help="General IVA Impuestos Importaciones / Exportaciones Monto base. La suma de"
                                                  "Columna base general del IVA para transacciones internacionales")
    imex_general_vat_tax_sum = fields.Float(#digits=dp.get_precision('Account'),
                                            string="Cantidad gravada del IVA general",
                                            help="Impuesto general a las importaciones / impuestos a la importación Monto del impuesto. La suma de"
                                                 "Columna de IVA general para transacciones internacionales")
    imex_additional_vat_base_sum = fields.Float(#digits=dp.get_precision('Account'),
                                                string="Importe sujeto a IVA adicional",
                                                help="Importes adicionales gravados con IVA / exportaciones Base Monto. La suma de"
                                                     "Columna Base de IVA adicional para transacciones internacionales")
    imex_additional_vat_tax_sum = fields.Float(#digits=dp.get_precision('Account'),
                                               string="Cantidad de IVA adicional gravada",
                                               help="Impuesto adicional sobre las importaciones / Importes de impuestos. La suma de "
                                                    "Columna de IVA adicional para transacciones internacionales")
    imex_reduced_vat_base_sum = fields.Float(#digits=dp.get_precision('Account'),
                                             string="Importe sujeto a impuestos de IVA Reducido",
                                             help="IVA Reducido Importaciones / exportaciones Base Monto base. La suma de "
                                                  "Columna base de IVA reducido para transacciones internacionales")
    imex_reduced_vat_tax_sum = fields.Float(#digits=dp.get_precision('Account'),
                                            string="Importe reducido de IVA",
                                            help="Reducción del IVA Impuesto de Importaciones / Exportaciones Monto del impuesto. La suma de "
                                                 "Columna de IVA reducido para transacciones internacionales")

    # Totalization fields for domestic transactions
    get_total_with_iva_do_sum = fields.Float(compute='_get_total_with_iva_sum',
                                             method=True, store=True,
                                             multi="get_total_with_iva",
                                             string='Importe total con IVA',
                                             help="Total nacional con totalización de IVA")
    do_vat_base_sum = fields.Float(#digits=dp.get_precision('Account'),
                                   string="Cantidad imponible nacional",
                                   help="Suma de todos los importes básicos de las transacciones nacionales (reducido, "
                                        "general y adicional)")
    do_exempt_vat_sum = fields.Float(
        #digits=dp.get_precision('Account'),
        string="Impuesto exento",
        help="Totalización de impuestos nacionales exentos. Para la Reserva de compra"
             "sumas Columna exenta para transacciones nacionales. En la reserva de venta"
             "Sumas de las columnas de exención del contribuyente y del no contribuyente")
    do_sdcf_vat_sum = fields.Float(#digits=dp.get_precision('Account'),
                                   string="Impuesto SDCF",
                                   help="Totalización de impuestos nacionales SDCF. Para el libro de compra se resume "
                                        "Columna SDCF para transacciones nacionales. Para la venta Reserve sumas"
                                        "Columnas SDCF de contribuyentes y no contribuyentes")
    do_general_vat_base_sum = fields.Float(#digits=dp.get_precision('Account'),
                                           string="Importe imponible general del IVA",
                                           help="Totalización general de la base imponible del IVA general "
                                                "Para el Libro de compras, suma la columna Base general del IVA para uso doméstico"
                                                "transacciones. Para el libro de venta se suma al contribuyente y al contribuyente no tributario"
                                                "Columnas generales de base de IVA")
    do_general_vat_tax_sum = fields.Float(#digits=dp.get_precision('Account'),
                                          string="Cantidad gravada del IVA general",
                                          help="Totalización de impuestos nacionales gravados con IVA general "
                                               "Para el libro de compras, suma la columna del impuesto general del IVA para los nacionales"
                                               "transacciones. Para el libro de venta se suma al contribuyente y al contribuyente no tributario"
                                               "Columnas generales del impuesto sobre el IVA")
    do_additional_vat_base_sum = fields.Float(#digits=dp.get_precision('Account'),
                                              string="Importe sujeto a IVA adicional",
                                              help="Totalización del monto base nacional gravado con IVA adicional "
                                                   "Para el Libro de compras, suma la columna Base de IVA adicional para"
                                                   "transacciones nacionales. Para la venta Libro que suma el contribuyente y no"
                                                   "Columnas de la base de IVA adicional del contribuyente")
    do_additional_vat_tax_sum = fields.Float(#digits=dp.get_precision('Account'),
                                             string="Cantidad de IVA adicional gravada",
                                             help="Totalización del monto del impuesto interno gravado con IVA adicional "
                                                  "Para el Libro de compras, suma la columna de IVA adicional para"
                                                  "transacciones nacionales. Para el libro de ventas suma las"
                                                  "Columnas de impuestos adicionales del contribuyente   y no Contribuyente")
    do_reduced_vat_base_sum = fields.Float(#digits=dp.get_precision('Account'),
                                           string="Importe sujeto a impuestos reducido",
                                           help="Reduced VAT Taxed Domestic Base Amount Totalization."
                                                " For Purchase Book it sums Reduced VAT Base column for domestic"
                                                " transactions. For Sale Book it sums Tax Payer and Non-Tax Payer"
                                                " Reduced VAT Base columns")
    do_reduced_vat_tax_sum = fields.Float(#digits=dp.get_precision('Account'),
                                          string="Importe reducido de IVA",
                                          help="Reducción del total de impuestos nacionales gravados con IVA reducido "
                                               "Para el libro de compras, suma la columna de impuestos reducidos de IVA para nacionales"
                                               "transacciones. Para el libro de venta se suma al contribuyente y al no contribuyente "
                                               "Columnas de IVA reducido")
    do_adjustment_vat_tax_sum = fields.Float(#compute='_get_do_adjustment_vat_tax_sum',
                                             method=True, type='float',
                                             string='Ajuste IVA de Cantidad de Impuesto')

    # Apply only for sale book
    # Totalization fields for tax payer and Non-Tax Payer transactions
    ntp_fbl_ids = fields.One2many("fiscal.book.line", "ntp_fb_id", string="Non-Tax Payer Detail Lines",
                                  help="Non-Tax Payer Lines that are grouped by the statement law that"
                                       " represent the data of are consolidate book lines")
    get_total_with_iva_tp_sum = fields.Float(compute='_get_total_with_iva_sum',
                                             method=True, store=True,
                                      #       multi="get_total_with_iva",
                                             string="Total amount with VAT",
                                             help="Tax Payer Total with VAT Totalization")
    tp_vat_base_sum = fields.Float(#digits=dp.get_precision('Account'),
                                   string="Tax Payer Taxable Amount",
                                   help="Sum of all Tax Payer Grand Base Sum (reduced, general and"
                                        " additional taxes)")
    tp_exempt_vat_sum = fields.Float(#digits=dp.get_precision('Account'),
                                     string="Exempt Tax",
                                     help="Tax Payer Exempt Tax Totalization. Sum of Exempt column"
                                          " for tax payer transactions")
    tp_sdcf_vat_sum = fields.Float(#digits=dp.get_precision('Account'),
                                   string="SDCF Tax",
                                   help="Tax Payer SDCF Tax Totalization. Sum of SDCF column for"
                                        " tax payer transactions")
    tp_general_vat_base_sum = fields.Float(#digits=dp.get_precision('Account'),
                                           string="General VAT Taxable Amount",
                                           help="General VAT Taxed Tax Payer Base Amount Totalization."
                                                " Sum of General VAT Base column for taxy payer transactions")
    tp_general_vat_tax_sum = fields.Float(#digits=dp.get_precision('Account'),
                                          string="General VAT Taxed Amount",
                                          help="General VAT Taxed Tax Payer Tax Amount Totalization."
                                               " Sum of General VAT Tax column for tax payer transactions")
    tp_additional_vat_base_sum = fields.Float(#digits=dp.get_precision('Account'),
                                              string="Additional VAT Taxable Amount",
                                              help="Additional VAT Taxed Tax Payer Base Amount Totalization."
                                                   " Sum of Additional VAT Base column for tax payer transactions")
    tp_additional_vat_tax_sum = fields.Float(digits=dp.get_precision('Account'),
                                             string="Additional VAT Taxed Amount",
                                             help="Additional VAT Taxed Tax Payer Tax Amount Totalization."
                                                  " Sum of Additional VAT Tax column for tax payer transactions")
    tp_reduced_vat_base_sum = fields.Float(#digits=dp.get_precision('Account'),
                                           string="Reduced VAT Taxable Amount",
                                           help="Reduced VAT Taxed Tax Payer Base Amount Totalization."
                                                " Sum of Reduced VAT Base column for tax payer transactions")
    tp_reduced_vat_tax_sum = fields.Float(#digits=dp.get_precision('Account'),
                                          string="Reduced VAT Taxed Amount",
                                          help="Reduced VAT Taxed Tax Payer Tax Amount Totalization."
                                               " Sum of Reduced VAT Tax column for tax payer transactions")
    get_total_with_iva_ntp_sum = fields.Float(compute='_get_total_with_iva_sum',
                                              method=True, store=True,
                                        #      multi="get_total_with_iva",
                                              string="Total amount with VAT",
                                              help="Non-Tax Payer Total with VAT Totalization")
    ntp_vat_base_sum = fields.Float(#digits=dp.get_precision('Account'),
                                    string="Non-Tax Payer Taxable Amount",
                                    help="Non-Tax Payer Grand Base Totalization. Sum of all no tax"
                                         " payer tax bases (reduced, general and additional)")
    ntp_exempt_vat_sum = fields.Float(#digits=dp.get_precision('Account'),
                                      string="Exempt Tax",
                                      help="Non-Tax Payer Exempt Tax Totalization. Sum of Exempt"
                                           " column for Non-Tax Payer transactions")
    ntp_sdcf_vat_sum = fields.Float(#digits=dp.get_precision('Account'),
                                    string="SDCF Tax",
                                    help="Non-Tax Payer SDCF Tax Totalization. Sum of SDCF column"
                                         " for Non-Tax Payer transactions")
    ntp_general_vat_base_sum = fields.Float(#digits=dp.get_precision('Account'),
                                            string="General VAT Taxable Amount",
                                            help="General VAT Taxed Non-Tax Payer Base Amount Totalization."
                                                 " Sum of General VAT Base column for taxy payer transactions")
    ntp_general_vat_tax_sum = fields.Float(#digits=dp.get_precision('Account'),
                                           string="General VAT Taxed Amount",
                                           help="General VAT Taxed Non-Tax Payer Tax Amount Totalization."
                                                " Sum of General VAT Tax column for Non-Tax Payer transactions")
    ntp_additional_vat_base_sum = fields.Float(#digits=dp.get_precision('Account'),
                                               string="Additional VAT Taxable Amount",
                                               help="Additional VAT Taxed Non-Tax Payer Base Amount Totalization."
                                                    " Sum of Additional VAT Base column for Non-Tax Payer"
                                                    " transactions")
    ntp_additional_vat_tax_sum = fields.Float(#digits=dp.get_precision('Account'),
                                              string="Additional VAT Taxed Amount",
                                              help="Additional VAT Taxed Non-Tax Payer Tax Amount Totalization."
                                                   " Sum of Additional VAT Tax column for Non-Tax Payer"
                                                   " transactions")
    ntp_reduced_vat_base_sum = fields.Float(#digits=dp.get_precision('Account'),
                                            string="Reduced VAT Taxable Amount",
                                            help="Reduced VAT Taxed Non-Tax Payer Base Amount Totalization."
                                                 " Sum of Reduced VAT Base column for Non-Tax Payer transactions")
    ntp_reduced_vat_tax_sum = fields.Float(#digits=dp.get_precision('Account'),
                                           string="Reduced VAT Taxed Amount",
                                           help="Reduced VAT Taxed Non-Tax Payer Tax Amount Totalization."
                                                " Sum of Reduced VAT Tax column for Non-Tax Payer transactions")
    _rec_rame = 'fiscal_book_rec'
    time_period = fields.Selection(TIME_PERIODS, 'Período')

    # TODO revisar los efectos de este constraint
    _sql_constraints = [
        # ('period_type_company_uniq', 'unique (period_id,type,company_id,fortnight)',
        ('period_type_company_uniq', 'unique (type,company_id,fortnight)',
         'The period, type, fortnight combination must be unique per company!'),
    ]

    def get_time_period(self, period_type, fiscal_book=None):
        dates_selected = {}
        if not period_type:
            raise exceptions.except_orm("Error!", "Debe seleccionar un período para el libro fiscal.")
        today = date.today()
        if period_type == 'custom':
            if fiscal_book:
                dt_from = fiscal_book.period_start
                dt_to = fiscal_book.period_end
            else:
                dt_from = self.period_start
                dt_to = self.period_end
        elif period_type == 'this_month':
            dt_from = today.replace(day=1) or False
            dt_to = (today.replace(day=1) + timedelta(days=31)).replace(day=1) - timedelta(days=1)
        elif period_type == 'this_quarter':
            quarter = (today.month - 1) // 3 + 1
            dt_to = (today.replace(month=quarter * 3, day=1) + timedelta(days=31)).replace(day=1) - timedelta(days=1)
            dt_from = dt_to.replace(day=1, month=dt_to.month - 2, year=dt_to.year) or False
        elif period_type == 'this_year':
            company_fiscalyear_dates = self.env.company.compute_fiscalyear_dates(datetime.now())
            dt_from = company_fiscalyear_dates['date_from'] or False
            dt_to = company_fiscalyear_dates['date_to']
        elif period_type == 'last_month':
            dt_to = today.replace(day=1) - timedelta(days=1)
            dt_from = dt_to.replace(day=1) or False
        elif period_type == 'last_quarter':
            quarter = (today.month - 1) // 3 + 1
            quarter = quarter - 1 if quarter > 1 else 4
            dt_to = (today.replace(month=quarter * 3, day=1,
                                   year=today.year if quarter != 4 else today.year - 1) + timedelta(days=31)).replace(
                day=1) - timedelta(days=1)
            dt_from = dt_to.replace(day=1, month=dt_to.month - 2, year=dt_to.year) or False
        else:       #last_year option
            # company_fiscalyear_dates = self.env.company.compute_fiscalyear_dates(
            #     datetime.now().replace(year=today.year - 1))
            # dt_from = company_fiscalyear_dates['date_from'] or False
            # dt_to = company_fiscalyear_dates['date_to']
            dto = 0

        dates_selected.update({'dt_from': dt_from, 'dt_to': dt_to})
        return dates_selected

    # action methods
    # TODO Revisar colocar este onchange en el metodo creado para las fechas
    @api.onchange('article_number', 'period_start', 'period_end')
    def onchange_field_clear_book(self):
        """ It make clear all stuff of book. """
        self.clear_book()

    # update book methods
    
    def _get_invoice_ids(self, fb_id):
        """
        It returns ids from open and paid invoices regarding to the type and
        period of the fiscal book order by date invoiced.
        """
        # inv_brw = inv_obj.search([('fb_id', '=', fb_id.id)])
        # inv_type = inv_brw.type == 'sale' \
        inv_obj = self.env['account.move']
        # fb_brw = self.browse(fb_id)
        inv_type = fb_id.type and fb_id.type == 'sale' \
                   and ['out_invoice', 'out_refund'] \
                   or ['in_invoice', 'in_refund']
        inv_state = ['paid', 'open']
        # pull invoice data
        local_period = self.get_time_period(self.time_period)
        ref = fb_id.company_id.id

        inv_ids = inv_obj.search([('invoice_date', '>=', local_period.get('dt_from')),
                                  ('invoice_date', '<=', local_period.get('dt_to')),
                                  ('company_id', '=', fb_id.company_id.id),
                                  ('type', 'in', inv_type),
                                  ('state', 'in', inv_state)],
                                 order='invoice_date asc')


        if fb_id.fortnight:
            inv_ids = self.get_invoices_from_fortnight(fb_id, inv_ids)
        if fb_id.type == 'purchase':
            inv_ids = self.get_invoices_sin_cred(fb_id, inv_ids)
        return inv_ids

    
    def get_invoices_sin_cred(self, ids, inv_ids):
        """
        if the fiscal book is of type purchase then need to filter the invoice
        of the book by only the ones how has sin_cred == False.
        return the filter invoices list.
        @param inv_ids: list of invoice ids
        @return invoices list
        """
        inv_obj = self.env['account.move']
        ids = isinstance(ids, (int, int)) and [ids] or ids
        res = list()
        for inv_id in inv_ids:
            # inv_brw = inv_obj.browse(inv_id)
            if not inv_id.sin_cred:
                res.append(inv_id)
        return res

    
    def get_invoices_from_fortnight(self, ids, inv_ids, d_st, d_en):
        """
        return the invoices with the same fortnight as the fiscal book.
        @param inv_ids: list of invoice ids
        @return invoices list
        """

        inv_obj = self.env['account.move']
        # ids = isinstance(ids, (int, int)) and ids or ids[0]
        res = list()
        # fb_fortnight = self.browse(ids).fortnight
        fb_fortnight = ids.fb_fortnight == 'second' and True or False
        for inv_id in inv_ids:
            inv_brw = inv_obj.browse(inv_id.id)
            for invoice in inv_brw:
                if fb_fortnight:
                    if d_st <= invoice.invoice_date <= d_en:
                        res.append(inv_id)
                else:
                    local_date = d_en.splict('-')
                    fortnight_date = datetime.strptime(local_date[0] + '-' + local_date[1] + '-15',
                                                       DEFAULT_SERVER_DATE_FORMAT)
                    init_date = datetime.strptime(local_date[0] + '-' + local_date[1] + '-1',
                                                  DEFAULT_SERVER_DATE_FORMAT)
                    if init_date <= invoice.invoice_date <= fortnight_date:
                        res.append(inv_id)
            # fortnight = inv_obj.search([('date_document','>=',d_st),('date_document','<=', d_en)])
            # if fb_fortnight == fortnight:
            #    res.append(inv_id)
        return res

    
    def action_confirm(self):
        if not self.fbl_ids:
            self.update_book()
        self.write({'state': 'confirmed'})

    
    def action_done(self):
        self.write({'state': 'done'})

    
    def action_cancel(self):
        self.clear_book()
        self.write({'state': 'cancel'})

    
    def set_to_draft(self):
        self.write({'state': 'draft'})

    
    def update_book(self):
        """ It generate and fill book data with invoices, wh iva lines and
        taxes. """
        local_fb = self.browse(self.ids)
        for fb_brw in local_fb:
            self.clear_book()
            self.update_book_invoices(fb_brw)
            self.update_book_issue_invoices(fb_brw.id)
            self.update_book_wh_iva_lines(fb_brw.id)
            # TODO METODO RELACIONADO CON MODULO l10n_ve_imex (importaciones)
            # self.update_book_customs_form(fb_brw.id)
            self.update_book_lines(fb_brw.id)
        return True

    
    def update_book_invoices(self, fb_id):
        """ It relate/unrelate the invoices to the fical book.
        @param fb_id: fiscal book id
        """

        inv_obj = self.env['account.move']
        # Relate invoices
        inv_ids = self._get_invoice_ids(fb_id)
        for invoice in inv_ids:
            invoice.write({'fb_id': fb_id.id})


        return True

    
    def _get_issue_invoice_ids(self, fb_id):
        """ It returns ids from not open or paid invoices regarding to the type
        and period of the fiscal book order by date invoiced.
        @param fb_id: fiscal book id.
        """

        inv_obj = self.env['account.move']
        fb_brw = self.browse(fb_id)
        inv_type = fb_brw.type == 'sale' \
                   and ['out_invoice', 'out_refund'] \
                   or ['in_invoice', 'in_refund']
        inv_state = ['posted']
        # pull invoice data
        # issue_inv_ids = inv_obj.search(['|', '&', ('fb_id', '=', fb_brw.id),
        #            ('period_id', '!=', fb_brw.period_id.id),
        #            '&', '&', ('period_id', '=', fb_brw.period_id.id),
        #            ('type', 'in', inv_type), ('state', 'not in', inv_state)],
        #            order='invoice_date asc')
        local_period = self.get_time_period(self.time_period)
        domain = ['|', '&', (True, '=', True), ('fb_id', '=', fb_brw.id),
                  '&', '&', '&', ('invoice_date', '>=', local_period.get('dt_from')),
                  ('invoice_date', '<=', local_period.get('dt_to')),
                  ('type', 'in', inv_type), ('state', 'in', inv_state)]
        issue_inv_ids = inv_obj.search(domain, order='invoice_date asc')
        if fb_brw.fortnight:
            issue_inv_ids = self.get_invoices_from_fortnight(fb_id, issue_inv_ids)
        if fb_brw.type == 'purchase':
            issue_inv_ids = self.get_invoices_sin_cred(fb_id, issue_inv_ids)

        return issue_inv_ids

    def update_book_issue_invoices(self, fb_id):
        """ It relate the issue invoices to the fiscal book. That criterion is:
          - Invoices of the period in state different form open or paid state.
          - Invoices already related to the book but it have a period change.
        @param fb_id: fiscal book id
        """
        docum = ' '
        inv_obj = self.env['account.move']
        issue_inv_ids = self._get_issue_invoice_ids(fb_id)
        for invoice in issue_inv_ids:
            impuestos_exc = (invoice.amount_total + (invoice.amount_tax_signed))
            total = invoice.amount_total
            a_pagar = invoice.amount_total

            if invoice.type == 'in_invoice':
                docum = invoice.supplier_invoice_number
            elif invoice.type == 'out_invoice':
                docum = invoice.name
            elif invoice.type == 'in_refund' or 'out_refund':
                docum = invoice.invoice_origin
            invoice.write({'issue_fb_id': fb_id,
                           'amount_untaxed_signed': impuestos_exc,
                           'amount_total_signed':total,
                           'amount_residual_signed': a_pagar,
                           'invoice_origin': docum
            })
        return True

    def _get_wh_iva_line_ids(self, fb_id):
        """ It returns ids from wh iva lines with state 'done' regarding to the
        fiscal book period.
        @param fb_id: fiscal book id
        """

        awi_obj = self.env['account.wh.iva']
        awil_obj = self.env['account.wh.iva.line']
        fb_brw = self.browse(fb_id)
        awil_type = fb_brw.type == 'sale' \
                    and ['out_invoice', 'out_refund'] \
                    or ['in_invoice', 'in_refund']
        # pull wh iva line data
        awil_ids = []
        local_period = self.get_time_period(self.time_period)
        domain = [('date_ret', '>=', local_period.get('dt_from')),
                  ('date_ret', '<=', local_period.get('dt_to')),
                  ('type', 'in', awil_type),
                  ('state', '=', 'done')]
        awi_ids = awi_obj.search(domain)
        if fb_brw.fortnight:
            awi_ids = self.get_awi_from_fortnight(fb_id, awi_ids)

        for awi_id in awi_ids:
            awil_ids.append(awil_obj.search([('retention_id', '=', awi_id.id)]))
            # awil_ids.extend(list_ids)
        return awil_ids

    def get_awi_from_fortnight(self, ids, awi_ids, d_st=None, d_en=None):
        """
        return the awi ids with the same fortnight as the fiscal book.
        @param awi_ids: list of account withholding iva document ids.
        @param ids: only one fiscal book id.
        @return account withholding document id list
        """


        awi_obj = self.env['account.wh.iva']
        # ids = isinstance(ids, (int, int)) and ids or ids[0]
        res = list()
        fb_fortnight = self.browse(ids).fortnight
        fb_fortnight = fb_fortnight == 'second' and True or False
        for awi_id in awi_ids:
            awi_brw = awi_obj.browse(awi_id)
            # period, fortnight = period_obj._find_fortnight(date=awi_brw.date_ret)
            # period = period
            # if fb_fortnight == fortnight:
            #    res.append(awi_id)

            if fb_fortnight:
                if d_st <= awi_id.date_ret <= d_en:
                    res.append(awi_id)
            else:
                local_date = d_en.splict('-')
                fortnight_date = datetime.strptime(local_date[0] + '-' + local_date[1] + '-15',
                                                   DEFAULT_SERVER_DATE_FORMAT)
                init_date = datetime.strptime(local_date[0] + '-' + local_date[1] + '-1',
                                              DEFAULT_SERVER_DATE_FORMAT)
                if init_date <= awi_id.date_ret <= fortnight_date:
                    res.append(awi_id)
        return res

    # TODO: test this method.
    def update_book_wh_iva_lines(self, fb_id):
        """ It relate/unrelate the wh iva lines to the fiscal book.
        @param fb_id: fiscal book id
        """

        iwdl_obj = self.env['account.wh.iva.line']
        rp_obj = self.env['res.partner']
        fb_brw = self.browse(fb_id)
        # Relate wh iva lines
        iwdl_ids = self._get_wh_iva_line_ids(fb_id)

        if (fb_brw.type == "purchase" and iwdl_ids and not
        rp_obj._find_accounting_partner(
            fb_brw.company_id.partner_id).wh_iva_agent):
            raise exceptions.except_orm("Error!", "Tiene retenciones registradas pero no es un agente de retención.")
        for iwdl in iwdl_ids:
            iwdl.write({'fb_id': fb_id})
        # Unrelate wh iva lines (period book change, wh iva line have been
        # cancel or have change its period)
        all_iwdl_ids = iwdl_obj.search([('fb_id', '=', fb_id)])
        for iwdl_id_to_check in all_iwdl_ids:
            if iwdl_id_to_check not in iwdl_ids:
                iwdl_id_to_check.write({'fb_id': False})
        return True

    def _get_invoice_iwdl_id(self, fb_id, inv_id):
        """ It check if the invoice have wh iva lines asociated and if its
        check if it is at the same period. Return the wh iva line ID or False
        instead.
        @param fb_id: fiscal book id.
        @param inv_id: invoice id to get wh line.
        """

        # inv_obj = self.env['account.move']
        # inv_brw = inv_obj.browse( inv_id)
        iwdl_obj = self.env['account.wh.iva.line']
        iwdl_id = False
        if inv_id.wh_iva_id:
            iwdl_id = iwdl_obj.search([('invoice_id', '=', inv_id.id), ('fb_id', '=', fb_id)])
        return iwdl_id and iwdl_id[0] or False

    def _get_orphan_iwdl_ids(self, fb_id):
        """ It returns a list of ids from the orphan wh iva lines in the period
        that have not associated invoice.
        @param fb_id: fiscal book id
        """

        iwdl_obj = self.env['account.wh.iva.line']
        inv_ids = [inv_brw.id
                   for inv_brw in self.browse(fb_id).issue_invoice_ids]
        inv_wh_ids = \
            [iwdl_brw.invoice_id.id for iwdl_brw in self.browse(fb_id).iwdl_ids]
        orphan_inv_ids = set(inv_wh_ids) - set(inv_ids)
        orphan_inv_ids = list(orphan_inv_ids)
        hola = iwdl_obj.search([('invoice_id', 'in', orphan_inv_ids)])
        return orphan_inv_ids and hola or []

    def get_order_criteria_adjustment(self, book_type):
        #return book_type == 'sale' \
        #       and 'accounting_date asc, ctrl_number asc' \
        #       or 'emission_date asc, invoice_number asc'

        return book_type == 'sale' \
               and 'emission_date asc, ctrl_number asc' \
               or 'emission_date asc, invoice_number asc'

    def get_order_criteria(self, book_type):
        #return book_type == 'sale' \
        #   and 'accounting_date asc, invoice_number asc' \
        #   or 'emission_date asc, invoice_number asc'
        return book_type == 'sale' \
               and 'emission_date asc, invoice_number asc' \
               or 'emission_date asc, invoice_number asc'

    def order_book_lines(self, fb_id):
        """ It orders book lines by a set of criteria:
            - chronologically ascendant date (For purchase book by
              emission date, for sale book by accounting date).
            - ascendant ordering for fiscal printer ascending number.
            - ascendant ordering for z report number.
            - ascendant ordering for invoice number.
        @param fb_id: book id.
        """

        fbl_obj = self.env['fiscal.book.line']
        fb_brw = self.browse(fb_id)
        fbl_ids = [line_brw.id for line_brw in fb_brw.fbl_ids]

        ajst_order_criteria = self.get_order_criteria_adjustment(
            fb_brw.type)
        ajst_ordered_fbl_ids = fbl_obj.search([('id', 'in', fbl_ids), ('doc_type', '=', 'AJST')],
                                              order=ajst_order_criteria)

        for rank, fbl_id in enumerate(ajst_ordered_fbl_ids, 1):
            fbl_obj.write(fbl_id, {'rank': rank})

        order_criteria = self.get_order_criteria(fb_brw.type)
        ordered_fbl_ids = fbl_obj.search([('id', 'in', fbl_ids), ('doc_type', '!=', 'AJST')], order=order_criteria)

        for rank, fbl_id in enumerate(ordered_fbl_ids, len(ajst_ordered_fbl_ids) + 1):
            fbl_id.write({'rank': rank})

        return True

    def _get_no_match_date_iwdl_ids(self, fb_id):
        """ It returns a list of wh iva lines ids that have a invoice in the
        same book period but where the invoice invoice_date is different from
        the wh iva line date.
        @param fb_id: fiscal book id.
        """

        iwdl_obj = self.env['account.wh.iva.line']
        res = []

        for inv_brw in self.issue_invoice_ids:
            iwdl_id = self._get_invoice_iwdl_id(fb_id, inv_brw)
            if iwdl_id:
                if inv_brw.invoice_date != iwdl_id.date_ret:
                    res.append(iwdl_id)
        return res


    def get_t_type(self, doc_type=None, name=None):
        tt = ''
        if doc_type:
            if doc_type == "N/DB" or doc_type == "N/CR":
                tt = '02-COMP'
            elif name and name.find('PAPELANULADO') >= 0:
                tt = '03-ANU'
            else:
                tt = '01-REG'
        return tt

    # Funcion que limpia el numero de factura para que no aparezca "papelanulado"
    
    def get_number(self, local_inv_nbr):
        tt = ''
        busqueda = local_inv_nbr.find('PAPELANULADO')

        if busqueda != -1: #si es distinto de -1 encontro la palabra
            posicion = local_inv_nbr.find("(")
            tt = local_inv_nbr[0:posicion]
        else:
            tt = local_inv_nbr
        return tt

    
    def update_book_lines(self, fb_id):
        """ It updates the fiscal book lines values. Cretate, order and rank
        the book lines. Creates the book taxes too acorring to lines created.
        @param fb_id: fiscal book id
        """

        data = []
        data2= []
        iwdl_obj = self.env['account.wh.iva.line']
        fb_brw = self.browse(fb_id)
        rp_obj = self.env['res.partner']
        local_inv_affected = ''
        boll = False
        cliente = False
        proveedor = False
        inv_siva = []
        inv_iva = []
        for inv_brw in self.browse(fb_id).issue_invoice_ids:

            if inv_brw.wh_iva_id.state == 'draft' and inv_brw.state == 'posted' and inv_brw.sin_cred == False:

                inv_siva += inv_brw

            elif inv_brw.wh_iva_id.state == 'done' and inv_brw.state == 'posted' and inv_brw.sin_cred == False:
                inv_iva += inv_brw

            if not inv_brw.wh_iva_id and inv_brw.partner_id.wh_iva_agent == False and inv_brw.state == 'posted' and inv_brw.sin_cred == False:
                inv_siva += inv_brw
            elif not inv_brw.wh_iva_id and inv_brw.partner_id.wh_iva_agent == True and inv_brw.state == 'posted' and inv_brw.sin_cred == False:
                inv_siva += inv_brw


        printer_fiscal = self.company_id.printer_fiscal
        busq = self.browse(fb_id)
        if printer_fiscal == True and busq.type == 'sale':
            tabla_report_z = self.env['datos.zeta.diario']
            date_from1 = ''
            date_to1 = ''
            local_period = self.get_time_period(self.time_period)
            date_from = local_period.get('dt_from')
            date_to = local_period.get('dt_to')

            if len(str(date_from.month)) == 1:
                date_from1 = '0' + str(date_from.month)
            if len(str(date_to.month)) == 1:
                date_to1 = '0' + str(date_to.month)
            if len(str(date_from.month)) == 2:
                date_from1 = str(date_from.month)
            if len(str(date_to.month)) == 2:
                date_to1 = str(date_to.month)
            from_date = str(date_from.day) + '-' + date_from1 + '-' + str(date_from.year)
            to_date = str(date_to.day) + '-' + date_to1 + '-' + str(date_to.year)
            domain = [
                      ('fecha_ultimo_reporte_z', '>=', from_date),
                      ('fecha_ultimo_reporte_z', '<=', to_date),
                      ('numero_ultimo_reporte_z', '>','0')
                     ]
            report_z_ids = tabla_report_z.search(domain, order='fecha_ultimo_reporte_z asc')
  #          for iwdl_brw in iwdl_ids:
            for report_z in report_z_ids:
                # rp_brw = rp_obj._find_accounting_partner(iwdl_brw.retention_id.partner_id)
                # para obtener el tipo de transacción
                if float(report_z.ventas_exento) != 0 or float(report_z.base_imponible_ventas_iva_g) != 0  or \
                    float(report_z.base_imponible_ventas_iva_r) != 0 or float(report_z.base_imponible_ventas_iva_g)!= 0:
                    z_report = ''
                    people_type = 'N/A'

                    t_type = fb_brw.type == 'sale' and 'tp' or 'do'
                    if len(report_z.numero_ultimo_reporte_z) == 1:
                        z_report = report_z.numero_ultimo_reporte_z
                    if len(report_z.numero_ultimo_reporte_z) == 2:
                        z_report = '00'+ str(report_z.numero_ultimo_reporte_z)
                    elif len(report_z.numero_ultimo_reporte_z) == 3:
                        z_report = '0' + str(report_z.numero_ultimo_reporte_z)
                    date_str = report_z.fecha_ultimo_reporte_z
                    date_time_obj = datetime.strptime(date_str, '%d-%m-%Y').date()

                    values = {'report_z_id': report_z.id,
                              'accounting_date': date_time_obj or False,
                              'emission_date': date_time_obj  or False,
                              'type': t_type,
                              'doc_type':'Reporte Z',
                              'wh_number':  False,
                              'get_wh_vat':  0.0,
                              'partner_name': 'N/A',
                              'people_type': people_type,
                              'debit_affected': False,
                              'credit_affected':  False,
                              'partner_vat': 'N/A',
                              'affected_invoice':
                                  '',
                              'affected_invoice_date':
                                 date_time_obj,
                              'wh_rate':'',
                              'invoice_number': "",
                              'ctrl_number': "",
                              'void_form': '',
                              'fiscal_printer': False,
                              'n_ultima_factZ': report_z.numero_ultima_factura,
                              'z_report': z_report or False,
                              }
                    data.append((0, 0, values))


        if inv_iva:

                orphan_iwdl_ids = self._get_orphan_iwdl_ids(fb_id)
                no_match_dt_iwdl_ids = self._get_no_match_date_iwdl_ids(fb_id)
                iwdl_ids = orphan_iwdl_ids
                for nm in no_match_dt_iwdl_ids:
                    iwdl_ids += nm
                t_type = fb_brw.type == 'sale' and 'tp' or 'do'
                for iwdl_otro1 in inv_iva:
                  #  busq = self.env['account.move'].search([('id','=',)])
                    if iwdl_otro1 and iwdl_otro1.type == 'in_invoice':
                      otro = iwdl_otro1.id
                      iwdl_ids += iwdl_obj.search([('invoice_id', '=', otro)])

                for iwdl_brw in iwdl_ids:
                    # if iwdl_brw.type == 'in_invoice':
                        rp_brw = rp_obj._find_accounting_partner(iwdl_brw.retention_id.partner_id)
                        #para obtener el tipo de transacción

                        people_type = 'N/A'
                        document_v = 'N/A'
                        if rp_brw:
                            if rp_brw.company_type == 'company':
                                people_type = rp_brw.people_type_company
                                if people_type == 'pjdo':
                                    document_v = rp_brw.vat
                            elif rp_brw.company_type == 'person':
                                people_type = rp_brw.people_type_individual
                                if rp_brw.nationality == 'V' or rp_brw.nationality == 'E':
                                    document_v = str(rp_brw.nationality) + str(rp_brw.identification_id)
                                else:
                                    document_v = rp_brw.identification_id

                        doc_type = self.get_doc_type(inv_id=iwdl_brw.invoice_id.id)


                        if (doc_type == "N/DB" or doc_type == "N/CR"):
                            if fb_brw.type == 'sale':
                                if iwdl_brw.invoice_id.type == 'out_refund':
                                    cliente = True
                                    local_inv_affected = str(iwdl_brw.invoice_id.ref)[14:29] if iwdl_brw.invoice_id.ref else ''
                            elif  iwdl_brw.invoice_id.type == 'in_refund':
                                proveedor = True
                                local_inv_affected = str(iwdl_brw.invoice_id.ref)[14:29] if iwdl_brw.invoice_id.ref else ''

                        if doc_type == 'N/DB' or doc_type == 'N/CR':

                            sign = -1
                        else:
                            sign = 1
                        if (doc_type == "N/DB" or doc_type == "N/CR") and local_inv_affected:
                            boll = True
                        else:
                            boll = False
                        if boll == True:
                            fecha =  iwdl_brw.invoice_id.date or iwdl_brw.invoice_id.invoice_date
                        else:
                            fecha = fb_brw.fbl_ids.affected_invoice_date
                        values = {'iwdl_id': iwdl_brw.id,
                                  'type': t_type,
                                  'accounting_date': iwdl_brw.date_ret or False,
                                  'emission_date': iwdl_brw.date or iwdl_brw.date_ret or False,
                                  'doc_type': self.get_doc_type(inv_id=iwdl_brw.invoice_id.id, iwdl_id=iwdl_brw.id),
                                  'wh_number': iwdl_brw.retention_id.number or False,
                                  'get_wh_vat': iwdl_brw and iwdl_brw.amount_tax_ret or 0.0,
                                  'partner_name': rp_brw.name or 'N/A',
                                  'people_type': people_type,
                                   'debit_affected': local_inv_affected or False,
                                  #     inv_brw.parent_id and
                                  #     iwdl_brw.invoice_id.type in
                                  #     ['in_invoice', 'out_invoice'] and
                                  #     inv_brw.parent_id.parent_id and
                                  #     inv_brw.parent_id.number or
                                  #     False,
                                   'credit_affected': local_inv_affected and cliente and proveedor or False,
                                  #     inv_brw.parent_id and
                                  #     inv_brw.parent_id.type in
                                  #     ['in_refund', 'out_refund'] and
                                  #     inv_brw.parent_id.number or
                                  #     False,
                                  'partner_vat': document_v,
                                  # 'affected_invoice':
                                  #     iwdl_brw.invoice_id.fiscal_printer and
                                  #     iwdl_brw.invoice_id.invoice_printer or
                                  #     (fb_brw.type == 'sale' and
                                  #      iwdl_brw.invoice_id.supplier_invoice_number or
                                  #      iwdl_brw.invoice_id.supplier_invoice_number),
                                  'affected_invoice':
                                      (doc_type == "N/DB" or doc_type == "N/CR") and local_inv_affected,
                                  'affected_invoice_date':
                                    fecha,
                                  'wh_rate': iwdl_brw.wh_iva_rate,
                                  'invoice_number': iwdl_brw.invoice_id.name or "", # se agrega el campo numero de factura para las facturas fuera de periodo
                                  'ctrl_number': iwdl_brw.invoice_id.nro_ctrl or "", # se agrega el campo numero de control para las facturas fuera de periodo
                                  'void_form': self.get_t_type(doc_type),
                                  'fiscal_printer': iwdl_brw.invoice_id.fiscal_printer or False,
                                  'z_report': iwdl_brw.invoice_id.z_report or False,
                                  }
                        data.append((0, 0, values))



        for inv_otro in inv_siva:
      #      if not self.browse(fb_id).iwdl_ids and iwdl_id == False:
            #if inv_otro.type == 'in_invoice':
                local_inv_affected = ' '
                people_type = 'N/A'

                doc_type = self.get_doc_type(inv_id=inv_otro.id)

                rp_brw = rp_obj._find_accounting_partner(inv_otro.partner_id)

                people_type = 'N/A'
                document_v = 'N/A'
                if rp_brw:
                    if rp_brw.company_type == 'company':
                        people_type = rp_brw.people_type_company
                        if people_type == 'pjdo':
                            document_v = rp_brw.vat
                    elif rp_brw.company_type == 'person':
                        people_type = rp_brw.people_type_individual
                        if rp_brw.nationality == 'V' or rp_brw.nationality == 'E':
                            document_v = str(rp_brw.nationality) + str(rp_brw.identification_id)
                        else:
                            document_v = rp_brw.identification_id

        #        iwdl_brw = iwdl_id if iwdl_id and iwdl_id not in no_match_dt_iwdl_ids else False
                local_inv_nbr = inv_otro.fiscal_printer and inv_otro.invoice_printer or (
                                fb_brw.type == 'sale' and
                                inv_otro.name or
                                inv_otro.supplier_invoice_number)
                if local_inv_nbr :
                    local_local = local_inv_nbr
                else:
                    local_local = inv_otro.name

                if (doc_type == "N/DB" or doc_type == "N/CR"):
                    if fb_brw.type == 'sale':
                        if inv_otro.type == 'out_refund':
                            cliente = True
                            if inv_otro.nro_ctrl:
                               busq1 = self.env['account.move'].search([('nro_ctrl', '=', inv_otro.nro_ctrl)])
                               if busq1:
                                   for busq2 in busq1:
                                       if busq2.type == 'out_refund':
                                            local_inv_affected = str(inv_otro.ref)[14:29] if inv_otro.ref else ''
                    elif inv_otro.type == 'in_refund':
                        proveedor = True
                        local_inv_affected = str(inv_otro.ref)[14:29] if inv_otro.ref else ''

                if doc_type == 'N/DB' or doc_type == 'N/CR':

                    sign = -1
                else:
                    sign = 1
                if (doc_type == "N/DB" or doc_type == "N/CR") and local_inv_affected:
                    boll = True
                else:
                    boll = False
                if boll == True:
                    fecha = inv_otro.date or inv_otro.invoice_date
                else:
                    fecha = fb_brw.fbl_ids.affected_invoice_date


                values = {
                    'invoice_id': inv_otro.id,
                    'emission_date':
                        (inv_otro.date or inv_otro.invoice_date) or
                        False,
                    'accounting_date':
                        inv_otro.invoice_date or
                        False,

                    'type': self.get_transaction_type(
                        fb_id, inv_otro.id),

                    'debit_affected': local_inv_nbr or False,
                    'credit_affected': local_inv_nbr and (cliente or proveedor or False),
                    'ctrl_number':
                        not inv_otro.fiscal_printer and
                        (inv_otro.nro_ctrl if inv_otro.nro_ctrl != 'False' else ''),
                    'affected_invoice': local_inv_affected,
                    'affected_invoice_date': fecha,
                    'partner_name': rp_brw.name or 'N/A',
                    'people_type': people_type,
                    'partner_vat': document_v,
                    'invoice_number':self.get_number(local_local),
                    'doc_type': doc_type,
                    #'void_form':
                    #    inv_otro.name and (
                    #            inv_otro.name.find('PAPELANULADO') >= 0 and
                    #            '03-ANU' or
                    #            '01-REG') or
                    #    '01-REG',
                    'void_form': self.get_t_type(doc_type, local_local),
                    'fiscal_printer': inv_otro.fiscal_printer or False,
                    'z_report': inv_otro.z_report or False,
                  #  'custom_statement': False,
                # inv_otro.customs_form_id.name or False,# TODO VALOR RELACIONADO CON MODULO l10n_ve_imex (importaciones)
                #     'iwdl_id': ' ',
                    # 'wh_number': ' ',
                    # 'get_wh_vat': iwdl_brw  and iwdl_brw.amount_tax_ret * sign or 0.0,
                    # 'wh_rate': iwdl_brw and iwdl_brw.wh_iva_rate or 0.0,
                }
                data.append((0, 0, values))


        if data:
            self.write({'fbl_ids': data})
            self.link_book_lines_and_taxes(fb_id)
        # if data2:
        #     self.write({'fbl_ids': data})
        #     self.link_book_lines_and_taxes(fb_id)

        if fb_brw.article_number in ['77', '78']:
            self.update_book_ntp_lines(fb_brw.id)
        else:
            self.order_book_lines(fb_brw.id)

        return True



    def get_grouped_consecutive_lines_ids(self, lines_ids):
        """ Return a list of tuples that represent every line in the book.
        If there is a group of consecutive Non-Tax Payer with fiscal printer
        billing lines, it will return a unique tuple that holds the information
        of the lines. The return tutple has this format
            ('invoice_number'[0], 'invoice_number'[-1], [line_brw])
            - 'invoice_number'[0]: invoice number of the first line in the
            group
            - 'invoice_number'[-1]: invoice number of the last line in the
            group
            - [line_brw] list o browse records that weel be into the line.
        @param line_ids: list of book lines ids.
        """

        lines_brws = self.env['fiscal.book.line'].browse(lines_ids)
        res = list()
        group_list = list()
        group_value = False

        for line_brw in lines_brws:
            group_value = group_value or line_brw.type
            if line_brw.type == group_value and group_value == 'ntp' and line_brw.fiscal_printer:
                group_list.append(line_brw)
            else:
                if group_list:
                    res.append((group_list[0].invoice_number,
                                group_list[-1].invoice_number, group_value,
                                group_list))
                    group_value = line_brw.type
                    group_list = [line_brw]
                else:
                    res.append((line_brw.invoice_number, line_brw.invoice_number, group_value, [line_brw]))
                    group_value = False

        if group_list:
            res.append((group_list[0].invoice_number, group_list[-1].invoice_number, group_value, group_list))

        return res

    def update_book_ntp_lines(self, fb_id):
        """ It consolidate Non-Tax Payer book lines into one line considering
        the consecutiveness and next criteria: fiscal printer and z report.
        This consolidated groups are move to another field: Non-Tax Payer
        Detail operations. (This only applys when is a sale book)
        @param fb_id: fiscal book id
        """

        fbl_obj = self.env['fiscal.book.line']
        fb_brw = self.browse(fb_id)

        # separating groups
        lines_brws = fb_brw.fbl_ids
        order_dict = dict()
        date_values = list(set([line_brw.emission_date for line_brw in lines_brws]))
        date_values.sort()
        order_dict = {}.fromkeys(date_values)
        for date in date_values:
            date_records = [line_brw for line_brw in lines_brws if line_brw.emission_date == date]
            printers_values = list(set([line_brw.fiscal_printer for line_brw in date_records]))
            printers_values.sort()
            order_dict[date] = {}.fromkeys(printers_values)
            for printer in printers_values:
                printer_records = [line_brw for line_brw in date_records
                                   if line_brw.fiscal_printer == printer]
                z_report_values = list(set([line_brw.z_report for line_brw in printer_records]))
                z_report_values.sort()
                order_dict[date][printer] = {}.fromkeys(z_report_values)
                for z_report in z_report_values:
                    # this records needs to be order by invoice number
                    z_records = [(line_brw.invoice_number, line_brw) for line_brw in printer_records
                                 if line_brw.z_report == z_report]
                    z_records.sort()
                    z_records = [item[1] for item in z_records]
                    # group by type of line
                    order_dict[date][printer][z_report] = self.get_grouped_consecutive_lines_ids(
                        [item.id for item in z_records])

        # import pprint
        # print 'order_dict'
        # pprint.pprint(order_dict)

        # agruping and ranking
        rank = 1
        # order_dict[date][printer][z_report] = [ ('desde', 'hasta', 'tipot',
        #                                          list(line_brws)) ]
        ntp_groups_list = list()
        # format [ ( rank, invoice_number, [line_brws] ) ]
        ntp_no_group_list = list()  # format [ ( rank, [line_brws] ) ]
        order_no_group_list = list()  # format [ ( rank, line_id ) ]

        order_dates = order_dict.keys()
        order_dates.sort()
        for date in order_dates:
            order_printers = order_dict[date].keys()
            order_printers.sort()
            for printer in order_printers:
                order_z_reports = order_dict[date][printer].keys()
                order_z_reports.sort()
                for z_report in order_z_reports:
                    for line in order_dict[date][printer][z_report]:
                        if line[2] == 'ntp':
                            if line[0] == line[1] and len(line[3]) == 1:
                                ntp_no_group_list.append(
                                    (rank, line[3][0]))
                                # (rank, line[3][0].id))
                            elif line[0] != line[1] and len(line[3]) > 1:
                                ntp_groups_list.append(
                                    (rank, 'Desde: ' + line[0] +
                                     ' ... Hasta: ' + line[1], line[3]))
                            else:
                                raise exceptions.except_orm("Error!", "Esta es una línea no válida. Asegúrate de que "
                                                           "tener dos o más facturas con el"
                                                           "mismo número de factura")
                        elif line[2] != 'ntp':
                            order_no_group_list.append(
                                # (rank, line[3][0].id))
                                (rank, line[3][0]))
                        rank += 1

        # import pprint
        # print '\n ntp_no_group_list'
        # pprint.pprint(ntp_no_group_list)
        # print '\n ntp_groups_list'
        # pprint.pprint(ntp_groups_list)
        # print '\n order_no_group_list'
        # pprint.pprint(order_no_group_list)

        # ~ # rank lines that have nothing to do with ntp.
        for line in order_no_group_list:
            line[1].write({'rank': line[0]})

        # ~ # rank ntp individual lines.
        for line in ntp_no_group_list:
            line[1].write({'rank': line[0], 'partner_name': 'No Contribuyente', 'partner_vat': False})

        # create consolidate line using ntp_groups_list list, move group lines
        # to Non-Tax Payer lines detail.
        for line_tuple in ntp_groups_list:
            consolidate_line_id = self.create_consolidate_line(fb_id, line_tuple)
            for rank, line_brw in enumerate(line_tuple[-1], 1):
                line_brw.write({'fb_id': False,
                                'ntp_fb_id': fb_id,
                                'parent_id': consolidate_line_id,
                                'rank': -1})

        return True

    def create_consolidate_line(self, fb_id, line_tuple):
        """ Create a new consolidate Non-Tax Payer line for a group of no tax
        payer operations.
        @param fb_id: fiscal book line id.
        @param line_tuple: tuple with the information for construct the
                          consolidate line (rank, [brws]).
                          # format [ ( rank, invoice_number, [line_brws] ) ]
        """

        fbl_obj = self.env['fiscal.book.line']
        float_colums = ['total_with_iva', 'vat_sdcf', 'vat_exempt',
                        'vat_reduced_base', 'vat_reduced_tax',
                        'vat_general_base', 'vat_general_tax',
                        'vat_additional_base', 'vat_additional_tax']

        rank, invoice_number, child_brws = line_tuple
        child_ids = [line_brw.id for line_brw in child_brws]
        first_item_brw = fbl_obj.browse(child_brws[0].id)
        # fill common value
        values = {
            'rank': rank,
            'invoice_number': invoice_number,
            'child_ids': [(6, 0, child_ids)],
            # 'fb_id': first_item_brw.fb_id.id,
            'partner_name': 'No Contribuyente',
            'people_type': first_item_brw.people_type.upper() if first_item_brw.people_type else '',
            'emission_date': first_item_brw.emission_date,
            'accounting_date': first_item_brw.accounting_date,
            'doc_type': first_item_brw.doc_type,
            'type': first_item_brw.type,
            'fiscal_printer': first_item_brw.fiscal_printer,
            'z_report': first_item_brw.z_report,
        }
        # fill totalization values
        for col in float_colums:
            values[col] = sum([getattr(line_brw, col) for line_brw in child_brws])

        return fbl_obj.create(values)

    def update_book_taxes_summary(self):
        """ It update the summaroty of taxes by type for this book.
        @param fb_id: fiscal book id
        """

        self.clear_book_taxes_summary()
    #    ait_obj = self.env['account.invoice.tax']
        tax_types = ['exento', 'sdcf', 'reducido', 'general', 'adicional']
        op_types = self.type == 'sale' and ['ex', 'tp', 'ntp'] or ['im', 'do']
        base_sum = {}.fromkeys(op_types)
        base =0
        amount = 0
        tax_sum = base_sum.copy()
        for op_type in op_types:
            tax_sum[op_type] = {}.fromkeys(tax_types, 0.0)
            base_sum[op_type] = {}.fromkeys(tax_types, 0.0)


        for fbl in self.fbl_ids:
            if fbl.report_z_id:
                hola = 'dfdfd'
                if fbl.report_z_id:
                    if float(fbl.report_z_id.base_imponible_ventas_iva_g) != 0:
                        base = float(fbl.report_z_id.base_imponible_ventas_iva_g) - float(fbl.report_z_id.bi_iva_g_en_nota_de_credito)
                        amount =  float(fbl.report_z_id.impuesto_iva_g) - float(fbl.report_z_id.impuesto_iva_g_en_nota_de_credito)
                        base_sum[fbl.type]['general'] += base
                        tax_sum[fbl.type]['general'] += amount
                    if float(fbl.report_z_id.base_imponible_ventas_iva_r) != 0:
                        base = float(fbl.report_z_id.base_imponible_ventas_iva_r) - float(fbl.report_z_id.bi_iva_r_en_nota_de_credito)
                        amount = float(fbl.report_z_id.impuesto_iva_r) - float(fbl.report_z_id.impuesto_iva_r_en_nota_de_credito)
                        base_sum[fbl.type]['reducido'] += base
                        tax_sum[fbl.type]['reducido'] += amount
                    if float(fbl.report_z_id.base_imponible_ventas_iva_a) != 0:
                        base = float(fbl.report_z_id.base_imponible_ventas_iva_a) - float(fbl.report_z_id.bi_iva_a_en_nota_de_credito)
                        amount = float(fbl.report_z_id.impuesto_iva_a) - float(fbl.report_z_id.impuesto_iva_a_en_nota_de_credito)
                        base_sum[fbl.type]['adicional'] += base
                        tax_sum[fbl.type]['adicional'] += amount
                    if  float(fbl.report_z_id.ventas_exento) != 0:
                        base = float(fbl.report_z_id.ventas_exento) - float(fbl.report_z_id.nota_de_credito_exento)
                        base_sum[fbl.type]['exento'] += base

            if fbl.iwdl_id.invoice_id:
                sign = 1 if fbl.doc_type != 'N/CR' else -1
                for ait in fbl.iwdl_id.tax_line:
                    busq = self.env['account.tax'].search([('id', '=', ait.id_tax)])
                    if busq:
                        if busq.appl_type:
                            base_sum[fbl.type][busq.appl_type] += ait.base * sign
                            tax_sum[fbl.type][busq.appl_type] += ait.amount * sign
                        else:
                            raise exceptions.except_orm("Advertencia!", "En los impuestos no se encuentra el Tipo de Alicuota por favor colocar para proceder")

            elif fbl.invoice_id:
                sign = 1 if fbl.doc_type != 'N/CR' else -1
                for line in fbl.invoice_id.invoice_line_ids:
                    for tax in line.tax_ids:
                        busq = tax.appl_type
                        if busq:
                            base_sum[fbl.type][busq] += line.price_subtotal * sign
                            tax_sum[fbl.type][busq] += (line.price_total - line.price_subtotal) * sign
                        else:
                            raise exceptions.except_orm("Advertencia!", "En los impuestos no se encuentra el Tipo de Alicuota por favor colocar para proceder")




        data = [(0, 0, {'tax_type': ttype, 'op_type': optype,
                        'base_amount_sum': base_sum[optype][ttype],
                        'tax_amount_sum': tax_sum[optype][ttype]
                        })
                for ttype in tax_types
                for optype in op_types
                ]
        return data and self.write({'fbts_ids': data})

    def update_book_taxes_amount_fields(self):
        """ It update the base_amount and the tax_amount field for book, and
        extract data from the book tax summary to store fields inside the
        book model.
        @param fb_id: fiscal book id
        """
  #      ait_obj = self.env['account.invoice.tax']
        data = {}
        # totalization of book tax amount and base amount fields
        tax_amount = 0.0
        base_amount = 0.0
        for fbl_brw in self.fbl_ids:
            sign = 1 if fbl_brw.doc_type != 'N/CR' else -1

            if fbl_brw.report_z_id:
                if float(fbl_brw.report_z_id.base_imponible_ventas_iva_g) != 0:
                    base = float(fbl_brw.report_z_id.base_imponible_ventas_iva_g) - float(fbl_brw.report_z_id.bi_iva_g_en_nota_de_credito)
                    amount = float(fbl_brw.report_z_id.impuesto_iva_g) - float(fbl_brw.report_z_id.impuesto_iva_g_en_nota_de_credito)
                    base_amount += base
                    tax_amount += amount


            if fbl_brw.iwdl_id.invoice_id:
                for ait in fbl_brw.iwdl_id.tax_line:
                    base_amount += ait.base * sign
                    tax_amount += ait.amount * sign
            if fbl_brw.invoice_id:
                for line in fbl_brw.invoice_id.invoice_line_ids:
                    base_amount += line.price_subtotal * sign
                    tax_amount += (line.price_total-line.price_subtotal) * sign

        data['tax_amount'] = tax_amount
        data['base_amount'] = base_amount

        # totalization of book taxable and taxed amount for every tax type and
        # operation type
        vat_fields = [
            'imex_exempt_vat_sum',
            'imex_sdcf_vat_sum',
            'imex_general_vat_base_sum',
            'imex_general_vat_tax_sum',
            'imex_additional_vat_base_sum',
            'imex_additional_vat_tax_sum',
            'imex_reduced_vat_base_sum',
            'imex_reduced_vat_tax_sum',
            'do_exempt_vat_sum',
            'do_sdcf_vat_sum',
            'do_general_vat_base_sum',
            'do_general_vat_tax_sum',
            'do_additional_vat_base_sum',
            'do_additional_vat_tax_sum',
            'do_reduced_vat_base_sum',
            'do_reduced_vat_tax_sum',
            'tp_exempt_vat_sum',
            'tp_sdcf_vat_sum',
            'tp_general_vat_base_sum',
            'tp_general_vat_tax_sum',
            'tp_additional_vat_base_sum',
            'tp_additional_vat_tax_sum',
            'tp_reduced_vat_base_sum',
            'tp_reduced_vat_tax_sum',
            'ntp_exempt_vat_sum',
            'ntp_sdcf_vat_sum',
            'ntp_general_vat_base_sum',
            'ntp_general_vat_tax_sum',
            'ntp_additional_vat_base_sum',
            'ntp_additional_vat_tax_sum',
            'ntp_reduced_vat_base_sum',
            'ntp_reduced_vat_tax_sum',
        ]
        for field_name in vat_fields:
            data[field_name] = self.update_vat_fields(field_name)

        # more complex totalization amounts.
        # fb_brw = self.browse( fb_id)

        data['do_sdcf_and_exempt_sum'] = self.type == 'sale' \
                                         and (data['tp_exempt_vat_sum'] + data['tp_sdcf_vat_sum'] +
                                              data['ntp_exempt_vat_sum'] + data['ntp_sdcf_vat_sum']) \
                                         or (data['do_exempt_vat_sum'] + data['do_sdcf_vat_sum'])

        for optype in ['imex', 'do', 'tp', 'ntp']:
            data[optype + '_vat_base_sum'] = sum([data[optype + '_' + ttax + "_vat_base_sum"]
                                                  for ttax in ["general", "additional", "reduced"]])

        data['imex_vat_base_sum'] += data['imex_exempt_vat_sum'] + data['imex_sdcf_vat_sum']

        # sale book domestic fields transformations (ntp and tp sums)
        if self.type == 'sale':
            data["do_vat_base_sum"] = data["tp_vat_base_sum"] + data["ntp_vat_base_sum"]

            for ttax in ["general", "additional", "reduced"]:
                for amttype in ["base", "tax"]:
                    data['do_' + ttax + '_vat_' + amttype + '_sum'] = sum(
                        [data[optype + "_" + ttax + "_vat_" + amttype + "_sum"]
                         for optype in ["ntp", "tp"]])
            for ttax in ["exempt", "sdcf"]:
                data['do_' + ttax + '_vat_sum'] = \
                    sum([data[optype + "_" + ttax + "_vat_sum"]
                         for optype in ["ntp", "tp"]
                         ])

        return self.write(data)

    def update_vat_fields(self, field_name):
        """ It returns summation of a fiscal book tax column (Using
        fiscal.book.taxes.summary).

        """

        res = 0.0
        fbts_obj = self.env['fiscal.book.taxes.summary']

        # Identifying the field
        field_info = field_name[:-4].split('_')
        field_info.remove('vat')

        field_op, field_tax, field_amount = (len(field_info) == 3) \
                                            and field_info \
                                            or field_info + ['base']

        # Translation between the fb fields names and the fbts records data.
        tax_type = {'exempt': 'exento', 'sdcf': 'sdcf', 'reduced': 'reducido',
                    'general': 'general', 'additional': 'adicional'}
        amount_type = {'base': 'base_amount_sum', 'tax': 'tax_amount_sum'}


        for fbts_brw in self.fbts_ids:

            if fbts_brw.tax_type == tax_type[field_tax]:
                res = getattr(fbts_brw, amount_type[field_amount])
        return res

    def link_book_lines_and_taxes(self, fb_id):
        """ Updates the fiscal book taxes. Link the tax with the corresponding
        book line and update the fields of sum taxes in the book.
        @param fb_id: the id of the current fiscal book """

        #        fbl_obj = self.env['fiscal.book.line']
 #       ait_obj = self.env['account.invoice.tax']
        ut_obj = self.env['l10n.ut']
        fbt_obj = self.env['fiscal.book.taxes']
        # write book taxes
        data = []
        tax_data = {}
        exento = 0.0
        base_exento = 0
        amount = 0
        name = ' '
        base = 0
        fiscal_book = self.browse(fb_id)
        for fbl in fiscal_book.fbl_ids:
            if fbl.report_z_id:
                fiscal_taxes = self.env['fiscal.book.taxes']
                line_taxes = {'fb_id': fb_id, 'fbl_id': fbl.id, 'base_amount': 0.0, 'tax_amount': 0.0, 'name': ' ', 'exento':0 }
                sum_base_imponible = 0
                amount_field_data = {'total_with_iva':
                                         0.0,
                                     'vat_sdcf': 0.0, 'vat_exempt': 0.0, 'vat_general_base': 0.0, }


                if float(fbl.report_z_id.base_imponible_ventas_iva_g) != 0:
                    base = float(fbl.report_z_id.base_imponible_ventas_iva_g) - float(fbl.report_z_id.bi_iva_g_en_nota_de_credito)
                    amount = float(fbl.report_z_id.impuesto_iva_g) - float(fbl.report_z_id.impuesto_iva_g_en_nota_de_credito)
                    name = 'IVA 16%'
                if float(fbl.report_z_id.ventas_exento) != 0:
                    amount_field_data['vat_exempt'] += float(fbl.report_z_id.ventas_exento) - float(fbl.report_z_id.nota_de_credito_exento)
                    base_exento = float(fbl.report_z_id.ventas_exento) - float(fbl.report_z_id.nota_de_credito_exento)


                if float(fbl.report_z_id.base_imponible_ventas_iva_r) != 0:
                    base = float(fbl.report_z_id.base_imponible_ventas_iva_r) - float(fbl.report_z_id.bi_iva_r_en_nota_de_credito)
                    amount = float(fbl.report_z_id.impuesto_iva_r) - float(fbl.report_z_id.impuesto_iva_r_en_nota_de_credito)
                    name = 'IVA 8%'
                if float(fbl.report_z_id.base_imponible_ventas_iva_a) != 0:
                    base = float(fbl.report_z_id.base_imponible_ventas_iva_a) - float(fbl.report_z_id.bi_iva_a_en_nota_de_credito)
                    amount = float(fbl.report_z_id.impuesto_iva_a) - float(fbl.report_z_id.impuesto_iva_a_en_nota_de_credito)
                    name = 'IVA 31%'
                amount_field_data['total_with_iva'] += (amount + base)

                amount_field_data['vat_general_base'] += base


                line_taxes.update({'fb_id': fb_id,
                                   'fbl_id': fbl.id,
                                   'base_amount': amount_field_data['vat_general_base'],
                                   'tax_amount': amount,
                                   'name': name,
                                   'exento': base_exento,
                                   'type': fiscal_book.type})

                fbl.write(amount_field_data)

                if line_taxes:
                    fiscal_taxes.create(line_taxes)

                else:
                    data.append((0, 0, {'fb_id': fb_id,
                                        'fbl_id': fbl.id,

                                        }))
                    self.write({'fbt_ids': data})
                amount = base = base_exento = 0
                name = ' '
            ####################################### antes es report z#########################

            if fbl.iwdl_id.invoice_id:

                fiscal_taxes = self.env['fiscal.book.taxes']
                line_taxes = {'fb_id': fb_id, 'fbl_id': fbl.id, 'base_amount': 0.0, 'tax_amount': 0.0, 'name': ' ', }
                fiscal_book = self.browse(fb_id)
                f_xc = ut_obj.sxc(
                    fbl.iwdl_id.invoice_id.currency_id.id,
                    fbl.iwdl_id.invoice_id.company_id.currency_id.id,
                    fbl.iwdl_id.invoice_id.invoice_date)
                if fbl.doc_type == 'N/CR' or fbl.doc_type == 'N/DB':
                    sign = -1
                else:
                    sign = 1
                sum_base_imponible = 0
                amount_field_data = {'total_with_iva':
                                        0.0,
                                     'vat_sdcf': 0.0, 'vat_exempt': 0.0, 'vat_general_base': 0.0,}

                for ait in fbl.iwdl_id.tax_line:
                    busq = self.env['account.tax'].search([('id', '=', ait.id_tax)])
                    if busq:
                        if ait.amount == 0:
                            base = ait.base
                            name = ait.name
                            amount_field_data['vat_exempt'] += exento * sign
                        else:
                            base = ait.base
                            amount = ait.amount
                            name = ait.name
                        if (ait.amount + ait.base) > 0:
                            amount_field_data['total_with_iva'] += (ait.amount + ait.base)* sign
                            if busq.appl_type == 'sdcf':
                                    amount_field_data['vat_sdcf'] += base * sign
                            if busq.appl_type == 'exento':
                                amount_field_data['vat_exempt'] += base * sign
                            if busq.appl_type == 'general':
                                amount_field_data['vat_general_base'] += base * sign

                        tax_data.update({'fb_id': fb_id,
                                         'fbl_id': fbl.id,
                                        # 'ait_id': busq.id,
                                         'base_amount': amount_field_data['vat_general_base'],
                                         'tax_amount': ait.amount})

                        line_taxes.update({'fb_id': fb_id,
                                           'fbl_id': fbl.id,
                                           'base_amount':  base,
                                           'tax_amount': amount,
                                           'name': name,
                                           'type': fiscal_book.type

                                           })
                    fbl.write(amount_field_data)
                    if line_taxes:
                        fiscal_taxes.create(line_taxes)
                    else:
                        data.append((0, 0, {'fb_id': fb_id,
                                            'fbl_id': fbl.id,

                                            }))
                        self.write({'fbt_ids': data})


            if fbl.invoice_id:
                fiscal_book = self.browse(fb_id)
                fiscal_taxes = self.env['fiscal.book.taxes']
                line_taxes = {'fb_id': fb_id, 'fbl_id': fbl.id,'base_amount': 0.0 , 'tax_amount': 0.0, 'name': ' ',}
                f_xc = ut_obj.sxc(
                    fbl.invoice_id.currency_id.id,
                    fbl.invoice_id.company_id.currency_id.id,
                    fbl.invoice_id.invoice_date)
                busq = ' '
                if fbl.doc_type == 'N/CR' or fbl.doc_type == 'N/DB':
                    sign = -1
                else:
                    sign = 1
                sum_base_imponible = 0
                amount_field_data = {'total_with_iva':
                                         0.0,
                                     'vat_sdcf': 0.0, 'vat_exempt': 0.0, 'vat_general_base': 0.0, }


                for line in fbl.invoice_id.invoice_line_ids:
                    amount = 0
                    base = 0
                    busq =  ''
                    tax = ' '

                    for tax in line.tax_ids:
                        busq = tax.appl_type
                        name = tax.name
                    if busq:
                        if (line.price_total - line.price_subtotal) == 0:
                            base = line.price_subtotal
                            amount = 0
                            amount_field_data['vat_exempt'] += exento * sign
                        else:
                            base = (line.price_subtotal)
                            amount = (line.price_total - line.price_subtotal)

                        if ((line.price_total - line.price_subtotal) == 0 or (line.price_total - line.price_subtotal) > 0) and line.price_total > 0:
                            amount_field_data['total_with_iva'] += line.price_total * sign
                            if busq == 'sdcf':
                                amount_field_data['vat_sdcf'] += base * sign
                            if busq == 'exento':
                                amount_field_data['vat_exempt'] += base * sign
                            if busq == 'general':
                                amount_field_data['vat_general_base'] += base * sign

                        tax_data.update({'fb_id': fb_id,
                                         'fbl_id': fbl.id,
                                    #     'ait_id': fbl.id,
                                         'base_amount': base,
                                         'tax_amount': amount})

                        line_taxes.update({'fb_id': fb_id,
                                           'fbl_id': fbl.id,
                                           'base_amount': base,
                                           'tax_amount':amount,
                                           'name': name,
                                           'type': fiscal_book.type

                        })

                    fbl.write(amount_field_data)
                    if line_taxes:
                        fiscal_taxes.create(line_taxes)
                    else:
                        data.append((0, 0, {'fb_id': fb_id,
                                            'fbl_id': fbl.id,

                                            }))
                        self.write({'fbt_ids': data})




        self.update_book_taxes_summary()
        self.update_book_lines_taxes_fields()
        self.update_book_taxes_amount_fields()
        return True

    def update_book_lines_taxes_fields(self):
        """ Update taxes data for every line in the fiscal book given,
        extrating de data from the fiscal book taxes associated.
        @param fb_id: fiscal book line id.
        """
        tax_amount = 0
        fbl_obj = self.env['fiscal.book.line']
        field_names = ['vat_reduced_base', 'vat_reduced_tax',
                       'vat_general_base', 'vat_general_tax',
                       'vat_additional_base', 'vat_additional_tax']
        tax_type = {'reduced': 'reducido', 'general': 'general',
                    'additional': 'adicional'}
        for fbl_brw in self.fbl_ids:
            if fbl_brw.doc_type == 'N/CR' or fbl_brw.doc_type == 'N/DB':
                sign = -1
            else:
                sign = 1
            data = {}.fromkeys(field_names, 0.0)
            busq = ' '
            if fbl_brw.report_z_id:

                for field_name in field_names:
                    field_tax, field_amount = field_name[4:].split('_')

                    if field_tax == 'general' and (field_amount == 'base' or field_amount == 'tax'):
                        if float(fbl_brw.report_z_id.base_imponible_ventas_iva_g) != 0:
                            base = float(fbl_brw.report_z_id.base_imponible_ventas_iva_g) - float(fbl_brw.report_z_id.bi_iva_g_en_nota_de_credito)
                            tax_amount = float(fbl_brw.report_z_id.impuesto_iva_g) - float(fbl_brw.report_z_id.impuesto_iva_g_en_nota_de_credito)
                            data[field_name] += field_amount == 'base' and base \
                                            or tax_amount
                    if field_tax  == 'reduced' and (field_amount == 'base' or field_amount == 'tax'):
                        if float(fbl_brw.report_z_id.base_imponible_ventas_iva_r) != 0:
                            base = float(fbl_brw.report_z_id.base_imponible_ventas_iva_r) - float(fbl_brw.report_z_id.bi_iva_r_en_nota_de_credito)
                            tax_amount = float(fbl_brw.report_z_id.impuesto_iva_r) - float(fbl_brw.report_z_id.impuesto_iva_r_en_nota_de_credito)
                            data[field_name] += field_amount == 'base' and base \
                                                or tax_amount
                    if field_tax == 'additional' and (field_amount == 'base' or field_amount == 'tax'):
                        if float(fbl_brw.report_z_id.base_imponible_ventas_iva_a) != 0:
                            base = float(fbl_brw.report_z_id.base_imponible_ventas_iva_a) - float(fbl_brw.report_z_id.bi_iva_a_en_nota_de_credito)
                            tax_amount = float(fbl_brw.report_z_id.impuesto_iva_a) - float(fbl_brw.report_z_id.impuesto_iva_a_en_nota_de_credito)
                            data[field_name] += field_amount == 'base' and base \
                                                or tax_amount
                fbl_brw.write(data)

            if fbl_brw.iwdl_id.invoice_id:

               for line in fbl_brw.iwdl_id.invoice_id.invoice_line_ids:
                   for tax in line.tax_ids:
                       busq = tax.appl_type

                   for field_name in field_names:
                        field_tax, field_amount = field_name[4:].split('_')
                        base = line.price_subtotal
                        tax_amount = (line.price_total - line.price_subtotal)
                        if busq:
                            if busq == tax_type[field_tax]:
                                    data[field_name] += field_amount == 'base' and base * sign \
                                                        or tax_amount * sign
               fbl_brw.write(data)

            if fbl_brw.invoice_id:
                for line in fbl_brw.invoice_id.invoice_line_ids:
                    for tax in line.tax_ids:
                        busq = tax.appl_type
                    for field_name in field_names:
                        field_tax, field_amount = field_name[4:].split('_')
                        base = line.price_subtotal
                        tax_amount = (line.price_total - line.price_subtotal)
                        if busq:
                            if busq == tax_type[field_tax]:  # account.tax
                                # if not fbt_brw.fbl_id.iwdl_id.invoice_id.name: #facura de account.wh.iva.line
                                #     data[field_name] += field_amount == 'base' and (
                                #         fbt_brw.fbl_id.invoice_id.factura_id.amount_gravable if fbt_brw.base_amount == 0 else fbt_brw.base_amount) * sign \
                                #                         or fbt_brw.tax_amount * sign
                                # else:
                                data[field_name] += field_amount == 'base' and base * sign \
                                                    or tax_amount * sign

                fbl_brw.write(data)
        return True

    # clear book methods

    
    def clear_book(self):
        # def clear_book(self,  fb_id):
        """ It delete all book data information.
        @param fb_id: fiscal book line id
        """
        self.clear_book_taxes_amount_fields()
        # delete data
        self.clear_book_lines()
        self.clear_book_taxes()
        self.clear_book_taxes_summary()
        # unrelate data
        self.clear_book_invoices()
        self.clear_book_issue_invoices()
        self.clear_book_iwdl_ids()

    
    def clear_book_lines(self):
        """ It delete all book lines loaded in the book """
        for fbl in self.fbl_ids:
            fbl.unlink()
        # self.clear_book_taxes_amount_fields()
        return True

    
    def clear_book_taxes(self):
        """ It delete all book taxes loaded in the book """
        for fbt in self.fbt_ids:
            fbt.unlink()
        # self.clear_book_taxes_amount_fields()
        return

    
    def clear_book_taxes_summary(self):
        """ It delete fiscal book taxes summary data for the book """
        # context = self.env.context and {k:v for k,v in self.env.context.items()} or {}
        # cr = self.env.cr
        # ids = self.ids
        # uid = self.env.uid
        fbts_obj = self.env['fiscal.book.taxes.summary']
        # fb_id = isinstance(fb_id, (int, long)) and [fb_id] or fb_id
        fbts_ids = fbts_obj.search([('fb_id', 'in', [self.id])])
        # fbts_obj.unlink(fbts_ids)
        for fbts in fbts_ids:
            # if fbts_ids:
            fbts.unlink()
        return

    
    def clear_book_taxes_amount_fields(self):
        # def clear_book_taxes_amount_fields(self,  fb_id):
        """ Clean amount taxes fields in fiscal book """
        vat_fields = [
            'tax_amount',
            'base_amount',
            'imex_vat_base_sum',
            'imex_exempt_vat_sum',
            'imex_sdcf_vat_sum',
            'imex_general_vat_base_sum',
            'imex_general_vat_tax_sum',
            'imex_additional_vat_base_sum',
            'imex_additional_vat_tax_sum',
            'imex_reduced_vat_base_sum',
            'imex_reduced_vat_tax_sum',
            'do_vat_base_sum',
            'do_exempt_vat_sum',
            'do_sdcf_vat_sum',
            'do_general_vat_base_sum',
            'do_general_vat_tax_sum',
            'do_additional_vat_base_sum',
            'do_additional_vat_tax_sum',
            'do_reduced_vat_base_sum',
            'do_reduced_vat_tax_sum',
            'tp_vat_base_sum',
            'tp_exempt_vat_sum',
            'tp_sdcf_vat_sum',
            'tp_general_vat_base_sum',
            'tp_general_vat_tax_sum',
            'tp_additional_vat_base_sum',
            'tp_additional_vat_tax_sum',
            'tp_reduced_vat_base_sum',
            'tp_reduced_vat_tax_sum',
            'ntp_vat_base_sum',
            'ntp_exempt_vat_sum',
            'ntp_sdcf_vat_sum',
            'ntp_general_vat_base_sum',
            'ntp_general_vat_tax_sum',
            'ntp_additional_vat_base_sum',
            'ntp_additional_vat_tax_sum',
            'ntp_reduced_vat_base_sum',
            'ntp_reduced_vat_tax_sum',
        ]

        # return self.write( fb_id, {}.fromkeys(vat_fields, 0.0))
        return self.write({}.fromkeys(vat_fields, 0.0))

    
    def clear_book_invoices(self):
        """ Unrelate all invoices of the book. And delete fiscal book taxes """
        self.clear_book_taxes()
        for inv in self.invoice_ids:
            inv.write({'fb_id': False})
        return True

    
    def clear_book_issue_invoices(self):
        """ Unrelate all issue invoices of the book """
        for is_inv in self.issue_invoice_ids:
            is_inv.write({'issue_fb_id': False})
        return True


    
    def clear_book_iwdl_ids(self):
        """ Unrelate all wh iva lines of the book. """
        for iwdl in self.iwdl_ids:
            iwdl.write({'fb_id': False})
        return True

    def get_doc_type(self, inv_id=None, iwdl_id=None, cf_id=None):
        """ Returns a string that indicates de document type. For withholding
        returns 'AJST' and for invoice docuemnts returns different values
        depending of the invoice type: Debit Note 'N/DB', Credit Note 'N/CR',
        Invoice 'FACT'.
        @param inv_id : invoice id
        @param iwdl_id: wh iva line id
        """

        res = False
        # if fb_id:
        #    obj_fb = self.env['fiscal.book']
        #    fb_brw = obj_fb.browse( fb_id)
        if inv_id:
            inv_obj = self.env['account.move']
            inv_brw = inv_obj.browse(inv_id)
            if  inv_brw.type in ["in_refund"]:
                res = "N/DB"
            elif  inv_brw.type in ["out_refund"]:
                res = "N/CR"
            elif inv_brw.type in ["in_invoice", "out_invoice"]:
                res = "FACT"

            assert res, str(inv_brw) + ": Error in the definition \
                of the document type. \n There is not type category definied for \
                your invoice."
        elif iwdl_id:
            res = 'AJST' if self.type == 'sale' else 'RET'
        # TODO CONDICION RELACIONADO CON ELMODELO customs.form DEL MODULO l10n_ve_imex
        #        elif cf_id:
        #            res = 'F/IMP'

        return res

    def get_invoice_import_form(self, inv_id):
        """ Returns the Invoice reference
        @param inv_id: invoice id
        """

        inv_obj = self.env['account.move']
        inv_brw = inv_obj.browse(inv_id)
        return inv_brw.reference or False



    # TODO FUNCION RELACIONADO CON MODULO l10n_ve_imex (importaciones)
    def get_transaction_type(self, fb_id, inv_id):
        """ Method that returns the type of the fiscal book line related to the
        given invoice by cheking the customs form associated and the fiscal
        book type.
        @param fb_id: fiscal book id
        @param inv_id: invoice id
        """

        inv_obj = self.env['account.move']
        inv_brw = inv_obj.browse(inv_id)
        fb_brw = self.browse(fb_id)
        # TODO VALOR RELACIONADO CON MODULO l10n_ve_imex (importaciones)
        # if inv_brw.customs_form_id:
        #    return 'ex' if fb_brw.type == 'sale' else 'im'
        # else:
        if fb_brw.type == 'purchase':
            return 'do'
        else:
            return 'tp' if inv_brw.partner_id.vat_subjected else 'ntp'

    
    def unlink(self):
        """ Overwrite the unlink method to throw an exception if the book is
        not in cancel state."""
        
        for fb_brw in self.browse(self.ids):
            if fb_brw.state != 'cancel':
                raise UserError(_("Invalid Procedure!! \nYour book needs to be in cancel state to be deleted."))
            else:
                res = super(FiscalBook, self).unlink()
        return res


class FiscalBookLines(models.Model):
    TYPE = [('im', 'Imports'),
            ('do', 'Domestic'),
            ('ex', 'Exports'),
            ('tp', 'Tax Payer'),
            ('ntp', 'Non-Tax Payer')]

    
    def _get_wh_vat(self, fb_id):
        """ For a given book line it returns the vat withholding amount.
        """

        res = {}.fromkeys(self._ids, 0.0)
        for fbl_brw in self.search([('fb_id', '=', fb_id)]):
            sign = 1 if fbl_brw.doc_type != 'AJST' else -1
            if fbl_brw.iwdl_id:
                res[fbl_brw.id] = fbl_brw.iwdl_id.amount_tax_ret * sign
        return res

    @api.model
    def _get_based_tax_debit(self):
        """ It Returns the sum of all tax amount for the taxes realeted to the
        wh iva line.
        @param field_name: ['get_based_tax_debit'].
        """
        # TODO: for all taxes realted? only a tax type group?

        res = {}.fromkeys(self._ids, 0.0)

        for fbl_brw in self.browse():
            if fbl_brw.create_date != False:
                if fbl_brw.iwdl_id:
                    sign = 1 if fbl_brw.doc_type != 'AJST' else -1
                    for tax in fbl_brw.iwdl_id.tax_line:
                        res[fbl_brw.id] += tax.amount * sign
        return res

    def _compute_vat_rates(self, ids, field_name, arg):
        res = {}
        for item in self.browse(ids):
            res[item.id] = {
                'vat_reduced_rate': item.vat_reduced_base and
                                    item.vat_reduced_tax * 100 / item.vat_reduced_base,
                'vat_general_rate': item.vat_general_base and
                                    item.vat_general_tax * 100 / item.vat_general_base,
                'vat_additional_rate': item.vat_additional_base and
                                       item.vat_additional_tax * 100 / item.vat_additional_base,
            }
        return res


    _description = "Venta y compra de líneas de libros fiscales en Venezuela"
    _name = 'fiscal.book.line'
    _rec_name = 'rank'
    #_order = 'parent_id, rank'
 #   _parent_store = "True"
    base = fields.Float('base')
    amount =fields.Float('amount')
    name = fields.Char("Líneas de libros fiscales")
    fb_id = fields.Many2one('fiscal.book', 'Fiscal Book',
                            help='Libro fiscal que posee esta línea de libro', ondelete='cascade', index=True)
    ntp_fb_id = fields.Many2one("fiscal.book", "Detalle no contribuyente",
                                help="Detalle no contribuyente"
                                     " Este libro es solo para líneas que no pagan impuestos")
    fbt_ids = fields.One2many('fiscal.book.taxes', 'fbl_id', string='Lineas de impuestos',
                              help="Líneas fiscales que se registran en un libro fiscal")
    invoice_id = fields.Many2one('account.move', 'Factura',
                                 help="Factura relacionada con esta línea de libro")
    iwdl_id = fields.Many2one('account.wh.iva.line', 'Retencion de IVA',
                              help="Retención de la línea iva relacionada con esta línea del libro")
    report_z_id = fields.Many2one('datos.zeta.diario', 'reportes z ids')
    n_ultima_factZ = fields.Char('Numero de Ultima Factura')
    # TODO CAMPO RELACIONADO CON EL MODELO customs.form DEL MODULO l10n_ve_imex
    # cf_id = fields.Many2one('customs.form', 'Customs Form',
    #        help="Customs Form being recorded to this book line")
    parent_id = fields.Many2one("fiscal.book.line", string="Linea consolidada",
                                ondelete='cascade', help="Línea consolidada no contribuyente. Indique la identificación de la"
                                                         "línea consolidada a la que pertenece esta línea de contribuyente")
    parent_left = fields.Integer('Padre izquierdo', select=1)
    parent_right = fields.Integer('Padre Derecho', select=1)
    child_ids = fields.One2many("fiscal.book.line", "parent_id", string="Línea de detalle para no contribuyentes",
                                help="Grupo no contribuyente de líneas de libros que representa esta línea")

    #  Invoice and/or Document Data
    rank = fields.Integer("Line", required=True, default=0, help="Line Position")
    emission_date = fields.Date(string='Fecha de emisión', help='Fecha del documento de factura / Fecha del comprobante de línea de IVA')
    accounting_date = fields.Date(string='Fecha Contable',
                                  help="El día del registro contable [(factura, fecha de factura), "
                                       "(línea de retencion de IVA, Fecha de retencion)]")
    doc_type = fields.Char('Tipo de Documento', size=9, help='Tipo de Documento')
    partner_name = fields.Char(size=128, string='Nombre de la Empresa', help='')
    people_type = fields.Char(string='Tipo de Persona', help='')
    partner_vat = fields.Char(size=128, string='Nro. RIF', help='')
    affected_invoice = fields.Char(string='Factura Afectada', size=64,
                                   help="Para un tipo de línea de factura significa factura principal para un Débito "
                                        "o Nota de crédito. Para un tipo de línea de retención se entiende la factura"
                                        "número relacionado con la retención")
    # Apply for wh iva lines
    get_wh_vat = fields.Float(string="Retención de IVA", help="Retención de IVA")
    wh_number = fields.Char(string='Nro de  Comprobante de Retención', size=64, help="")
    affected_invoice_date = fields.Date(string="Fecha de factura Afectada", help="")
    wh_rate = fields.Float(string="Porcentaje de retención", help="")
    get_wh_debit_credit = fields.Float(compute='_get_based_tax_debit',
                                       method=True, store=True,
                                       string="Base Debito Fiscal",
                                       help="Suma de toda la cantidad de impuestos para los impuestos relacionados con la línea de retencion de IVA")

    # Apply for invoice lines
    ctrl_number = fields.Char(string='Nro de Control de Factura', size=64, help='')
    invoice_number = fields.Char(string='Nro de Factura', size=64, help='')
    # TODO chequear la necesidad de este camp. Esta reñacionado con imex?
    imex_date = fields.Date(string='Fecha Imex', help='Fecha de importacion/exportacion de Facturas')
    debit_affected = fields.Char(string='Notas de débito afectadas', size=256, help='Notas de débito afectadas')
    credit_affected = fields.Char(string='Notas de crédito afectadas', size=256, help='Notas de crédito afectadas')
    type = fields.Selection(TYPE, string='Tipo de Transaccion', required=True, help="")
    void_form = fields.Char(string='Tipo de Transaccion', size=192, help="Tipo de Operacion")
    fiscal_printer = fields.Char(string='Nro de Maquina Fiscal', size=192, help="")
    z_report = fields.Char(string='Reporte Z', size=64, help="")
    custom_statement = fields.Char(string="Declaracion Personalizada",
                                   size=192, help="")
    # -- taxes fields
    total_with_iva = fields.Float('Total con IVA', help="Sub Total of the invoice (untaxed amount) plus"
                                                         " all tax amount of the related taxes")
    vat_sdcf = fields.Float("SDCF", help="Not entitled to tax credit (The field name correspond to the"
                                         " spanih acronym for 'Sin Derecho a Credito Fiscal')")
    vat_exempt = fields.Float("Exento", help="Exempt is a Tax with 0 tax percentage")
    vat_reduced_base = fields.Float("Base Reducido", help="Vat Reduced Base Amount")
    vat_reduced_tax = fields.Float("IVA Reducido", help="Vat Reduced Tax Amount")
    vat_general_base = fields.Float("Base Imponible", help="Vat General Base Amount")
    vat_general_tax = fields.Float("IVA", help="Vat General Tax Amount")
    vat_additional_base = fields.Float("Base Adicional", help="Vat Generald plus Additional Base Amount")
    vat_additional_tax = fields.Float("IVA Adicional", help="Vat General plus Additional Tax Amount")
    vat_reduced_rate = fields.Float(compute='_compute_vat_rates',
                                    method=True, string='Alicuota Reducida', #multi='all',
                                    help="IVA reducido tipo impositivo")
    vat_general_rate = fields.Float(compute='_compute_vat_rates',
                                    method=True,
                                    string='Alicuota general', # multi='all',
                                    help="Tasa de impuesto general del IVA")
    vat_additional_rate = fields.Float(compute='_compute_vat_rates',
                                       method=True,
                                       string='Alicuota Adicional', #multi='all',
                                       help="IVA más tasa impositiva adicional ")


class FiscalBookTaxes(models.Model):
    _description = "Venezuela's Sale & Purchase Fiscal Book Taxes"
    _name = 'fiscal.book.taxes'
  #  _rec_name = 'ait_id'

    fb_id = fields.Many2one('fiscal.book', 'Fiscal Book', help='Fiscal Book where this tax is related to')
    fbl_id = fields.Many2one('fiscal.book.line', 'Fiscal Book Lines',
                             help='Fiscal Book Lines where this tax is related to')
   # ait_id = fields.Many2one('account.wh.iva.line.tax', 'Impuestos', help='Tax where is related to')
    type = fields.Char(string='tipo de libro')
    exento = fields.Float(string='Monto Exento',
                                  help='Monto exento',
                                  store=True)
    base_amount = fields.Float(#related='ait_id.base',
                                  string='Base Imponible',
                                  help='Amount used as Taxing Base',
                                  store=True)
    tax_amount = fields.Float(#related='ait_id.amount',
                                 string='Monto Gravado',
                                 help='Taxed Amount on Taxing Base',
                                 store=True)
    name = fields.Char(#related='ait_id.name',
                       string='Descripcion', store=True)
    currency_id = fields.Many2one('res.currency', string='Moneda')



class FiscalBookTaxesSummary(models.Model):
    TAX_TYPE = [('exento', '0% Exento'),
                ('sdcf', 'No tiene derecho a crédito fiscal'),
                ('general', 'Alicuota General'),
                ('reducido', 'Alicuota Reducida'),
                ('adicional', 'Alicuota General + Adicional')]

    OP_TYPE = [('im', 'Importaciones'),
               ('do', 'Nacionales'),
               ('ex', 'Exportaciones'),
               ('tp', 'Contribuyente'),
               ('ntp', 'no Contribuyente')]

    _description = "Venezuela's Sale & Purchase Fiscal Book Taxes Summary"
    _name = 'fiscal.book.taxes.summary'
    _order = 'op_type, tax_type asc'

    fb_id = fields.Many2one('fiscal.book', 'Fiscal Book')
    tax_type = fields.Selection(TAX_TYPE, 'Tipo de Impuesto')
    op_type = fields.Selection(OP_TYPE, string='Tipo de Operacion',
                               help="Tipo de Operacion:"
                                    " - Compra: Import or Domestic."
                                    " - Sales: Expertation, Tax Payer, Non-Tax Payer.")
    base_amount_sum = fields.Float('suma base impobible')
    tax_amount_sum = fields.Float('Suma del monto gravado')
    currency_id = fields.Many2one('res.currency', string='moneda')
    _rec_rame = 'Fiscal_book_taxes_summary_rec'


class AdjustmentBookLine(models.Model):
    TYPE_DOC = [('F', 'Factura'),
                ('ND', 'Nota de Debito'),
                ('NC', 'Nota de Credito'), ]

    _name = 'adjustment.book.line'

    date_accounting = fields.Date('Fecha Contable', required=True, help="Date accounting for adjustment book")
    date_admin = fields.Date('Date Administrative', required=True,
                             help="Date administrative for adjustment book")
    vat = fields.Char('RIF', size=10, required=True, help="Vat of partner for adjustment book")
    partner = fields.Char('Empresa', size=256, required=True, help="Partner for adjustment book")
    invoice_number = fields.Char('Nro de Factura', size=256, required=True, help="Invoice number for adjustment book")
    control_number = fields.Char('Nro de Control de Factura', size=256, required=True, help="")
    amount = fields.Float('Documento de importe en retención de IVA', # digits=dp.get_precision('Account'),
                          required=True,
                          help="Documento de importe en retención de IVA")
    type_doc = fields.Selection(TYPE_DOC, 'Tipo de Documento', select=True, required=True,
                                help="Tipo de documento para libro de ajustes"
                                     " -Invoice(F),-Debit Note(dn),-Credit Note(cn)")
    doc_affected = fields.Char('Affected Document', size=256, required=True,
                               help="Affected Document for adjustment book")
    uncredit_fiscal = fields.Float('Sin derecho a Credito Fiscal', #digits=dp.get_precision('Account'),
                                   # required=True,
                                   help="Sin derechoa credito fiscal")
    amount_untaxed_n = fields.Float('Amount Untaxed', #digits=dp.get_precision('Account'), required=True,
                                    help="Amount untaxed for national operations")
    percent_with_vat_n = fields.Float('VAT Withholding (%)', #digits=dp.get_precision('Account'), required=True,
                                      help="VAT percent (%) for national operations")
    amount_with_vat_n = fields.Float('VAT Withholding Amount', # digits=dp.get_precision('Account'), required=True,
                                     help="Percent(%) VAT for national operations")
    amount_untaxed_i = fields.Float('Amount Untaxed', # digits=dp.get_precision('Account'), required=True,
                                    help="Amount untaxed for international operations")
    percent_with_vat_i = fields.Float('VAT Withholding (%)', #digits=dp.get_precision('Account'), required=True,
                                      help="VAT percent (%) for international operations")
    amount_with_vat_i = fields.Float('VAT Withholding Amount', # digits=dp.get_precision('Account'), required=True,
                                     help="VAT amount for international operations")
    amount_with_vat = fields.Float('VAT Withholding Total Amount',
                                  # digits=dp.get_precision('Account'), required=True,
                                   help="VAT withholding total amount")
    voucher = fields.Char('VAT Withholding Voucher', size=256, required=True, help="VAT withholding voucher")
    fb_id = fields.Many2one('fiscal.book', 'Fiscal Book', help='Fiscal Book where this line is related to')

    _rec_rame = 'partner'
