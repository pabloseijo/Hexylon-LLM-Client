"""
Catálogo de comandos SCPI del generador de señales R&S SGU100A.

Fuente: R&S SGU100A User Manual, versión 10, capítulo 13 (Remote control commands).
Conexión: TCP/IP, puerto 5025 (SOCKET).
Unidades por defecto: frecuencia en Hz, nivel en dBm.

Este módulo replica el formato de command_catalog.py para que sea compatible
con context_builder, knowledge_handler y el orquestador.
"""

from __future__ import annotations

from typing import Any


GENERATOR_COMMAND_CATALOG: dict[str, dict[str, Any]] = {

    # -------------------------------------------------------------------------
    # COMANDOS COMUNES (IEEE 488.2)
    # -------------------------------------------------------------------------

    "*IDN": {
        "name": "*IDN",
        "category": "common",
        "description": "Returns the instrument identification string.",
        "read_syntax": ["*IDN?"],
        "write_syntax": [],
        "read_response": "Returns: Rohde&Schwarz,SGU100A,<part>/<serial>,<firmware>",
        "write_values": None,
        "units": None,
        "constraints": [],
        "notes": ["Read-only command."],
        "examples": ["*IDN?"],
        "related_commands": [],
    },
    "*RST": {
        "name": "*RST",
        "category": "common",
        "description": "Resets the instrument to its defined default state. Equivalent to SYSTem:PRESet.",
        "read_syntax": [],
        "write_syntax": ["*RST"],
        "read_response": None,
        "write_values": None,
        "units": None,
        "constraints": [],
        "notes": ["Recommended at the start of each remote session."],
        "examples": ["*RST", "*RST; *CLS"],
        "related_commands": ["*CLS"],
    },
    "*CLS": {
        "name": "*CLS",
        "category": "common",
        "description": "Clears the status registers and the output buffer. Does not alter register masks.",
        "read_syntax": [],
        "write_syntax": ["*CLS"],
        "read_response": None,
        "write_values": None,
        "units": None,
        "constraints": [],
        "notes": [],
        "examples": ["*CLS", "*RST; *CLS"],
        "related_commands": ["*RST"],
    },
    "*OPC": {
        "name": "*OPC",
        "category": "common",
        "description": "Sets bit 0 in the event status register when all preceding commands have finished. In query form, writes '1' to the output buffer.",
        "read_syntax": ["*OPC?"],
        "write_syntax": ["*OPC"],
        "read_response": "1 — when all preceding commands have finished.",
        "write_values": None,
        "units": None,
        "constraints": [],
        "notes": ["Useful for command synchronization."],
        "examples": ["*OPC?"],
        "related_commands": ["*WAI"],
    },
    "*WAI": {
        "name": "*WAI",
        "category": "common",
        "description": "Prevents execution of subsequent commands until all preceding commands have finished.",
        "read_syntax": [],
        "write_syntax": ["*WAI"],
        "read_response": None,
        "write_values": None,
        "units": None,
        "constraints": [],
        "notes": [],
        "examples": ["*WAI"],
        "related_commands": ["*OPC"],
    },

    # -------------------------------------------------------------------------
    # LOCK / UNLOCK
    # -------------------------------------------------------------------------

    "LOCK": {
        "name": "LOCK",
        "category": "control",
        "description": "Requests exclusive lock of the instrument for the controller. Prevents interference from other controllers.",
        "read_syntax": ["LOCK? <id>"],
        "write_syntax": [],
        "read_response": "1 if lock granted, 0 if denied.",
        "write_values": None,
        "units": None,
        "constraints": [
            "Use 0 as id to check if the instrument is already locked.",
            "Abort the program if the lock is denied.",
        ],
        "notes": [
            "Recommended at the start of every remote session.",
            "Use any arbitrary integer as the lock ID.",
        ],
        "examples": ["LOCK? 12345"],
        "related_commands": ["UNL"],
    },
    "UNL": {
        "name": "UNL",
        "category": "control",
        "description": "Releases the instrument lock.",
        "read_syntax": [],
        "write_syntax": ["UNL <id>"],
        "read_response": None,
        "write_values": ["<id>"],
        "units": None,
        "constraints": ["Must use the same ID used in LOCK?."],
        "notes": ["Always execute at the end of the remote session."],
        "examples": ["UNL 12345"],
        "related_commands": ["LOCK"],
    },

    # -------------------------------------------------------------------------
    # OUTPut — RF output control
    # -------------------------------------------------------------------------

    "OUTPut:STATe": {
        "name": "OUTPut:STATe",
        "category": "output",
        "description": "Activates or deactivates the RF output of the generator.",
        "read_syntax": ["OUTPut:STATe?"],
        "write_syntax": ["OUTPut:STATe ON", "OUTPut:STATe OFF"],
        "read_response": "Returns: 1 | ON | 0 | OFF",
        "write_values": ["1", "ON", "0", "OFF"],
        "units": None,
        "constraints": [],
        "notes": ["Short form: OUTP:STAT ON / OUTP:STAT OFF"],
        "examples": [
            "OUTPut:STATe ON",
            "OUTPut:STATe OFF",
            "OUTPut:STATe?",
        ],
        "related_commands": ["OUTPut:STATe:PON"],
    },
    "OUTPut:STATe:PON": {
        "name": "OUTPut:STATe:PON",
        "category": "output",
        "description": "Selects the RF output state when the instrument is powered on.",
        "read_syntax": ["OUTPut:STATe:PON?"],
        "write_syntax": ["OUTPut:STATe:PON OFF", "OUTPut:STATe:PON UNCHanged"],
        "read_response": "Returns: OFF | UNCHanged",
        "write_values": ["OFF", "UNCHanged"],
        "units": None,
        "constraints": [],
        "notes": ["RST: UNCHanged"],
        "examples": [
            "OUTPut:STATe:PON UNCHanged",
            "OUTPut:STATe:PON OFF",
        ],
        "related_commands": ["OUTPut:STATe"],
    },
    "OUTPut:AMODe": {
        "name": "OUTPut:AMODe",
        "category": "output",
        "description": "Sets the attenuator mode at the RF output.",
        "read_syntax": ["OUTPut:AMODe?"],
        "write_syntax": ["OUTPut:AMODe AUTO", "OUTPut:AMODe FIXed"],
        "read_response": "Returns: AUTO | FIXed",
        "write_values": ["AUTO", "FIXed"],
        "units": None,
        "constraints": [],
        "notes": [
            "AUTO: attenuator switches automatically over full range.",
            "FIXed: attenuator is fixed at current position.",
            "RST: AUTO",
        ],
        "examples": ["OUTPut:AMODe AUTO", "OUTPut:AMODe FIXed"],
        "related_commands": ["OUTPut:AFIXed:RANGe:LOWer", "OUTPut:AFIXed:RANGe:UPPer"],
    },
    "OUTPut:AFIXed:RANGe:LOWer": {
        "name": "OUTPut:AFIXed:RANGe:LOWer",
        "category": "output",
        "description": "Queries the minimum level settable without adjusting the attenuator.",
        "read_syntax": ["OUTPut:AFIXed:RANGe:LOWer?"],
        "write_syntax": [],
        "read_response": "Returns float in dBm.",
        "write_values": None,
        "units": ["dBm"],
        "constraints": [],
        "notes": ["Read-only command."],
        "examples": ["OUTPut:AFIXed:RANGe:LOWer?"],
        "related_commands": ["OUTPut:AFIXed:RANGe:UPPer"],
    },
    "OUTPut:AFIXed:RANGe:UPPer": {
        "name": "OUTPut:AFIXed:RANGe:UPPer",
        "category": "output",
        "description": "Queries the maximum level settable without adjusting the attenuator.",
        "read_syntax": ["OUTPut:AFIXed:RANGe:UPPer?"],
        "write_syntax": [],
        "read_response": "Returns float in dBm.",
        "write_values": None,
        "units": ["dBm"],
        "constraints": [],
        "notes": ["Read-only command."],
        "examples": ["OUTPut:AFIXed:RANGe:UPPer?"],
        "related_commands": ["OUTPut:AFIXed:RANGe:LOWer"],
    },
    "OUTPut:PROTection:CLEar": {
        "name": "OUTPut:PROTection:CLEar",
        "category": "output",
        "description": "Resets the protective circuit after it has been triggered. Output state is then controlled again by OUTPut:STATe.",
        "read_syntax": [],
        "write_syntax": ["OUTPut:PROTection:CLEar"],
        "read_response": None,
        "write_values": None,
        "units": None,
        "constraints": [],
        "notes": ["Short form: OUTP:PROT:CLE"],
        "examples": ["OUTP:PROT:CLE"],
        "related_commands": ["OUTPut:STATe"],
    },

    # -------------------------------------------------------------------------
    # SOURce:FREQuency — Frequency control
    # -------------------------------------------------------------------------

    "SOURce:FREQuency:CW": {
        "name": "SOURce:FREQuency:CW",
        "category": "frequency",
        "description": "Sets the RF frequency at the RF output connector.",
        "read_syntax": ["SOURce:FREQuency:CW?"],
        "write_syntax": [
            "SOURce:FREQuency:CW <value>",
            "FREQ <value> GHz",
            "FREQ <value> MHz",
            "FREQ <value> kHz",
        ],
        "read_response": "Returns frequency in Hz (float).",
        "write_values": None,
        "units": ["GHz", "MHz", "kHz", "Hz"],
        "constraints": [
            "Range: 1 MHz to 40 GHz (1E+6 to 40E+9 Hz).",
            "Increment: 1E-3 Hz.",
            "RST: 1 GHz (1E+9 Hz).",
        ],
        "notes": [
            "Short forms: FREQ 2 GHz, SOURce:FREQ:CW, SOURce:FREQ:FIXed.",
            "Units GHz, MHz, kHz and Hz are all valid.",
        ],
        "examples": [
            "SOURce:FREQuency:CW 2000000000",
            "FREQ 2 GHz",
            "FREQ 594 MHz",
            "SOURce:FREQuency:CW?",
        ],
        "related_commands": ["SOURce:POWer:LEVel:IMMediate:AMPLitude", "OUTPut:STATe"],
    },

    # -------------------------------------------------------------------------
    # SOURce:POWer — Level/power control
    # -------------------------------------------------------------------------

    "SOURce:POWer:LEVel:IMMediate:AMPLitude": {
        "name": "SOURce:POWer:LEVel:IMMediate:AMPLitude",
        "category": "power",
        "description": "Sets the RF level at the RF output connector. Includes any configured offset.",
        "read_syntax": ["SOURce:POWer:LEVel:IMMediate:AMPLitude?"],
        "write_syntax": [
            "SOURce:POWer:LEVel:IMMediate:AMPLitude <value>dBm",
            "POW <value>dBm",
        ],
        "read_response": "Returns level in dBm (float).",
        "write_values": None,
        "units": ["dBm"],
        "constraints": [
            "Range: -120 to 25 dBm.",
            "Increment: 0.01 dBm.",
            "RST: -10 dBm.",
        ],
        "notes": [
            "Short forms: POW -10dBm, SOURce:POWer, SOURce:POWer:LEVel:IMMediate.",
            "This command considers the configured offset. Use SOURce:POWer:POWer to set level without offset.",
        ],
        "examples": [
            "SOURce:POWer:LEVel:IMMediate:AMPLitude -10dBm",
            "POW -10dBm",
            "POW 0dBm",
            "SOURce:POWer:LEVel:IMMediate:AMPLitude?",
        ],
        "related_commands": [
            "SOURce:POWer:POWer",
            "SOURce:POWer:LEVel:IMMediate:OFFSet",
            "SOURce:POWer:LIMit:AMPLitude",
            "OUTPut:STATe",
        ],
    },
    "SOURce:POWer:POWer": {
        "name": "SOURce:POWer:POWer",
        "category": "power",
        "description": "Sets the level at the RF output connector. Does NOT consider any configured offset.",
        "read_syntax": ["SOURce:POWer:POWer?"],
        "write_syntax": ["SOURce:POWer:POWer <value>", "POW:POW <value>"],
        "read_response": "Returns level in dBm (float).",
        "write_values": None,
        "units": ["dBm"],
        "constraints": [
            "Range: -120 to 25 dBm.",
            "Increment: 0.01 dBm.",
            "RST: -10 dBm.",
        ],
        "notes": [
            "Unlike SOURce:POWer:LEVel:IMMediate:AMPLitude, this ignores any offset.",
            "Short form: POW:POW 15",
        ],
        "examples": [
            "POW:POW 15",
            "SOURce:POWer:POWer -5",
        ],
        "related_commands": [
            "SOURce:POWer:LEVel:IMMediate:AMPLitude",
            "SOURce:POWer:LEVel:IMMediate:OFFSet",
        ],
    },
    "SOURce:POWer:LEVel:IMMediate:OFFSet": {
        "name": "SOURce:POWer:LEVel:IMMediate:OFFSet",
        "category": "power",
        "description": "Specifies a constant level offset for a downstream attenuator or amplifier.",
        "read_syntax": ["SOURce:POWer:LEVel:IMMediate:OFFSet?"],
        "write_syntax": ["SOURce:POWer:LEVel:IMMediate:OFFSet <value>"],
        "read_response": "Returns offset in dB (float).",
        "write_values": None,
        "units": ["dB"],
        "constraints": [
            "Range: -100 to 100 dB.",
            "Increment: 0.1 dB.",
            "RST: 0 dB.",
            "Only dB is permitted — linear units (V, W) are not allowed.",
        ],
        "notes": [
            "Relation: POWer = RF output level + OFFSet.",
            "Entering an offset does not change the RF output level, only the query value of POWer.",
        ],
        "examples": [
            "SOURce:POWer:LEVel:IMMediate:OFFSet 3",
            "SOURce:POWer:LEVel:IMMediate:OFFSet 0",
        ],
        "related_commands": ["SOURce:POWer:LEVel:IMMediate:AMPLitude"],
    },
    "SOURce:POWer:LIMit:AMPLitude": {
        "name": "SOURce:POWer:LIMit:AMPLitude",
        "category": "power",
        "description": "Sets the upper limit of the RF signal power.",
        "read_syntax": ["SOURce:POWer:LIMit:AMPLitude?"],
        "write_syntax": ["SOURce:POWer:LIMit:AMPLitude <value>dBm"],
        "read_response": "Returns upper limit in dBm (float).",
        "write_values": None,
        "units": ["dBm"],
        "constraints": [
            "Range: -300 to 30 dBm.",
            "Increment: 0.01 dBm.",
            "Factory preset: 30 dBm.",
            "NOT reset by *RST — only by factory preset (SYST:FPR).",
        ],
        "notes": [],
        "examples": [
            "SOURce:POWer:LIMit:AMPLitude 30dBm",
            "SOURce:POWer:LIMit:AMPLitude?",
        ],
        "related_commands": ["SOURce:POWer:LEVel:IMMediate:AMPLitude"],
    },
    "SOURce:POWer:PEP": {
        "name": "SOURce:POWer:PEP",
        "category": "power",
        "description": "Queries the RF signal peak envelope power (PEP) at the DUT.",
        "read_syntax": ["SOURce:POWer:PEP?"],
        "write_syntax": [],
        "read_response": "Returns PEP in dBm. Range: -120 to 25 dBm.",
        "write_values": None,
        "units": ["dBm"],
        "constraints": [],
        "notes": ["Read-only command."],
        "examples": ["SOURce:POWer:PEP?"],
        "related_commands": ["SOURce:POWer:LEVel:IMMediate:AMPLitude"],
    },
    "SOURce:POWer:RANGe:LOWer": {
        "name": "SOURce:POWer:RANGe:LOWer",
        "category": "power",
        "description": "Queries the minimum level in the current level mode.",
        "read_syntax": ["SOURce:POWer:RANGe:LOWer?"],
        "write_syntax": [],
        "read_response": "Returns float in dBm.",
        "write_values": None,
        "units": ["dBm"],
        "constraints": [],
        "notes": ["Read-only command."],
        "examples": ["SOURce:POWer:RANGe:LOWer?"],
        "related_commands": ["SOURce:POWer:RANGe:UPPer"],
    },
    "SOURce:POWer:RANGe:UPPer": {
        "name": "SOURce:POWer:RANGe:UPPer",
        "category": "power",
        "description": "Queries the maximum level in the current level mode.",
        "read_syntax": ["SOURce:POWer:RANGe:UPPer?"],
        "write_syntax": [],
        "read_response": "Returns float in dBm.",
        "write_values": None,
        "units": ["dBm"],
        "constraints": [],
        "notes": ["Read-only command."],
        "examples": ["SOURce:POWer:RANGe:UPPer?"],
        "related_commands": ["SOURce:POWer:RANGe:LOWer"],
    },
    "SOURce:POWer:ALC:STATe": {
        "name": "SOURce:POWer:ALC:STATe",
        "category": "power",
        "description": "Activates or deactivates the automatic level control (ALC).",
        "read_syntax": ["SOURce:POWer:ALC:STATe?"],
        "write_syntax": [
            "SOURce:POWer:ALC:STATe ON",
            "SOURce:POWer:ALC:STATe OFF",
            "SOURce:POWer:ALC:STATe OFFTable",
            "SOURce:POWer:ALC:STATe ONTable",
        ],
        "read_response": "Returns: 1 | OFFTable | ONTable | ON",
        "write_values": ["1", "OFFTable", "ONTable", "ON"],
        "units": None,
        "constraints": ["RST: ONTable"],
        "notes": [],
        "examples": ["SOURce:POWer:ALC:STATe ON"],
        "related_commands": ["SOURce:POWer:ALC:SONCe"],
    },
    "SOURce:POWer:ALC:SONCe": {
        "name": "SOURce:POWer:ALC:SONCe",
        "category": "power",
        "description": "Briefly activates automatic level control for correction purposes.",
        "read_syntax": [],
        "write_syntax": ["SOURce:POWer:ALC:SONCe"],
        "read_response": None,
        "write_values": None,
        "units": None,
        "constraints": [],
        "notes": ["Event command — no parameters."],
        "examples": ["SOURce:POWer:ALC:SONCe"],
        "related_commands": ["SOURce:POWer:ALC:STATe"],
    },
    "SOURce:POWer:LMODe": {
        "name": "SOURce:POWer:LMODe",
        "category": "power",
        "description": "Selects the level mode.",
        "read_syntax": ["SOURce:POWer:LMODe?"],
        "write_syntax": [
            "SOURce:POWer:LMODe NORMal",
            "SOURce:POWer:LMODe LNOise",
            "SOURce:POWer:LMODe LDIStortion",
        ],
        "read_response": "Returns: NORMal | LNOise | LDIStortion",
        "write_values": ["NORMal", "LNOise", "LDIStortion"],
        "units": None,
        "constraints": [],
        "notes": [
            "NORMal: automatic best settings selection.",
            "LNOise: optimized for lowest noise.",
            "LDIStortion: optimized for lowest distortion.",
        ],
        "examples": ["SOURce:POWer:LMODe LNOise"],
        "related_commands": ["SOURce:POWer:SCHaracteristic"],
    },
    "SOURce:POWer:SCHaracteristic": {
        "name": "SOURce:POWer:SCHaracteristic",
        "category": "power",
        "description": "Selects the characteristic for the level setting.",
        "read_syntax": ["SOURce:POWer:SCHaracteristic?"],
        "write_syntax": [
            "SOURce:POWer:SCHaracteristic AUTO",
            "SOURce:POWer:SCHaracteristic UNINterrupted",
            "SOURce:POWer:SCHaracteristic CVSWr",
            "SOURce:POWer:SCHaracteristic MONotone",
        ],
        "read_response": "Returns: AUTO | UNINterrupted | CVSWr | USER | MONotone",
        "write_values": ["AUTO", "UNINterrupted", "CVSWr", "USER", "MONotone"],
        "units": None,
        "constraints": ["RST: AUTO"],
        "notes": [],
        "examples": ["SOURce:POWer:SCHaracteristic AUTO"],
        "related_commands": ["SOURce:POWer:LMODe"],
    },

    # -------------------------------------------------------------------------
    # SOURce:SETTings — Apply configuration
    # -------------------------------------------------------------------------

    "SOURce:SETTings:APPLy": {
        "name": "SOURce:SETTings:APPLy",
        "category": "control",
        "description": "Applies the signal settings and enables the output. Required after setting frequency and level when SGU operates as upconverter.",
        "read_syntax": [],
        "write_syntax": ["SOURce:SETTings:APPLy", "SETTings:APPLy"],
        "read_response": None,
        "write_values": None,
        "units": None,
        "constraints": [],
        "notes": [
            "Short form: SETTings:APPLy",
            "Mandatory to make changes take effect in upconverter mode.",
        ],
        "examples": ["SETTings:APPLy", "SOURce:SETTings:APPLy"],
        "related_commands": [
            "SOURce:FREQuency:CW",
            "SOURce:POWer:LEVel:IMMediate:AMPLitude",
            "OUTPut:STATe",
        ],
    },

    # -------------------------------------------------------------------------
    # SOURce:LOSCillator — Local oscillator
    # -------------------------------------------------------------------------

    "SOURce:LOSCillator:FREQuency": {
        "name": "SOURce:LOSCillator:FREQuency",
        "category": "oscillator",
        "description": "Queries the required frequency of the local oscillator input signal.",
        "read_syntax": ["SOURce:LOSCillator:FREQuency?", "LOSCillator:FREQuency?"],
        "write_syntax": [],
        "read_response": "Returns float in Hz. Range: 1 MHz to 20 GHz. RST: 1 GHz.",
        "write_values": None,
        "units": ["Hz"],
        "constraints": [],
        "notes": [
            "Read-only command.",
            "Required when SGU acts as external upconverter.",
            "Short form: LOSCillator:FREQuency?",
        ],
        "examples": ["LOSCillator:FREQuency?"],
        "related_commands": ["SOURce:LOSCillator:POWer", "SOURce:SETTings:APPLy"],
    },
    "SOURce:LOSCillator:POWer": {
        "name": "SOURce:LOSCillator:POWer",
        "category": "oscillator",
        "description": "Queries the required level of the local oscillator input signal.",
        "read_syntax": ["SOURce:LOSCillator:POWer?", "LOSCillator:POWer?"],
        "write_syntax": [],
        "read_response": "Returns float in dBm. Range: -120 to 25 dBm. RST: -10 dBm.",
        "write_values": None,
        "units": ["dBm"],
        "constraints": [],
        "notes": [
            "Read-only command.",
            "Required when SGU acts as external upconverter.",
            "Short form: LOSCillator:POWer?",
        ],
        "examples": ["LOSCillator:POWer?"],
        "related_commands": ["SOURce:LOSCillator:FREQuency", "SOURce:SETTings:APPLy"],
    },

    # -------------------------------------------------------------------------
    # Fast speed commands
    # -------------------------------------------------------------------------

    "FFASt": {
        "name": "FFASt",
        "category": "fast",
        "description": "Sets the RF output frequency with minimum latency. No unit allowed — value in Hz.",
        "read_syntax": [],
        "write_syntax": ["FFASt <value>"],
        "read_response": None,
        "write_values": None,
        "units": None,
        "constraints": [
            "No unit allowed — Hz is implicit.",
            "Bypasses the status system — cannot be combined with *OPC?.",
        ],
        "notes": ["Use only when minimum latency is critical."],
        "examples": ["FFASt 12750000000"],
        "related_commands": ["PFASt", "SOURce:FREQuency:CW"],
    },
    "PFASt": {
        "name": "PFASt",
        "category": "fast",
        "description": "Sets the RF output level with minimum latency. No unit allowed — value in dBm. Does not consider offset.",
        "read_syntax": [],
        "write_syntax": ["PFASt <value>"],
        "read_response": None,
        "write_values": None,
        "units": None,
        "constraints": [
            "No unit allowed — dBm is implicit.",
            "Bypasses the status system — cannot be combined with *OPC?.",
            "Does not consider any configured offset.",
        ],
        "notes": ["Use only when minimum latency is critical."],
        "examples": ["PFASt -10"],
        "related_commands": ["FFASt", "SOURce:POWer:LEVel:IMMediate:AMPLitude"],
    },

    # -------------------------------------------------------------------------
    # SOURce:IQ — I/Q modulation
    # -------------------------------------------------------------------------

    "SOURce:IQ:STATe": {
        "name": "SOURce:IQ:STATe",
        "category": "modulation",
        "description": "Switches I/Q modulation on or off.",
        "read_syntax": ["SOURce:IQ:STATe?"],
        "write_syntax": ["SOURce:IQ:STATe ON", "SOURce:IQ:STATe OFF"],
        "read_response": "Returns: 1 | ON | 0 | OFF",
        "write_values": ["1", "ON", "0", "OFF"],
        "units": None,
        "constraints": ["RST: 0 (OFF)"],
        "notes": ["Only available for R&S SGU-B120V/-B140V options."],
        "examples": ["SOURce:IQ:STATe ON", "SOURce:IQ:STATe OFF"],
        "related_commands": ["SOURce:IQ:IMPairment:STATe"],
    },

    # -------------------------------------------------------------------------
    # SOURce:PULM — Pulse modulation
    # -------------------------------------------------------------------------

    "SOURce:PULM:STATe": {
        "name": "SOURce:PULM:STATe",
        "category": "modulation",
        "description": "Activates or deactivates pulse modulation.",
        "read_syntax": ["SOURce:PULM:STATe?"],
        "write_syntax": ["SOURce:PULM:STATe ON", "SOURce:PULM:STATe OFF"],
        "read_response": "Returns: 0 | 1 | OFF | ON",
        "write_values": ["0", "1", "OFF", "ON"],
        "units": None,
        "constraints": ["RST: 0 (OFF)"],
        "notes": ["Short form: PULM:STAT ON"],
        "examples": ["PULM:STAT ON", "SOURce:PULM:STATe OFF"],
        "related_commands": [],
    },

    # -------------------------------------------------------------------------
    # SYSTem — System
    # -------------------------------------------------------------------------

    "SYSTem:ERRor:ALL": {
        "name": "SYSTem:ERRor:ALL",
        "category": "system",
        "description": "Queries all errors in the error queue.",
        "read_syntax": ["SYSTem:ERRor:ALL?"],
        "write_syntax": [],
        "read_response": "Returns all errors as string.",
        "write_values": None,
        "units": None,
        "constraints": [],
        "notes": ["Read-only command."],
        "examples": ["SYSTem:ERRor:ALL?"],
        "related_commands": ["SYSTem:ERRor:NEXT"],
    },
    "SYSTem:ERRor:NEXT": {
        "name": "SYSTem:ERRor:NEXT",
        "category": "system",
        "description": "Queries the next error in the error queue.",
        "read_syntax": ["SYSTem:ERRor:NEXT?"],
        "write_syntax": [],
        "read_response": "Returns next error as string.",
        "write_values": None,
        "units": None,
        "constraints": [],
        "notes": ["Read-only command."],
        "examples": ["SYSTem:ERRor:NEXT?"],
        "related_commands": ["SYSTem:ERRor:ALL"],
    },
    "SYSTem:COMMunicate:NETWork:IPADdress": {
        "name": "SYSTem:COMMunicate:NETWork:IPADdress",
        "category": "system",
        "description": "Queries the IP address of the instrument.",
        "read_syntax": ["SYSTem:COMMunicate:NETWork:IPADdress?"],
        "write_syntax": [],
        "read_response": "Returns IP address string (x.x.x.x).",
        "write_values": None,
        "units": None,
        "constraints": [],
        "notes": [
            "Read-only command.",
            "Default TCP port for SCPI SOCKET: 5025.",
        ],
        "examples": ["SYSTem:COMMunicate:NETWork:IPADdress?"],
        "related_commands": [],
    },
}


