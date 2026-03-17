#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WORKER DE IMPRESIÓN PARA ODOO (UBUNTU/LINUX)
Procesa la cola de trabajos de impresión y los envía a las impresoras reales

REQUISITOS:
    pip install requests

    En Ubuntu, instalar CUPS:
    sudo apt update
    sudo apt install cups
    sudo apt install libcups2-dev

    Para impresoras PDF/PostScript:
    sudo apt install printer-driver-all

EJECUCIÓN:
    python print_worker.py

    O como servicio systemd:
    sudo cp print_worker.service /etc/systemd/system/
    sudo systemctl daemon-reload
    sudo systemctl enable print_worker
    sudo systemctl start print_worker
"""

import requests
import time
import sys
import os
import subprocess
import tempfile
import socket

# Configuración Odoo
ODOO_URL = "http://localhost:8069"
DB_NAME = "postgres"
USERNAME = "admin"
PASSWORD = "admin"

# Intervalo de verificación (segundos)
CHECK_INTERVAL = 5

def get_session():
    """Obtener sesión de Odoo"""
    url = f"{ODOO_URL}/web/session/authenticate"
    payload = {
        "jsonrpc": "2.0",
        "params": {
            "db": DB_NAME,
            "login": USERNAME,
            "password": PASSWORD
        }
    }
    try:
        response = requests.post(url, json=payload, timeout=10)
        result = response.json()
        if result.get("result"):
            return response.cookies
    except Exception as e:
        print(f"Error de conexión: {e}")
    return None

def call_method(cookies, model, method, domain=None, fields=None):
    """Llamar a un método de Odoo"""
    url = f"{ODOO_URL}/web/dataset/call_kw"
    payload = {
        "jsonrpc": "2.0",
        "method": "call",
        "params": {
            "model": model,
            "method": method,
            "args": domain or [],
            "kwargs": {}
        }
    }
    try:
        response = requests.post(url, json=payload, cookies=cookies, timeout=10)
        return response.json()
    except Exception as e:
        print(f"Error calling {model}.{method}: {e}")
        return {"error": str(e)}

def get_available_printers():
    """Obtener lista de impresoras disponibles en CUPS"""
    try:
        result = subprocess.run(['lpstat', '-p'], capture_output=True, text=True)
        if result.returncode == 0:
            printers = []
            for line in result.stdout.split('\n'):
                if line.startswith('printer '):
                    name = line.split()[1]
                    printers.append(name)
            return printers
        return []
    except FileNotFoundError:
        print("⚠️  CUPS no instalado. Ejecuta: sudo apt install cups")
        return []

def print_to_cups_printer(printer_name, pdf_data):
    """Imprimir PDF a impresora configurada en CUPS (Ubuntu/Linux)"""
    try:
        # Guardar PDF temporal
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as f:
            f.write(pdf_data)
            temp_path = f.name

        # Verificar que la impresora existe
        check_result = subprocess.run(['lpstat', '-p', printer_name],
                                    capture_output=True, text=True)
        if check_result.returncode != 0:
            # Intentar listar impresoras disponibles
            printers = get_available_printers()
            if printers:
                return False, f"Impresora '{printer_name}' no encontrada. Disponibles: {', '.join(printers)}"
            else:
                return False, f"Impresora '{printer_name}' no encontrada. CUPS puede no estar instalado."

        # Enviar a imprimir usando lp (CUPS)
        result = subprocess.run(['lp', '-d', printer_name, temp_path],
                              capture_output=True, text=True)

        if result.returncode == 0:
            # Obtener el ID del trabajo
            job_id = result.stdout.strip().split()[-1] if result.stdout.strip() else "desconocido"
            # Limpiar archivo temporal
            try:
                os.unlink(temp_path)
            except:
                pass
            return True, f"Enviado a CUPS (Job #{job_id})"
        else:
            error = result.stderr.strip() or result.stdout.strip()
            return False, f"Error CUPS: {error}"

    except FileNotFoundError:
        return False, "CUPS (lp) no instalado. Ejecuta: sudo apt install cups"
    except Exception as e:
        return False, str(e)

def print_to_network_printer(ip, port, pdf_data):
    """Imprimir PDF a impresora de red (envío directo)"""
    try:
        import socket

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        sock.connect((ip, port))
        sock.send(pdf_data)
        sock.close()

        return True, "Enviado a impresora de red"
    except Exception as e:
        return False, f"Error de red: {e}"

def print_job(job, printer_config):
    """Procesar un trabajo de impresión"""
    print(f"\n📄 Procesando trabajo #{job['id']}: {job['document_model']} #{job['document_id']}")

    # Obtener el contenido del archivo
    file_content = job.get('file_content')
    if not file_content:
        return False, "No hay contenido de archivo"

    # Decodificar base64 si es necesario
    import base64
    try:
        pdf_data = base64.b64decode(file_content)
    except:
        pdf_data = file_content

    # Determinar tipo de impresión
    connection_type = printer_config.get('connection_type', 'network')

    if connection_type == 'network':
        ip = printer_config.get('ip_address')
        port = printer_config.get('port', 9100)
        if not ip:
            return False, "No hay IP configurada"
        return print_to_network_printer(ip, port, pdf_data)

    else:  # usb, local, wifi, bluetooth - usan CUPS
        printer_name = printer_config.get('printer_identifier')
        if not printer_name:
            return False, "No hay nombre de impresora"
        return print_to_cups_printer(printer_name, pdf_data)

def update_job_status(cookies, job_id, status, error_msg=None):
    """Actualizar estado del trabajo"""
    values = {"status": status}
    if error_msg:
        values["error_message"] = error_msg

    result = call_method(cookies, "direct.print.job", "write",
                        [[job_id], values])

    if result.get("error"):
        print(f"⚠️  Error actualizando estado: {result['error']}")

def main():
    print("=" * 60)
    print("WORKER DE IMPRESIÓN ODOO (UBUNTU/LINUX)")
    print("=" * 60)

    # Mostrar impresoras disponibles en CUPS
    print("\n🖨️  Impresoras disponibles en CUPS:")
    printers = get_available_printers()
    if printers:
        for p in printers:
            print(f"   - {p}")
    else:
        print("   ⚠️  No hay impresoras configuradas en CUPS")
        print("   Para agregar una impresora:")
        print("   sudo lpadmin -p 'Nombre' -v 'socket://192.168.1.50:9100' -m 'everywhere'")

    print(f"\nConectando a {ODOO_URL}...")

    cookies = get_session()
    if not cookies:
        print("❌ No se pudo conectar. Verifica usuario/contraseña.")
        return

    print(f"✅ Conectado como {USERNAME}")
    print(f"⏱️  Verificando cola cada {CHECK_INTERVAL} segundos...")
    print("Presiona Ctrl+C para detener\n")

    try:
        while True:
            # Buscar trabajos pendientes
            result = call_method(cookies, "direct.print.job", "search_read",
                                [[[("status", "=", "pending")]]],
                                ["id", "document_model", "document_id", "printer_id", "file_content"])

            if result.get("result"):
                jobs = result["result"]
                if jobs:
                    print(f"\n🔍 {len(jobs)} trabajo(s) pendiente(s)")

                    for job in jobs:
                        # Obtener detalles de la impresora
                        printer_result = call_method(cookies, "direct.print.printer", "read",
                                                    [[job["printer_id"][0]]],
                                                    ["name", "printer_identifier", "connection_type", "ip_address", "port"])

                        if printer_result.get("result"):
                            printer_config = printer_result["result"][0]

                            # Actualizar a "imprimiendo"
                            update_job_status(cookies, job["id"], "printing")

                            # Intentar imprimir
                            success, message = print_job(job, printer_config)

                            if success:
                                print(f"✅ {message}")
                                update_job_status(cookies, job["id"], "success")
                            else:
                                print(f"❌ Error: {message}")
                                update_job_status(cookies, job["id"], "error", message)
                        else:
                            print(f"⚠️  No se pudo obtener info de impresora para trabajo #{job['id']}")

            time.sleep(CHECK_INTERVAL)

    except KeyboardInterrupt:
        print("\n\n🛑 Worker detenido.")

if __name__ == "__main__":
    main()
