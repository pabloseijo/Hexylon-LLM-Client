# Hexylon LLM Client

Cliente inteligente para control de equipos Hexylon mediante lenguaje natural, basado en una arquitectura desacoplada:

LLM → MCP → Hexylon

---

# Descripción general

Este repositorio implementa la capa de inteligencia de negocio para el control de equipos RF Hexylon de Gsertel utilizando lenguaje natural.

El sistema permite:

- Ejecutar comandos SCPI sin conocer la sintaxis
- Consultar documentación técnica de la API
- Lanzar tareas de medición periódicas
- Analizar resultados automáticamente
- Mantener contexto conversacional durante la sesión
- Visualizar tareas en una interfaz web
- Recibir actualizaciones en tiempo real por WebSocket
- Descargar resultados CSV generados por las tareas

Arquitectura global:

LLM → MCP → Hexylon

Donde:

- Hexylon expone una API SCPI sobre TCP en el puerto 5025
- MCP actúa como pasarela transparente, sin lógica de negocio
- Este cliente implementa toda la inteligencia, la planificación, la ejecución de tareas, la memoria y la interfaz de usuario

---

# Capacidades actuales

El sistema soporta:

## 1. Ejecución de comandos en lenguaje natural

Ejemplo:

"dame la potencia actual" → POW? → interpretación → respuesta técnica

---

## 2. Consultas documentales (knowledge)

Permite consultar:

- Qué hace un comando
- Qué devuelve
- Qué métricas existen
- Cómo funciona una parte del sistema
- Qué restricciones tiene la API

Con tres niveles de respuesta:

- determinista mediante catálogo
- semideterminista mediante topics
- LLM con contexto documental controlado

---

## 3. Tareas de medición asíncronas

Ejemplo:

"mídeme POW y MER cada 10 segundos durante 2 minutos"

El sistema:

- genera un TaskPlan mediante LLM
- ejecuta la tarea en segundo plano
- guarda resultados en CSV
- permite cancelación y monitorización
- expone el estado por API REST y WebSocket
- refleja tareas activas en la interfaz web

---

## 4. Análisis automático de resultados

Incluye:

- parseo robusto de CSV
- cálculo de estadísticas
- detección de tendencias
- interpretación de resultados mediante LLM

---

## 5. Memoria conversacional

Sistema de memoria en 4 niveles:

- Estado de sesión
- Log de eventos
- Historial persistente de tareas
- Historial conversacional completo

Permite:

- follow-ups como "y eso qué significa"
- contexto continuo durante la sesión
- preguntas sobre el estado del sistema y de las tareas

---

## 6. Interfaz web en tiempo real

La interfaz web permite:

- enviar mensajes al pipeline
- ver tareas activas
- ver estados de tareas
- recibir eventos del sistema en tiempo real
- descargar CSV generados
- visualizar respuestas estructuradas en markdown

Características técnicas:

- React + TypeScript + Vite
- WebSocket para sincronización en tiempo real
- Renderizado markdown con soporte GFM
- Layout centrado (max-width controlado)
- Componentización por roles (user, assistant, system)

---

## 7. Interfaz conversacional avanzada

La interfaz web implementa un modelo de interacción tipo chat moderno con:

- Renderizado completo en markdown (títulos, listas, código)
- Layout centrado con ancho máximo (1080px)
- Animación progresiva de escritura (typewriter)
- Indicador de respuesta en tiempo real (animación tipo “respiración”)
- Separación visual clara entre usuario, sistema y asistente
- Estilo consistente con sistema de diseño corporativo

Esto permite una experiencia más legible, estructurada y cercana a herramientas modernas de interacción con LLM.

---

# Arquitectura interna

## Pipeline principal

Orden de evaluación:

1. Análisis post-tarea
2. Pregunta sobre la sesión
3. Cancelar tarea
4. Listar tareas
5. Lanzar tarea
6. Knowledge
7. Command (SCPI)
8. Interpretación formateada (markdown)

---

## Flujo de ejecución

Usuario → Pipeline → LLM (si aplica) → MCP → Hexylon → Interpretación → Usuario

---

# Estructura del proyecto

## src/api/

server.py  
Servidor FastAPI que expone la API REST y el WebSocket para la interfaz web

task_notifier.py  
Puente entre el código síncrono de tareas y el sistema de notificaciones del backend

