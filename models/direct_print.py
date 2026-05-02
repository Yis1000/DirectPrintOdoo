# -*- coding: utf-8 -*-
from odoo import models, fields


class DirectPrintPrinter(models.Model):
    _name = 'direct.print.printer'
    _description = 'Direct Print - Printer'

    name = fields.Char(
        string='Printer Name', required=True,
        help='Friendly name to identify this printer (e.g. "Front Desk Printer").')
    printer_identifier = fields.Char(
        string='System Identifier', required=True,
        help='Exact printer name as registered in the OS '
             '(e.g. HP_LaserJet_1010) or its network identifier.')
    connection_type = fields.Selection([
        ('usb', 'USB / Local'),
        ('network', 'Network (TCP/IP)'),
        ('wifi', 'Wi-Fi'),
        ('bluetooth', 'Bluetooth'),
    ], string='Connection Type', default='network', help='How the printer is connected.')
    ip_address = fields.Char(
        string='IP Address',
        help='Printer IP address when on the network (e.g. 192.168.1.50).')
    port = fields.Integer(
        string='Port', default=9100,
        help='Network port of the printer (usually 9100).')
    active = fields.Boolean(
        string='Active', default=True,
        help='Untick to disable this printer temporarily.')


class DirectPrintConfig(models.Model):
    _name = 'direct.print.config'
    _description = 'Direct Print - Configuration'

    name = fields.Char(
        string='Configuration Name', required=True,
        help='Friendly name to identify this print rule.')
    print_area = fields.Selection([
        ('all', 'All Odoo (Global)'),
        ('sale', 'Sales'),
        ('purchase', 'Purchase'),
        ('account', 'Invoicing'),
        ('stock', 'Inventory / Pickings'),
        ('mrp', 'Manufacturing'),
    ], string='Print Area', default='all', required=True,
        help='Which area of Odoo this rule applies to. Choose "All Odoo" to apply to any document.')
    printer_id = fields.Many2one(
        'direct.print.printer', string='Printer', required=True,
        help='Printer used to print the documents.')
    user_id = fields.Many2one(
        'res.users', string='User', default=lambda self: self.env.user,
        help='Specific user this rule applies to. Leave empty to apply to every user.')
    auto_print = fields.Boolean(
        string='Auto-print on Workflow', default=False,
        help='If enabled, the document is printed automatically (without prompting) '
             'when confirmed/posted/validated.')


class DirectPrintLog(models.Model):
    _name = 'direct.print.log'
    _description = 'Direct Print - Log'
    _order = 'printed_at desc'

    document_model = fields.Char(string='Document Model')
    document_id = fields.Integer(string='Document ID')
    printer_id = fields.Many2one('direct.print.printer', string='Printer Used')
    user_id = fields.Many2one('res.users', string='User')
    status = fields.Selection([
        ('success', 'Success'),
        ('error', 'Error'),
    ], string='Status')
    error_message = fields.Text(string='Error Message')
    printed_at = fields.Datetime(string='Printed At', default=fields.Datetime.now)
