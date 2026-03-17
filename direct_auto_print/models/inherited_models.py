# -*- coding: utf-8 -*-
from odoo import models, api, _

# Funciones auxiliares para impresión directa
def _action_direct_print(self):
    """Método para impresión directa desde el botón"""
    for record in self:
        ok = self.env['direct.print.service'].print_document(record)
        if ok:
            record.message_post(body=_("Se está imprimiendo"))
        else:
            record.message_post(body=_("Error al iniciar la impresión"))

def _auto_print_if_enabled(self):
    """Método para impresión automática"""
    for record in self:
        area_mapping = {
            'sale.order': 'sale',
            'purchase.order': 'purchase',
            'account.move': 'account',
            'stock.picking': 'stock',
            'mrp.production': 'mrp'
        }
        record_area = area_mapping.get(record._name, 'all')

        # Buscar si hay configuración de auto impresión para esta área y usuario
        configs = self.env['direct.print.config'].search([
            ('user_id', '=', self.env.user.id),
            ('print_area', 'in', [record_area, 'all']),
            ('auto_print', '=', True)
        ], order='print_area desc', limit=1)

        if not configs:
            # Intentar global
            configs = self.env['direct.print.config'].search([
                ('user_id', '=', False),
                ('print_area', 'in', [record_area, 'all']),
                ('auto_print', '=', True)
            ], order='print_area desc', limit=1)

        if configs:
            self.env['direct.print.service'].print_document(record)

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    action_direct_print = _action_direct_print
    _auto_print_if_enabled = _auto_print_if_enabled

    def action_confirm(self):
        res = super(SaleOrder, self).action_confirm()
        self._auto_print_if_enabled()
        return res

class AccountMove(models.Model):
    _inherit = 'account.move'

    action_direct_print = _action_direct_print
    _auto_print_if_enabled = _auto_print_if_enabled

    def action_post(self):
        res = super(AccountMove, self).action_post()
        self._auto_print_if_enabled()
        return res

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    action_direct_print = _action_direct_print
    _auto_print_if_enabled = _auto_print_if_enabled

    def button_validate(self):
        res = super(StockPicking, self).button_validate()
        self._auto_print_if_enabled()
        return res

class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    action_direct_print = _action_direct_print
    _auto_print_if_enabled = _auto_print_if_enabled

    def button_mark_done(self):
        res = super(MrpProduction, self).button_mark_done()
        self._auto_print_if_enabled()
        return res

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    action_direct_print = _action_direct_print
    _auto_print_if_enabled = _auto_print_if_enabled

    def button_confirm(self):
        res = super(PurchaseOrder, self).button_confirm()
        # Purchase order confirm logic might be different depending on config
        # Requirement says: "when a sale order is confirmed... a stock picking... an invoice... a manufacturing order..."
        # It didn't explicitly mention auto-print for Purchase Order trigger, but requested the button.
        # I will add auto-print hook just in case, or leave it out if not requested.
        # "Automatic Printing: ... sale order, stock picking, invoice, manufacturing order"
        # Purchase is NOT in the automatic list, only in the button list.
        # So I will NOT call _auto_print_if_enabled here.
        return res

class ResPartner(models.Model):
    _inherit = 'res.partner'

    action_direct_print = _action_direct_print
    _auto_print_if_enabled = _auto_print_if_enabled

    # No auto-print trigger for partners
