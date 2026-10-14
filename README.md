<h1 align="center">FirmadorSRI 🇪🇨</h1>

<p align="center">
  <strong>Servidor de firmado electrónico XAdES-BES para el SRI Ecuador</strong><br>
  <em>Self-hosted XAdES-BES signing server for Ecuador's SRI e-invoices</em>
</p>

<p align="center">
  <img alt="Python" src="https://img.shields.io/badge/Python-3.12-3776AB?style=flat&logo=python&logoColor=white">
  <img alt="FastAPI" src="https://img.shields.io/badge/FastAPI-0.115-009688?style=flat&logo=fastapi&logoColor=white">
  <img alt="Docker" src="https://img.shields.io/badge/Docker-ready-2496ED?style=flat&logo=docker&logoColor=white">
  <img alt="XAdES-BES" src="https://img.shields.io/badge/XML-XAdES--BES-8A2BE2?style=flat">
  <img alt="License" src="https://img.shields.io/badge/License-MIT-green?style=flat">
</p>

---

## 🇪🇸 Español

**FirmadorSRI** es un servidor de firmado electrónico **autocontenido** para los
comprobantes del **Servicio de Rentas Internas (SRI)** de Ecuador. Recibe un
comprobante en XML (factura, nota de crédito/débito, guía de remisión,
comprobante de retención o liquidación de compra), le aplica una firma
**XAdES-BES** y lo devuelve listo para enviar al SRI.

Es **agnóstico del sistema que lo consume**: cualquier ERP, backend, script o
SuiteScript puede firmar contra su endpoint HTTP. No depende de servicios de
firmado de terceros.

### ✨ Características

- **XAdES-BES completo**: firma *enveloped* con `SignedProperties`, `SigningCertificate`, `DataObjectFormat` y `KeyInfo`.
- **API HTTP simple**: un `POST` con el XML en Base64 y devuelve el XML firmado.
- **Dockerizado**: levanta en un comando, sin instalar nada más.
- **Validación XSD opcional** contra los esquemas oficiales del SRI (incluidos en `xsd/`).
- **Dos modos de certificado**: certificado fijo local o certificado por petición.
- **Uso como librería**: `firmar_xml(xml_bytes, p12_path, password)`.

### 🏗️ Cómo funciona

```
┌─────────────┐   POST /Firma/sri (JSON, XML en Base64)   ┌──────────────────┐
│ Tu sistema  │ ────────────────────────────────────────▶ │   FirmadorSRI    │
│ (ERP, etc.) │                                           │  (FastAPI/Docker)│
└─────────────┘ ◀──────────────────────────────────────── └──────────────────┘
                  { "status": "OK", "xmlfirma": "<Base64>" }         │
                                                                     ▼
                                                        firma XAdES-BES con tu .p12
```

### 🚀 Inicio rápido

```bash
# 1. Clona
git clone https://github.com/cristobalmontenegro/FirmadorSRI.git
cd FirmadorSRI

# 2. Coloca tu certificado
cp /ruta/tu_certificado.p12 certificados/certificado.p12

# 3. Ajusta P12_PATH en docker-compose.yml si tu archivo se llama distinto

# 4. Levanta
docker compose up -d --build

# 5. Comprueba
curl http://localhost:8099/health
# {"status":"OK"}
```

### ⚙️ Configuración (variables de entorno)

| Variable | Por defecto | Descripción |
|:---|:---|:---|
| `PORT` | `8080` | Puerto interno del servidor |
| `HOST` | `0.0.0.0` | Interfaz de red |
| `ENDPOINT_PATH` | `/Firma/sri` | Ruta del endpoint de firma |
| `P12_PATH` | `./certificado.p12` | Ruta al `.p12` (modo LOCAL) |
| `XSD_DIR` | *(vacío)* | Carpeta con XSD para validar antes de firmar (vacío = desactivado) |
| `FORCE_LOCAL_P12` | `1` | Modo de certificado (ver abajo) |

#### Modos de certificado

| Modo | Configuración | Comportamiento |
|:---|:---|:---|
| **LOCAL** (por defecto) | `FORCE_LOCAL_P12=1` | Firma **siempre** con `P12_PATH` e ignora lo que venga en la petición. |
| **REQUEST** | `FORCE_LOCAL_P12=` *(vacío)* | Firma con `ruta` + `certificado` enviados en cada petición. Útil para multi-empresa. |

> En modo REQUEST, el `.p12` debe existir **dentro del contenedor** (normalmente vía un volumen montado) y la ruta del volumen debe coincidir **exactamente** con la enviada en la petición.

### 🔌 API

**`POST {ENDPOINT_PATH}`** — firma un comprobante.

**Request** (`application/json`):

| Campo | Tipo | Obligatorio | Descripción |
|:---|:---|:---:|:---|
| `xmlfirma` | string | ✅ | Comprobante XML codificado en **Base64** |
| `psw` | string | ✅ | Contraseña del `.p12` |
| `certificado` | string | — | Nombre del `.p12` (modo REQUEST) |
| `ruta` | string | — | Carpeta del `.p12` (modo REQUEST) |
| `numfactura` | string | — | Identificador para el log (no afecta la firma) |

**Response** (`application/json`):

```json
{
  "status": "OK",
  "xmlfirma": "<XML firmado en Base64>"
}
```

**Ejemplo con `curl`:**

