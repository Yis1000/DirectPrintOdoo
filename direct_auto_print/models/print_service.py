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
            ('print_area', 'in', [record_area, 'all']),
            ('company_id', '=', self.env.company.id)
        ], order='print_area desc', limit=1)

        if not configs:
            _logger.info("No se encontró configuración por usuario, buscando global...")
            configs = self.env['direct.print.config'].search([
                ('user_id', '=', False),
                ('print_area', 'in', [record_area, 'all']),
                ('company_id', '=', self.env.company.id)
            ], order='print_area desc', limit=1)
        
        if not configs:
            _logger.info(f"No se encontró configuración de impresión para el área {record_area}")
            return False

        config = configs[0]
        
        if report_name:
            report = self.env['ir.actions.report']._get_report_from_name(report_name)
        elif config.report_id:
            report = config.report_id
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
            # 2. Renderizar PDF o Texto según configuración
            # Verificación extra: asegurar que el registro existe en el entorno actual
            if not record.exists():
                 raise UserError(f"El registro {record.id} no existe o fue eliminado.")
                 
            file_content = None
            if printer.printer_language == 'pdf':
                _logger.info(f"Renderizando reporte PDF {report.report_name} para registro ID {record.id}")
                pdf_raw, _type = self.env['ir.actions.report']._render_qweb_pdf(report.report_name, res_ids=record.ids)
                file_content = base64.b64encode(pdf_raw)
            else:
                _logger.info(f"Renderizando reporte de texto (ZPL/Raw) {report.report_name} para registro ID {record.id}")
                text_raw, _type = self.env['ir.actions.report']._render_qweb_text(report.report_name, res_ids=record.ids)
                file_content = base64.b64encode(text_raw)
            
            # 3. Crear el Job en Cola
            self.env['direct.print.job'].create({
                'document_model': record._name,
                'document_id': record.id,
                'printer_id': printer.id,
                'config_id': config.id,
                'user_id': self.env.user.id,
                'status': 'pending',
                'file_content': file_content,
                'company_id': self.env.company.id,
                'attempts': 0
            })
            _logger.info("Trabajo de impresión encolado correctamente.")
            return True

        except Exception as e:
            error_msg = str(e)
            _logger.error(f"Error encolando documento: {error_msg}")
            # Si hay error creando el pdf de base, se crea un job en error para que conste
            self.env['direct.print.job'].create({
                'document_model': record._name,
                'document_id': record.id,
                'printer_id': printer.id,
                'config_id': config.id,
                'user_id': self.env.user.id,
                'status': 'error',
                'error_message': f"Generación: {error_msg}",
                'company_id': self.env.company.id,
                'attempts': 1
            })
            return False

    @api.model
    def _process_print_queue(self):
        """
        Llamado por el Cron job para procesar todas las impresiones pendientes.
        """
        pending_jobs = self.env['direct.print.job'].search([('status', '=', 'pending'), ('attempts', '<', 3)])
        for job in pending_jobs:
            job.write({'status': 'printing'})
            self.env.cr.commit()  # Asegurar que se ve como imprimiendo si crashea luego
            
            try:
                if not job.printer_id.active:
                    raise Exception("Impresora inactiva.")
                if not job.file_content:
                    raise Exception("No hay contenido de archivo para imprimir.")
                    
                decoded_data = base64.b64decode(job.file_content)
                self._send_to_printer(job.printer_id, decoded_data)
                
                job.write({'status': 'success'})
            except Exception as e:
                job.write({
                    'status': 'error',
                    'error_message': str(e),
                    'attempts': job.attempts + 1
                })
            self.env.cr.commit()

    def _send_to_printer(self, printer, decoded_data):
        """
        Envía los datos a la impresora según si es PDF o ZPL/Raw.
        """
        # Crear archivo temporal
        if printer.printer_language == 'pdf':
            ext = '.pdf'
        else:
            ext = '.zpl' if printer.printer_language == 'zpl' else '.txt'
            
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as temp_file:
            temp_file.write(decoded_data)
            temp_file_path = temp_file.name

        try:
            if printer.connection_type == 'network' and printer.ip_address:
                self._print_via_socket(printer.ip_address, printer.port, decoded_data)
            else:
                is_windows = os.name == 'nt'
                if is_windows:
                    if printer.printer_language in ['zpl', 'raw']:
                        ps_cmd = [
                            'powershell',
                            '-NoProfile',
                            '-Command',
                            f"Get-Content -LiteralPath '{temp_file_path}' | Out-Printer -Name '{printer.printer_identifier}'"
                        ]
                        subprocess.check_call(ps_cmd)
                    else:
                        set_default_cmd = [
                            'rundll32',
                            'printui.dll,PrintUIEntry',
                            '/y',
                            f"/n{printer.printer_identifier}"
                        ]
                        try:
                            subprocess.check_call(set_default_cmd)
                        except Exception:
                            pass
                        print_cmd = [
                            'powershell',
                            '-NoProfile',
                            '-Command',
                            f"$p=Start-Process -FilePath '{temp_file_path}' -Verb Print -PassThru; $p | Wait-Process"
                        ]
                        subprocess.check_call(print_cmd)
                else:
                    if printer.printer_language in ['zpl', 'raw']:
                        cmd = ['lp', '-d', printer.printer_identifier, '-o', 'raw', temp_file_path]
                    else:
                        cmd = ['lp', '-d', printer.printer_identifier, temp_file_path]
                    subprocess.check_call(cmd)
                
        finally:
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)

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
