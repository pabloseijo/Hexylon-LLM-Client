# Hexylon LLM Client

Cliente inteligente para control de equipos Hexylon mediante lenguaje natural, construido sobre una arquitectura local basada en LLM + MCP.

---

# Descripción general

Este proyecto implementa la capa de inteligencia de negocio de una arquitectura de control RF basada en lenguaje natural para equipos Hexylon de Gsertel.

La arquitectura global del sistema es:

LLM → MCP → Hexylon

Donde:

- **Hexylon** expone una API SCPI por TCP.
- **MCP** actúa como pasarela transparente entre cliente y equipo.
- **Este repositorio (`hexylon-llm-client`)** implementa toda la lógica de interpretación, generación y razonamiento.

El objetivo es permitir que un usuario interactúe con el Hexylon mediante lenguaje natural mientras el sistema traduce internamente dichas peticiones a comandos SCPI válidos.

---

# Arquitectura funcional

El flujo completo de ejecución es:

Usuario → Generación NL→SCPI → MCP → Hexylon → Interpretación de respuesta → Usuario

Más detalladamente:

1. El usuario introduce una petición en lenguaje natural.
2. El sistema construye contexto documental dinámico.
3. El LLM genera el comando SCPI correspondiente.
4. El comando se envía al MCP.
5. El MCP lo reenvía al Hexylon.
6. La respuesta SCPI se interpreta y normaliza.
7. Se devuelve una respuesta inteligible al usuario.

---

# Estructura del proyecto

## `src/llm/clients/`

Contiene adaptadores de infraestructura externos.

### `ollama_client.py`
Cliente HTTP para comunicación con Ollama local.

Responsabilidades:
- envío de prompts al modelo
- recepción de completions
- configuración de parámetros de inferencia

---

### `mcp_client.py`
Cliente de comunicación con el servidor MCP.

Responsabilidades:
- conexión streamable-http con MCP
- invocación de herramientas MCP
- envío de comandos SCPI al Hexylon

---

## `src/llm/core/`

Contiene la lógica principal de negocio.

### `scpi_generator.py`
Generador de comandos SCPI a partir de lenguaje natural.

Responsabilidades:
- construcción de prompt de generación
- inyección de contexto documental dinámico
- llamada al LLM para generación SCPI
- validación básica del SCPI generado

---

### `pipeline.py`
Orquestador principal del flujo extremo a extremo.

Responsabilidades:
- coordinar generación SCPI
- enviar comando al MCP
- interpretar respuesta
- devolver resultado final

---

### `interpreter.py`
Interpretador de respuestas SCPI.

Responsabilidades:
- parseo determinista de respuestas simples
- fallback a LLM para interpretación compleja
- normalización de salida

---

## `src/llm/knowledge/`

Capa de conocimiento documental estructurado.

### `api_reference.py`
Referencia compacta de la API SCPI.

Uso:
- contexto base permanente para generación

---

### `api_extended.py`
Referencia documental extensa de la API.

Uso:
- reserva para fallback documental futuro
- ampliaciones de contexto complejas

---

### `command_catalog.py`
Catálogo estructurado de comandos SCPI.

Contiene:
- sintaxis
- descripción
- restricciones
- ejemplos
- metadatos por comando

---

### `command_selector.py`
Selector heurístico de comandos relevantes.

Responsabilidades:
- detectar qué comandos pueden ser relevantes para una petición
- reducir contexto inyectado al LLM

---

### `topic_catalog.py`
Catálogo estructurado de áreas funcionales de la API.

Ejemplos:
- spectrum_analyser
- tuning
- profiles
- iptv

---

### `topic_selector.py`
Selector heurístico de temas funcionales.

Responsabilidades:
- detectar áreas generales de conocimiento implicadas en la petición

---

### `context_builder.py`
Constructor de contexto documental dinámico.

Responsabilidades:
- combinar referencia base
- seleccionar comandos relevantes
- seleccionar topics relevantes
- construir contexto final para el prompt

---

## `src/llm/normalization/`

### `unit_normalizer.py`
Utilidades de normalización semántica.

Responsabilidades:
- normalización de unidades
- normalización de booleanos
- formateo homogéneo de respuestas

---

## `test/`

Contiene scripts de prueba y validación manual.

---

# Ejecución del proyecto

## Requisitos previos

Debe existir:

- Instancia local de Ollama operativa
- Modelo descargado en Ollama
- MCP desplegado y accesible
- Hexylon accesible desde el MCP

---

## Instalación de dependencias

pip install -r requirements.txt

---

## Ejecución manual del pipeline

La forma exacta dependerá del entrypoint que definas, pero típicamente:

python3 -m src.llm.core.pipeline

o mediante script específico:

python3 scripts/run_pipeline.py

---

# Flujo de conocimiento dinámico

Uno de los componentes clave de esta arquitectura es la capa `knowledge`.

El sistema no utiliza un prompt estático monolítico.

En su lugar:

1. Analiza la petición del usuario.
2. Detecta comandos relevantes.
3. Detecta temas funcionales relevantes.
4. Construye contexto reducido.
5. Inyecta únicamente la documentación necesaria.

Esto permite:

- reducir consumo de tokens
- mejorar precisión del LLM
- minimizar alucinaciones
- escalar mejor con APIs grandes

---

# Principios arquitectónicos

Este proyecto sigue estrictamente estas decisiones de diseño:

---

## MCP como pasarela pura

El MCP:

- no contiene lógica de negocio
- no interpreta respuestas
- no transforma datos
- no toma decisiones

Su única responsabilidad es:

- reenviar SCPI al Hexylon

---

## Toda la lógica reside en el cliente LLM

Este repositorio concentra:

- generación NL→SCPI
- razonamiento contextual
- interpretación de respuestas
- conocimiento documental
- validación semántica

---

## Conocimiento estructurado y seleccionable

La documentación de la API no se trata como texto plano.

Se modela estructuradamente para permitir:

- recuperación selectiva
- contexto dinámico
- razonamiento asistido por documentación

---

# Estado actual del proyecto

Actualmente implementado:

- Cliente Ollama funcional
- Cliente MCP funcional
- Generador NL→SCPI operativo
- Pipeline extremo a extremo funcional
- Interpretador de respuestas básico
- Capa de conocimiento documental estructurada
- Selección dinámica de contexto por comandos y topics

---

# Trabajo futuro previsto

Líneas naturales de evolución:

- Integración de `api_extended.py` como fallback documental
- Mejora de heurísticas de selección contextual
- Validación avanzada de comandos generados
- Interpretación semántica avanzada de respuestas complejas
- Trazabilidad / logging estructurado del pipeline
- Benchmarks de precisión NL→SCPI

---

# Filosofía de diseño

Este sistema prioriza:

- Robustez frente a complejidad innecesaria
- Determinismo donde sea posible
- Separación estricta de responsabilidades
- Arquitectura mantenible y extensible
- Control explícito del contexto suministrado al LLM

---

# Autoría

Proyecto desarrollado como parte de integración de control inteligente de equipos Hexylon mediante LLM y MCP en entorno de ingeniería Televes.