# Flujo de PY-Backups

Sistema de copias de seguridad para la oficina. Un servidor en la PC del admin, un script en cada PC de los trabajadores y una web para ver y pedir. **Este repo es público: aquí solo hay diseño y código; los datos reales (usuarios, MACs, tokens, copias) viven fuera.**

## Decisiones tomadas

| Tema | Decisión |
|---|---|
| Servidor | FastAPI en un solo proceso, sin Docker |
| Base de datos | SQLite (SQLAlchemy + Alembic), archivo fuera del repo |
| Web | Jinja + HTMX servidos por el mismo FastAPI, sin Node |
| Script de las PCs | Python stdlib, sale hacia el servidor, nunca recibe conexiones |
| Identidad | MAC resuelta por el servidor (ARP) + token por PC. La MAC ata al usuario con su equipo; el token es la credencial |
| Compresión | `.tar.xz` en volúmenes de 2 GB (`tarfile` + `lzma`), con manifest SHA-256 por volumen |
| Copia | Espejo incremental (`actual\`) + snapshot comprimido desde el espejo al atender |
| Zona horaria | La local del servidor |
| Git | Commits directos a `main` mientras haya un solo desarrollador |

## Actores

- **Admin** (dueño del servidor y del disco externo).
- **Trabajador** (una persona, una o más PCs registradas).
- **Script** (corre en la PC del trabajador; reporta y sube).

## Admin

1. Entra con usuario y contraseña.
2. **Dashboard:** usuarios registrados, quiénes están online (el script reportó hace menos de 5 min), último respaldo, peso total, regularidad, alertas por días sin copia.
3. **Registrar PC:** crea el "hueco" de un usuario y obtiene un código de un solo uso. La PC lo canjea y quedan guardados su MAC y su token. Una PC puede tener varias MACs (Wi-Fi y cable).
4. **Notificación de solicitud:** "XXX solicita un backup [normal | alta | urgente]". Botones:
   - **Postergar** (hasta una hora o fecha).
   - **Atender:** menú para elegir dónde guardar; el servidor comprime desde el espejo en una carpeta con la marca de tiempo exacta.

## Trabajador

1. Entra con su **nombre de usuario**. El servidor mira desde qué MAC llega: si el nombre no coincide con la MAC registrada, no entra.
2. **Panel:** histórico de copias, métricas de peso y regularidad, contacto con el admin.
3. **Solicitar respaldo:** crea la solicitud con un nivel de urgencia.
4. Restaurar: descarga archivos o carpetas desde la web (el servidor descomprime bajo demanda).

## Solicitud

Estados: `pendiente` → `pospuesta (hasta X)` → `atendida` → `completada` | `fallida`. El trabajador ve el estado de lo que pidió.

## Fuera de línea

Si el servidor está apagado la web no carga, así que la cola local vive en el script: un acceso directo "Solicitar respaldo" guarda la solicitud o el mensaje y lo envía cuando el servidor vuelva.

## Reglas de seguridad

- La MAC se puede falsificar: no es credencial, solo une usuario con equipo.
- Un token por PC, con alcance limitado (subir solo lo suyo), caducidad y revocación individual.
- Todo se filtra por trabajador por defecto: nadie ve lo de otro.
- Log de auditoría: quién descargó o restauró qué.
- Antes de escribir en el disco externo se comprueba un archivo marcador; si no está, el servidor se niega a recibir copias.
- Los tests nunca tocan la base real ni el disco real.

## Orden de construcción

1. Esqueleto (hecho): FastAPI + página + test.
2. Login admin y registro de PC (usuario + MAC + token).
3. Script con heartbeat y estado online.
4. Solicitud → notificación → atender.
5. Subida al espejo y snapshot comprimido.
6. Panel del trabajador.
7. Mensajes y cola local.
