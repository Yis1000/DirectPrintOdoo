# -*- coding: utf-8 -*-
import logging
import os
import socket
import subprocess
import tempfile

from odoo import api, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class DirectPrintService(models.AbstractModel):
    _name = 'direct.print.service'
    _description = 'Direct Print Service'

    @api.model
    def print_document(self, record, report_name=None):
        """Find the matching configuration, render the PDF and send it to the printer."""
        _logger.info("Looking up print configuration for %s - User: %s", record._name, self.env.user.id)

        area_mapping = {
            'sale.order': 'sale',
            'purchase.order': 'purchase',
            'account.move': 'account',
            'stock.picking': 'stock',
            'mrp.production': 'mrp',
        }
        record_area = area_mapping.get(record._name, 'all')

        configs = self.env['direct.print.config'].search([
            ('user_id', '=', self.env.user.id),
            ('print_area', 'in', [record_area, 'all']),
        ], order='print_area desc', limit=1)

        if not configs:
            _logger.info("No per-user configuration found, falling back to global rules.")
            configs = self.env['direct.print.config'].search([
                ('user_id', '=', False),
                ('print_area', 'in', [record_area, 'all']),
            ], order='print_area desc', limit=1)

        if not configs:
            _logger.info("No print configuration found for area %s", record_area)
            return False

        config = configs[0]

        if report_name:
            report = self.env['ir.actions.report']._get_report_from_name(report_name)
        else:
            report = self.env['ir.actions.report'].search([('model', '=', record._name)], limit=1)

        if not report:
            raise UserError(_("No default report is configured for model %s.") % record._name)

        _logger.info("Match: %s - Printer: %s - Report: %s", config.name, config.printer_id.name, report.name)
        printer = config.printer_id

        if not printer.active:
            self._log_print(record, printer, 'error', "The configured printer is inactive.")
            raise UserError(_("The configured printer is inactive."))

        try:
            _logger.info("Rendering report %s for record id %s", report.report_name, record.id)
            if not record.exists():
                raise UserError(_("Record %s no longer exists.") % record.id)

            pdf_content, _type = report._render_qweb_pdf(record.ids)

            self._send_to_printer(printer, pdf_content)
            self._log_print(record, printer, 'success')
            return True

        except Exception as e:
            error_msg = str(e)
            _logger.error("Direct print failed: %s", error_msg)
            self._log_print(record, printer, 'error', error_msg)
            return False

    def _send_to_printer(self, printer, pdf_content):
        """Push the PDF bytes to the printer (raw socket for network, lp for system queues)."""
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_pdf:
            temp_pdf.write(pdf_content)
            temp_pdf_path = temp_pdf.name

        try:
            if printer.connection_type == 'network' and printer.ip_address:
                self._print_via_socket(printer.ip_address, printer.port, pdf_content)
            else:
                cmd = ['lp', '-d', printer.printer_identifier, temp_pdf_path]
                subprocess.check_call(cmd)
        finally:
            if os.path.exists(temp_pdf_path):
                os.remove(temp_pdf_path)

    def _print_via_socket(self, host, port, content):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10)
            sock.connect((host, port))
            sock.sendall(content)
            sock.close()
        except Exception as e:
            raise Exception("Network connection to printer %s:%s failed - %s" % (host, port, e))

    def _log_print(self, record, printer, status, error_msg=False):
        """Persist the log entry on a separate cursor so it survives a rollback of the main one."""
        try:
            with self.pool.cursor() as new_cr:
                new_env = api.Environment(new_cr, self.env.uid, {})
                new_env['direct.print.log'].create({
                    'document_model': record._name,
                    'document_id': record.id,
                    'printer_id': printer.id,
                    'user_id': self.env.user.id,
                    'status': status,
                    'error_message': error_msg,
                })
                new_cr.commit()
        except Exception as e:
            _logger.error("Failed to write direct print log: %s", e)
