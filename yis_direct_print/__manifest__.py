# -*- coding: utf-8 -*-
{
    'name': 'Direct Print',
    'version': '18.0.1.0.0',
    'category': 'Tools',
    'summary': 'Push Odoo reports straight to a configured printer — no PDF download needed.',
    'description': """
Direct Print
============
Send Odoo reports (sale orders, invoices, delivery slips, manufacturing orders,
purchase orders, contacts) directly to a local or network printer.

* Manage a catalogue of printers (USB/local, network/TCP-IP, Wi-Fi, Bluetooth).
* Assign printers per business area (Sales, Purchase, Invoicing, Inventory,
  Manufacturing or Global) and per user.
* One-click "Direct Print" button on supported documents.
* Optional auto-print on key business events (sale confirm, invoice post,
  picking validate, MO done).
* Persistent log of every print attempt.

Maintained by HIGA — https://higa.group
""",
    'author': 'HIGA',
    'website': 'https://higa.group',
    'maintainer': 'HIGA',
    'support': 'https://higa.group',
    'depends': ['base', 'sale', 'account', 'stock', 'mrp', 'purchase', 'contacts'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/direct_print_views.xml',
        'views/inherited_views.xml',
    ],
    'images': ['static/description/banner.png'],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
