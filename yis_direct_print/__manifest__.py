# -*- coding: utf-8 -*-
{
    'name': 'Impresión Directa Automática',
    'version': '16.0.1.0.0',
    'category': 'Tools',
    'summary': 'Imprime reportes directamente en impresoras configuradas sin descargar PDF',
    'description': """
        Módulo para imprimir documentos de Odoo directamente a una impresora local o de red.
        Permite configurar impresoras, asignarlas a reportes y usuarios, y habilitar la impresión automática
        al confirmar ventas, validar albaranes, etc.
    """,
    'author': 'HIGA',
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

