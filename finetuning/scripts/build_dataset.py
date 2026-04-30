import json
from pathlib import Path


OUTPUT = Path("finetuning/datasets/hexylon_scpi_sft.jsonl")

SYSTEM_COMMAND = (
    "Eres un generador de comandos SCPI para un equipo Hexylon. "
    "Devuelve únicamente un comando SCPI válido o UNKNOWN. "
    "No añadas explicaciones, markdown ni texto adicional."
)

SYSTEM_KNOWLEDGE = (
    "Eres un asistente técnico especializado en la API SCPI del equipo Hexylon. "
    "Responde en español técnico, de forma clara y precisa. "
    "No inventes comandos, sintaxis ni comportamientos."
)


def example(system: str, user: str, assistant: str) -> dict:
    return {
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
            {"role": "assistant", "content": assistant},
        ]
    }


def command_variations(label: str) -> list[str]:
    return [
        f"Dame {label}",
        f"Consulta {label}",
        f"Mide {label}",
        f"Lee {label}",
        f"Quiero saber {label}",
        f"Necesito consultar {label}",
        f"Puedes darme {label}",
        f"Obtén {label}",
        f"Devuélveme {label}",
        f"Comprueba {label}",
        f"Verifica {label}",
        f"Muéstrame {label}",
    ]


