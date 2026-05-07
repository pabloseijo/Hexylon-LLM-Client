"""
Catálogo de comandos SCPI del generador de señales R&S SGU100A.

Fuente: R&S SGU100A User Manual, versión 10, capítulo 13 (Remote control commands).
Conexión: TCP/IP, puerto 5025 (SOCKET).
Unidades por defecto: frecuencia en Hz, nivel en dBm.
"""

SGU100A_COMMAND_CATALOG = {

    # -------------------------------------------------------------------------
    # COMANDOS COMUNES (IEEE 488.2)
    # -------------------------------------------------------------------------

    "*IDN?": {
        "description": "Devuelve la identificación del instrumento.",
        "type": "query",
        "returns": "string — formato: Rohde&Schwarz,SGU100A,<part>/<serial>,<fw>",
        "example": "*IDN?",
        "notes": "Solo lectura.",
    },
    "*RST": {
        "description": "Resetea el instrumento a su estado por defecto.",
        "type": "write",
        "returns": None,
        "example": "*RST",
        "notes": "Equivalente a SYSTem:PRESet.",
    },
    "*CLS": {
        "description": "Limpia los registros de estado y el buffer de salida.",
        "type": "write",
        "returns": None,
        "example": "*CLS",
        "notes": "No altera las máscaras de los registros.",
    },
    "*OPC": {
        "description": "Activa el bit 0 del registro de eventos cuando todos los comandos anteriores han terminado.",
        "type": "write/query",
        "returns": "1 cuando todos los comandos anteriores han terminado (modo query).",
        "example": "*OPC?",
        "notes": "Útil para sincronización de comandos.",
    },
    "*OPC?": {
        "description": "Escribe '1' en el buffer de salida cuando todos los comandos anteriores han terminado.",
        "type": "query",
        "returns": "1",
        "example": "*OPC?",
        "notes": "Útil para sincronización.",
    },
    "*WAI": {
        "description": "Impide la ejecución de comandos posteriores hasta que todos los anteriores hayan terminado.",
        "type": "event",
        "returns": None,
        "example": "*WAI",
        "notes": None,
    },

    # -------------------------------------------------------------------------
    # LOCK / UNLOCK
    # -------------------------------------------------------------------------

    "LOCK?": {
        "description": "Solicita el bloqueo exclusivo del instrumento para el controlador. Evita interferencias de otros controladores.",
        "type": "query",
        "returns": "1 si el bloqueo fue concedido, 0 si denegado.",
        "example": "LOCK? 12345",
        "params": {
            "Lock Request Id": "Número entero arbitrario que identifica al controlador. Usar 0 para comprobar si ya está bloqueado.",
        },
        "notes": "Recomendado al inicio de cada sesión remota.",
    },
    "UNL": {
        "description": "Libera el bloqueo del instrumento.",
        "type": "write",
        "returns": None,
        "example": "UNL 12345",
        "params": {
            "Lock Request Id": "El mismo número usado en LOCK?.",
        },
        "notes": "Siempre ejecutar al finalizar la sesión.",
    },

    # -------------------------------------------------------------------------
    # OUTPUT — Control de la salida RF
    # -------------------------------------------------------------------------

    "OUTPut:STATe": {
        "description": "Activa o desactiva la salida RF del generador.",
        "type": "write/query",
        "returns": "1|ON|0|OFF",
        "example": "OUTPut:STATe ON",
        "params": {
            "State": "1 | ON | 0 | OFF",
        },
        "notes": "Forma abreviada: OUTP:STAT ON / OUTP:STAT OFF",
    },
    "OUTPut:STATe:PON": {
        "description": "Selecciona el estado de la salida RF al encender el instrumento.",
        "type": "write/query",
        "returns": "OFF | UNCHanged",
        "example": "OUTPut:STATe:PON UNCHanged",
        "params": {
            "Mode": "OFF — salida desactivada al encender. UNCHanged — mantiene el estado anterior.",
        },
        "notes": "RST: UNCHanged",
    },
    "OUTPut:AMODe": {
        "description": "Configura el modo del atenuador en la salida RF.",
        "type": "write/query",
        "returns": "AUTO | FIXed",
        "example": "OUTPut:AMODe AUTO",
        "params": {
            "AMode": "AUTO — el atenuador se conmuta automáticamente. FIXed — atenuador fijo en posición actual.",
        },
        "notes": "RST: AUTO",
    },
    "OUTPut:AFIXed:RANGe:LOWer?": {
        "description": "Consulta el nivel mínimo que se puede configurar sin ajustar el atenuador.",
        "type": "query",
        "returns": "float — unidad: dBm",
        "example": "OUTPut:AFIXed:RANGe:LOWer?",
        "notes": "Solo lectura.",
    },
    "OUTPut:AFIXed:RANGe:UPPer?": {
        "description": "Consulta el nivel máximo que se puede configurar sin ajustar el atenuador.",
        "type": "query",
        "returns": "float — unidad: dBm",
        "example": "OUTPut:AFIXed:RANGe:UPPer?",
        "notes": "Solo lectura.",
    },
    "OUTPut:PROTection:CLEar": {
        "description": "Resetea el circuito de protección tras haberse activado. El estado de la salida vuelve a ser controlado por OUTPut:STATe.",
        "type": "event",
        "returns": None,
        "example": "OUTP:PROT:CLE",
        "notes": None,
    },

    # -------------------------------------------------------------------------
    # SOURce:FREQuency — Control de frecuencia
    # -------------------------------------------------------------------------

    "SOURce:FREQuency:CW": {
        "description": "Configura la frecuencia RF en el conector de salida del instrumento.",
        "type": "write/query",
        "returns": "float — Hz",
        "example": "SOURce:FREQuency:CW 2000000000",
        "params": {
            "Cw": "float — Rango: 1E+6 a 40E+9 Hz. Incremento: 1E-3 Hz. RST: 1E+9 Hz.",
        },
        "notes": "Forma corta: FREQ 2 GHz. Las unidades GHz, MHz, kHz son válidas.",
        "aliases": ["FREQ", "SOURce:FREQ:CW", "SOURce:FREQ:FIXed"],
    },

    # -------------------------------------------------------------------------
    # SOURce:POWer — Control de nivel/potencia
    # -------------------------------------------------------------------------

    "SOURce:POWer:LEVel:IMMediate:AMPLitude": {
        "description": "Configura el nivel RF en el conector de salida del instrumento.",
        "type": "write/query",
        "returns": "float — dBm",
        "example": "SOURce:POWer:LEVel:IMMediate:AMPLitude -10dBm",
        "params": {
            "Amplitude": "float — Rango: -120 a 25 dBm. Incremento: 0.01. RST: -10 dBm.",
        },
        "notes": "Forma corta: POW -10dBm. Incluye el offset si está configurado.",
        "aliases": ["POW", "SOURce:POWer", "SOURce:POWer:LEVel:IMMediate"],
    },
    "SOURce:POWer:POWer": {
        "description": "Configura el nivel en el conector de salida RF. No considera el offset configurado.",
        "type": "write/query",
        "returns": "float — dBm",
        "example": "POW:POW 15",
        "params": {
            "Power": "float — Rango: -120 a 25 dBm. Incremento: 0.01. RST: -10 dBm.",
        },
        "notes": "A diferencia de SOURce:POWer:LEVel, este comando ignora el offset.",
    },
    "SOURce:POWer:LEVel:IMMediate:OFFSet": {
        "description": "Especifica el offset de nivel constante de un atenuador/amplificador externo.",
        "type": "write/query",
        "returns": "float — dB",
        "example": "SOURce:POWer:LEVel:IMMediate:OFFSet 3",
        "params": {
            "Offset": "float — Rango: -100 a 100 dB. Incremento: 0.1. RST: 0.",
        },
        "notes": "Solo se permite dB como unidad. La relación es: POWer = RF output + OFFSet.",
    },
    "SOURce:POWer:LIMit:AMPLitude": {
        "description": "Configura el límite superior de la potencia de la señal RF.",
        "type": "write/query",
        "returns": "float — dBm",
        "example": "SOURce:POWer:LIMit:AMPLitude 30dBm",
        "params": {
            "Amplitude": "float — Rango: -300 a 30 dBm. RST: 30 dBm.",
        },
        "notes": "No se resetea con *RST — solo con preset de fábrica.",
    },
    "SOURce:POWer:PEP?": {
        "description": "Consulta la potencia de envolvente de pico (PEP) de la señal RF en el DUT.",
        "type": "query",
        "returns": "float — Rango: -120 a 25 dBm.",
        "example": "SOURce:POWer:PEP?",
        "notes": "Solo lectura.",
    },
    "SOURce:POWer:RANGe:LOWer?": {
        "description": "Consulta el nivel mínimo del rango en el modo de nivel actual.",
        "type": "query",
        "returns": "float — dBm",
        "example": "SOURce:POWer:RANGe:LOWer?",
        "notes": "Solo lectura.",
    },
    "SOURce:POWer:RANGe:UPPer?": {
        "description": "Consulta el nivel máximo del rango en el modo de nivel actual.",
        "type": "query",
        "returns": "float — dBm",
        "example": "SOURce:POWer:RANGe:UPPer?",
        "notes": "Solo lectura.",
    },
    "SOURce:POWer:ALC:STATe": {
        "description": "Activa o desactiva el control automático de nivel (ALC).",
        "type": "write/query",
        "returns": "1 | OFFTable | ONTable | ON",
        "example": "SOURce:POWer:ALC:STATe ON",
        "params": {
            "State": "1 | OFFTable | ONTable | ON. RST: ONTable.",
        },
        "notes": None,
    },
    "SOURce:POWer:ALC:SONCe": {
        "description": "Activa brevemente el control automático de nivel para corrección.",
        "type": "event",
        "returns": None,
        "example": "SOURce:POWer:ALC:SONCe",
        "notes": None,
    },
    "SOURce:POWer:LMODe": {
        "description": "Selecciona el modo de nivel.",
        "type": "write/query",
        "returns": "NORMal | LNOise | LDIStortion",
        "example": "SOURce:POWer:LMODe LNOise",
        "params": {
            "LevMode": "NORMal — selección automática. LNOise — menor ruido. LDIStortion — menor distorsión.",
        },
        "notes": None,
    },
    "SOURce:POWer:SCHaracteristic": {
        "description": "Selecciona la característica para la configuración de nivel.",
        "type": "write/query",
        "returns": "AUTO | UNINterrupted | CVSWr | USER | MONotone",
        "example": "SOURce:POWer:SCHaracteristic AUTO",
        "params": {
            "Characteristic": "AUTO | UNINterrupted | CVSWr | USER | MONotone. RST: AUTO.",
        },
        "notes": None,
    },

    # -------------------------------------------------------------------------
    # SOURce:SETTings — Aplicar configuración
    # -------------------------------------------------------------------------

    "SOURce:SETTings:APPLy": {
        "description": "Aplica la configuración de señal y activa la salida. Necesario tras configurar frecuencia y nivel cuando el SGU actúa como upconverter.",
        "type": "event",
        "returns": None,
        "example": "SETTings:APPLy",
        "notes": "Forma corta: SETTings:APPLy. Obligatorio para que los cambios surtan efecto en modo upconverter.",
        "aliases": ["SETTings:APPLy"],
    },

    # -------------------------------------------------------------------------
    # SOURce:LOSCillator — Oscilador local
    # -------------------------------------------------------------------------

    "SOURce:LOSCillator:FREQuency?": {
        "description": "Consulta la frecuencia requerida de la señal del oscilador local.",
        "type": "query",
        "returns": "float — Rango: 1E+6 a 20E+9 Hz. RST: 1E+9 Hz.",
        "example": "LOSCillator:FREQuency?",
        "notes": "Solo lectura. Necesario cuando el SGU actúa como upconverter externo.",
        "aliases": ["LOSCillator:FREQuency?"],
    },
    "SOURce:LOSCillator:POWer?": {
        "description": "Consulta el nivel requerido de la señal del oscilador local.",
        "type": "query",
        "returns": "float — Rango: -120 a 25 dBm. RST: -10 dBm.",
        "example": "LOSCillator:POWer?",
        "notes": "Solo lectura. Necesario cuando el SGU actúa como upconverter externo.",
        "aliases": ["LOSCillator:POWer?"],
    },

    # -------------------------------------------------------------------------
    # SOURce:IQ — Modulación I/Q
    # -------------------------------------------------------------------------

    "SOURce:IQ:STATe": {
        "description": "Activa o desactiva la modulación I/Q.",
        "type": "write/query",
        "returns": "1 | ON | 0 | OFF",
        "example": "SOURce:IQ:STATe ON",
        "params": {
            "State": "1 | ON | 0 | OFF. RST: 0 (OFF).",
        },
        "notes": None,
    },

    # -------------------------------------------------------------------------
    # Fast speed commands — Configuración rápida
    # -------------------------------------------------------------------------

    "FFASt": {
        "description": "Configura la frecuencia RF con mínima latencia. No admite unidades.",
        "type": "write",
        "returns": None,
        "example": "FFASt 12750000000",
        "params": {
            "Freq": "float — sin unidades (Hz implícito). Bypasses the status system.",
        },
        "notes": "No se puede combinar con *OPC?. Solo para uso cuando la latencia es crítica.",
    },
    "PFASt": {
        "description": "Configura el nivel RF con mínima latencia. No admite unidades.",
        "type": "write",
        "returns": None,
        "example": "PFASt -10",
        "params": {
            "Pow": "float — sin unidades (dBm implícito). No considera offset.",
        },
        "notes": "No se puede combinar con *OPC?. Solo para uso cuando la latencia es crítica.",
    },

    # -------------------------------------------------------------------------
    # SYSTem — Sistema
    # -------------------------------------------------------------------------

    "SYSTem:ERRor:ALL?": {
        "description": "Consulta todos los errores en la cola de errores.",
        "type": "query",
        "returns": "string",
        "example": "SYSTem:ERRor:ALL?",
        "notes": "Solo lectura.",
    },
    "SYSTem:ERRor:NEXT?": {
        "description": "Consulta el siguiente error en la cola de errores.",
        "type": "query",
        "returns": "string",
        "example": "SYSTem:ERRor:NEXT?",
        "notes": "Solo lectura.",
    },
    "SYSTem:VERSion?": {
        "description": "Consulta la versión SCPI implementada.",
        "type": "query",
        "returns": "string",
        "example": "SYSTem:VERSion?",
        "notes": "Solo lectura.",
    },
    "SYSTem:COMMunicate:NETWork:IPADdress?": {
        "description": "Consulta la dirección IP del instrumento.",
        "type": "query",
        "returns": "string — formato: x.x.x.x",
        "example": "SYSTem:COMMunicate:NETWork:IPADdress?",
        "notes": "Solo lectura.",
    },

    # -------------------------------------------------------------------------
    # SOURce:PULM — Modulación de pulso
    # -------------------------------------------------------------------------

    "SOURce:PULM:STATe": {
        "description": "Activa o desactiva la modulación de pulso.",
        "type": "write/query",
        "returns": "0 | 1 | OFF | ON",
        "example": "PULM:STAT ON",
        "params": {
            "State": "0 | 1 | OFF | ON. RST: 0 (OFF).",
        },
        "notes": None,
    },
}


