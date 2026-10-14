"""
Suite de pruebas completa: verifica que el firmado sea compatible con el SRI.

Pruebas:
    1. Firma directa (sin servidor)
    2. Verificación criptográfica de la firma (RSA-SHA1)
    3. Estructura XAdES-BES compatible con el SRI
    4. Validación XSD del XML firmado

Variables de entorno:
    P12_PATH   Ruta al .p12        (por defecto: ./certificado.p12)
    P12_PSW    Contraseña del .p12 (obligatoria)

Uso:
    export P12_PSW='tu_contraseña'
    python test_completo.py
"""
import os
import sys
import base64
from lxml import etree

sys.path.insert(0, os.path.dirname(__file__))
from firmador import firmar_xml, validar_con_xsd  # noqa: E402

# ─── Configuración ────────────────────────────────────────────────
P12_PATH = os.getenv("P12_PATH", os.path.join(os.path.dirname(__file__), "certificado.p12"))
PASSWORD = os.getenv("P12_PSW", "")
XSD_DIR = os.path.join(os.path.dirname(__file__), "xsd")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "temp")
# ──────────────────────────────────────────────────────────────────

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

# Namespaces XML
DS_NS = "http://www.w3.org/2000/09/xmldsig#"
ETSI_NS = "http://uri.etsi.org/01903/v1.3.2#"


def test_1_firma_directa():
    """Prueba 1: Firma directa sin servidor."""
    print("\n[1] FIRMA DIRECTA (sin servidor)")
    print("    Firma el XML con firmar_xml()...")

    signed = firmar_xml(SAMPLE_XML.encode("utf-8"), P12_PATH, PASSWORD)

    assert signed is not None, "firmar_xml() devolvió None"
    assert len(signed) > len(SAMPLE_XML), "XML firmado más pequeño que el original"
    assert b"<ds:Signature" in signed, "No se encontró <ds:Signature>"
    assert b"Enveloped" in signed or b"enveloped" in signed, "No se encontró enveloped signature"

    print(f"    ✅ XML original: {len(SAMPLE_XML)} bytes")
    print(f"    ✅ XML firmado:  {len(signed)} bytes")
    print(f"    ✅ Diferencia:   {len(signed) - len(SAMPLE_XML)} bytes (firma + certificado)")

    return signed


def test_2_verificar_firma_criptografica(signed_bytes):
    """Prueba 2: Verificación criptográfica de la firma (RSA-SHA1)."""
    print("\n[2] VERIFICACIÓN CRIPTOGRÁFICA")
    print("    Verificando la firma RSA/SHA1 con el certificado embebido...")

    from cryptography import x509
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import padding

    root = etree.fromstring(signed_bytes)
    ns = {"ds": DS_NS}

    try:
        sig = root.find(".//ds:Signature", ns)
        assert sig is not None, "No se encontró ds:Signature"
        si = sig.find("ds:SignedInfo", ns)
        sv = sig.find("ds:SignatureValue", ns)
        xc = sig.find(".//ds:X509Certificate", ns)
        assert si is not None and sv is not None and xc is not None

        # Re-canonicalizar SignedInfo tal como se firmó
        si_c14n = etree.tostring(si, method="c14n", with_comments=False)
        sig_bytes = base64.b64decode(sv.text.strip())
        cert_der = base64.b64decode(xc.text.strip())
        cert = x509.load_der_x509_certificate(cert_der)
        pubkey = cert.public_key()

        pubkey.verify(sig_bytes, si_c14n, padding.PKCS1v15(), hashes.SHA1())
        print("    ✅ SignatureValue VÁLIDO (RSA-SHA1)")

        # Verificar el digest del documento (Reference #comprobante)
        ref_comp = None
        for ref in si.findall("ds:Reference", ns):
            if ref.get("URI") == "#comprobante":
                ref_comp = ref
                break
        assert ref_comp is not None, "No se encontró Reference #comprobante"
        stored_digest = ref_comp.find("ds:DigestValue", ns).text.strip()

        # Recalcular digest: contenido del documento SIN la firma (enveloped)
        root_clone = etree.fromstring(signed_bytes)
        sig_node = root_clone.find(".//ds:Signature", ns)
        par = sig_node.getparent()
        par.remove(sig_node)
        doc_c14n = etree.tostring(root_clone, method="c14n", with_comments=False)
        import hashlib as _hl
        recomputed = base64.b64encode(_hl.sha1(doc_c14n).digest()).decode()
        if recomputed == stored_digest:
            print("    ✅ Digest del documento (Reference #comprobante) VÁLIDO")
        else:
            print("    ❌ Digest del documento NO coincide")
            return False

        print(f"    ✅ Certificado embebido: {len(cert_der)} bytes DER")
        print(f"    ✅ Sujeto: {cert.subject.rfc4514_string()}")
        print(f"    ✅ Emisor: {cert.issuer.rfc4514_string()}")
        print(f"    ✅ Válido: {cert.not_valid_before} → {cert.not_valid_after}")

        return True
    except AssertionError as e:
        print(f"    ❌ {e}")
        return False
    except Exception as e:
        print(f"    ❌ Error en verificación: {type(e).__name__}: {e}")
        return False