def build_command_examples() -> list[dict]:
    examples = []

    read_commands = {
        "MER?": ["el MER", "MER actual", "la medida MER"],
        "POW?": ["la potencia", "el nivel de señal", "la potencia RF"],
        "CN?": ["el C/N", "la relación portadora ruido", "el carrier noise"],
        "CBER?": ["el CBER", "el BER antes de corrección", "el BER previo"],
        "VBER?": ["el VBER"],
        "BCHBER?": ["el BCHBER"],
        "PREBER?": ["el PreBER"],
        "POSTBER?": ["el PostBER"],
        "PRELDPCBER?": ["el PreLDPCBER"],
        "PREBCHBER?": ["el PreBCHBER"],
        "MSCBER?": ["el MSCBER"],
        "FICBER?": ["el FICBER"],
        "CBERA?": ["el CBER de la capa A"],
        "VBERA?": ["el VBER de la capa A"],
        "CBERB?": ["el CBER de la capa B"],
        "VBERB?": ["el VBER de la capa B"],
        "CBERC?": ["el CBER de la capa C"],
        "VBERC?": ["el VBER de la capa C"],
        "CNBOOT?": ["el C/N bootstrap"],
        "LKM?": ["el margen de enlace", "el link margin"],
        "PER?": ["el PER"],
        "SER?": ["el SER"],
        "HUM?": ["el HUM"],
        "CSO?": ["el CSO"],
        "LOCK?": ["si la señal está bloqueada", "el lock", "si el equipo está sincronizado"],
        "MEAS?": ["las medidas actuales", "las mediciones actuales"],
        "PAR?": ["los parámetros de la señal", "los parámetros actuales"],
        "FREQ?": ["la frecuencia actual", "la frecuencia sintonizada"],
        "BAND?": ["la banda actual", "la banda seleccionada"],
        "CH?": ["el canal actual"],
        "INPUT?": ["la entrada actual"],
        "LAMBDA?": ["la lambda actual"],
        "PROF?": ["el perfil actual"],
        "LPROF?": ["los perfiles disponibles"],
        "SERVICES?": ["los servicios del TS", "los servicios disponibles"],
        "IDN?": ["la identificación del equipo", "la información del equipo"],
        "RBW?": ["el RBW"],
        "VBW?": ["el VBW"],
        "SPAN?": ["el span"],
        "RLEVEL?": ["el nivel de referencia"],
        "OPT_POW?": ["la potencia óptica"],
        "OPT_POW_1310?": ["la potencia óptica en 1310"],
        "OPT_POW_1490?": ["la potencia óptica en 1490"],
        "OPT_POW_1550?": ["la potencia óptica en 1550"],
    }

    for scpi, labels in read_commands.items():
        for label in labels:
            for user_text in command_variations(label):
                examples.append(example(SYSTEM_COMMAND, user_text, scpi))

    write_commands = {
        "FREQ 650MHz": [
            "Pon la frecuencia en 650 MHz",
            "Sintoniza 650 MHz",
            "Cambia a 650 MHz",
            "Configura la frecuencia a 650 MHz",
        ],
        "FREQ 594MHz": [
            "Pon la frecuencia en 594 MHz",
            "Sintoniza 594 MHz",
            "Cambia a 594 MHz",
        ],
        "FREQ 1.25GHz": [
            "Pon la frecuencia en 1.25 GHz",
            "Sintoniza 1.25 GHz",
            "Cambia a 1.25 GHz",
        ],
        "BAND TER": [
            "Cambia a banda terrestre",
            "Selecciona banda terrestre",
            "Pon banda TER",
        ],
        "BAND SAT": [
            "Cambia a banda satélite",
            "Selecciona banda satélite",
            "Pon banda SAT",
        ],
        "BAND FM": [
            "Selecciona banda FM",
            "Pon banda FM",
            "Cambia a FM",
        ],
        "BAND DAB": [
            "Selecciona banda DAB",
            "Pon banda DAB",
            "Cambia a DAB",
        ],
        "CH UP": [
            "Cambia al siguiente canal",
            "Sintoniza el siguiente canal",
            "Avanza al canal siguiente",
        ],
        "CH DOWN": [
            "Cambia al canal anterior",
            "Sintoniza el canal anterior",
            "Retrocede al canal anterior",
        ],
        "CH 38": [
            "Sintoniza el canal 38",
            "Cambia al canal 38",
            "Selecciona el canal 38",
        ],
        "INPUT RF": [
            "Cambia la entrada a RF",
            "Selecciona entrada RF",
            "Pon entrada RF",
        ],
        "INPUT FO": [
            "Cambia la entrada a fibra óptica",
            "Selecciona entrada óptica",
            "Pon entrada FO",
        ],
        "INPUT IP": [
            "Selecciona entrada IP",
            "Cambia la entrada a IP",
            "Pon entrada IP",
        ],
        "INPUT ASI": [
            "Selecciona entrada ASI",
            "Cambia la entrada a ASI",
        ],
        "INPUT CVBS": [
            "Selecciona entrada CVBS",
            "Cambia la entrada a CVBS",
        ],
        "LAMBDA 1310": [
            "Pon lambda a 1310",
            "Configura lambda 1310",
            "Selecciona lambda 1310",
        ],
        "LAMBDA 1490": [
            "Pon lambda a 1490",
            "Configura lambda 1490",
            "Selecciona lambda 1490",
        ],
        "LAMBDA 1550": [
            "Pon lambda a 1550",
            "Configura lambda 1550",
            "Selecciona lambda 1550",
        ],
        "RBW AUTO": [
            "Pon el RBW en automático",
            "Configura RBW automático",
            "Activa RBW auto",
        ],
        "RBW 300HzW": [
            "Pon el RBW en 300 HzW",
            "Configura RBW a 300 HzW",
        ],
        "VBW AUTO": [
            "Pon el VBW en automático",
            "Configura VBW automático",
            "Activa VBW auto",
        ],
        "VBW 10KHz": [
            "Pon el VBW en 10 KHz",
            "Configura VBW a 10 KHz",
        ],
        "SPAN 20MHz": [
            "Pon el span en 20 MHz",
            "Configura el span a 20 MHz",
        ],
        "RLEVEL AUTO": [
            "Pon el nivel de referencia en automático",
            "Configura RLEVEL automático",
        ],
        "RLEVEL 80dBuV": [
            "Pon el nivel de referencia en 80 dBuV",
            "Configura RLEVEL a 80 dBuV",
        ],
        "ATT": [
            "Reinicia la atenuación",
            "Restablece la atenuación",
        ],
        "HOLD MAX ON": [
            "Activa hold máximo",
            "Pon hold máximo",
        ],
        "HOLD MAX OFF": [
            "Desactiva hold máximo",
            "Quita hold máximo",
        ],
        "HOLD MIN ON": [
            "Activa hold mínimo",
            "Pon hold mínimo",
        ],
        "HOLD MIN OFF": [
            "Desactiva hold mínimo",
            "Quita hold mínimo",
        ],
        "HOLD CLEAR": [
            "Limpia el hold del espectro",
            "Borra el hold",
        ],
        "SERVICE 2371": [
            "Selecciona el servicio 2371",
            "Cambia al servicio 2371",
        ],
        "PROF demo_import": [
            "Selecciona el perfil demo_import",
            "Cambia al perfil demo_import",
        ],
        "IMAG": [
            "Haz una captura de pantalla",
            "Captura la pantalla del equipo",
            "Saca un pantallazo",
        ],
    }

    for scpi, inputs in write_commands.items():
        for user_text in inputs:
            examples.append(example(SYSTEM_COMMAND, user_text, scpi))

    return examples


