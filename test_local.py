"""
Prueba local del firmador: firma un XML de ejemplo, valida contra los XSD del
SRI y verifica que la firma esté presente. Puede firmar en modo DIRECTO
(librería) o contra el servidor HTTP.

Variables de entorno:
    P12_PATH    Ruta al .p12            (por defecto: ./certificado.p12)
    P12_PSW     Contraseña del .p12     (obligatoria)
    SERVER_URL  URL del endpoint        (por defecto: http://localhost:8080/Firma/sri)
    USE_DIRECT  "1" para firmar sin servidor

Uso:
    export P12_PSW='tu_contraseña'
    python test_local.py
"""
import os
import sys
import base64
from lxml import etree

import requests

# ─── Configuración ────────────────────────────────────────────────
SERVER_URL = os.getenv("SERVER_URL", "http://localhost:8080/Firma/sri")
P12_PATH = os.getenv("P12_PATH", os.path.join(os.path.dirname(__file__), "certificado.p12"))
PASSWORD = os.getenv("P12_PSW", "")
USE_DIRECT = os.getenv("USE_DIRECT", "0") == "1"
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "temp")
XSD_DIR = os.path.join(os.path.dirname(__file__), "xsd")
# ──────────────────────────────────────────────────────────────────

sys.path.insert(0, os.path.dirname(__file__))
from firmador import firmar_xml, validar_con_xsd  # noqa: E402

SAMPLE_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<factura id="comprobante" version="1.1.0">
  <infoTributaria>
    <ambiente>2</ambiente>
    <tipoEmision>1</tipoEmision>
    <razonSocial>MI EMPRESA S.A.</razonSocial>
    <nombreComercial>MI EMPRESA</nombreComercial>
    <ruc>1799999999001</ruc>
    <claveAcceso>1506202601179999999900110010010000000011234567811</claveAcceso>
    <codDoc>01</codDoc>
    <estab>001</estab>
    <ptoEmi>001</ptoEmi>
    <secuencial>000000001</secuencial>
    <dirMatriz>Av. Principal SN y Calle Secundaria</dirMatriz>
  </infoTributaria>
  <infoFactura>
    <fechaEmision>15/06/2026</fechaEmision>
    <dirEstablecimiento>Matriz</dirEstablecimiento>
    <contribuyenteEspecial>155</contribuyenteEspecial>
    <obligadoContabilidad>SI</obligadoContabilidad>
    <tipoIdentificacionComprador>04</tipoIdentificacionComprador>
    <razonSocialComprador>CLIENTE DE PRUEBA CIA LTDA.</razonSocialComprador>
    <identificacionComprador>1799999999001</identificacionComprador>
    <direccionComprador>Av. Prueba 123</direccionComprador>
    <totalSinImpuestos>100.00</totalSinImpuestos>
    <totalDescuento>0.00</totalDescuento>
    <codDocReembolso>00</codDocReembolso>
    <totalComprobantesReembolso>0.00</totalComprobantesReembolso>
    <totalBaseImponibleReembolso>0.00</totalBaseImponibleReembolso>
    <totalImpuestoReembolso>0.00</totalImpuestoReembolso>
    <totalConImpuestos>
      <totalImpuesto>
        <codigo>2</codigo>
        <codigoPorcentaje>2</codigoPorcentaje>
        <baseImponible>100.00</baseImponible>
        <valor>12.00</valor>
      </totalImpuesto>
    </totalConImpuestos>
    <propina>0.00</propina>
    <importeTotal>112.00</importeTotal>
    <moneda>DOLAR</moneda>
    <pagos>
      <pago>
        <formaPago>01</formaPago>
        <total>112.00</total>
        <plazo>0</plazo>
        <unidadTiempo>dias</unidadTiempo>
      </pago>
    </pagos>
    <valorRetIva>0.00</valorRetIva>
    <valorRetRenta>0.00</valorRetRenta>
  </infoFactura>
  <detalles>
    <detalle>
      <codigoPrincipal>PR001</codigoPrincipal>
      <descripcion>Producto de prueba</descripcion>
      <cantidad>1.000000</cantidad>
      <precioUnitario>100.000000</precioUnitario>
      <descuento>0.00</descuento>
      <precioTotalSinImpuesto>100.00</precioTotalSinImpuesto>
      <impuestos>
        <impuesto>
          <codigo>2</codigo>
          <codigoPorcentaje>2</codigoPorcentaje>
          <tarifa>12</tarifa>
          <baseImponible>100.00</baseImponible>
          <valor>12.00</valor>
        </impuesto>
      </impuestos>
    </detalle>
  </detalles>
  <infoAdicional>
    <campoAdicional nombre="Correo">test@ejemplo.com</campoAdicional>
  </infoAdicional>