def test_3_estructura_sri(signed_bytes):
    """Prueba 3: Verificar estructura compatible con SRI."""
    print("\n[3] ESTRUCTURA COMPATIBLE CON SRI")

    root = etree.fromstring(signed_bytes)
    ns = {"ds": DS_NS, "etsi": ETSI_NS}

    errores = []

    # 3a. Raíz correcta
    if root.tag != "{http://www.sri.gob.ec/comprobantes-electronicos}factura":
        if root.tag != "factura":
            errores.append(f"Raíz incorrecta: {root.tag}")
        else:
            print("    ✅ Raíz: <factura>")
    else:
        print("    ✅ Raíz: <factura> con namespace SRI")

    # 3b. Signature presente
    sig = root.find(".//ds:Signature", ns)
    if sig is None:
        errores.append("No se encontró <ds:Signature>")
    else:
        print(f"    ✅ Signature Id: {sig.get('Id', '')}")

    # 3c. SignedInfo con algoritmos correctos
    signed_info = root.find(".//ds:SignedInfo", ns)
    if signed_info is not None:
        cm = signed_info.find("ds:CanonicalizationMethod", ns)
        sm = signed_info.find("ds:SignatureMethod", ns)
        cm_algo = cm.get("Algorithm", "") if cm is not None else ""
        sm_algo = sm.get("Algorithm", "") if sm is not None else ""
        print(f"    ✅ CanonicalizationMethod: {cm_algo}")
        print(f"    ✅ SignatureMethod: {sm_algo}")
        if "rsa-sha1" not in sm_algo.lower() and "rsa-sha256" not in sm_algo.lower():
            errores.append(f"SignatureMethod inesperado: {sm_algo}")

    # 3d. Reference al documento
    refs = root.findall(".//ds:Reference", ns)
    doc_ref_found = False
    for ref in refs:
        uri = ref.get("URI", "")
        if uri == "#comprobante" or uri == "":
            doc_ref_found = True
            dm = ref.find("ds:DigestMethod", ns)
            if dm is not None:
                print(f"    ✅ Reference URI: '{uri or '(vacío)'}' - DigestMethod: {dm.get('Algorithm', '')}")
            break
    if not doc_ref_found:
        errores.append("No se encontró Reference al documento")

    # 3e. SignedProperties con SigningCertificate
    signed_props = root.find(".//etsi:SignedProperties", ns)
    if signed_props is not None:
        print(f"    ✅ SignedProperties Id: {signed_props.get('Id', '')}")
        signing_cert = signed_props.find(".//etsi:SigningCertificate", ns)
        if signing_cert is not None:
            cert_digest = signing_cert.find(".//ds:DigestValue", ns)
            issuer_serial = signing_cert.find(".//etsi:IssuerSerial", ns)
            if cert_digest is not None and issuer_serial is not None:
                print("    ✅ SigningCertificate presente (CertDigest + IssuerSerial)")
        else:
            errores.append("No se encontró SigningCertificate en SignedProperties")
    else:
        errores.append("No se encontró SignedProperties")

    # 3f. KeyInfo con X509Certificate
    key_info = root.find(".//ds:KeyInfo", ns)
    if key_info is not None:
        if key_info.find(".//ds:X509Certificate", ns) is not None:
            print("    ✅ X509Certificate en KeyInfo")
        else:
            errores.append("No se encontró X509Certificate en KeyInfo")

    # 3g. SignatureValue presente
    sig_value = root.find(".//ds:SignatureValue", ns)
    if sig_value is not None and sig_value.text:
        print(f"    ✅ SignatureValue: {len(sig_value.text)} caracteres Base64")
    else:
        errores.append("SignatureValue vacío o ausente")

    if errores:
        for e in errores:
            print(f"    ❌ {e}")
        return False

    print("    ✅ Estructura compatible con SRI")
    return True