def build_knowledge_examples() -> list[dict]:
    definitions = {
        "MER": "El MER mide la calidad de la modulación de la señal y se expresa en dB.",
        "POW": "El comando POW? devuelve la potencia o nivel de señal con las unidades configuradas en el equipo.",
        "CN": "El comando CN? devuelve la relación portadora/ruido en dB.",
        "CBER": "El comando CBER? devuelve la tasa de error antes del primer corrector de errores.",
        "VBER": "El comando VBER? devuelve la tasa de error antes de la corrección Reed-Solomon cuando está disponible.",
        "LOCK": "El comando LOCK? indica si la señal está bloqueada, devolviendo TRUE o FALSE.",
        "FREQ": "El comando FREQ permite consultar o configurar la frecuencia sintonizada.",
        "BAND": "El comando BAND permite consultar o cambiar la banda activa del equipo.",
        "MEAS": "El comando MEAS? devuelve las medidas en tiempo real mostradas actualmente por el equipo.",
        "PAR": "El comando PAR? devuelve parámetros de la señal sintonizada cuando están disponibles.",
        "VBW": "El comando VBW permite consultar o cambiar el ancho de banda de vídeo del analizador de espectro.",
        "RBW": "El comando RBW permite consultar o cambiar el ancho de banda de resolución del analizador de espectro.",
        "SPAN": "El comando SPAN permite consultar o cambiar el rango de frecuencias mostrado por el analizador de espectro.",
        "RLEVEL": "El comando RLEVEL permite consultar o cambiar el nivel de referencia del espectro.",
    }

    templates = [
        "Qué es {cmd}",
        "Qué hace {cmd}",
        "Para qué sirve {cmd}",
        "Explícame {cmd}",
        "Qué devuelve {cmd}",
        "Cómo se usa {cmd}",
    ]

    examples = []

    for cmd, answer in definitions.items():
        for template in templates:
            examples.append(
                example(SYSTEM_KNOWLEDGE, template.format(cmd=cmd), answer)
            )

    examples.extend([
        example(
            SYSTEM_KNOWLEDGE,
            "Qué comandos hay para medidas",
            "Los comandos principales de medida incluyen MEAS?, POW?, CN?, MER?, CBER?, VBER?, BCHBER?, LKM?, PER?, SER?, HUM? y CSO?.",
        ),
        example(
            SYSTEM_KNOWLEDGE,
            "Qué comandos hay para espectro",
            "Los comandos relacionados con espectro incluyen RBW?, VBW?, SPAN?, RLEVEL?, ATT y HOLD.",
        ),
        example(
            SYSTEM_KNOWLEDGE,
            "Qué comandos hay para entrada",
            "El comando INPUT permite consultar o seleccionar entradas como RF, FO, IP, ASI, CVBS, TSP, ETI y EDI.",
        ),
    ])

    return examples


def build_unknown_examples() -> list[dict]:
    inputs = [
        "Cuéntame un chiste",
        "Qué tiempo hace hoy",
        "Busca información en internet",
        "Analiza todo el sistema",
        "Haz un diagnóstico completo",
        "Ponlo bien",
        "Mejora la señal automáticamente",
        "Arregla la instalación",
        "Optimiza el canal",
        "Haz una receta",
        "Reproduce música",
        "Abre el navegador",
        "Dime una película",
        "Consulta noticias actuales",
        "Calcula mi nómina",
        "Escribe un poema",
        "Configura todo",
        "Soluciona el problema",
        "Haz una prueba completa",
        "Ejecuta mantenimiento general",
    ]

    return [example(SYSTEM_COMMAND, text, "UNKNOWN") for text in inputs]


def deduplicate(rows: list[dict]) -> list[dict]:
    seen = set()
    result = []

    for row in rows:
        key = json.dumps(row, ensure_ascii=False, sort_keys=True)
        if key not in seen:
            seen.add(key)
            result.append(row)

    return result


def main() -> None:
    dataset = []
    dataset.extend(build_command_examples())
    dataset.extend(build_knowledge_examples())
    dataset.extend(build_unknown_examples())

    dataset = deduplicate(dataset)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT.open("w", encoding="utf-8") as file:
        for row in dataset:
            file.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(f"Dataset generado: {len(dataset)} ejemplos")
    print(f"Archivo: {OUTPUT}")


if __name__ == "__main__":
    main()