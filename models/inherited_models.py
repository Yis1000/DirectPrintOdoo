# -*- coding: utf-8 -*-
from odoo import models


class DirectPrintMixin(models.AbstractModel):
    _name = 'direct.print.mixin'
    _description = 'Direct Print Mixin'

    def action_direct_print(self):
        for record in self:
            self.env['direct.print.service'].print_document(record)

    def _auto_print_if_enabled(self):
        area_mapping = {
            'sale.order': 'sale',
            'purchase.order': 'purchase',
            'account.move': 'account',
            'stock.picking': 'stock',
            'mrp.production': 'mrp',
        }
        for record in self:
            record_area = area_mapping.get(record._name, 'all')

            configs = self.env['direct.print.config'].search([
                ('user_id', '=', self.env.user.id),
                ('print_area', 'in', [record_area, 'all']),
                ('auto_print', '=', True),
            ], order='print_area desc', limit=1)

            if not configs:
                configs = self.env['direct.print.config'].search([
                    ('user_id', '=', False),
                    ('print_area', 'in', [record_area, 'all']),
                    ('auto_print', '=', True),
                ], order='print_area desc', limit=1)

            if configs:
                self.env['direct.print.service'].print_document(record)


class SaleOrder(models.Model):
    _name = 'sale.order'
    _inherit = ['sale.order', 'direct.print.mixin']

    def action_confirm(self):
        res = super().action_confirm()
        self._auto_print_if_enabled()
        return res


class AccountMove(models.Model):
    _name = 'account.move'
    _inherit = ['account.move', 'direct.print.mixin']

    def action_post(self):
        res = super().action_post()
        self._auto_print_if_enabled()
        return res


class StockPicking(models.Model):
    _name = 'stock.picking'
    _inherit = ['stock.picking', 'direct.print.mixin']

    def button_validate(self):
        res = super().button_validate()
        self._auto_print_if_enabled()
        return res


class MrpProduction(models.Model):
    _name = 'mrp.production'
    _inherit = ['mrp.production', 'direct.print.mixin']

    def button_mark_done(self):
        res = super().button_mark_done()
        self._auto_print_if_enabled()
        return res


class PurchaseOrder(models.Model):
    _name = 'purchase.order'
    _inherit = ['purchase.order', 'direct.print.mixin']


class ResPartner(models.Model):
    _name = 'res.partner'
    _inherit = ['res.partner', 'direct.print.mixin']
