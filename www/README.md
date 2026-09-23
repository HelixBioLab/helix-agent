# Helix Agent: sitio de descarga

Sitio estático publicado por [pages.yml](../.github/workflows/pages.yml) en
https://webiwabou.github.io/bioinformatica.org/.

La identidad visual sigue a Helix Learn: hélice de ADN, tipografía Georgia,
verde bosque `#244d3e`, salvia `#dcebb5` y papel `#fafbf8`.
El nombre público es Helix Agent; el ejecutable, las rutas de configuración y
los archivos publicados conservan `bioinformatica` por compatibilidad.

`index.html`, `styles.css`, `site.js` y `favicon.svg` no necesitan compilación.
Los selectores de idioma y sistema funcionan con CSS incluso sin JavaScript.
El script recuerda las preferencias, detecta el sistema inicial y permite copiar
los comandos. No hay fuentes, imágenes ni scripts de terceros.

El workflow copia `install` e `install.ps1` desde la raíz al sitio publicado.
Para revisar también esos enlaces en local, prepara una carpeta temporal con
`www/` y ambos instaladores, y sírvela con un servidor HTTP estático.

La guía ofrece wget, curl nativo, PowerShell/WSL y descarga desde GitHub Releases.
Las instrucciones por distribución instalan los requisitos con su gestor de
paquetes; el agente se instala sin sudo. El instalador usa un descargador nativo
para los metadatos y los archivos, evitando los ejecutables de Snap por sus
[restricciones de acceso a archivos](https://snapcraft.io/docs/explanation/security/security-policies/).
