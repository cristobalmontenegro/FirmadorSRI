# 🔐 certificados/

Coloca aquí tu(s) archivo(s) `.p12` (o `.pfx`) para que el contenedor pueda
leerlos.

El `docker-compose.yml` monta esta carpeta en el contenedor como solo-lectura:

```yaml
volumes:
  - ./certificados:/app/Firmado:ro
```

Ejemplo de estructura:

```
certificados/
└── certificado.p12      # tu certificado de firma electrónica
```

## ⚠️ Nunca subas certificados al repositorio

Los `.p12` contienen tu clave privada de firma. `.gitignore` ya bloquea
`*.p12`, `*.pfx`, `*.pem` y `*.key`, pero verifica siempre antes de hacer
`git add`.

Ajusta `P12_PATH` (modo LOCAL) o la ruta que envíe tu cliente (modo REQUEST)
para que coincidan con el nombre real de tu archivo.
---

# 🌐 certificados/ (English)

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