import sys
sys.path.insert(0, "src")

from llm.knowledge.query_classifier import classify
from llm.core.scpi_generator import detect_intent

casos = [
    # EXACT COMMAND
    ("que hace el comando FREQ",         "exact_command"),
    ("explicame el comando BAND",        "exact_command"),
    ("que hace CH",                      "exact_command"),
    ("que hace INPUT",                   "exact_command"),
    ("que hace LAMBDA",                  "exact_command"),
    ("que hace MODE",                    "exact_command"),
    ("que hace WIDGETS",                 "exact_command"),
    ("que hace PROF",                    "exact_command"),
    ("que hace LPROF",                   "exact_command"),
    ("que hace LOCK",                    "exact_command"),
    ("que hace IDN",                     "exact_command"),
    ("que hace IMAG",                    "exact_command"),
    ("que hace SERVICES",                "exact_command"),
    ("que hace SERVICE",                 "exact_command"),
    ("que hace RBW",                     "exact_command"),
    ("que hace VBW",                     "exact_command"),
    ("que hace SPAN",                    "exact_command"),
    ("que hace RLEVEL",                  "exact_command"),
    ("que hace ATT",                     "exact_command"),
    ("que hace HOLD",                    "exact_command"),
    ("que hace FSTR",                    "exact_command"),
    ("que hace ANT",                     "exact_command"),
    ("que hace EXTAMP",                  "exact_command"),
    ("que hace VDC",                     "exact_command"),
    ("que hace ADDCHIPTV",               "exact_command"),
    ("que hace DELCHIPTV",               "exact_command"),
    ("que hace LCHIPTV",                 "exact_command"),

    # METRIC DEFINITION
    ("que es el MER",                    "metric_definition"),
    ("que es el CBER",                   "metric_definition"),
    ("que es el VBER",                   "metric_definition"),
    ("que es el BCHBER",                 "metric_definition"),
    ("que es el POW",                    "metric_definition"),
    ("que es el CN",                     "metric_definition"),
    ("que es el LKM",                    "metric_definition"),
    ("que es el PER",                    "metric_definition"),
    ("que es el SER",                    "metric_definition"),
    ("que es el HUM",                    "metric_definition"),
    ("que es el CSO",                    "metric_definition"),
    ("que es PREBER",                    "metric_definition"),
    ("que es POSTBER",                   "metric_definition"),
    ("que es PRELDPCBER",                "metric_definition"),
    ("que es PREBCHBER",                 "metric_definition"),
    ("que es MSCBER",                    "metric_definition"),
    ("que es FICBER",                    "metric_definition"),
    ("que es CNBOOT",                    "metric_definition"),
    ("que es ECHOES",                    "metric_definition"),
    ("que es OPT_POW",                   "metric_definition"),
    ("que es OPT_POW_1310",              "metric_definition"),

    # TOPIC
    ("que comandos hay para el espectro",        "topic"),
    ("que comandos hay para la sintonia",        "topic"),
    ("que opciones hay para los perfiles",       "topic"),
    ("que comandos hay para IPTV",               "topic"),
    ("que hay para las medidas de senal",        "topic"),
    ("que comandos hay para el modo y widgets",  "topic"),
    ("que hay para entradas de senal",           "topic"),
    ("que comandos hay para senal optica",       "topic"),

    # HOW TO
    ("como cambio de banda en modo radio",       "how_to"),
    ("como selecciono un servicio por SID",      "how_to"),
    ("como configuro el span del espectro",      "how_to"),
    ("como anado un canal IPTV",                 "how_to"),
    ("como subo un plan de canales",             "how_to"),

    # UNSUPPORTED
    ("recetas de cocina",                        "unsupported"),
    ("que tiempo hace hoy",                      "unsupported"),
    ("cuentame un chiste",                       "unsupported"),
    ("quien gano el mundial",                    "unsupported"),
]

col1 = 45
col2 = 10
col3 = 20
col4 = 20
col5 = 15

header = (
    "   "
    + "CONSULTA".ljust(col1)
    + "INTENT".ljust(col2)
    + "ESPERADO".ljust(col3)
    + "REAL".ljust(col4)
    + "CMD".ljust(col5)
)
print(header)
print("-" * (3 + col1 + col2 + col3 + col4 + col5))

errores = 0
for consulta, esperado in casos:
    intent = detect_intent(consulta)
    r = classify(consulta)
    ok = "OK" if r.query_type == esperado else "!!"
    if r.query_type != esperado:
        errores += 1
    cmd = str(r.matched_command) if r.matched_command else "-"
    print(
        f"{ok} "
        + consulta.ljust(col1)
        + intent.ljust(col2)
        + esperado.ljust(col3)
        + r.query_type.ljust(col4)
        + cmd.ljust(col5)
    )

print()
print(f"Resultado: {len(casos) - errores}/{len(casos)} correctos, {errores} errores")