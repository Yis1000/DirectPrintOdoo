# -*- coding: utf-8 -*-
import base64
import logging
import subprocess
import os
import tempfile
from odoo import models, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class DirectPrintService(models.AbstractModel):
    _name = 'direct.print.service'
    _description = 'Servicio de Impresión Directa'

    @api.model
    def print_document(self, record, report_name=None):
        """
        Encuentra la configuración adecuada, renderiza el PDF y lo envía a la impresora.
        """
        # 1. Buscar configuración de impresión
        # Prioridad: Usuario actual + Modelo -> Configuración global
        
        # Ajuste de búsqueda: Buscar configuraciones por área de impresión
        _logger.info(f"Buscando configuración de impresión para {record._name} - Usuario: {self.env.user.id}")
        
        area_mapping = {
            'sale.order': 'sale',
            'purchase.order': 'purchase',
            'account.move': 'account',
            'stock.picking': 'stock',
            'mrp.production': 'mrp'
        }
        record_area = area_mapping.get(record._name, 'all')

        configs = self.env['direct.print.config'].search([
            ('user_id', '=', self.env.user.id),
            ('print_area', 'in', [record_area, 'all'])
        ], order='print_area desc', limit=1)

        if not configs:
            _logger.info("No se encontró configuración por usuario, buscando global...")
            configs = self.env['direct.print.config'].search([
                ('user_id', '=', False), # Configuración global
                ('print_area', 'in', [record_area, 'all'])
            ], order='print_area desc', limit=1)
        
        if not configs:
            _logger.info(f"No se encontró configuración de impresión para el área {record_area}")
            return False

        config = configs[0]
        
        if report_name:
            report = self.env['ir.actions.report']._get_report_from_name(report_name)
        else:
            report = self.env['ir.actions.report'].search([('model', '=', record._name)], limit=1)
            
        if not report:
            raise UserError(_("No existe un reporte configurado por defecto para el modelo %s") % record._name)

        _logger.info(f"Configuración encontrada: {config.name} - Impresora: {config.printer_id.name} - Reporte: {report.name}")
        printer = config.printer_id

        if not printer.active:
            self._log_print(record, printer, 'error', "La impresora está inactiva.")
            raise UserError(_("La impresora configurada está inactiva."))

        try:
            # 2. Renderizar PDF
            # _render_qweb_pdf espera ids como lista, pero devuelve contenido para todos.
            # Aseguramos que pasamos el ID correcto.
            _logger.info(f"Renderizando reporte {report.report_name} para registro ID {record.id}")
            # Verificación extra: asegurar que el registro existe en el entorno actual
            if not record.exists():
                 raise UserError(f"El registro {record.id} no existe o fue eliminado.")

            pdf_content, _type = self.env['ir.actions.report']._render_qweb_pdf(report.report_name, res_ids=record.ids)
            
            # 3. Enviar a la impresora
            self._send_to_printer(printer, pdf_content)
            
            # 4. Log éxito
            self._log_print(record, printer, 'success')
            return True

        except Exception as e:
            error_msg = str(e)
            _logger.error(f"Error imprimiendo documento: {error_msg}")
            # Log de error usando cursor separado
            self._log_print(record, printer, 'error', error_msg)
            # No hacemos raise para no interrumpir el flujo del usuario, solo notificamos
            # raise UserError(_("Error al imprimir: %s") % error_msg)
            return False

    def _send_to_printer(self, printer, pdf_content):
        """
        Envía el contenido PDF a la impresora del sistema usando lp/lpr.
        """
        # Crear archivo temporal
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_pdf:
            temp_pdf.write(pdf_content)
            temp_pdf_path = temp_pdf.name

        try:
            # Construir comando
            # Si es network, a veces se usa socket://ip:port, pero lp espera una cola de sistema.
            # Asumiremos que printer_identifier es el nombre de la cola en el sistema (CUPS)
            # O si se quiere usar netcat para impresoras raw port 9100:
            
            if printer.connection_type == 'network' and printer.ip_address:
                 # Ejemplo simple enviando raw a puerto 9100 (netcat/socket)
                 # Esto es muy básico y funciona para muchas impresoras de red modernas (JetDirect)
                 # Si no, usar lp con el nombre de la impresora del sistema
                 self._print_via_socket(printer.ip_address, printer.port, pdf_content)
            else:
                # Usar comando de sistema lp
                # Requiere que la impresora esté instalada en el SO donde corre Odoo
                cmd = ['lp', '-d', printer.printer_identifier, temp_pdf_path]
                subprocess.check_call(cmd)
                
        finally:
            # Limpiar
            if os.path.exists(temp_pdf_path):
                os.remove(temp_pdf_path)

    def _print_via_socket(self, host, port, content):
        import socket
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10)
            sock.connect((host, port))
            sock.sendall(content)
            sock.close()
        except Exception as e:
            raise Exception(f"Fallo conexión de red a impresora {host}:{port} - {str(e)}")

    def _log_print(self, record, printer, status, error_msg=False):
        """
        Registra el log en una transacción separada para persistir incluso si hay rollback.
        """
        try:
            with self.pool.cursor() as new_cr:
                # Crear nuevo entorno con el cursor nuevo
                new_env = api.Environment(new_cr, self.env.uid, {})
                new_env['direct.print.log'].create({
                    'document_model': record._name,
                    'document_id': record.id,
                    'printer_id': printer.id,
                    'user_id': self.env.user.id,
                    'status': status,
                    'error_message': error_msg
                })
                # Commit explícito de la nueva transacción
                new_cr.commit()
        except Exception as e:
            _logger.error(f"Error al escribir log de impresión: {str(e)}")

