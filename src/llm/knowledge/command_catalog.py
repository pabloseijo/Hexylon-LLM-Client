"""
Catálogo de comandos estructurado para la API SCPI de Hexylon.

Este módulo almacena conocimiento por comando en un formato normalizado para que
pueda ser utilizado posteriormente para:
- construcción de prompts consciente de comandos
- explicación de comandos
- selección dinámica de contexto
- capas futuras de recuperación o enrutamiento
"""

from __future__ import annotations

from typing import Any

COMMAND_CATALOG: dict[str, dict[str, Any]] = {
    "FREQ": {
        "name": "FREQ",
        "category": "tuning",
        "description": "Reads or changes the tuned frequency.",
        "read_syntax": ["FREQ?"],
        "write_syntax": ["FREQ xxxx.xx[GHz/MHz/kHz]"],
        "read_response": "Returns the tuned frequency in MHz.",
        "write_values": None,
        "units": ["GHz", "MHz", "kHz"],
        "constraints": [],
        "notes": [
            "Use '?' for read operation.",
            "Write syntax must include a numeric value and a valid frequency unit.",
        ],
        "examples": [
            "FREQ?",
            "FREQ 594.00MHz",
            "FREQ 1.25GHz",
        ],
        "related_commands": ["BAND", "CH"],
    },
    "BAND": {
        "name": "BAND",
        "category": "tuning",
        "description": "Reads or changes the active band of the Hexylon.",
        "read_syntax": ["BAND?"],
        "write_syntax": [
            "BAND TER",
            "BAND SAT",
            "BAND FM",
            "BAND DAB",
        ],
        "read_response": "Returns the current band: TER, SAT, FM or DAB.",
        "write_values": ["TER", "SAT", "FM", "DAB"],
        "units": None,
        "constraints": [
            "BAND TER or BAND SAT may fail in Radio Analyser mode.",
            "BAND FM or BAND DAB may fail in TV Analyser mode.",
        ],
        "notes": [
            "Band changes are mode-dependent.",
        ],
        "examples": [
            "BAND?",
            "BAND TER",
            "BAND SAT",
        ],
        "related_commands": ["FREQ", "MODE", "CH"],
    },
    "CH": {
        "name": "CH",
        "category": "tuning",
        "description": "Reads the tuned channel or tunes to the next, previous or a named channel.",
        "read_syntax": ["CH?"],
        "write_syntax": [
            "CH UP",
            "CH DOWN",
            "CH <Channel_name>",
        ],
        "read_response": "Returns the tuned channel.",
        "write_values": ["UP", "DOWN", "<Channel_name>"],
        "units": None,
        "constraints": [
            "Channel names are case sensitive.",
            "If the channel does not exist in the plan, the device returns an error.",
            "If IPTV is selected, CH <Channel_name> selects a channel from the IPTV list.",
        ],
        "notes": [
            "Use CH UP and CH DOWN to navigate through the channel plan.",
        ],
        "examples": [
            "CH?",
            "CH UP",
            "CH DOWN",
            "CH 38",
        ],
        "related_commands": ["FREQ", "BAND", "SERVICE"],
    },
    "INPUT": {
        "name": "INPUT",
        "category": "input",
        "description": "Gets or sets the active signal input.",
        "read_syntax": ["INPUT?"],
        "write_syntax": [
            "INPUT RF",
            "INPUT FO",
            "INPUT IP",
            "INPUT ASI",
            "INPUT CVBS",
            "INPUT TSP",
            "INPUT ETI",
            "INPUT EDI",
        ],
        "read_response": "Returns the current signal input.",
        "write_values": ["RF", "FO", "IP", "ASI", "CVBS", "TSP", "ETI", "EDI"],
        "units": None,
        "constraints": [],
        "notes": [
            "FO means Fiber Optics.",
            "TSP means TS player.",
        ],
        "examples": [
            "INPUT?",
            "INPUT RF",
            "INPUT IP",
        ],
        "related_commands": ["LAMBDA", "MEAS"],
    },
    "LAMBDA": {
        "name": "LAMBDA",
        "category": "optical",
        "description": "Gets or sets the lambda used for the optical signal.",
        "read_syntax": ["LAMBDA?"],
        "write_syntax": [
            "LAMBDA 1310",
            "LAMBDA 1490",
            "LAMBDA 1550",
        ],
        "read_response": "Returns the current lambda: 1310, 1490 or 1550.",
        "write_values": ["1310", "1490", "1550"],
        "units": ["nm"],
        "constraints": [],
        "notes": [
            "This command applies to optical input contexts.",
        ],
        "examples": [
            "LAMBDA?",
            "LAMBDA 1310",
            "LAMBDA 1550",
        ],
        "related_commands": ["INPUT", "OPT_POW", "OPT_POW_1310", "OPT_POW_1490", "OPT_POW_1550"],
    },
    "MODE": {
        "name": "MODE",
        "category": "ui_mode",
        "description": "Gets or sets the analyser mode and screen index.",
        "read_syntax": ["MODE?"],
        "write_syntax": [
            "MODE TV",
            "MODE TV 1",
            "MODE TV 2",
            "MODE TV 3",
            "MODE TV 4",
            "MODE RADIO",
            "MODE RADIO 1",
            "MODE RADIO 2",
            "MODE RADIO 3",
        ],
        "read_response": "Returns the mode (TV or Radio) and the current screen index.",
        "write_values": [
            "TV",
            "TV 1",
            "TV 2",
            "TV 3",
            "TV 4",
            "RADIO",
            "RADIO 1",
            "RADIO 2",
            "RADIO 3",
        ],
        "units": None,
        "constraints": [
            "Invalid indexes produce an error.",
            "TV mode supports index 4 (Waterfall).",
            "Radio mode supports indexes 1, 2 and 3.",
        ],
        "notes": [
            "If no index is provided, the device uses the last screen used in that mode.",
        ],
        "examples": [
            "MODE?",
            "MODE TV",
            "MODE TV 2",
            "MODE RADIO 3",
        ],
        "related_commands": ["BAND", "WIDGETS", "ECHOES", "RBW", "VBW", "SPAN", "RLEVEL"],
    },
    "PROF": {
        "name": "PROF",
        "category": "profiles",
        "description": "Reads or changes the active user profile.",
        "read_syntax": ["PROF?"],
        "write_syntax": ["PROF <PROFILE_NAME>"],
        "read_response": "Returns the current user profile.",
        "write_values": ["<PROFILE_NAME>"],
        "units": None,
        "constraints": [],
        "notes": [
            "The profile name must exist in the device.",
        ],
        "examples": [
            "PROF?",
            "PROF demo_import",
        ],
        "related_commands": ["LPROF"],
    },
    "LPROF": {
        "name": "LPROF",
        "category": "profiles",
        "description": "Lists the profiles stored in the Hexylon.",
        "read_syntax": ["LPROF?"],
        "write_syntax": [],
        "read_response": "Returns the list of stored profiles.",
        "write_values": None,
        "units": None,
        "constraints": [],
        "notes": [
            "Read-only command.",
        ],
        "examples": [
            "LPROF?",
        ],
        "related_commands": ["PROF"],
    },
    "LOCK": {
        "name": "LOCK",
        "category": "status",
        "description": "Returns whether the signal is locked.",
        "read_syntax": ["LOCK?"],
        "write_syntax": [],
        "read_response": "Returns TRUE if the signal is locked and FALSE otherwise.",
        "write_values": None,
        "units": None,
        "constraints": [],
        "notes": [
            "Read-only command.",
            "Boolean-like response represented as TRUE/FALSE text.",
        ],
        "examples": [
            "LOCK?",
        ],
        "related_commands": ["MEAS", "PAR", "IDN"],
    },
    "IDN": {
        "name": "IDN",
        "category": "device_info",
        "description": "Returns identification and device information.",
        "read_syntax": ["IDN?"],
        "write_syntax": [],
        "read_response": "Returns model, reference, serial number, software version and calibration date.",
        "write_values": None,
        "units": None,
        "constraints": [],
        "notes": [
            "Read-only command.",
        ],
        "examples": [
            "IDN?",
        ],
        "related_commands": ["LOCK"],
    },
    "MEAS": {
        "name": "MEAS",
        "category": "measurements",
        "description": "Returns the real-time measurements currently displayed on screen.",
        "read_syntax": ["MEAS?"],
        "write_syntax": [],
        "read_response": "Returns the measurements currently displayed in the UI.",
        "write_values": None,
        "units": None,
        "constraints": [],
        "notes": [
            "If optical input is enabled, optical power may appear at the end of the result.",
            "Response content depends on what is currently displayed on the device.",
        ],
        "examples": [
            "MEAS?",
        ],
        "related_commands": ["POW", "CN", "MER", "PAR", "LOCK"],
    },
    "PAR": {
        "name": "PAR",
        "category": "measurements",
        "description": "Returns the tuned signal parameters shown in the Parameters widget, when available.",
        "read_syntax": ["PAR?"],
        "write_syntax": [],
        "read_response": "Returns signal parameters such as standard, bandwidth, carriers, guard interval and similar values.",
        "write_values": None,
        "units": None,
        "constraints": [],
        "notes": [
            "The command depends on parameter availability in the current context.",
            "It is associated with the Parameters widget.",
        ],
        "examples": [
            "PAR?",
        ],
        "related_commands": ["MEAS", "MODE", "WIDGETS"],
    },
    "RBW": {
        "name": "RBW",
        "category": "spectrum",
        "description": "Reads or changes the resolution bandwidth.",
        "read_syntax": ["RBW?"],
        "write_syntax": [
            "RBW xxxx.xx[HzW/KHzW/MHzW]",
            "RBW AUTO",
        ],
        "read_response": "Returns the current resolution bandwidth.",
        "write_values": ["<value><unit>", "AUTO"],
        "units": ["HzW", "KHzW", "MHzW"],
        "constraints": [
            "Spectrum analyser must be maximized.",
        ],
        "notes": [
            "Supports automatic mode with RBW AUTO.",
        ],
        "examples": [
            "RBW?",
            "RBW 300HzW",
            "RBW AUTO",
        ],
        "related_commands": ["VBW", "SPAN", "RLEVEL", "ATT", "HOLD", "MODE"],
    },
    "VBW": {
        "name": "VBW",
        "category": "spectrum",
        "description": "Reads or changes the video bandwidth.",
        "read_syntax": ["VBW?"],
        "write_syntax": [
            "VBW xxxx.xx[Hz/KHz/MHz]",
            "VBW AUTO",
        ],
        "read_response": "Returns the current video bandwidth.",
        "write_values": ["<value><unit>", "AUTO"],
        "units": ["Hz", "KHz", "MHz"],
        "constraints": [
            "Spectrum analyser must be maximized.",
        ],
        "notes": [
            "Supports automatic mode with VBW AUTO.",
        ],
        "examples": [
            "VBW?",
            "VBW 10KHz",
            "VBW AUTO",
        ],
        "related_commands": ["RBW", "SPAN", "RLEVEL", "ATT", "HOLD"],
    },
    "SPAN": {
        "name": "SPAN",
        "category": "spectrum",
        "description": "Reads or changes the spectrum span.",
        "read_syntax": ["SPAN?"],
        "write_syntax": [
            "SPAN xxxx.xx[KHz/KHz/MHz]",
        ],
        "read_response": "Returns the current span.",
        "write_values": ["<value><unit>"],
        "units": ["KHz", "MHz"],
        "constraints": [
            "Spectrum analyser must be maximized.",
        ],
        "notes": [
            "The original documentation duplicates KHz in the unit notation.",
        ],
        "examples": [
            "SPAN?",
            "SPAN 20MHz",
        ],
        "related_commands": ["RBW", "VBW", "RLEVEL"],
    },
    "RLEVEL": {
        "name": "RLEVEL",
        "category": "spectrum",
        "description": "Reads or changes the spectrum reference level.",
        "read_syntax": ["RLEVEL?"],
        "write_syntax": [
            "RLEVEL xxxx.xx[dBuV/dBmV/dBm]",
            "RLEVEL AUTO",
        ],
        "read_response": "Returns the current reference level.",
        "write_values": ["<value><unit>", "AUTO"],
        "units": ["dBuV", "dBmV", "dBm"],
        "constraints": [
            "Spectrum analyser must be maximized.",
        ],
        "notes": [
            "Supports automatic mode with RLEVEL AUTO.",
        ],
        "examples": [
            "RLEVEL?",
            "RLEVEL 80dBuV",
            "RLEVEL AUTO",
        ],
        "related_commands": ["RBW", "VBW", "SPAN", "ATT", "HOLD"],
    },
    "SERVICES": {
        "name": "SERVICES",
        "category": "services",
        "description": "Returns the list of TS service SIDs.",
        "read_syntax": ["SERVICES?"],
        "write_syntax": [],
        "read_response": "Returns the list of service SIDs in the transport stream.",
        "write_values": None,
        "units": None,
        "constraints": [],
        "notes": [
            "Read-only command.",
        ],
        "examples": [
            "SERVICES?",
        ],
        "related_commands": ["SERVICE"],
    },
    "SERVICE": {
        "name": "SERVICE",
        "category": "services",
        "description": "Selects a TS service by SID.",
        "read_syntax": [],
        "write_syntax": ["SERVICE <SID>"],
        "read_response": None,
        "write_values": ["<SID>"],
        "units": None,
        "constraints": [],
        "notes": [
            "Write-only command in the documented API.",
        ],
        "examples": [
            "SERVICE 2371",
        ],
        "related_commands": ["SERVICES"],
    },
    "IMAG": {
        "name": "IMAG",
        "category": "utility",
        "description": "Takes a screenshot of the meter and returns a download URL.",
        "read_syntax": [],
        "write_syntax": ["IMAG"],
        "read_response": "Returns a URL to download the generated screenshot.",
        "write_values": None,
        "units": None,
        "constraints": [],
        "notes": [
            "wget requires --no-check-certificate.",
            "curl requires --insecure."
        ],
        "examples": ["IMAG"],
        "related_commands": [],
    },
    "LCHIPTV": {
        "name": "LCHIPTV",
        "category": "iptv",
        "description": "Returns the list of IPTV channels.",
        "read_syntax": ["LCHIPTV"],
        "write_syntax": [],
        "read_response": "Returns the IPTV channel list.",
        "write_values": None,
        "units": None,
        "constraints": [],
        "notes": ["Read-only command."],
        "examples": ["LCHIPTV"],
        "related_commands": ["ADDCHIPTV", "DELCHIPTV", "CH"],
    },
    "ADDCHIPTV": {
        "name": "ADDCHIPTV",
        "category": "iptv",
        "description": "Adds a new IPTV channel to the IPTV channel list.",
        "read_syntax": [],
        "write_syntax": ["ADDCHIPTV [channel name] [IP] [IP origin] [port]"],
        "read_response": None,
        "write_values": ["channel name", "IP", "IP origin", "port"],
        "units": None,
        "constraints": [],
        "notes": [],
        "examples": ["ADDCHIPTV MyChannel 239.0.0.1 0.0.0.0 1234"],
        "related_commands": ["LCHIPTV", "DELCHIPTV"],
    },
    "DELCHIPTV": {
        "name": "DELCHIPTV",
        "category": "iptv",
        "description": "Deletes an IPTV channel from the IPTV channel list.",
        "read_syntax": [],
        "write_syntax": ["DELCHIPTV [channel name]"],
        "read_response": None,
        "write_values": ["channel name"],
        "units": None,
        "constraints": [],
        "notes": [],
        "examples": ["DELCHIPTV MyChannel"],
        "related_commands": ["LCHIPTV", "ADDCHIPTV"],
    },
    "WIDGETS": {
        "name": "WIDGETS",
        "category": "ui_mode",
        "description": "Reads or configures the active analyser widgets layout.",
        "read_syntax": ["WIDGETS?"],
        "write_syntax": ["WIDGETS Widget_Name1 Widget_Name2 ..."],
        "read_response": "Returns the names of the active widgets.",
        "write_values": ["1, 4 or 6 widget names"],
        "units": None,
        "constraints": [
            "Only 1, 4 or 6 widget names are valid.",
            "Invalid widget count returns an error."
        ],
        "notes": [
            "1 widget = single-widget mode.",
            "4 widgets = Mosaic 3+1.",
            "6 widgets = Mosaic 6."
        ],
        "examples": [
            "WIDGETS?",
            "WIDGETS SPC MER PAR MEA"
        ],
        "related_commands": ["MODE", "PAR", "ECHOES"],
    },
    "POW": {
        "name": "POW",
        "category": "measurements",
        "description": "Returns the power measurement.",
        "read_syntax": ["POW?"],
        "write_syntax": [],
        "read_response": "Returns power with the currently selected units.",
        "write_values": None,
        "units": ["dBuV", "dBmV", "dBm"],
        "constraints": [],
        "notes": ["Read-only command."],
        "examples": ["POW?"],
        "related_commands": ["MEAS"],
    },
    "CN": {
        "name": "CN",
        "category": "measurements",
        "description": "Returns the C/N measurement in dB.",
        "read_syntax": ["CN?"],
        "write_syntax": [],
        "read_response": "Returns C/N in dB.",
        "write_values": None,
        "units": ["dB"],
        "constraints": [],
        "notes": ["Read-only command."],
        "examples": ["CN?"],
        "related_commands": ["MER", "POW"],
    },
    "VA": {
        "name": "VA",
        "category": "measurements",
        "description": "Returns the V/A measurement when available.",
        "read_syntax": ["VA?"],
        "write_syntax": [],
        "read_response": "Returns V/A in dB.",
        "write_values": None,
        "units": ["dB"],
        "constraints": [],
        "notes": ["May be unavailable depending on context."],
        "examples": ["VA?"],
        "related_commands": ["CN", "MER"],
    },
    "MER": {
        "name": "MER",
        "category": "measurements",
        "description": "Returns the MER measurement.",
        "read_syntax": ["MER?"],
        "write_syntax": [],
        "read_response": "Returns MER in dB.",
        "write_values": None,
        "units": ["dB"],
        "constraints": [],
        "notes": [],
        "examples": ["MER?"],
        "related_commands": ["CN", "CBER", "VBER"],
    },
    "CBER": {
        "name": "CBER",
        "category": "measurements",
        "description": "Returns BER before the first error corrector.",
        "read_syntax": ["CBER?"],
        "write_syntax": [],
        "read_response": "Returns BER in scientific notation.",
        "write_values": None,
        "units": None,
        "constraints": [],
        "notes": [],
        "examples": ["CBER?"],
        "related_commands": ["VBER", "BCHBER"],
    },
    "VBER": {
        "name": "VBER",
        "category": "measurements",
        "description": "Returns BER before Reed-Solomon correction.",
        "read_syntax": ["VBER?"],
        "write_syntax": [],
        "read_response": "Returns BER or NVAL.",
        "write_values": None,
        "units": None,
        "constraints": [],
        "notes": ["May return NVAL when unavailable."],
        "examples": ["VBER?"],
        "related_commands": ["CBER", "BCHBER"],
    },
    "BCHBER": {
        "name": "BCHBER",
        "category": "measurements",
        "description": "Returns BER before BCH correction.",
        "read_syntax": ["BCHBER?"],
        "write_syntax": [],
        "read_response": "Returns BER or NVAL.",
        "write_values": None,
        "units": None,
        "constraints": [],
        "notes": ["May return NVAL when unavailable."],
        "examples": ["BCHBER?"],
        "related_commands": ["VBER", "CBER"],
    },
    "ECHOES": {
        "name": "ECHOES",
        "category": "measurements",
        "description": "Returns the list of echoes detected by the meter.",
        "read_syntax": ["ECHOES?"],
        "write_syntax": [],
        "read_response": "Returns echoes with delay and level.",
        "write_values": None,
        "units": ["µs", "dB"],
        "constraints": [
            "Echoes or PDP widget must be active."
        ],
        "notes": [],
        "examples": ["ECHOES?"],
        "related_commands": ["WIDGETS", "MODE"],
    },
    "OPT_POW": {
        "name": "OPT_POW",
        "category": "optical",
        "description": "Returns current optical power.",
        "read_syntax": ["OPT_POW?"],
        "write_syntax": [],
        "read_response": "Returns optical power measurement.",
        "write_values": None,
        "units": None,
        "constraints": [],
        "notes": [],
        "examples": ["OPT_POW?"],
        "related_commands": ["OPT_POW_1310", "OPT_POW_1490", "OPT_POW_1550"],
    },
    "OPT_POW_1310": {
        "name": "OPT_POW_1310",
        "category": "optical",
        "description": "Returns optical power at 1310 nm.",
        "read_syntax": ["OPT_POW_1310?"],
        "write_syntax": [],
        "read_response": "Returns optical power at 1310 nm.",
        "write_values": None,
        "units": None,
        "constraints": [],
        "notes": [],
        "examples": ["OPT_POW_1310?"],
        "related_commands": ["OPT_POW"],
    },
    "OPT_POW_1490": {
        "name": "OPT_POW_1490",
        "category": "optical",
        "description": "Returns optical power at 1490 nm.",
        "read_syntax": ["OPT_POW_1490?"],
        "write_syntax": [],
        "read_response": "Returns optical power at 1490 nm.",
        "write_values": None,
        "units": None,
        "constraints": [],
        "notes": [],
        "examples": ["OPT_POW_1490?"],
        "related_commands": ["OPT_POW"],
    },
    "OPT_POW_1550": {
        "name": "OPT_POW_1550",
        "category": "optical",
        "description": "Returns optical power at 1550 nm.",
        "read_syntax": ["OPT_POW_1550?"],
        "write_syntax": [],
        "read_response": "Returns optical power at 1550 nm.",
        "write_values": None,
        "units": None,
        "constraints": [],
        "notes": [],
        "examples": ["OPT_POW_1550?"],
        "related_commands": ["OPT_POW"],
    },
    "ATT": {
        "name": "ATT",
        "category": "spectrum",
        "description": "Restarts control attenuation.",
        "read_syntax": [],
        "write_syntax": ["ATT"],
        "read_response": None,
        "write_values": None,
        "units": None,
        "constraints": [
            "Spectrum analyser must be maximized."
        ],
        "notes": [],
        "examples": ["ATT"],
        "related_commands": ["RBW", "VBW", "SPAN", "RLEVEL", "HOLD"],
    },
    "HOLD": {
        "name": "HOLD",
        "category": "spectrum",
        "description": "Changes the spectrum hold mode.",
        "read_syntax": [],
        "write_syntax": [
            "HOLD MAX ON",
            "HOLD MAX OFF",
            "HOLD MIN ON",
            "HOLD MIN OFF",
            "HOLD CLEAR",
        ],
        "read_response": None,
        "write_values": ["MAX ON", "MAX OFF", "MIN ON", "MIN OFF", "CLEAR"],
        "units": None,
        "constraints": [
            "Spectrum analyser must be maximized."
        ],
        "notes": [],
        "examples": [
            "HOLD MAX ON",
            "HOLD CLEAR",
        ],
        "related_commands": ["ATT", "RBW", "VBW", "SPAN", "RLEVEL"],
    },
    "FSTR": {
        "name": "FSTR",
        "category": "utility",
        "description": "Reads or changes field strength measurement state.",
        "read_syntax": ["FSTR?"],
        "write_syntax": ["FSTR ON", "FSTR OFF"],
        "read_response": "Returns ON or OFF.",
        "write_values": ["ON", "OFF"],
        "units": None,
        "constraints": [],
        "notes": [],
        "examples": ["FSTR?", "FSTR ON"],
        "related_commands": ["ANT"],
    },
    "ANT": {
        "name": "ANT",
        "category": "utility",
        "description": "Reads or changes the antenna used for field strength measurement.",
        "read_syntax": ["ANT?"],
        "write_syntax": ["ANT <ANTENNA_NAME>"],
        "read_response": "Returns current antenna name.",
        "write_values": ["<ANTENNA_NAME>"],
        "units": None,
        "constraints": [],
        "notes": [],
        "examples": ["ANT?", "ANT MyAntenna"],
        "related_commands": ["FSTR"],
    },
    "EXTAMP": {
        "name": "EXTAMP",
        "category": "utility",
        "description": "Reads or changes external attenuator/amplifier compensation.",
        "read_syntax": ["EXTAMP?"],
        "write_syntax": ["EXTAMP <±value>"],
        "read_response": "Returns compensation value.",
        "write_values": ["<±value>"],
        "units": None,
        "constraints": [],
        "notes": [],
        "examples": ["EXTAMP?", "EXTAMP +10"],
        "related_commands": [],
    },
    "VDC": {
        "name": "VDC",
        "category": "utility",
        "description": "Reads or changes RF output voltage.",
        "read_syntax": ["VDC?"],
        "write_syntax": [
            "VDC <xV(+22KHz)>",
            "VDC OFF",
            "VDC AUTO",
        ],
        "read_response": "Returns current RF output voltage configuration.",
        "write_values": ["<xV(+22KHz)>", "OFF", "AUTO"],
        "units": ["V"],
        "constraints": [],
        "notes": [],
        "examples": ["VDC?", "VDC 13V", "VDC AUTO"],
        "related_commands": [],
    },
    "LKM": {
        "name": "LKM",
        "category": "measurements",
        "description": "Returns the Link Margin measurement when available.",
        "read_syntax": ["LKM?"],
        "write_syntax": [],
        "read_response": "Returns Link Margin measurement.",
        "write_values": None,
        "units": None,
        "constraints": [],
        "notes": ["May be unavailable depending on context."],
        "examples": ["LKM?"],
        "related_commands": ["MEAS", "MER", "CN"],
    },
    "PER": {
        "name": "PER",
        "category": "measurements",
        "description": "Returns the Packet Error Rate when available.",
        "read_syntax": ["PER?"],
        "write_syntax": [],
        "read_response": "Returns PER measurement.",
        "write_values": None,
        "units": None,
        "constraints": [],
        "notes": ["May be unavailable depending on context."],
        "examples": ["PER?"],
        "related_commands": ["SER", "CBER", "VBER"],
    },
    "SER": {
        "name": "SER",
        "category": "measurements",
        "description": "Returns the Symbol Error Rate when available.",
        "read_syntax": ["SER?"],
        "write_syntax": [],
        "read_response": "Returns SER measurement.",
        "write_values": None,
        "units": None,
        "constraints": [],
        "notes": ["May be unavailable depending on context."],
        "examples": ["SER?"],
        "related_commands": ["PER", "CBER", "VBER"],
    },
    "HUM": {
        "name": "HUM",
        "category": "measurements",
        "description": "Returns the HUM measurement in percent when available.",
        "read_syntax": ["HUM?"],
        "write_syntax": [],
        "read_response": "Returns HUM percentage.",
        "write_values": None,
        "units": ["%"],
        "constraints": [],
        "notes": ["May be unavailable depending on context."],
        "examples": ["HUM?"],
        "related_commands": ["MEAS"],
    },
    "CSO": {
        "name": "CSO",
        "category": "measurements",
        "description": "Returns the CSO measurement in dB when available.",
        "read_syntax": ["CSO?"],
        "write_syntax": [],
        "read_response": "Returns CSO in dB.",
        "write_values": None,
        "units": ["dB"],
        "constraints": [],
        "notes": ["May be unavailable depending on context."],
        "examples": ["CSO?"],
        "related_commands": ["MEAS"],
    },
    "PREBER": {
        "name": "PREBER",
        "category": "measurements",
        "description": "Returns the PreBER measurement when available.",
        "read_syntax": ["PREBER?"],
        "write_syntax": [],
        "read_response": "Returns PreBER measurement.",
        "write_values": None,
        "units": None,
        "constraints": [],
        "notes": ["May be unavailable depending on context."],
        "examples": ["PREBER?"],
        "related_commands": ["POSTBER", "CBER", "VBER"],
    },
    "POSTBER": {
        "name": "POSTBER",
        "category": "measurements",
        "description": "Returns the PostBER measurement when available.",
        "read_syntax": ["POSTBER?"],
        "write_syntax": [],
        "read_response": "Returns PostBER measurement.",
        "write_values": None,
        "units": None,
        "constraints": [],
        "notes": ["May be unavailable depending on context."],
        "examples": ["POSTBER?"],
        "related_commands": ["PREBER"],
    },
    "PRELDPCBER": {
        "name": "PRELDPCBER",
        "category": "measurements",
        "description": "Returns BER before LDPC correction when available.",
        "read_syntax": ["PRELDPCBER?"],
        "write_syntax": [],
        "read_response": "Returns PreLDPCBER measurement.",
        "write_values": None,
        "units": None,
        "constraints": [],
        "notes": ["May be unavailable depending on context."],
        "examples": ["PRELDPCBER?"],
        "related_commands": ["PREBCHBER", "CBER", "VBER"],
    },
    "PREBCHBER": {
        "name": "PREBCHBER",
        "category": "measurements",
        "description": "Returns BER before BCH correction when available.",
        "read_syntax": ["PREBCHBER?"],
        "write_syntax": [],
        "read_response": "Returns PreBCHBER measurement.",
        "write_values": None,
        "units": None,
        "constraints": [],
        "notes": ["May be unavailable depending on context."],
        "examples": ["PREBCHBER?"],
        "related_commands": ["PRELDPCBER", "BCHBER"],
    },
    "MSCBER": {
        "name": "MSCBER",
        "category": "measurements",
        "description": "Returns MSCBER when available.",
        "read_syntax": ["MSCBER?"],
        "write_syntax": [],
        "read_response": "Returns MSCBER measurement.",
        "write_values": None,
        "units": None,
        "constraints": [],
        "notes": ["May be unavailable depending on context."],
        "examples": ["MSCBER?"],
        "related_commands": ["FICBER"],
    },
    "FICBER": {
        "name": "FICBER",
        "category": "measurements",
        "description": "Returns FICBER when available.",
        "read_syntax": ["FICBER?"],
        "write_syntax": [],
        "read_response": "Returns FICBER measurement.",
        "write_values": None,
        "units": None,
        "constraints": [],
        "notes": ["May be unavailable depending on context."],
        "examples": ["FICBER?"],
        "related_commands": ["MSCBER"],
    },
    "CBERA": {
        "name": "CBERA",
        "category": "measurements",
        "description": "Returns CBER for layer A when available.",
        "read_syntax": ["CBERA?"],
        "write_syntax": [],
        "read_response": "Returns CBERA measurement.",
        "write_values": None,
        "units": None,
        "constraints": [],
        "notes": ["May be unavailable depending on context."],
        "examples": ["CBERA?"],
        "related_commands": ["VBERA"],
    },
    "VBERA": {
        "name": "VBERA",
        "category": "measurements",
        "description": "Returns VBER for layer A when available.",
        "read_syntax": ["VBERA?"],
        "write_syntax": [],
        "read_response": "Returns VBERA measurement.",
        "write_values": None,
        "units": None,
        "constraints": [],
        "notes": ["May be unavailable depending on context."],
        "examples": ["VBERA?"],
        "related_commands": ["CBERA"],
    },
    "CBERB": {
        "name": "CBERB",
        "category": "measurements",
        "description": "Returns CBER for layer B when available.",
        "read_syntax": ["CBERB?"],
        "write_syntax": [],
        "read_response": "Returns CBERB measurement.",
        "write_values": None,
        "units": None,
        "constraints": [],
        "notes": ["May be unavailable depending on context."],
        "examples": ["CBERB?"],
        "related_commands": ["VBERB"],
    },
    "VBERB": {
        "name": "VBERB",
        "category": "measurements",
        "description": "Returns VBER for layer B when available.",
        "read_syntax": ["VBERB?"],
        "write_syntax": [],
        "read_response": "Returns VBERB measurement.",
        "write_values": None,
        "units": None,
        "constraints": [],
        "notes": ["May be unavailable depending on context."],
        "examples": ["VBERB?"],
        "related_commands": ["CBERB"],
    },
    "CBERC": {
        "name": "CBERC",
        "category": "measurements",
        "description": "Returns CBER for layer C when available.",
        "read_syntax": ["CBERC?"],
        "write_syntax": [],
        "read_response": "Returns CBERC measurement.",
        "write_values": None,
        "units": None,
        "constraints": [],
        "notes": ["May be unavailable depending on context."],
        "examples": ["CBERC?"],
        "related_commands": ["VBERC"],
    },
    "VBERC": {
        "name": "VBERC",
        "category": "measurements",
        "description": "Returns VBER for layer C when available.",
        "read_syntax": ["VBERC?"],
        "write_syntax": [],
        "read_response": "Returns VBERC measurement.",
        "write_values": None,
        "units": None,
        "constraints": [],
        "notes": ["May be unavailable depending on context."],
        "examples": ["VBERC?"],
        "related_commands": ["CBERC"],
    },
    "CNBOOT": {
        "name": "CNBOOT",
        "category": "measurements",
        "description": "Returns bootstrap C/N measurement when available.",
        "read_syntax": ["CNBOOT?"],
        "write_syntax": [],
        "read_response": "Returns bootstrap C/N measurement.",
        "write_values": None,
        "units": ["dB"],
        "constraints": [],
        "notes": ["May be unavailable depending on context."],
        "examples": ["CNBOOT?"],
        "related_commands": ["CN", "MER"],
    },
}