# -------------------------------------------------------------------------
# Helper functions — same interface as command_catalog.py
# -------------------------------------------------------------------------

def get_generator_command_info(command_name: str) -> dict[str, Any] | None:
    """
    Returns the normalized knowledge entry for a generator command name.
    Case-insensitive. Strips trailing '?' if present.
    """
    normalized = command_name.strip().upper().rstrip("?")
    # Direct lookup
    if normalized in GENERATOR_COMMAND_CATALOG:
        return GENERATOR_COMMAND_CATALOG[normalized]
    # Try matching by short alias patterns
    for key, info in GENERATOR_COMMAND_CATALOG.items():
        aliases = info.get("aliases", [])
        if any(normalized == a.strip().upper().rstrip("?") for a in aliases):
            return info
    return None


def generator_command_exists(command_name: str) -> bool:
    return get_generator_command_info(command_name) is not None


def get_generator_commands_by_category(category: str) -> dict[str, dict[str, Any]]:
    normalized = category.strip().lower()
    return {
        k: v for k, v in GENERATOR_COMMAND_CATALOG.items()
        if v.get("category") == normalized
    }


def get_generator_command_context(command_names: list[str]) -> str:
    """
    Builds a compact textual context block for a list of generator command names.
    Same format as get_command_context() in command_catalog.py.
    """
    context_blocks: list[str] = []

    for command_name in command_names:
        info = get_generator_command_info(command_name)
        if not info:
            continue

        lines: list[str] = [
            f"COMMAND: {info['name']}",
            f"CATEGORY: {info['category']}",
            f"DESCRIPTION: {info['description']}",
        ]

        read_syntax = info.get("read_syntax") or []
        if read_syntax:
            lines.append("READ SYNTAX:")
            lines.extend(f"- {item}" for item in read_syntax)

        write_syntax = info.get("write_syntax") or []
        if write_syntax:
            lines.append("WRITE SYNTAX:")
            lines.extend(f"- {item}" for item in write_syntax)

        read_response = info.get("read_response")
        if read_response:
            lines.append(f"READ RESPONSE: {read_response}")

        constraints = info.get("constraints") or []
        if constraints:
            lines.append("CONSTRAINTS:")
            lines.extend(f"- {item}" for item in constraints)

        notes = info.get("notes") or []
        if notes:
            lines.append("NOTES:")
            lines.extend(f"- {item}" for item in notes)

        examples = info.get("examples") or []
        if examples:
            lines.append("EXAMPLES:")
            lines.extend(f"- {item}" for item in examples)

        context_blocks.append("\n".join(lines))

    return "\n\n".join(context_blocks)


# -------------------------------------------------------------------------
# Priority commands for testing (power and frequency)
# -------------------------------------------------------------------------

GENERATOR_PRIORITY_COMMANDS = [
    "SOURce:FREQuency:CW",
    "SOURce:POWer:LEVel:IMMediate:AMPLitude",
    "OUTPut:STATe",
    "SOURce:SETTings:APPLy",
    "*IDN",
    "*RST",
    "LOCK",
    "UNL",
]