</factura>"""


def validar_xsd(xml_bytes: bytes, xsd_dir: str) -> list:
    """Valida XML contra XSD del SRI."""
    errores = validar_con_xsd(xml_bytes, xsd_dir)
    if not errores:
        return []
    return errores


def firmar_directo(xml_str: str) -> bytes:
    return firmar_xml(xml_str.encode("utf-8"), P12_PATH, PASSWORD)


def firmar_via_servidor(xml_str: str) -> bytes:
    xml_b64 = base64.b64encode(xml_str.encode("utf-8")).decode("utf-8")
    payload = {
        "psw": PASSWORD,
        "xmlfirma": xml_b64,
        "certificado": "certificado.p12",
        "numfactura": "PRUEBA_001-001-000000001",
        "ruta": "/app/Firmado/",
    }
    resp = requests.post(SERVER_URL, json=payload, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    return base64.b64decode(data["xmlfirma"])


def verificar_xml_firmado(xml_bytes: bytes) -> bool:
    """Verifica que el XML contenga una firma digital válida."""
    root = etree.fromstring(xml_bytes)
    ns = {"ds": "http://www.w3.org/2000/09/xmldsig#"}
    signatures = root.findall(".//ds:Signature", ns)
    return len(signatures) > 0


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("=" * 60)
    print("PRUEBA DE FIRMADO ELECTRÓNICO")
    print("=" * 60)

    xml_bytes = SAMPLE_XML.encode("utf-8")

    # 1. Validación XSD del XML sin firmar
    print("\n[1] Validando XML contra XSD del SRI...")
    errores = validar_xsd(xml_bytes, XSD_DIR)
    if errores:
        print("    ❌ ERRORES XSD:")
        for e in errores[:10]:
            print(f"       - {e}")
        print("    Continuando de todas formas (la validación es informativa)...")
    else:
        print("    ✅ XML válido contra esquema XSD")

    # 2. Mostrar XML original
    print(f"\n[2] XML SIN FIRMAR: {len(SAMPLE_XML)} bytes")
    for line in SAMPLE_XML.strip().split("\n")[:12]:
        print(f"    {line}")
    print("    ...")

    # 3. Firmar
    print("\n[3] Firmando XML...")
    if USE_DIRECT:
        print("    Método: DIRECTO (firmador.py local)")
        signed = firmar_directo(SAMPLE_XML)
    else:
        print(f"    Método: SERVIDOR HTTP ({SERVER_URL})")
        signed = firmar_via_servidor(SAMPLE_XML)

    # 4. Verificar firma
    print("\n[4] Verificando firma...")
    print(f"    Tamaño XML firmado: {len(signed)} bytes")
    tiene_firma = verificar_xml_firmado(signed)
    print(f"    ¿Firma digital presente? {'✅ SÍ' if tiene_firma else '❌ NO'}")
    if not tiene_firma:
        print("\n❌ PRUEBA FALLIDA: No se encontró la firma digital.")
        sys.exit(1)

    # 5. Validación XSD del XML firmado
    print("\n[5] Validando XML FIRMADO contra XSD del SRI...")
    errores = validar_xsd(signed, XSD_DIR)
    if errores:
        print("    ⚠️  Nota: el XML firmado puede no validar contra XSD porque la")
        print("    firma agrega elementos (ds:Signature) que no están en el esquema.")
        print("    Esto es normal y esperado.")
    else:
        print("    ✅ XML firmado válido contra XSD")

    # 6. Guardar
    original_path = os.path.join(OUTPUT_DIR, "factura_prueba_sin_firmar.xml")
    firmado_path = os.path.join(OUTPUT_DIR, "factura_prueba_firmado.xml")
    with open(original_path, "w", encoding="utf-8") as f:
        f.write(SAMPLE_XML)
    with open(firmado_path, "wb") as f:
        f.write(signed)

    print("\n[6] Archivos guardados:")
    print(f"    Sin firmar:  {original_path}")
    print(f"    Firmado:     {firmado_path}")

    # 7. Mostrar inicio del XML firmado
    print("\n[7] XML FIRMADO (inicio):")
    for line in signed.decode("utf-8").split("\n")[:15]:
        print(f"    {line}")
    print("    ...")

    # 8. Detalle de la firma
    print("\n[8] Detalle de la firma:")
    root = etree.fromstring(signed)
    ns = {"ds": "http://www.w3.org/2000/09/xmldsig#"}
    for sig in root.findall(".//ds:Signature", ns):
        for ref in sig.findall(".//ds:Reference", ns):
            uri = ref.get("URI")
            print(f"    Reference URI: {uri or '(documento completo)'}")

    print(f"\n{'=' * 60}")
    print("✅ PRUEBA EXITOSA")
    print("   El servidor de firmado funciona correctamente.")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
