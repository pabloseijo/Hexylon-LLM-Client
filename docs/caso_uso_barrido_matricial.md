# Caso de uso: Barrido matricial frecuencia/potencia con cliente LLM

## 1. Descripción general

Este caso de uso documenta la ejecución de un barrido matricial frecuencia/potencia sobre un equipo de medida Hexylon (GSERTEL) controlado mediante un cliente LLM. El sistema automatiza la configuración del generador RF R&S SGU100A y la adquisición de medidas en el receptor Hexylon, generando resultados en CSV y gráficas automáticas.

---

## 2. Topología del sistema

```
Cliente LLM (chat)
        ↓
   Orchestrator
        ↓
┌───────────────────────┐
│  Generador R&S SGU100A │
│  TCP socket :5025      │
└───────────────────────┘
        ↓ RF
┌───────────────────────┐
│  hexylon_a             │
│  Receptor RF           │
└───────────────────────┘
```

- **Protocolo de control Hexylon:** SCPI sobre TCP puerto 5025
- **Protocolo de control generador:** SCPI sobre TCP puerto 5025
- **Interfaz de usuario:** chat LLM en lenguaje natural

---

## 3. Stack tecnológico

| Componente | Tecnología |
|---|---|
| Backend | Python |
| Control Hexylon | MCP (Model Context Protocol) |
| Control generador | Socket TCP directo |
| Frontend | React + TypeScript |
| Gráficas | Recharts |
| Progreso en tiempo real | WebSocket |
| Persistencia | CSV |

---

## 4. Prompt de usuario para lanzar el barrido

El usuario introduce en el chat el siguiente prompt en lenguaje natural:

```
Barrido matricial frecuencia/potencia: 200-900 MHz paso 50 MHz;
-10 a -90 dBm paso -10 dB; equipos hexylon_a, hexylon_b
```

El cliente LLM interpreta este prompt y lanza automáticamente un `MatrixSweepExecutor` con los parámetros extraídos:

| Parámetro | Valor |
|---|---|
| Frecuencia inicio | 200 MHz |
| Frecuencia fin | 900 MHz |
| Paso de frecuencia | 50 MHz |
| Potencia inicio | -10 dBm |
| Potencia fin | -90 dBm |
| Paso de potencia | -10 dBm |
| Equipos receptores | hexylon_a, hexylon_b |
| Comandos de medida | `FREQ?`, `POW?` |

**Total de puntos del barrido:** 15 frecuencias × 9 niveles de potencia = 135 puntos por receptor.

---

## 5. Secuencia de ejecución por punto

Para cada combinación (potencia, frecuencia) el sistema ejecuta en orden:

1. `POW <x>dBm` → generador (configura nivel de potencia)
2. `FREQ <f> MHz` → generador (configura frecuencia RF)
3. `FREQ <f> MHz` → Hexylon (resintoniza receptor)
4. Espera 1 segundo (estabilización)
5. `LOCK?` → Hexylon (verifica enganche)
6. Espera 1 segundo adicional
7. `FREQ?` → Hexylon (lectura de frecuencia sintonizada)
8. `POW?` → Hexylon (lectura de potencia recibida)
9. Escritura de fila en CSV y flush
10. Evento WebSocket `matrix_sweep_progress` al frontend

---

## 6. Tolerancia a fallos por equipo

El sistema implementa aislamiento automático de equipos fallidos durante el barrido:

- Si un equipo devuelve error en cualquier comando, queda añadido al conjunto `disabled_machines`.
- Los puntos siguientes del barrido omiten ese equipo con el valor `SKIPPED: equipo deshabilitado por error previo`.
- El resto de equipos continúan midiendo con normalidad.
- Se emite un evento WebSocket `machine_disabled` con la máquina afectada, la razón, la frecuencia y la potencia en el momento del fallo.

---

## 7. Resultados del barrido ejecutado

**Fecha de ejecución:** 2026-05-13 10:08:47

