"""
Firmador XAdES-BES para comprobantes electrónicos del SRI (Ecuador).

Genera una firma XMLDSig *enveloped* con estructura **XAdES-BES** completa
(``SignedProperties`` incluido), que el validador del SRI acepta.

    Algoritmo : RSA-SHA1  (compatibilidad con el ecosistema; ver README)
    Firma     : enveloped sobre el nodo raíz con id="comprobante"
    References: #SignedProperties, #KeyInfo y #comprobante

Se puede usar como librería (:func:`firmar_xml`) o como script de línea de
comandos.
"""
import sys
import os
import base64
import datetime
import hashlib
import random
from lxml import etree
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding as asym_padding, rsa
from cryptography.hazmat.primitives.serialization import pkcs12

DS_NS = "http://www.w3.org/2000/09/xmldsig#"
ETSI_NS = "http://uri.etsi.org/01903/v1.3.2#"
C14N_URI = "http://www.w3.org/TR/2001/REC-xml-c14n-20010315"
ENVELOPED_URI = "http://www.w3.org/2000/09/xmldsig#enveloped-signature"
RSA_SHA1_URI = "http://www.w3.org/2000/09/xmldsig#rsa-sha1"
SHA1_URI = "http://www.w3.org/2000/09/xmldsig#sha1"
XADES_SIGNED_PROPS_URI = "http://uri.etsi.org/01903#SignedProperties"


def _b64sha1(data):
    return base64.b64encode(hashlib.sha1(data).digest()).decode()


def _get_issuer_dn(cert_obj):
    """Construye el X509IssuerName en formato RFC 2253 (orden invertido)."""
    name_map = {
        'countryName': 'C', 'organizationName': 'O',
        'organizationalUnitName': 'OU', 'commonName': 'CN',
        'serialNumber': 'serialNumber', 'localityName': 'L',
        'stateOrProvinceName': 'ST',
    }
    parts = []
    for a in cert_obj.issuer:
        short = name_map.get(a.oid._name, a.oid._name)
        parts.append(short + "=" + a.value)
    parts.reverse()
    return ','.join(parts)


def _rand_id():
    return random.randint(100000, 999999)


def validar_con_xsd(xml_bytes, xsd_dir):
    """Valida un XML contra los esquemas XSD del SRI.

    Devuelve una lista de errores (vacía si el XML es válido contra alguno de
    los esquemas presentes en ``xsd_dir``).
    """
    if not xsd_dir or not os.path.isdir(xsd_dir):
        return []
    try:
        xml_doc = etree.fromstring(xml_bytes)
    except Exception as e:
        return [f"Error al parsear XML: {e}"]

    errores = []
    for fname in sorted(os.listdir(xsd_dir)):
        if not fname.endswith(".xsd"):
            continue
        xsd_path = os.path.join(xsd_dir, fname)
        try:
            with open(xsd_path, "rb") as f:
                xsd_doc = etree.parse(f)
            schema = etree.XMLSchema(xsd_doc)
            if schema.validate(xml_doc):
                return []
            else:
                errores = [f"{fname}: {e}" for e in schema.error_log]
        except Exception:
            continue
    return errores if errores else ["No se encontró un XSD que valide el XML"]


