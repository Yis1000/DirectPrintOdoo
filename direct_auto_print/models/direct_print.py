# -*- coding: utf-8 -*-
from odoo import models, fields, api

class DirectPrintPrinter(models.Model):
    _name = 'direct.print.printer'
    _description = 'Impresora para Impresión Directa'

    name = fields.Char(string='Nombre de Impresora', required=True, help="Nombre amistoso para reconocer esta impresora (ej. Impresora Recepción).")
    printer_identifier = fields.Char(string='Identificador de Sistema', required=True,
                                     help="El nombre exacto de la impresora en el sistema operativo (ej. HP_LaserJet_1010) o en la red.")
    connection_type = fields.Selection([
        ('usb', 'USB / Local'),
        ('network', 'Red (TCP/IP)'),
        ('wifi', 'WiFi'),
        ('bluetooth', 'Bluetooth')
    ], string='Tipo de Conexión', default='network', help="Cómo está conectada la impresora.")
    printer_language = fields.Selection([
        ('pdf', 'PDF (Impresora Normal)'),
        ('zpl', 'ZPL (Etiquetas Zebra)'),
        ('raw', 'Texto Plano / Raw')
    ], string='Lenguaje de Impresión', default='pdf', required=True, help="El formato de datos que acepta la impresora. PDF para A4/Tickets, ZPL para etiquetas.")
    ip_address = fields.Char(string='Dirección IP', help="Dirección IP si la impresora está en red (ej. 192.168.1.50).")
    port = fields.Integer(string='Puerto', default=9100, help="Puerto de red de la impresora (generalmente 9100).")
    active = fields.Boolean(string='Activo', default=True, help="Desmarcar para deshabilitar temporalmente esta impresora.")
    company_id = fields.Many2one('res.company', string='Compañía', default=lambda self: self.env.company, required=True)

    # Campos computados para vistas
    status_color = fields.Selection([
        ('success', 'Verde'),
        ('danger', 'Rojo')
    ], string='Color de Estado', compute='_compute_status_color', store=False)

    status_icon = fields.Char(string='Icono de Estado', compute='_compute_status_color', store=False)

    def _compute_status_color(self):
        for record in self:
            if record.active:
                record.status_color = 'success'
                record.status_icon = 'fa-check-circle'
            else:
                record.status_color = 'danger'
                record.status_icon = 'fa-times-circle'

    # Contador de trabajos
    job_count = fields.Integer(string='Trabajos', compute='_compute_job_count')

    def _compute_job_count(self):
        for record in self:
            record.job_count = self.env['direct.print.job'].search_count([
                ('printer_id', '=', record.id),
                ('status', 'in', ['pending', 'printing'])
            ])

    def action_view_jobs(self):
        """Ver los trabajos de esta impresora"""
        self.ensure_one()
        return {
            'name': f'Trabajos de {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'direct.print.job',
            'view_mode': 'list,form',
            'domain': [('printer_id', '=', self.id)],
            'context': {'default_printer_id': self.id}
        }

    def toggle_active(self):
        """Alternar estado activo"""
        for record in self:
            record.active = not record.active

class DirectPrintConfig(models.Model):
    _name = 'direct.print.config'
    _description = 'Configuración de Impresión Directa'

    name = fields.Char(string='Nombre de Configuración', required=True, help="Un nombre para identificar esta regla de impresión.")
    print_area = fields.Selection([
        ('all', 'Todo Odoo (Global)'),
        ('sale', 'Ventas'),
        ('purchase', 'Compras'),
        ('account', 'Facturación'),
        ('stock', 'Inventario / Albaranes'),
        ('mrp', 'Fabricación')
    ], string='Área de Impresión', default='all', required=True, help="¿Para qué parte de Odoo se usará esta configuración? Selecciona 'Todo Odoo' para que sirva para cualquier documento.")
    printer_id = fields.Many2one('direct.print.printer', string='Impresora', required=True, help="Selecciona por cuál impresora saldrán los documentos.")
    user_id = fields.Many2one('res.users', string='Usuario', default=lambda self: self.env.user, help="Usuario específico para esta regla. Déjalo vacío si quieres que aplique a cualquier usuario.")
    auto_print = fields.Boolean(string='Impresión Automática en Flujos', default=False, help="Si se activa, el documento se imprimirá automáticamente sin preguntar al confirmarlo (ej. al validar una venta o inventario).")
    report_id = fields.Many2one('ir.actions.report', string='Reporte específico')
    company_id = fields.Many2one('res.company', string='Compañía', default=lambda self: self.env.company, required=True)
    active = fields.Boolean(string='Activo', default=True)

    # Campo para icono de área
    area_icon = fields.Char(string='Icono de Área', compute='_compute_area_icon', store=False)

    def _compute_area_icon(self):
        icons = {
            'all': 'fa-globe',
            'sale': 'fa-shopping-cart',
            'purchase': 'fa-shopping-bag',
            'account': 'fa-file-invoice-dollar',
            'stock': 'fa-boxes',
            'mrp': 'fa-industry',
        }
        for record in self:
            record.area_icon = icons.get(record.print_area, 'fa-print')

class DirectPrintJob(models.Model):
    _name = 'direct.print.job'
    _description = 'Trabajo de Impresión (Cola)'
    _order = 'printed_at desc'

    document_model = fields.Char(string='Modelo del Documento')
    document_id = fields.Integer(string='ID del Documento')
    printer_id = fields.Many2one('direct.print.printer', string='Impresora Destino')
    config_id = fields.Many2one('direct.print.config', string='Configuración Utilizada')
    user_id = fields.Many2one('res.users', string='Usuario Creador')
    status = fields.Selection([
        ('pending', 'Pendiente'),
        ('printing', 'Imprimiendo'),
        ('success', 'Éxito'),
        ('error', 'Error')
    ], string='Estado', default='pending')
    error_message = fields.Text(string='Mensaje de Error')
    file_content = fields.Binary(string='Contenido del Archivo', attachment=True, 
                                 help="El PDF o ZPL a imprimir. Guardado por si se necesita reintentar sin volver a generarlo.")
    printed_at = fields.Datetime(string='Fecha de Creación', default=fields.Datetime.now)
    company_id = fields.Many2one('res.company', string='Compañía', default=lambda self: self.env.company, required=True)
    attempts = fields.Integer(string='Intentos', default=0)

    def action_retry(self):
        for job in self:
            if job.status == 'error':
                job.write({
                    'status': 'pending',
                    'error_message': False
                })
        return True
