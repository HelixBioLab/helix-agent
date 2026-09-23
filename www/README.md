# Helix Agent: sitio de descarga

Sitio estático publicado por [pages.yml](../.github/workflows/pages.yml) en
https://helixbiolab.github.io/helix-agent/.

La identidad visual sigue a Helix Learn: hélice de ADN, tipografía Georgia,
verde bosque `#244d3e`, salvia `#dcebb5` y papel `#fafbf8`.
El nombre público es Helix Agent; el ejecutable, las rutas de configuración y
los archivos publicados usan `helix`.

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

La portada reproduce `media/helix-agent-demo.mp4`, una copia del video de demostración
remultiplexada desde MOV sin recomprimir, con controles y sin reproducción automática.
`media/helix-agent-demo.jpg` es su imagen de portada.

En una primera visita, la descarga prioriza el sistema de escritorio informado por
el navegador (Windows, macOS o Linux); las elecciones manuales se conservan.
En móviles o plataformas desconocidas no se muestra una recomendación automática.
La distribución de Linux se elige manualmente porque los navegadores no la
[identifican de manera fiable](https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/User-agent_reduction).
