# Hexylon LLM Client

Cliente inteligente para control de equipos Hexylon mediante lenguaje natural, basado en una arquitectura desacoplada LLM → MCP → Hexylon.

---

# Descripción general

Este repositorio implementa la capa de inteligencia de negocio para el control de equipos RF Hexylon de Gsertel utilizando lenguaje natural.

El sistema permite:

- Ejecutar comandos SCPI sin conocer la sintaxis
- Consultar documentación técnica de la API
- Lanzar tareas de medición periódicas
- Analizar resultados automáticamente
- Mantener contexto conversacional durante la sesión

Arquitectura global:

LLM → MCP → Hexylon

Donde:

- Hexylon expone una API SCPI sobre TCP (puerto 5025)
- MCP actúa como pasarela transparente (sin lógica)
- Este cliente implementa toda la inteligencia

---

# Capacidades actuales

El sistema soporta:

## 1. Ejecución de comandos en lenguaje natural

Ejemplo:

"dame la potencia actual" → POW? → interpretación → respuesta técnica

---

## 2. Consultas documentales (knowledge)

- Qué hace un comando
- Qué devuelve
- Qué métricas existen
- Cómo funciona una parte del sistema

Con tres niveles de respuesta:
- determinista (catálogo)
- semideterminista (topics)
- LLM con contexto controlado

---

## 3. Tareas de medición asíncronas

Ejemplo:

"mídeme POW y MER cada 10 segundos durante 2 minutos"

El sistema:
- genera un TaskPlan mediante LLM
- ejecuta la tarea en segundo plano
- guarda resultados en CSV
- permite cancelación y monitorización

---

## 4. Análisis automático de resultados

- Parseo robusto de CSV
- Cálculo de estadísticas
- Detección de tendencias
- Respuesta interpretada por LLM

---

## 5. Memoria conversacional

Sistema de memoria en 4 niveles:

- Estado de sesión (última tarea, último CSV)
- Log de eventos (acciones realizadas)
- Historial persistente de tareas
- Historial conversacional completo

Permite:

- follow-ups ("y eso qué significa")
- contexto continuo
- preguntas sobre la sesión

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

---

## Flujo de ejecución

Usuario → Pipeline → LLM (si aplica) → MCP → Hexylon → Interpretación → Usuario

---

# Estructura del proyecto

## src/llm/clients/

ollama_client.py  
Cliente HTTP para el LLM (Ollama remoto)

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
Estado operativo (última tarea, último CSV, etc.)

session_log.py  
Eventos de sesión en RAM

task_history.py  
Historial persistente en ~/.hexylon

conversation_history.py  
Historial conversacional para el LLM

---

## src/llm/tasks/

Sistema de ejecución de tareas

task_planner.py  
LLM → TaskPlan (JSON estructurado)

task_executor.py  
Ejecución en hilo separado

csv_writer.py  
Persistencia incremental

task_analyzer.py  
Análisis de resultados

task_models.py  
Modelos de datos

---

## src/llm/normalization/

unit_normalizer.py  
Normalización de unidades y valores

---

## test/

Pruebas de integración

test_chat_flows.py  
Validación de comportamiento conversacional completo

---

# Sistema de tareas

Pipeline:

1. Usuario define tarea en lenguaje natural
2. LLM genera TaskPlan estructurado
3. Executor lanza hilo asíncrono
4. Se ejecutan comandos SCPI periódicamente
5. Se guardan resultados en CSV
6. Se actualiza memoria y logs

Características:

- cancelación inmediata
- múltiples tareas concurrentes
- escritura incremental
- integración con análisis

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
- COMMAND_SENT
- KNOWLEDGE_QUERY

---

## Nivel 3 — task_history

Persistencia en disco:
~/.hexylon/task_history.jsonl

---

## Nivel 4 — conversation_history

Historial conversacional completo:

- máximo 20 turnos
- formato compatible con Ollama
- usado en todas las respuestas narrativas

---

# Sistema de conocimiento

No se utiliza un prompt monolítico.

El sistema:

1. Clasifica la consulta
2. Selecciona comandos relevantes
3. Selecciona topics relevantes
4. Construye contexto dinámico
5. Ejecuta LLM con contexto mínimo necesario

Ventajas:

- menor consumo de tokens
- mayor precisión
- menor alucinación

---

# Ejecución

Ejecutar el chat interactivo:

PYTHONPATH=src python3 scripts/chat_pipeline.py

---

# Pruebas

Ejecutar batería de pruebas:

PYTHONPATH=src python3 test/test_chat_flows.py

Casos cubiertos:

- comandos básicos
- follow-ups contextuales
- knowledge
- gestión de tareas
- análisis de resultados
- preguntas de sesión

---

# Principios de diseño

## Separación estricta

- MCP sin lógica
- LLM como capa de inteligencia
- ejecución determinista en tasks

---

## Control del LLM

- uso solo donde aporta valor
- validación de outputs
- prompts restrictivos

---

## Determinismo

- parsing de CSV
- ejecución de tareas
- estructura de memoria

---

## Arquitectura extensible

- modularidad clara
- responsabilidades aisladas
- fácil evolución

---

# Estado actual

Sistema funcional con:

- pipeline completo operativo
- memoria conversacional integrada
- tareas asíncronas estables
- análisis automático funcional
- batería de tests validada (6/6)

---

# Líneas futuras

- triggers y condiciones en tareas
- mejora de interpretación semántica
- logging estructurado avanzado
- tests automatizados más extensos
- optimización de prompts

---

# Autoría

Desarrollado como sistema de control inteligente para equipos Hexylon en entorno de ingeniería Televes, basado en LLM + MCP.