```bash
B64=$(base64 -w0 ejemplos/factura_sin_firmar.xml)

curl -s -X POST http://localhost:8099/Firma/sri \
  -H "Content-Type: application/json" \
  -d "{\"psw\":\"TU_CONTRASEÑA\",\"xmlfirma\":\"$B64\",\"numfactura\":\"001-001-000000001\"}" \
  | python3 -c "import sys,json,base64;open('firmado.xml','wb').write(base64.b64decode(json.load(sys.stdin)['xmlfirma']))"
```

**`GET /health`** — devuelve `{"status":"OK"}` (útil para *healthchecks*).

### 🔐 Seguridad — léelo antes de producción

- **RSA-SHA1 (legacy).** El SRI aún acepta firmas **RSA-SHA1**, y es el algoritmo
  que usa este firmador por compatibilidad. Es criptográficamente más débil que
  SHA-256; si tu entorno del SRI admite SHA-256, migra el firmador cuando sea
  viable (el código está aislado en `firmador.py`).
- **HTTPS.** El servidor habla **HTTP plano**; la contraseña del `.p12` (`psw`)
  viaja en el cuerpo de la petición. **No lo expongas a Internet sin TLS.**
  Ponlo detrás de un *reverse proxy* (Nginx, Caddy, Traefik) con HTTPS, o
  restringe el acceso por firewall/VPN a las IPs de tus emisores.
- **Nunca subas tu `.p12` al repositorio.** `.gitignore` ya bloquea
  `*.p12`, `*.pfx`, `*.pem` y `*.key`.
- Monta la carpeta de certificados como **solo lectura** (`:ro`), como hace el
  `docker-compose.yml` incluido.

### 🧪 Pruebas

```bash
# Dependencias
pip install -r requirements.txt

export P12_PATH=/ruta/tu_certificado.p12
export P12_PSW='tu_contraseña'

python test_completo.py    # firma + verificación criptográfica + estructura + XSD
python test_local.py       # demo vía librería o servidor HTTP
```

La suite `test_completo.py` verifica el `SignatureValue`, el *digest* del
documento y la estructura XAdES-BES completa, y devuelve código de salida ≠ 0
si algo falla.

### 📁 Estructura

```
FirmadorSRI/
├── firmador.py            # Núcleo: firma XAdES-BES + validación XSD
├── servidor.py            # API FastAPI
├── test_completo.py       # Suite de verificación
├── test_local.py          # Prueba de humo (librería / HTTP)
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── xsd/                   # Esquemas oficiales del SRI
├── certificados/          # Aquí van tus .p12 (ignorados por git)
└── examples/              # XML de ejemplo y script de firmado
```

### ⚖️ Aviso legal

Este proyecto es una herramienta técnica **no oficial**, sin vínculo con el
**SRI** ni con ningún proveedor de certificados. El uso de la firma electrónica
y el cumplimiento normativo son responsabilidad exclusiva del usuario. Verifica
siempre que tus comprobantes sean **autorizados** por el SRI en su portal.

---

## 🇬🇧 English

**FirmadorSRI** is a **self-contained** electronic signing server for the tax
documents of Ecuador's **Internal Revenue Service (SRI)**. It takes an XML
document (invoice, credit/debit note, waybill, withholding receipt or purchase
settlement), applies an **XAdES-BES** signature and returns it ready to submit.

It is **agnostic to the consuming system**: any ERP, backend, script or
SuiteScript can sign against its HTTP endpoint. No third-party signing service
required.

### ✨ Features

- **Full XAdES-BES**: *enveloped* signature with `SignedProperties`, `SigningCertificate`, `DataObjectFormat` and `KeyInfo`.
- **Simple HTTP API**: one `POST` with the Base64 XML, get the signed XML back.
- **Dockerized**: up and running in one command.
- **Optional XSD validation** against the official SRI schemas (bundled in `xsd/`).
- **Two certificate modes**: fixed local certificate or per-request certificate.
- **Library usage**: `firmar_xml(xml_bytes, p12_path, password)`.

### ⚙️ Configuration

Same environment variables and API as described in the Spanish section above.

### 🔐 Security notes

- **RSA-SHA1 (legacy)** for SRI compatibility — weaker than SHA-256; migrate when feasible.
- **HTTP only**: the `.p12` password travels in the request body. **Put it behind HTTPS** (reverse proxy) or restrict access by firewall/VPN.
- **Never commit** your `.p12`; `.gitignore` already excludes `*.p12`, `*.pfx`, `*.pem` and `*.key`.
- Mount the certificates folder **read-only** (`:ro`).

### ⚖️ Disclaimer

Unofficial technical tool, not affiliated with the **SRI** or any certificate
provider. Electronic signing and regulatory compliance are the sole
responsibility of the user.

---

## ☕ Apóyame / Support me

**ES:** Si este proyecto te resultó útil, puedes invitarme un café. ¡Gracias!
**EN:** If this project was useful to you, you can buy me a coffee. Thanks!

<p align="center">
  <a href="https://ko-fi.com/cristobalmontenegro" target="_blank">
    <img height="36" style="border:0px;height:36px;" src="https://storage.ko-fi.com/cdn/kofi6.png?v=6" border="0" alt="Buy Me a Coffee at ko-fi.com" />
  </a>
</p>

## 📄 Licencia / License

[MIT](LICENSE) © 2026 Cristóbal Montenegro