# -------------------------------------------------------------------------
# Resumen de comandos más usados para configuración de señal
# -------------------------------------------------------------------------

SGU100A_QUICK_REFERENCE = """
## Configuración básica de señal (uso más frecuente)

### 1. Iniciar sesión remota
*RST; *CLS
LOCK? 12345

### 2. Configurar frecuencia
SOURce:FREQuency:CW 2000000000    # 2 GHz
# o forma corta:
FREQ 2 GHz

### 3. Configurar nivel/potencia
SOURce:POWer:LEVel:IMMediate:AMPLitude -10dBm
# o forma corta:
POW -10dBm

### 4. Activar salida RF
OUTPut:STATe ON

### 5. Aplicar configuración (necesario en modo upconverter)
SETTings:APPLy

### 6. Finalizar sesión
UNL 12345

## Rangos importantes
- Frecuencia: 1 MHz a 40 GHz
- Nivel: -120 a 25 dBm (incremento: 0.01 dBm)
- Puerto TCP: 5025

## Unidades admitidas
- Frecuencia: GHz, MHz, kHz, Hz
- Nivel: dBm (las unidades lineales V, W no están permitidas en OFFSet)
"""


# -------------------------------------------------------------------------
# Comandos prioritarios para pruebas (potencia y frecuencia)
# -------------------------------------------------------------------------

SGU100A_PRIORITY_COMMANDS = [
    "SOURce:FREQuency:CW",
    "SOURce:POWer:LEVel:IMMediate:AMPLitude",
    "OUTPut:STATe",
    "SOURce:SETTings:APPLy",
    "*IDN?",
    "*RST",
    "LOCK?",
    "UNL",
]