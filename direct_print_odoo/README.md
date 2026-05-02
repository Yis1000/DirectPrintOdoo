# Impresión Directa Automática (Direct Auto Print)

## Descripción
Módulo para Odoo 19.0 que permite la impresión directa de documentos a una impresora local o de red sin necesidad de descargar previamente el archivo PDF correspondiente.

### Características Principales:
* **Configuración de Impresoras:** Permite dar de alta y configurar impresoras locales o de red en el sistema.
* **Asignación Flexible:** Posibilidad de asignar impresoras específicas a reportes concretos y a usuarios.
* **Impresión Automática:** Habilita flujos para automatizar la impresión en eventos clave (por ejemplo, al confirmar una orden de venta, al validar un albarán de entrega, etc.).

## Dependencias
Este módulo depende de las siguientes aplicaciones base de Odoo:
- `base`
- `sale`
- `account`
- `stock`
- `mrp`
- `purchase`
- `contacts`

## Versión
- Odoo: **19.0**
- Licencia: **LGPL-3**
- Autor: **HIGA**
