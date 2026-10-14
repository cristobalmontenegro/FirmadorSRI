# certificados/

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
