"""
Canonical compact SCPI reference for Hexylon.
Designed for NL -> SCPI generation prompts.
This module contains a concise, high-signal reference optimized for
command generation, not for full documentation storage.
"""

API_REFERENCE = """
HEXYLON SCPI CANONICAL REFERENCE

DEVICE
- Hexylon RF meter
- Advanced API over SCPI
- Transport: TCP
- Port: 5025

GENERAL RULES
- Use only documented SCPI commands.
- Do not invent aliases, synonyms or unofficial commands.
- Read operations use the exact command ending in '?'.
- Write operations must follow the documented syntax exactly.
- Output exactly one SCPI command.
- Do not output explanations, JSON, markdown or extra text.
- Commands must be terminated by Enter or end of line.

HIGH-PRIORITY COMMANDS

1. FREQUENCY
- Read: FREQ?
- Write: FREQ xxxx.xx[GHz/MHz/kHz]
- Meaning: read or change tuned frequency
- Read response: tuned frequency in MHz

2. BAND
- Read: BAND?
- Write: BAND TER
- Write: BAND SAT
- Write: BAND FM
- Write: BAND DAB
- Meaning: read or change active band
- Constraints:
  - BAND TER or BAND SAT may fail in Radio Analyser mode
  - BAND FM or BAND DAB may fail in TV Analyser mode

3. CHANNEL
- Read: CH?
- Write: CH UP
- Write: CH DOWN
- Write: CH <Channel_name>
- Meaning: read tuned channel or move/select a channel
- Constraints:
  - Channel names are case sensitive
  - If the channel does not exist in the plan, the device returns an error

4. INPUT
- Read: INPUT?
- Write: INPUT RF
- Write: INPUT FO
- Write: INPUT IP
- Write: INPUT ASI
- Write: INPUT CVBS
- Write: INPUT TSP
- Write: INPUT ETI
- Write: INPUT EDI
- Meaning: get or set active signal input

5. OPTICAL LAMBDA
- Read: LAMBDA?
- Write: LAMBDA 1310
- Write: LAMBDA 1490
- Write: LAMBDA 1550
- Meaning: get or set optical wavelength

6. MODE
- Read: MODE?
- Write: MODE TV
- Write: MODE TV 1
- Write: MODE TV 2
- Write: MODE TV 3
- Write: MODE TV 4
- Write: MODE RADIO
- Write: MODE RADIO 1
- Write: MODE RADIO 2
- Write: MODE RADIO 3
- Meaning: get or set analyser mode and screen index
- Constraints:
  - Invalid indexes produce an error
  - TV mode supports index 4 (Waterfall)
  - Radio mode supports indexes 1, 2 and 3

7. PROFILES
- Read: LPROF?
- Read: PROF?
- Write: PROF <PROFILE_NAME>
- Meaning: list profiles, read current profile or change profile

8. LOCK STATUS
- Read only: LOCK?
- Meaning: returns TRUE if locked, FALSE otherwise

9. DEVICE INFORMATION
- Read only: IDN?
- Meaning: returns model, reference, serial number, software version and calibration date

10. SCREENSHOT
- Command: IMAG
- Meaning: returns a URL to download a screenshot
- Notes:
  - wget requires --no-check-certificate
  - curl requires --insecure

MEASUREMENT COMMANDS (READ ONLY)
- MEAS?
- POW?
- CN?
- VA?
- MER?
- CBER?
- VBER?
- BCHBER?
- LKM?
- PER?
- SER?
- HUM?
- CSO?
- PREBER?
- POSTBER?
- PRELDPCBER?
- PREBCHBER?
- MSCBER?
- FICBER?
- CBERA?
- VBERA?
- CBERB?
- VBERB?
- CBERC?
- VBERC?
- CNBOOT?
- ECHOES?
- OPT_POW?
- OPT_POW_1310?
- OPT_POW_1490?
- OPT_POW_1550?
- PAR?

MEASUREMENT NOTES
- MEAS? returns the measurements currently displayed on screen
- VBER? may return NVAL when the value is unavailable
- BCHBER? may return NVAL when the value is unavailable
- ECHOES? requires Echoes or PDP widget to be active
- PAR? returns signal parameters shown in the Parameters widget when available

SERVICE COMMANDS
- Read: SERVICES?
- Write: SERVICE <SID>
- Meaning: list service SIDs or select a TS service by SID

OTHER SUPPORTED COMMANDS
- FSTR?
- FSTR ON
- FSTR OFF
- ANT?
- ANT <ANTENNA_NAME>
- EXTAMP?
- EXTAMP <value>
- VDC?
- VDC <xV(+22KHz)>
- VDC OFF
- VDC AUTO

GENERATION POLICY
- Prefer the simplest valid documented command.
- If the user asks to read a value, prefer the read form with '?'.
- If the user asks to set or change a value, prefer the exact documented write form.
- Never output more than one command.
- Never explain the command.
- Never invent undocumented commands.
"""