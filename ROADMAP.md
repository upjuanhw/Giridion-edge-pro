# Gridiron Edge Pro — plan maestro

## Objetivo
Dashboard móvil NFL/NCAAF inspirado en un mercado financiero y la cartelera de Caliente. Datos verificados, pronósticos probabilísticos auditables y control de exposición. **No publicar probabilidades como calibradas ni cuotas como vigentes sin evidencia.**

## Estado confirmado (2026-10-10)
- [x] Repositorio público y despliegue automático Render.
- [x] Aplicación web accesible en Android mediante acceso directo.
- [x] Inicio en «Partidos» con navegación visible.
- [x] Marcadores ESPN públicos (best effort; sin SLA).
- [x] Importación CSV de cuotas.
- [x] Calculadora EV y simulador manual.
- [x] Baseline histórico y backtesting cronológico experimental.
- [x] Carga de temporadas ESPN implementada (integridad aún sin auditar).

## Sprint 1 — interfaz y confiabilidad
- [x] Filtros por fecha, estado y equipo; horarios locales de México.
- [ ] Tarjetas con escudos (escudos ESPN implementados cuando están disponibles; validación visual móvil pendiente).
- [ ] Vista detallada completa (ficha desplegable con récord y enlace ESPN implementada; estadísticas avanzadas pendientes).
- [ ] Comprobaciones de integridad de ESPN (auditoría de filas, duplicados, fechas, resultados implementada; cobertura semanal completa pendiente).
- [ ] Pruebas unitarias para parsing y probabilidades (primeros casos escritos y conectados a CI; ejecución exitosa pendiente de verificar).
- [ ] Prueba visual Android y rendimiento.

## Sprint 2 — calidad de datos
- [ ] Históricos NFL completos y cobertura NCAAF por conferencia.
- [ ] Estadísticas de puntos, eficiencia y posesiones por equipo.
- [ ] Métricas rolling sin fuga temporal, local/visitante, SOS.
- [ ] Lesiones, QB y profundidad con fuentes verificadas.
- [ ] Descanso, viaje y clima cuando exista fuente fiable.

## Sprint 3 — modelado
- [ ] Modelo NFL separado del de NCAAF.
- [ ] Modelo bayesiano con incertidumbre y priors documentados.
- [ ] Monte Carlo de ML, spread y totales coherente con empate/prórroga.
- [ ] Backtesting walk-forward, calibración, Brier/log loss, intervalos.
- [ ] Benchmark contra baseline y líneas de cierre.
- [ ] Auditoría de sesgos, estabilidad y reproducibilidad.

## Sprint 4 — mercado
- [ ] Investigar acceso autorizado a cuotas Caliente y restricciones.
- [ ] Si no hay acceso, flujo de importación manual cómodo y verificable.
- [ ] Momios timestamp, vig/no-vig, movimiento de línea.
- [ ] EV neto, ranking por valor y umbrales de confianza.
- [ ] Alertas únicamente con fuentes y reglas verificadas.

## Sprint 5 — gestión y producto
- [ ] Portafolio de boletos, patas, exposición y correlaciones.
- [ ] Seguimiento de resultados y ROI, incluyendo CLV.
- [ ] Quinela y comparativas semanales.
- [ ] PWA/icono y accesibilidad móvil.
- [ ] Monitoreo, documentación, manejo de errores, seguridad.

## Criterios para llamar una fase «lista»
1. Código desplegado en Render con estado LIVE.
2. Pruebas automatizadas pertinentes pasando.
3. Verificación funcional y visual en móvil.
4. Fuentes y limitaciones visibles; no inventar cuotas, datos ni picks.
5. Actualizar este documento y registrar riesgos pendientes.

## Riesgos / bloqueos
- ESPN es una fuente pública no oficial: cobertura y esquema pueden cambiar.
- La conexión directa a Caliente no está autorizada ni disponible todavía.
- El baseline actual no ha demostrado precisión predictiva o rentabilidad.
- No hay un agente autónomo de desarrollo continuo en segundo plano; los cambios de código requieren sesiones activas.
