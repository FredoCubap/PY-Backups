# Visión de PY-Backups

> Borrador para revisar. Lo marcado como **(propuesto)** no está decidido todavía.

## 1. Para qué existe

Hoy las copias de seguridad de la oficina se hacen a mano: se guardan en `.rar` seccionados, una carpeta por trabajador, en un disco externo. Funciona, pero depende de una persona, no avisa cuando alguien deja de respaldar y no deja ver el estado de un vistazo.

**PY-Backups hace que respaldar sea fácil para el admin y casi invisible para los trabajadores**, con un solo disco externo y sin depender de servicios de terceros.

Nació como solución temporal y rápida. La visión es que sea lo bastante sólida para dejar de ser temporal.

## 2. Qué problema resuelve

| Problema hoy | Cómo lo resuelve |
|---|---|
| Hay que acordarse de respaldar a cada persona | El script de cada PC copia solo lo que cambió, sin que nadie haga nada |
| No se sabe quién respaldó ni cuándo | Dashboard con estado, último respaldo y alertas por días sin copia |
| Los trabajadores piden copias por mensaje | Solicitud con nivel de urgencia y aprobación del admin |
| Los `.rar` viejos se hacen a mano | Snapshots comprimidos automáticos (`.tar.xz`, volúmenes de 2 GB) con carpeta por marca de tiempo |
| Cuesta recuperar un archivo | Restauración desde la web, sin descomprimir a mano |

## 3. Para quién

- **Admin (1 persona):** monitorea, aprueba solicitudes y decide dónde va cada copia.
- **Trabajadores (la oficina):** ven su histórico, piden copias y recuperan archivos.

Solo uso interno, dentro de la red de la oficina.

## 4. Principios

1. **Simple antes que completo.** Un solo proceso, una base SQLite, sin Docker ni Node.
2. **Los equipos salen hacia el servidor, nunca al revés.** Las PCs no abren puertos entrantes.
3. **Los datos no se pierden por accidente.** Nada se borra de golpe: el espejo no replica borrados y hay retención.
4. **Cada trabajador ve solo lo suyo.**
5. **El repo es público, los datos no.** Usuarios, MACs, tokens, bases de datos y copias nunca se suben.
6. **Se prueba antes de confiar.** Los tests no tocan la base real ni el disco real, y cada etapa se verifica con una PC de prueba antes de pasar a la siguiente.
7. **Los respaldos se verifican.** Una copia que nunca se comprobó no cuenta como copia.

## 5. Qué incluye y qué no

**Incluye:**
- Servidor web en la PC del admin, y script Python en cada PC.
- Identidad por MAC más token por PC.
- Espejo incremental, snapshots comprimidos y restauración.
- Solicitudes con urgencia, notificaciones y mensajes con el admin.
- Dashboard de monitoreo para el admin y panel propio para cada trabajador.

**No incluye (por ahora):**
- Acceso desde fuera de la oficina o desde internet.
- Respaldo de la nube, el correo o aplicaciones.
- Cifrado de las copias en el disco **(propuesto: etapa posterior)**.
- Integración con Net Control u otros sistemas. Se mantiene separado hasta que este esté estable.
- Soporte de otros sistemas operativos: solo Windows.

## 6. Cómo sabremos que funciona

- Todas las PCs registradas reportan y respaldan sin intervención.
- El admin sabe en menos de un minuto quién lleva días sin respaldar.
- Una restauración de prueba funciona desde la web, y los hashes del manifest coinciden.
- La compresión corre sin que la laptop del servidor se note lenta.
- Nunca ha llegado un dato real al repositorio.

## 7. Etapas (propuesto)

Cada etapa se prueba con una PC real antes de pasar a la siguiente.

| # | Etapa | Terminada cuando |
|---|---|---|
| 0 | Esqueleto | FastAPI responde, el test pasa. **Hecha** |
| 1 | Cimientos de datos y login admin | Base SQLite con migraciones, el admin entra con contraseña |
| 2 | Registro de PC | Código de un solo uso; el servidor guarda MAC y token de la PC; se rechaza una MAC que no coincide |
| 3 | Script con heartbeat | La PC aparece online/offline en el dashboard |
| 4 | Subida al espejo | Una carpeta de prueba se copia de forma incremental al disco, con comprobación del archivo marcador |
| 5 | Solicitud y atención | El trabajador solicita, el admin recibe aviso, pospone o atiende y se crea el snapshot `.tar.xz` |
| 6 | Panel del trabajador | Histórico, peso y regularidad; solo ve lo suyo |
| 7 | Restauración y verificación | Se baja un archivo desde la web; el manifest se verifica |
| 8 | Cola local y mensajes | La solicitud hecha con el servidor apagado se envía al volver |

**Primera entrega útil (propuesto): etapas 1 a 4.** Con eso ya se copia de forma automática y se ve quién respalda, que es lo que más duele hoy. Lo demás se suma encima.

## 8. Riesgos

| Riesgo | Plan |
|---|---|
| **Un solo disco externo:** si falla, se pierde todo | Una segunda copia en otro disco (regla 3-2-1), aunque sea manual al principio |
| **El disco se desconecta o cambia de letra** | Archivo marcador: el servidor se niega a escribir si no lo ve |
| **La MAC cambia** (cable y Wi-Fi, adaptadores nuevos) | Varias MACs por PC y re-registro con código nuevo |
| **La MAC se falsifica** | El token es la credencial real; la MAC solo ata usuario y equipo |
| **La compresión satura la laptop** | Una a la vez, prioridad baja, preset de LZMA ajustable |
| **La PC del admin es el único servidor** | Si está apagada no se respalda; el script reintenta al volver. A futuro, un equipo dedicado |
| **Datos reales en un repo público** | `.gitignore` estricto, datos de prueba inventados, revisar el `git status` antes de cada commit |
| **Privacidad de los trabajadores** | Avisar qué se copia y para qué antes de instalar nada (política de uso) |

## 9. Preguntas abiertas

1. ¿Cuántas PCs y cuántos GB por persona? Define el tamaño del disco y lo que tarda la primera copia.
2. ¿Qué carpetas se respaldan por defecto: Escritorio y Documentos, u otras?
3. ¿Cuánto tiempo se conservan los snapshots antes de borrarse (retención)?
4. ¿Dónde vive la segunda copia?
5. ¿Hay una política escrita que cubra el respaldo de los archivos de los trabajadores?
