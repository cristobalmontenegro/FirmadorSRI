"""
Ejemplo mínimo: firma `factura_sin_firmar.xml` usando `firmador.py` como
librería (sin levantar el servidor).

Uso:
    export P12_PATH=/ruta/a/tu/certificado.p12
    export P12_PSW='tu_contraseña'
    python examples/firmar_factura.py

Genera `examples/factura_firmada.xml`.
"""
import os
import sys

DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(DIR))  # raíz del repo (donde está firmador.py)

from firmador import firmar_xml  # noqa: E402

ENTRADA = os.path.join(DIR, "factura_sin_firmar.xml")
SALIDA = os.path.join(DIR, "factura_firmada.xml")


def main():
    p12_path = os.getenv("P12_PATH")
    password = os.getenv("P12_PSW", "")
    if not p12_path:
        print("ERROR: define P12_PATH con la ruta a tu archivo .p12")
        return 1
    if not os.path.exists(p12_path):
        print(f"ERROR: no existe el certificado: {p12_path}")
        return 1

    with open(ENTRADA, "rb") as f:
        xml_bytes = f.read()

    firmado = firmar_xml(xml_bytes, p12_path, password)

    with open(SALIDA, "wb") as f:
        f.write(firmado)

    print(f"OK: {ENTRADA} -> {SALIDA} ({len(firmado)} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