**Resultado:** Barrido completado — 135 puntos adquiridos en hexylon_a.

### 7.1 Parámetros del barrido ejecutado

| Parámetro | Valor |
|---|---|
| Frecuencias | 200, 250, 300, 350, 400, 450, 500, 550, 600, 650, 700, 750, 800, 850, 900 MHz |
| Niveles de potencia | -10, -20, -30, -40, -50, -60, -70, -80, -90 dBm |
| Total de puntos | 135 |
| Duración | 10:08:47 → 10:35:30 (~27 min) |

### 7.2 Resumen de medidas hexylon_a (POW?)

| Potencia generador (dBm) | Media POW medida (dBµV) |
|---|---|
| -10 | 92.52 |
| -20 | 82.56 |
| -30 | 72.57 |
| -40 | 62.51 |
| -50 | 7.89 |
| -60 | 0.24 |
| -70 | 0.07 |
| -80 | 0.04 |
| -90 | 14.17 |

Rango total medido: **-2.2 dBµV** a **92.8 dBµV**.

Se observa una correlación lineal clara entre -10 y -40 dBm (~10 dBµV por cada 10 dBm), con caída brusca de la señal a partir de -50 dBm, indicando el umbral de sensibilidad del receptor en estas condiciones.

### 7.3 Muestra del CSV generado

| timestamp | generator_power_dbm | generator_frequency_mhz | hexylon_a_frequency_set_response | hexylon_a_FREQ? | hexylon_a_POW? |
|---|---|---|---|---|---|
| 2026-05-13 10:08:47 | -10.0 | 200.0 | CMD OK | FREQ 200000 kHz | 92.5 dBµV |
| 2026-05-13 10:09:35 | -10.0 | 400.0 | CMD OK | FREQ 400000 kHz | 92.3 dBµV |
| 2026-05-13 10:11:36 | -10.0 | 900.0 | CMD OK | FREQ 900000 kHz | 92.4 dBµV |
| 2026-05-13 10:17:47 | -40.0 | 200.0 | CMD OK | FREQ 200000 kHz | 62.6 dBµV |
| 2026-05-13 10:20:47 | -50.0 | 200.0 | CMD OK | FREQ 200000 kHz | 52.8 dBµV |
| 2026-05-13 10:21:11 | -50.0 | 300.0 | CMD OK | FREQ 300000 kHz | -0.6 dBµV |
| 2026-05-13 10:32:43 | -90.0 | 200.0 | CMD OK | FREQ 200000 kHz | -2.2 dBµV |
| 2026-05-13 10:35:30 | -90.0 | 900.0 | CMD OK | FREQ 900000 kHz | 15.7 dBµV |

---

## 8. Prompt de usuario para graficar los resultados

Una vez completado el barrido, el usuario introduce en el chat:

```
Grafica los resultados del último barrido matricial. Usa el CSV generado.
Para el hexylon_a, convierte las medidas de POW? de dBµV a dBm restando
108.75 dB (sistema 75 Ω). Representa en el eje X la frecuencia del generador
en MHz, en el eje Y la potencia medida en hexylon_a en dBm, y pinta una línea
por cada nivel de potencia del generador. Cada línea tiene 15 puntos,
uno por cada frecuencia del barrido.
```

### Descripción de la gráfica generada

| Elemento | Valor |
|---|---|
| Eje X | Frecuencia del generador (MHz) |
| Eje Y | Potencia medida por hexylon_a (dBm) |
| Líneas | Una por cada nivel de potencia del generador: -10, -20 ... -90 dBm (9 líneas) |
| Puntos por línea | 15 (uno por cada frecuencia del barrido) |
| Conversión | dBm = dBµV − 108.75 (sistema 75 Ω) |
| Receptor | hexylon_a |

### Gráfica resultante

![Barrido matricial RF - hexylon_a](../output/plots/hexylon_a_matrix_sweep_plot.png)