# Política de seguridad y publicación

Este repositorio es **público** y contiene exclusivamente código y muestras ficticias. No copiar documentación interna, expedientes, texto libre de tickets, consultas reales, esquemas completos, series de activos, topologías, usuarios, contraseñas, tokens, firmas ni bitácoras.

La configuración real se aloja fuera de Git (`TIC_CATALOG_PATH`, `TIC_PRIVATE_QA_CONFIG`, `TIC_QA_DSN_*`, `TIC_LLM_BASE_URL`, etc.). Los administradores determinan y documentan el perímetro y los permisos. SQL Server debe aplicar la restricción READ ONLY en el principal, además de los controles de la aplicación. Una consulta denegada es un límite de seguridad, no un obstáculo que deba sortearse.

Las hipótesis y procedimientos son propuestas hasta que una prueba independiente confirme el resultado. No ejecutar mutaciones, escalamiento de privilegios ni restablecimiento de contraseñas desde el agente.

El filtro de expresiones regulares **no garantiza anonimización**. Cualquier procesamiento de datos reales requiere revisión y autorización institucional y debe permanecer en infraestructura corporativa.
