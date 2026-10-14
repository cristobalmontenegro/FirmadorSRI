# 🇪🇨 Esquemas XSD del SRI (Ecuador)

Esquemas oficiales de comprobantes electrónicos del **Servicio de Rentas
Internas (SRI)** de Ecuador, usados para validar el XML **antes** de firmarlo.

| Archivo | Comprobante | Versión |
|:---|:---|:---|
| `factura_V1.1.0.xsd` | Factura | 1.1.0 |
| `NotaCredito_V1.1.0.xsd` | Nota de Crédito | 1.1.0 |
| `NotaDebito_V1.0.0.xsd` | Nota de Débito | 1.0.0 |
| `GuiaRemision_V1.1.0.xsd` | Guía de Remisión | 1.1.0 |
| `ComprobanteRetencion_V2.0.0.xsd` | Comprobante de Retención | 2.0.0 |
| `LiquidacionCompra_V1.1.0.xsd` | Liquidación de Compra | 1.1.0 |
| `xmldsig-core-schema.xsd` | Firma XML (XMLDSig) | — |

## Validación opcional

La validación contra XSD es **opcional**. Si no la configuras, el servidor
firma igualmente.

Para activarla, apunta `XSD_DIR` a esta carpeta:

```yaml
environment:
  - XSD_DIR=/app/xsd
```

El servidor intenta validar el XML entrante contra **cada** esquema de la
carpeta y acepta el documento si **alguno** lo valida.

## Origen

Los esquemas provienen de la documentación oficial de comprobantes
electrónicos del SRI (fichas técnicas). Si necesitas una versión más reciente,
descárgala desde el portal del SRI y reemplaza el archivo correspondiente.
---

# 🌐 Esquemas XSD del SRI (Ecuador) (English)

**🇬🇧 English**

> The full documentation is in Spanish above. This is a brief English summary.

- **Author:** Cristóbal Montenegro ([@cristobalmontenegro](https://github.com/cristobalmontenegro))
- **License:** MIT — see [`LICENSE`](../../LICENSE).

---

## ☕ Support me / Apóyame

**EN:** If any of this was useful, you can buy me a coffee. Thanks for the support!

**ES:** Si te resultó útil, puedes invitarme un café. ¡Gracias por el apoyo!

<p align="center">
  <a href="https://ko-fi.com/cristobalmontenegro" target="_blank">
    <img height="36" style="border:0px;height:36px;" src="https://storage.ko-fi.com/cdn/kofi6.png?v=6" border="0" alt="Buy Me a Coffee at ko-fi.com" />
  </a>
</p>

---

## 👤 Author / Autoría

**Cristóbal Montenegro**  
GitHub: [@cristobalmontenegro](https://github.com/cristobalmontenegro)