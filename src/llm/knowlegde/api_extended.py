"""
Extended Hexylon SCPI reference.
Designed as a secondary or fallback documentation source.
Contains broad API coverage, including detailed command syntax,
constraints, upload formats and operational notes.
"""

API_EXTENDED = """
HEXYLON SCPI EXTENDED REFERENCE

GENERAL
- Device: Hexylon
- API type: Advanced API
- Protocol: SCPI
- Transport: TCP
- Port: 5025
- All commands must be followed by Enter or end of line.

1. FREQUENCY
Command: FREQ
- Read: FREQ?
- Write: FREQ xxxx.xx[GHz/MHz/kHz]
- Description: reads or changes the tuned frequency
- Read response: tuned frequency in MHz

2. BAND
Command: BAND
- Read: BAND?
- Write: BAND TER
- Write: BAND SAT
- Write: BAND FM
- Write: BAND DAB
- Description: reads or changes the active band
- Read response: TER / SAT / FM / DAB
- Constraints:
  - BAND TER or BAND SAT in Radio Analyser mode returns an error
  - BAND FM or BAND DAB in TV Analyser mode returns an error

3. CHANNEL
Command: CH
- Read: CH?
- Write: CH UP
- Write: CH DOWN
- Write: CH <Channel_name>
- Description: reads the tuned channel, moves to next/previous channel, or tunes by channel name
- Notes:
  - If IPTV is selected, CH <Channel_name> selects the channel with that name from the IPTV list
  - Channel names are case sensitive
  - If the channel is not found in the channel plan, an error is returned

4. IPTV CHANNEL LIST MANAGEMENT
- Read: LCHIPTV
  - Returns the list of IPTV channels
- Write: ADDCHIPTV [channel name] [IP] [IP origin] [port]
  - Adds a new IPTV channel
- Write: DELCHIPTV [channel name]
  - Deletes an IPTV channel from the list

5. SCREENSHOT
Command: IMAG
- Description: takes a screenshot of the meter
- Response: URL to download the image
- Notes:
  - wget requires --no-check-certificate
  - curl requires --insecure

6. INPUT SELECTION
Command: INPUT
- Read: INPUT?
- Write: INPUT RF
- Write: INPUT FO
- Write: INPUT IP
- Write: INPUT ASI
- Write: INPUT CVBS
- Write: INPUT TSP
- Write: INPUT ETI
- Write: INPUT EDI
- Description: gets or sets the Hexylon signal input
- Read response values:
  - RF
  - Fiber Optics
  - IP
  - ASI
  - CVBS
  - TS player
  - ETI player
  - EDI

7. OPTICAL LAMBDA
Command: LAMBDA
- Read: LAMBDA?
- Write: LAMBDA 1310
- Write: LAMBDA 1490
- Write: LAMBDA 1550
- Description: gets or sets the optical lambda
- Read response: 1310 / 1490 / 1550

8. ANALYSER MODE
Command: MODE
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
- Description: gets or sets analyser mode and screen index

Available screens:
- TV mode:
  - 1: Scan
  - 2: Mosaic 3+1
  - 3: Mosaic 6
  - 4: Waterfall
- Radio mode:
  - 1: Scan
  - 2: Mosaic 3+1
  - 3: Mosaic 6

Notes:
- If no index is added, the device returns to the last used screen in that mode
- Sending an invalid index causes an error
- Documentation states index > 3 causes an error, but TV mode explicitly supports index 4

9. WIDGET CONFIGURATION
Command: WIDGETS
- Read: WIDGETS?
  - Returns widget names shown in analyser mode
  - 1 name: single-widget mode
  - 4 names: Mosaic 3+1 mode
  - 6 names: Mosaic 6 mode

- Write: WIDGETS Widget_Name1 Widget_Name2 ...
  - Sets the number of widgets and the function shown in each one
  - Order is left to right and top to bottom

Valid widget counts:
- 1
- 4
- 6

Invalid widget counts produce an error.

TV analyser widget names:
- TV
- SER
- PAR
- MEA
- SPC
- CON
- ECH
- MER
- UNC
- ADV
- TAB
- ALR
- SFN
- EPG
- TLT
- GPS
- PCR
- BOOT

Radio analyser widget names:
- RI
- PAR
- SER
- MEA
- SPC
- FMD
- ECH
- CON
- MER
- EFIB
- SSH
- ACRC
- MPX
- SFN
- PRS
- GPS

Widget layout notes:
- There are three possible analyser layouts:
  1. Single widget fullscreen
  2. Mosaic 3+1
  3. Mosaic 6
- In Mosaic 3+1, bottom large widget restrictions apply:
  - TV analyser: Spectrum, Echoes, MER(Carrier)
  - Radio analyser: Spectrum, MER(Carrier), MPX Spectrum

10. PLAN UPLOAD
Upload method:
- POST to: https://<ip>/upload/plan
- Example:
  curl -k --request POST --url https://<ip>/upload/plan --form plan=@<file_plan.csv>

Supported format:
- CSV only
- Comma delimited

Terrestrial / FM / DAB plan file format:
- First line: plan name
- Second line: Name,Freq(KHz),Bw(KHz)
- Next lines: Channel Name, Frequency in KHz, BandWidth in KHz

Example:
PLAN_NAME
Name,Freq(KHz),Bw(KHz)
E02,50500,7000
E03,57500,7000
E04,64500,7000
S01,107500,7000

Satellite plan file format:
- First line: profile name or plan name as documented
- Second line: Name,Polarity,Freq(KHz),Bw(KHz)
- Next lines: Channel Name, Polarity, Real Frequency in KHz, BandWidth in KHz

Valid polarity values:
- V
- H
- L
- C

Example:
PROFILE_NAME
Name,Polarity,Freq(KHz),Bw(KHz)
HB1A,H,10960000,10125
HB1B,H,10978000,10125
HB1C,H,10987000,10125
HB1D,H,10999000,4455
HB1E,H,11012000,4320

11. PROFILE UPLOAD
Upload method:
- POST to: https://<ip>/upload/profile
- Example:
  curl -k --request POST --url https://<ip>/upload/profile --form profile=@<file_profile.csv>

Supported format:
- CSV only
- Comma delimited

Profile file format:
- First line: profile name
- Second line: type,name,vcc,norm,pol,diseqc
- Next lines: one line per plan

Rules:
- One terrestrial plan or one satellite plan is mandatory
- FM and DAB plans are optional
- Up to 4 satellite plans are allowed
- If multiple satellites are used, DiseqC is mandatory

Valid parameters:
- type:
  - ter
  - sat
  - fm
  - dab

- name:
  - channel plan name
  - must already exist in Hexylon

- vcc:
  - Terrestrial / FM / DAB:
    - OFF
    - 5V
    - 13V
    - 18V
    - 24V
  - Satellite:
    - OFF
    - AUTO
    - 13V
    - 18V
    - 13+22KHz
    - 18+22+KHz

- norm:
  - B/G
  - D/K
  - I
  - L
  - NTSC
  - only for terrestrial

- pol:
  - ALL
  - VL
  - HL
  - VH
  - HH
  - only for satellite

- diseqc:
  - OFF
  - A
  - B
  - C
  - D
  - only for satellite

Example:
demo_import
type,name,vcc,norm,pol,diseq
ter,CCIR,OFF,B/G,,
sat,ASTRA19,AUTO,,ALL,A
sat,HOTBIRD13,AUTO,,ALL,B
dab,DAB+
fm,FM

12. PROFILE COMMANDS
- Read: LPROF?
  - Lists the profiles stored in Hexylon
- Read: PROF?
  - Reads the current user profile
- Write: PROF <PROFILE_NAME>
  - Changes the user profile

13. LOCK STATUS
- Read only: LOCK?
- Returns TRUE if the signal is locked
- Returns FALSE if the signal is not locked

14. MEASUREMENTS AND PARAMETERS
The following commands are read only unless explicitly stated otherwise.

Main displayed measurements:
- MEAS?
  - Returns the measurements displayed on screen
  - Example:
    POW 84.1 dBµV | C/N 41.7 dB | LwSh 41.2 dB | UpSh 40.2 dB | MER 27.4 dB | PreLDPCBER <1.0E-6 | PreBCHBER <1.0E-8
  - If optical input is enabled, optical power is shown at the end

Power and quality:
- POW?
- CN?
- VA?
- MER?

BER / error related:
- CBER?
- VBER?
  - Returns NVAL when unavailable
- BCHBER?
  - Returns NVAL when unavailable
- PREBER?
- POSTBER?
- PRELDPCBER?
- PREBCHBER?
- MSCBER?
- FICBER?

Margins and related metrics:
- LKM?
- PER?
- SER?
- HUM?
- CSO?

Layer-specific metrics:
- CBERA?
- VBERA?
- CBERB?
- VBERB?
- CBERC?
- VBERC?

Bootstrap:
- CNBOOT?

Echoes:
- ECHOES?
  - Returns list of echoes with current distance/time units
  - Echo data includes echo number, delay, level, and DAB TII if available
  - Echoes or PDP widget must be active

Example:
#0 | 9 µs | -3.0 dB
#1 | 10 µs | -4.9 dB
#2 | 14 µs | -8.2 dB
#3 | 15 µs | -10.1 dB

Optical power:
- OPT_POW?
- OPT_POW_1310?
- OPT_POW_1490?
- OPT_POW_1550?

Signal parameters:
- PAR?
  - Returns tuned signal parameters shown in the Parameters widget when available
  - Example:
    Standard ATSC3 | BW 6.0 MHz | N. Carriers 8K | Guard Interval 6/1536 | PLP ID 0 | Constellation 16QAM | Code Rate 9/15 | Offset 13 MHz | TxID - - -

15. SPECTRUM ANALYSER COMMANDS
Requirement:
- Spectrum analyser must be maximized

RBW
- Read: RBW?
- Write: RBW xxxx.xx[HzW/KHzW/MHzW]
- Write: RBW AUTO
- Description: reads or changes resolution bandwidth

VBW
- Read: VBW?
- Write: VBW xxxx.xx[Hz/KHz/MHz]
- Write: VBW AUTO
- Description: reads or changes video bandwidth

SPAN
- Read: SPAN?
- Write: SPAN xxxx.xx[KHz/KHz/MHz]
- Description: reads or changes the span

RLEVEL
- Read: RLEVEL?
- Write: RLEVEL xxxx.xx[dBuV/dBmV/dBm]
- Write: RLEVEL AUTO
- Description: reads or changes reference level

ATT
- Write: ATT
- Description: restarts control attenuation

HOLD
- Write: HOLD MAX ON
- Write: HOLD MAX OFF
- Write: HOLD MIN ON
- Write: HOLD MIN OFF
- Write: HOLD CLEAR
- Description: changes spectrum hold feature

16. SERVICE COMMANDS
- Read: SERVICES?
  - Returns the list of TS service SIDs
  - Example:
    5300 | 5301 | 5303 | 5304 | 5305 | 5309 | 5310 | 5311 | 5312 | 5313 | 5314

- Write: SERVICE <SID>
  - Selects a TS service by SID
  - Example:
    SERVICE 2371

17. OTHER COMMANDS

FSTR
- Read: FSTR?
- Write: FSTR ON
- Write: FSTR OFF
- Description: reads or changes field strength measurement

ANT
- Read: ANT?
- Write: ANT <ANTENNA_NAME>
- Description: reads or changes the antenna used to measure field strength

EXTAMP
- Read: EXTAMP?
- Write: EXTAMP <±value>
- Description: reads or changes external attenuator or amplifier compensation

VDC
- Read: VDC?
- Write: VDC <xV(+22KHz)>
- Write: VDC OFF
- Write: VDC AUTO
- Description: reads or changes RF output voltage

18. DEVICE INFORMATION
- Read only: IDN?
- Returns:
  - model
  - reference
  - serial number
  - software version
  - calibration date

Example:
Model HEXYLON | Reference 901622 | Serial 03201147700090 | Vs 1.39.00019 | cal. date 18 jan 2022 v13

USAGE POLICY FOR LLM INTEGRATION
- Use only documented commands.
- Prefer the shortest valid command that directly matches user intent.
- Respect read/write distinctions exactly.
- Do not invent commands or undocumented values.
- Be careful with mode-dependent constraints.
- Be careful with commands that require UI state, such as ECHOES? or spectrum analyser commands.
"""