def firmar_xml(xml_bytes, p12_path, password):
    """Firma un XML en formato XAdES-BES enveloped (RSA-SHA1).

    Args:
        xml_bytes: contenido del comprobante sin firmar (bytes).
        p12_path:  ruta al archivo PKCS#12 (.p12 / .pfx) con la clave privada.
        password:  contraseña del .p12.

    Returns:
        bytes del XML firmado, con declaración UTF-8.
    """
    with open(p12_path, "rb") as f:
        p12_data = f.read()

    private_key, cert_obj, _ = pkcs12.load_key_and_certificates(
        p12_data, password.encode()
    )

    cert_der = cert_obj.public_bytes(serialization.Encoding.DER)
    cert_b64 = base64.b64encode(cert_der).decode()
    cert_fp_sha1 = _b64sha1(cert_der)
    issuer_dn = _get_issuer_dn(cert_obj)
    serial = cert_obj.serial_number

    parser = etree.XMLParser(remove_blank_text=False, strip_cdata=False)
    doc = etree.fromstring(xml_bytes, parser)
    # El comprobante de entrada debe traer id="comprobante" en la raíz: es el
    # destino de la Reference enveloped. No modificamos el documento entrante.

    rand = _rand_id()
    sig_id = f"Signature{rand}"
    sig_props_id = f"{sig_id}-SignedProperties{_rand_id()}"
    ref_id = f"Reference-ID-{_rand_id()}"
    cert_id = f"Certificate{random.randint(1000000, 9999999)}"
    obj_id = f"{sig_id}-Object{_rand_id()}"
    # Patrón de Ids alineado con el usado habitualmente en el ecosistema
    # ecuatoriano (Signature-SignedInfo<nº> / SignatureValue<nº>).
    si_id = f"Signature-SignedInfo{_rand_id()}"
    sv_id = f"SignatureValue{_rand_id()}"
    signing_time = datetime.datetime.now(datetime.timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%S+00:00"
    )

    NSMAP = {'etsi': ETSI_NS, 'ds': DS_NS}
    signed_props = etree.Element(f"{{{ETSI_NS}}}SignedProperties", nsmap=NSMAP)
    signed_props.set('Id', sig_props_id)
    ssp = etree.SubElement(signed_props, f"{{{ETSI_NS}}}SignedSignatureProperties")
    st = etree.SubElement(ssp, f"{{{ETSI_NS}}}SigningTime")
    st.text = signing_time
    sc = etree.SubElement(ssp, f"{{{ETSI_NS}}}SigningCertificate")
    ce = etree.SubElement(sc, f"{{{ETSI_NS}}}Cert")

    cd = etree.SubElement(ce, f"{{{ETSI_NS}}}CertDigest")
    dm1 = etree.SubElement(cd, f"{{{DS_NS}}}DigestMethod")
    dm1.set('Algorithm', SHA1_URI)
    dv1 = etree.SubElement(cd, f"{{{DS_NS}}}DigestValue")
    dv1.text = cert_fp_sha1

    iss = etree.SubElement(ce, f"{{{ETSI_NS}}}IssuerSerial")
    xi = etree.SubElement(iss, f"{{{DS_NS}}}X509IssuerName")
    xi.text = issuer_dn
    xs = etree.SubElement(iss, f"{{{DS_NS}}}X509SerialNumber")
    xs.text = str(serial)

    sdo = etree.SubElement(signed_props, f"{{{ETSI_NS}}}SignedDataObjectProperties")
    dof = etree.SubElement(sdo, f"{{{ETSI_NS}}}DataObjectFormat")
    dof.set('ObjectReference', f'#{ref_id}')
    dd = etree.SubElement(dof, f"{{{ETSI_NS}}}Description")
    dd.text = "contenido comprobante"
    dm = etree.SubElement(dof, f"{{{ETSI_NS}}}MimeType")
    dm.text = "text/xml"

    # El KeyInfo se construye ANTES de SignedInfo porque una de las References
    # digiere este nodo (digest SHA1 del <ds:KeyInfo> canonicalizado completo).
    ki = etree.Element(f"{{{DS_NS}}}KeyInfo", nsmap={'ds': DS_NS})
    ki.set('Id', cert_id)
    xd = etree.SubElement(ki, f"{{{DS_NS}}}X509Data")
    xc = etree.SubElement(xd, f"{{{DS_NS}}}X509Certificate")
    xc.text = cert_b64
    if isinstance(private_key, rsa.RSAPrivateKey):
        nums = private_key.public_key().public_numbers()
        kv = etree.SubElement(ki, f"{{{DS_NS}}}KeyValue")
        rsa_kv = etree.SubElement(kv, f"{{{DS_NS}}}RSAKeyValue")
        mod = etree.SubElement(rsa_kv, f"{{{DS_NS}}}Modulus")
        mod.text = base64.b64encode(nums.n.to_bytes((nums.n.bit_length() + 7) // 8, 'big')).decode()
        exp = etree.SubElement(rsa_kv, f"{{{DS_NS}}}Exponent")
        exp.text = base64.b64encode(nums.e.to_bytes((nums.e.bit_length() + 7) // 8, 'big')).decode()
    keyinfo_digest = None  # se calcula sobre el nodo ya anidado, al final
    signed_info = etree.Element(f"{{{DS_NS}}}SignedInfo", nsmap=NSMAP)
    signed_info.set('Id', si_id)
    cm = etree.SubElement(signed_info, f"{{{DS_NS}}}CanonicalizationMethod")
    cm.set('Algorithm', C14N_URI)
    sm = etree.SubElement(signed_info, f"{{{DS_NS}}}SignatureMethod")
    sm.set('Algorithm', RSA_SHA1_URI)

    r1 = etree.SubElement(signed_info, f"{{{DS_NS}}}Reference")
    r1.set('Id', f"SignedPropertiesID{_rand_id()}")
    r1.set('Type', XADES_SIGNED_PROPS_URI)
    r1.set('URI', f'#{sig_props_id}')
    r1dm = etree.SubElement(r1, f"{{{DS_NS}}}DigestMethod")
    r1dm.set('Algorithm', SHA1_URI)
    r1dv = etree.SubElement(r1, f"{{{DS_NS}}}DigestValue")
    r1dv.text = "PLACEHOLDER"

    r2 = etree.SubElement(signed_info, f"{{{DS_NS}}}Reference")
    r2.set('URI', f'#{cert_id}')
    r2dm = etree.SubElement(r2, f"{{{DS_NS}}}DigestMethod")
    r2dm.set('Algorithm', SHA1_URI)
    r2dv = etree.SubElement(r2, f"{{{DS_NS}}}DigestValue")
    r2dv.text = "PLACEHOLDER"

    r3 = etree.SubElement(signed_info, f"{{{DS_NS}}}Reference")
    r3.set('Id', ref_id)
    r3.set('URI', '#comprobante')
    tf = etree.SubElement(r3, f"{{{DS_NS}}}Transforms")
    t1 = etree.SubElement(tf, f"{{{DS_NS}}}Transform")
    t1.set('Algorithm', ENVELOPED_URI)
    r3dm = etree.SubElement(r3, f"{{{DS_NS}}}DigestMethod")
    r3dm.set('Algorithm', SHA1_URI)
    r3dv = etree.SubElement(r3, f"{{{DS_NS}}}DigestValue")
    r3dv.text = "PLACEHOLDER"

    sve = etree.Element(f"{{{DS_NS}}}SignatureValue", nsmap={'ds': DS_NS})
    sve.set('Id', sv_id)
    sve.text = ""

    qp = etree.Element(f"{{{ETSI_NS}}}QualifyingProperties", nsmap=NSMAP)
    qp.set('Target', f'#{sig_id}')
    qp.append(signed_props)
    oe = etree.Element(f"{{{DS_NS}}}Object", nsmap={'ds': DS_NS})
    oe.set('Id', obj_id)
    oe.append(qp)

    sig = etree.Element(f"{{{DS_NS}}}Signature", nsmap=NSMAP)
    sig.set('Id', sig_id)
    sig.append(signed_info)
    sig.append(sve)
    sig.append(ki)
    sig.append(oe)
    doc.append(sig)

    # ── Cálculo de digests sobre los nodos YA anidados ──────────────
    # La canonicalización usa el contexto real de namespaces del documento.
    ki_ctx = doc.find(f".//{{{DS_NS}}}KeyInfo[@Id='{cert_id}']")
    sp_ctx = doc.find(f".//{{{ETSI_NS}}}SignedProperties[@Id='{sig_props_id}']")
    si_ctx = doc.find(f".//{{{DS_NS}}}SignedInfo[@Id='{si_id}']")

    # 1. digest del comprobante con la firma excluida (transform enveloped)
    doc.remove(sig)
    doc_c14n = etree.tostring(doc, method='c14n', with_comments=False)
    doc_digest = _b64sha1(doc_c14n)
    doc.append(sig)

    # 2. digest de SignedProperties y de KeyInfo (con la firma presente)
    sp_digest = _b64sha1(etree.tostring(sp_ctx, method='c14n', with_comments=False))
    keyinfo_digest = _b64sha1(etree.tostring(ki_ctx, method='c14n', with_comments=False))

    # 3. rellenar las References
    for ref in signed_info.findall(f"{{{DS_NS}}}Reference"):
        uri = ref.get('URI')
        if uri == f'#{sig_props_id}':
            ref.find(f"{{{DS_NS}}}DigestValue").text = sp_digest
        elif uri == f'#{cert_id}':
            ref.find(f"{{{DS_NS}}}DigestValue").text = keyinfo_digest
        elif uri == '#comprobante':
            ref.find(f"{{{DS_NS}}}DigestValue").text = doc_digest

    # 4. SignatureValue se calcula sobre el SignedInfo ya rellenado
    si_c14n = etree.tostring(si_ctx, method='c14n', with_comments=False)
    sv = private_key.sign(si_c14n, asym_padding.PKCS1v15(), hashes.SHA1())
    sve.text = base64.b64encode(sv).decode()

    return etree.tostring(doc, xml_declaration=True, encoding='UTF-8', standalone=False)


def main_cli():
    """Punto de entrada para línea de comandos."""
    if len(sys.argv) != 5:
        print("Uso: python firmador.py <xml_in> <p12_path> <password> <xml_out>")
        sys.exit(1)
    try:
        with open(sys.argv[1], "rb") as f:
            xml_bytes = f.read()
        signed = firmar_xml(xml_bytes, sys.argv[2], sys.argv[3])
        with open(sys.argv[4], "wb") as f:
            f.write(signed)
        print("OK - FIRMADO XAdES-BES")
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main_cli()
