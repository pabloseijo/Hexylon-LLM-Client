# Fine-tuning experimental para generación SCPI

## Objetivo

Este módulo implementa una prueba controlada de fine-tuning mediante LoRA para evaluar la viabilidad de mapear lenguaje natural a comandos SCPI del equipo Hexylon.

El objetivo es validar si un modelo reducido puede aprender correspondencias directas del tipo:

´´´
input: "dame el MER"
output: "MER?"
´´´

El alcance de este experimento es exclusivamente evaluativo.

---

## Modelo utilizado

Entrenamiento:

´´´
Qwen2.5-0.5B-Instruct
´´´

Motivo:

- Permite entrenamiento en CPU
- Bajo coste computacional
- Compatible con LoRA

---

## Modelo en producción

El sistema en producción utiliza:

´´´
qwen3.5:9b
´´´

Ejecutado mediante Ollama.

Restricciones:

- No admite entrenamiento directo
- Solo inferencia
- Hardware insuficiente para entrenamiento de 9B
- El problema no requiere mayor capacidad generativa

---

## Resultados del experimento

Comportamiento observado:

Casos correctos:

´´´
"Dame el MER actual"      -> MER?
"Consulta el BER previo"  -> CBER?
"Qué hace CN"             -> CN?
´´´

Errores detectados:

´´´
"Pon el VBW en 10 KHz"    -> VBW 10KHz      (formato inválido)
"Cuéntame un chiste"      -> CHC?           (comando inventado)
´´´

---

## Análisis técnico

El modelo:

- Aprende mappings frecuentes
- Generaliza parcialmente

Pero falla en:

- sintaxis estricta SCPI
- validación de comandos
- restricción de dominio

Esto es consistente con la naturaleza probabilística de los LLM.

---

## Decisión de arquitectura

El fine-tuning NO se utiliza como mecanismo principal de generación SCPI.

Se adopta un enfoque híbrido:

´´´
entrada usuario
→ reglas deterministas
→ LLM (solo candidato)
→ normalizador SCPI
→ validador (catálogo cerrado)
→ comando final o UNKNOWN
´´´

El LLM no tiene autoridad sobre la validez del comando.

---

## Uso del módulo

### 1. Construcción del dataset

´´´
PYTHONPATH=src python3 finetuning/scripts/build_dataset.py
´´´

---

### 2. División en train/validation

´´´
PYTHONPATH=src python3 finetuning/scripts/split_dataset.py
´´´

---

### 3. Validación del dataset

´´´
PYTHONPATH=src python3 finetuning/scripts/validate_dataset.py
´´´

---

### 4. Entrenamiento LoRA en CPU

´´´
PYTHONPATH=src python3 finetuning/scripts/train_cpu_lora.py
´´´

---

### 5. Test del modelo entrenado

´´´
PYTHONPATH=src python3 finetuning/scripts/test_cpu_lora.py
´´´

---

### 6. Evaluación

Evaluación general:

´´´
PYTHONPATH=src python3 finetuning/scripts/evaluate_dataset.py
´´´

Evaluación específica SCPI:

´´´
PYTHONPATH=src python3 finetuning/scripts/evaluate_scpi_generator.py
´´´

---

## Estructura del módulo

´´´
finetuning/
├── datasets/
│   ├── hexylon_scpi_sft.jsonl
│   ├── train.jsonl
│   └── val.jsonl
├── eval/
│   ├── eval_prompts.jsonl
│   └── eval_scpi_cases.jsonl
├── output/
│   └── cpu_lora_test/
│       ├── checkpoint-*
│       ├── adapter_model.safetensors
│       └── tokenizer.json
├── scripts/
│   ├── build_dataset.py
│   ├── split_dataset.py
│   ├── validate_dataset.py
│   ├── train_cpu_lora.py
│   ├── test_cpu_lora.py
│   ├── evaluate_dataset.py
│   └── evaluate_scpi_generator.py
└── README.md
´´´

---

## Conclusión

El fine-tuning mejora parcialmente la generación de comandos simples, pero no garantiza:

- cumplimiento del estándar SCPI
- validez sintáctica
- ausencia de comandos inválidos

Dado que SCPI es un protocolo formal y cerrado, la solución correcta requiere:

- control determinista
- normalización estricta
- validación contra catálogo

El modelo debe utilizarse únicamente como componente auxiliar de interpretación, no como generador final.

---
