"""
Servidor HTTP para firmado de comprobantes electrónicos del SRI (Ecuador).

Expone un endpoint que recibe un comprobante en Base64 y devuelve el mismo
XML ya firmado (XAdES-BES). Pensado para correr en Docker y ser consumido por
cualquier sistema (ERP, SuiteScript, backend propio, etc.).

Configuración por variables de entorno:

    PORT=8080                 Puerto del servidor
    HOST=0.0.0.0              Interfaz de red
    ENDPOINT_PATH=/Firma/sri  Ruta del endpoint de firma
    P12_PATH=...              Ruta local al .p12 (se usa en modo LOCAL)
    XSD_DIR=...               Directorio opcional con XSD para validar antes de firmar

    FORCE_LOCAL_P12           Modo de certificado:
                              - definida con cualquier valor (p. ej. "1"):
                                modo LOCAL. Firma siempre con P12_PATH e ignora
                                `ruta`/`certificado` del request.                (por defecto)
                              - definida VACÍA (`FORCE_LOCAL_P12=`):
                                modo REQUEST. Firma con el `ruta` + `certificado`
                                que envíe el cliente (deben existir dentro del
                                contenedor, normalmente vía volumen montado).
"""
import os
import base64
import logging
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn

from firmador import firmar_xml, validar_con_xsd

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("firmador")

app = FastAPI(title="Servidor de Firmado SRI", version="2.0.0")

DIR = os.path.dirname(os.path.abspath(__file__))
P12_PATH = os.getenv("P12_PATH", os.path.join(DIR, "certificado.p12"))
XSD_DIR = os.getenv("XSD_DIR", "")

# Modo de certificado. Ver docstring del módulo.
USE_REQUEST_CERT = os.getenv("FORCE_LOCAL_P12", "1").strip() == ""


class FirmaRequest(BaseModel):
    psw: str
    xmlfirma: str
    certificado: Optional[str] = None
    numfactura: Optional[str] = None
    ruta: Optional[str] = None


class FirmaResponse(BaseModel):
    status: str
    xmlfirma: str


@app.get("/health")
def health():
    return {"status": "OK"}


ENDPOINT_PATH = os.getenv("ENDPOINT_PATH", "/Firma/sri")


@app.post(ENDPOINT_PATH, response_model=FirmaResponse)
def firmar(req: FirmaRequest):
    try:
        xml_decoded = base64.b64decode(req.xmlfirma)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Base64 inválido: {e}")

    if XSD_DIR:
        errores = validar_con_xsd(xml_decoded, XSD_DIR)
        if errores:
            logger.warning(f"XSD validation failed: {errores}")
            raise HTTPException(
                status_code=400,
                detail=f"XML no válido contra XSD: {'; '.join(errores)}",
            )

    # Resuelve el archivo .p12:
    #   - modo LOCAL:   certificado fijo P12_PATH.
    #   - modo REQUEST: ruta + certificado enviados por el cliente.
    if USE_REQUEST_CERT and req.ruta and req.certificado:
        p12_path = os.path.join(req.ruta, req.certificado)
    else:
        p12_path = P12_PATH

    logger.info(
        f"Firmando con certificado: {p12_path} "
        f"[{'from request' if p12_path != P12_PATH else 'local'}]"
    )

    try:
        signed = firmar_xml(xml_decoded, p12_path, req.psw)
    except Exception as e:
        logger.error(f"Error al firmar ({p12_path}): {e}")
        raise HTTPException(status_code=500, detail=f"Error de firma: {e}")

    xmlfirma_b64 = base64.b64encode(signed).decode("utf-8")

    logger.info(f"Firmado OK - numfactura: {req.numfactura or 'N/A'}")

    return FirmaResponse(status="OK", xmlfirma=xmlfirma_b64)


def main():
    port = int(os.getenv("PORT", "8080"))
    host = os.getenv("HOST", "0.0.0.0")
    logger.info(f"Servidor iniciado en {host}:{port}{ENDPOINT_PATH}")
    logger.info(f"Certificado: {P12_PATH}")
    if XSD_DIR:
        logger.info(f"Validación XSD activa: {XSD_DIR}")
    else:
        logger.info("Validación XSD: DESACTIVADA")
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