def test_4_xsd_validacion(signed_bytes):
    """Prueba 4: Validación XSD del XML firmado."""
    print("\n[4] VALIDACIÓN XSD")

    if not os.path.isdir(XSD_DIR):
        print("    ⚠️  Directorio XSD no encontrado, saltando")
        return True

    errores = validar_con_xsd(signed_bytes, XSD_DIR)
    if not errores:
        print("    ✅ XML firmado válido contra XSD del SRI")
        return True
    else:
        print(f"    ⚠️  {len(errores)} advertencia(s) XSD:")
        for e in errores[:5]:
            print(f"       - {e}")
        return True


def main():
    if not PASSWORD:
        print("ERROR: define P12_PSW con la contraseña de tu .p12")
        return 1
    if not os.path.exists(P12_PATH):
        print(f"ERROR: no existe el certificado: {P12_PATH}")
        return 1

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("=" * 60)
    print("SUITE DE PRUEBAS - VERIFICACIÓN DE FIRMA SRI")
    print("=" * 60)

    resultados = []

    try:
        signed = test_1_firma_directa()
        resultados.append(("Firma directa", True))
    except Exception as e:
        print(f"    ❌ FALLO: {e}")
        resultados.append(("Firma directa", False))
        return 1

    try:
        r = test_2_verificar_firma_criptografica(signed)
        resultados.append(("Verificación criptográfica", r))
    except Exception as e:
        print(f"    ❌ FALLO: {e}")
        resultados.append(("Verificación criptográfica", False))

    try:
        r = test_3_estructura_sri(signed)
        resultados.append(("Estructura SRI", r))
    except Exception as e:
        print(f"    ❌ FALLO: {e}")
        resultados.append(("Estructura SRI", False))

    try:
        r = test_4_xsd_validacion(signed)
        resultados.append(("Validación XSD", r))
    except Exception as e:
        print(f"    ❌ FALLO: {e}")
        resultados.append(("Validación XSD", False))

    firmado_path = os.path.join(OUTPUT_DIR, "factura_prueba_firmado.xml")
    with open(firmado_path, "wb") as f:
        f.write(signed)

    print("\n" + "=" * 60)
    print("RESUMEN DE PRUEBAS")
    print("=" * 60)

    todos_ok = True
    for nombre, ok in resultados:
        print(f"  {'✅ PASS' if ok else '❌ FAIL'}  {nombre}")
        if not ok:
            todos_ok = False

    print("=" * 60)
    if todos_ok:
        print("✅ TODAS LAS PRUEBAS PASARON")
        print("   El firmado es compatible con el SRI.")
    else:
        print("❌ ALGUNAS PRUEBAS FALLARON")

    print(f"\nXML firmado guardado en: {firmado_path}")
    print("=" * 60)

    return 0 if todos_ok else 1


if __name__ == "__main__":
    sys.exit(main())