def get_command_info(command_name: str) -> dict[str, Any] | None:
    """
    Devuelve la entrada de conocimiento normalizada para un nombre de comando.

    La búsqueda no es sensible a mayúsculas e ignora un '?' final si está presente.
    """
    normalized = command_name.strip().upper().rstrip("?")
    return COMMAND_CATALOG.get(normalized)


def command_exists(command_name: str) -> bool:
    """
    Devuelve True si el comando existe en el catálogo.
    """
    return get_command_info(command_name) is not None


def get_commands_by_category(category: str) -> dict[str, dict[str, Any]]:
    """
    Devuelve todos los comandos pertenecientes a una categoría dada.
    """
    normalized = category.strip().lower()
    return {
        command_name: command_info
        for command_name, command_info in COMMAND_CATALOG.items()
        if command_info.get("category") == normalized
    }


def get_command_context(command_names: list[str]) -> str:
    """
    Construye un bloque de contexto textual compacto para una lista de nombres de comandos.

    Este auxiliar es útil para inyección de prompts cuando solo un pequeño subconjunto de comandos es relevante para la solicitud actual del usuario.
    """
    context_blocks: list[str] = []

    for command_name in command_names:
        command_info = get_command_info(command_name)
        if not command_info:
            continue

        lines: list[str] = [
            f"COMMAND: {command_info['name']}",
            f"CATEGORY: {command_info['category']}",
            f"DESCRIPTION: {command_info['description']}",
        ]

        read_syntax = command_info.get("read_syntax") or []
        if read_syntax:
            lines.append("READ SYNTAX:")
            lines.extend(f"- {item}" for item in read_syntax)

        write_syntax = command_info.get("write_syntax") or []
        if write_syntax:
            lines.append("WRITE SYNTAX:")
            lines.extend(f"- {item}" for item in write_syntax)

        read_response = command_info.get("read_response")
        if read_response:
            lines.append(f"READ RESPONSE: {read_response}")

        constraints = command_info.get("constraints") or []
        if constraints:
            lines.append("CONSTRAINTS:")
            lines.extend(f"- {item}" for item in constraints)

        notes = command_info.get("notes") or []
        if notes:
            lines.append("NOTES:")
            lines.extend(f"- {item}" for item in notes)

        examples = command_info.get("examples") or []
        if examples:
            lines.append("EXAMPLES:")
            lines.extend(f"- {item}" for item in examples)

        context_blocks.append("\n".join(lines))

    return "\n\n".join(context_blocks)