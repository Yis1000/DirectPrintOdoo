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
    ip_address = fields.Char(string='Dirección IP', help="Dirección IP si la impresora está en red (ej. 192.168.1.50).")
    port = fields.Integer(string='Puerto', default=9100, help="Puerto de red de la impresora (generalmente 9100).")
    active = fields.Boolean(string='Activo', default=True, help="Desmarcar para deshabilitar temporalmente esta impresora.")

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

class DirectPrintLog(models.Model):
    _name = 'direct.print.log'
    _description = 'Log de Impresión Directa'
    _order = 'printed_at desc'

    document_model = fields.Char(string='Modelo del Documento')
    document_id = fields.Integer(string='ID del Documento')
    printer_id = fields.Many2one('direct.print.printer', string='Impresora Utilizada')
    user_id = fields.Many2one('res.users', string='Usuario')
    status = fields.Selection([
        ('success', 'Éxito'),
        ('error', 'Error')
    ], string='Estado')
    error_message = fields.Text(string='Mensaje de Error')
    printed_at = fields.Datetime(string='Fecha de Impresión', default=fields.Datetime.now)