---

## src/llm/clients/

ollama_client.py  
Cliente HTTP para el LLM

mcp_client.py  
Cliente de comunicación con MCP

---

## src/llm/core/

pipeline.py  
Orquestador principal del sistema

scpi_generator.py  
Generación de comandos SCPI

intent_router.py  
Enrutado semántico entre command y knowledge

interpreter.py  
Interpretación de respuestas SCPI

---

## src/llm/knowledge/

Sistema documental estructurado

- command_catalog.py
- topic_catalog.py
- context_builder.py
- command_selector.py
- topic_selector.py
- query_classifier.py
- response_formatter.py

---

## src/llm/memory/

Sistema de memoria en múltiples niveles

session_memory.py  
Estado operativo inmediato

session_log.py  
Eventos estructurados en memoria

task_history.py  
Historial persistente en disco

conversation_history.py  
Historial conversacional compatible con el LLM

---

## src/llm/tasks/

Sistema de ejecución de tareas

task_planner.py  
Conversión LLM → TaskPlan estructurado

task_executor.py  
Ejecución en hilo separado

csv_writer.py  
Persistencia incremental

task_analyzer.py  
Análisis de resultados

task_models.py  
Modelos de datos

condition_evaluator.py  
Evaluación determinista de condiciones de alerta y parada

---

## src/llm/normalization/

unit_normalizer.py  
Normalización de unidades y valores

---

## ui/

Interfaz web React + TypeScript + Vite

### ui/src/components/

Chat.tsx  
Consola principal de interacción

TaskPanel.tsx  
Panel lateral de tareas

MessageBubble.tsx  
Render de mensajes de conversación

### ui/src/hooks/

useWebSocket.ts  
Gestión de conexión WebSocket y reconexión

### ui/src/api/

client.ts  
Cliente HTTP frontend para consumir el backend

### ui/src/types.ts

Tipos compartidos del frontend

---

## scripts/

chat_pipeline.py  
Chat CLI interactivo del pipeline

run_pipeline.py  
Ejecución directa del pipeline

run.sh  
Arranque conjunto de backend y frontend

---

## test/

Pruebas de integración

test_chat_flows.py  
Validación de comportamiento conversacional completo

---

# Sistema de tareas

Flujo general:

1. El usuario define una tarea en lenguaje natural
2. El LLM genera un TaskPlan estructurado
3. El TaskExecutor lanza la tarea en un hilo separado
4. Se ejecutan comandos SCPI periódicamente
5. Se guardan resultados en CSV
6. Se actualiza memoria y logs
7. El backend emite eventos de tarea por WebSocket
8. La interfaz web sincroniza el estado en tiempo real

Características principales:

- cancelación inmediata
- múltiples tareas concurrentes
- escritura incremental en CSV
- análisis posterior de resultados
- eventos task_created, task_completed, task_cancelled, task_failed y task_alert
- consulta de tareas activas por REST
- representación estructurada en la interfaz (markdown + bloques)

---

# Sistema de memoria

## Nivel 1 — session_memory

Estado inmediato:

- última tarea lanzada
- última tarea completada
- último CSV
- última métrica

---

## Nivel 2 — session_log

Eventos estructurados:

- TASK_LAUNCHED
- TASK_COMPLETED
- TASK_CANCELLED
- TASK_FAILED
- TASK_ALERT_TRIGGERED
- COMMAND_SENT
- KNOWLEDGE_QUERY
- SESSION_QUESTION

---

## Nivel 3 — task_history

Persistencia en disco:

~/.hexylon/task_history.jsonl

---

## Nivel 4 — conversation_history

Historial conversacional completo:

- máximo 20 turnos
- formato compatible con el cliente LLM
- usado en respuestas narrativas e interpretativas

---

# Sistema de conocimiento

No se utiliza un prompt monolítico.

El sistema:

1. clasifica la consulta
2. selecciona comandos relevantes
3. selecciona topics relevantes
4. construye contexto dinámico
5. ejecuta el LLM con el contexto mínimo necesario

Ventajas:

- menor consumo de tokens
- mayor precisión
- menor alucinación
- mayor control del contexto inyectado

---

# API del backend

## Endpoints principales

POST /chat  
Envía un mensaje al pipeline y devuelve la respuesta interpretada.  
Si la petición genera una tarea, también devuelve la metadata de la tarea.

GET /tasks  
Devuelve las tareas activas actuales.

DELETE /tasks/{task_id}  
Cancela una tarea activa.

GET /tasks/history  
Devuelve historial persistente de tareas.

GET /health  
Healthcheck básico del backend.

GET /download?file=...  
Descarga un CSV generado por una tarea.

WS /ws  
Canal WebSocket para eventos en tiempo real.

## Eventos WebSocket

El backend emite:

- task_created
- task_completed
- task_cancelled
- task_failed
- task_alert

---

# Ejecución

## 1. Ejecutar backend + frontend juntos

Desde la raíz del proyecto:
```bash
    ./scripts/run.sh
```

Esto arranca:

- Backend FastAPI en http://127.0.0.1:8001
- Frontend Vite en http://127.0.0.1:5173

---

## 2. Ejecutar solo el backend

Desde la raíz del proyecto:

```bash
    PYTHONPATH=src uvicorn src.api.server:app --reload --port 8001
```

---

## 3. Ejecutar solo el frontend

Desde el directorio ui:

```bash
    npm install
    npm run dev -- --host 127.0.0.1 --port 5173
```

---

## 4. Ejecutar el chat CLI

Desde la raíz del proyecto:

```bash
    PYTHONPATH=src python3 scripts/chat_pipeline.py
```

---

## 5. Ejecutar el pipeline directamente

Desde la raíz del proyecto:

```bash
    PYTHONPATH=src python3 scripts/run_pipeline.py
```

---

# Pruebas

## Ejecutar batería principal

Desde la raíz del proyecto:

```bash
    PYTHONPATH=src python3 test/test_chat_flows.py
```

Casos cubiertos:

- comandos básicos
- follow-ups contextuales
- knowledge
- gestión de tareas
- análisis de resultados
- preguntas de sesión

---

# Requisitos

Entorno previsto:

- Python 3.10 o superior
- Node.js y npm para la interfaz web
- acceso al MCP configurado
- acceso al equipo Hexylon a través del MCP
- LLM accesible desde el cliente

---

# Principios de diseño

## Separación estricta

- MCP sin lógica
- LLM como capa de inteligencia
- ejecución determinista en tasks
- UI separada del backend

---

## Control del LLM

- uso solo donde aporta valor
- validación de outputs
- prompts restrictivos
- reducción del contexto a lo estrictamente necesario

---

## Determinismo

- parsing de CSV
- ejecución de tareas
- condiciones y alertas
- estructura de memoria
- sincronización de tareas desde backend como fuente de verdad

---

## Arquitectura extensible

- modularidad clara
- responsabilidades aisladas
- fácil evolución
- backend y frontend desacoplados

---

## Presentación estructurada

- uso obligatorio de markdown en respuestas LLM
- separación semántica de contenido
- consistencia visual entre mensajes
- priorización de legibilidad técnica sobre densidad

---
# Sistema de renderizado

Las respuestas del LLM no se presentan como texto plano.

Se aplica un sistema de renderizado basado en:

- markdown estructurado
- estilos tipográficos controlados
- bloques de código diferenciados
- listas semánticas

Esto permite:

- mejorar la legibilidad técnica
- evitar ambigüedad en comandos
- separar claramente contenido funcional y descriptivo

---

# Estado actual

Sistema funcional con:

- pipeline completo operativo
- memoria conversacional integrada
- tareas asíncronas estables
- análisis automático funcional
- interfaz web operativa
- sincronización REST + WebSocket estable
- descarga de CSV desde la UI
- contrato frontend/backend alineado
- renderizado markdown completo en frontend
- animaciones de escritura en respuestas del LLM
- indicador visual de procesamiento en tiempo real
- layout UI unificado con ancho máximo controlado

---

# Líneas futuras

- tipado estricto de eventos WebSocket
- persistencia completa de tareas finalizadas, canceladas y fallidas en endpoint dedicado
- logging estructurado avanzado
- tests frontend y end-to-end
- optimización de prompts
- consolidación del modelo de estado de tareas
- mejoras en streaming de tokens y render progresivo
---

# Autoría

Desarrollado como sistema de control inteligente para equipos Hexylon en entorno de ingeniería Televes, basado en LLM + MCP.