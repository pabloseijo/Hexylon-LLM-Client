from llm.core.interpreter import interpret_response


def main() -> None:
    cases = [
        (
            "¿Cuál es la frecuencia actual?",
            "FREQ?",
            "FREQ 530000 kHz",
        ),
        (
            "¿Está bloqueada la señal?",
            "LOCK?",
            "TRUE",
        ),
        (
            "¿Qué banda está seleccionada?",
            "BAND?",
            "BAND TER",
        ),
        (
            "Dime la identificación del equipo",
            "IDN?",
            "Model HEXYLON | Reference 901620 | Serial 03210979600010 | Vs 1.48.00004 | cal. date 24 mar 2021 v13",
        ),
        (
            "¿Cuál es el perfil actual?",
            "PROF?",
            "Perfil_Terrestre_1",
        ),
        (
            "Muéstrame las medidas actuales",
            "MEAS?",
            "POW 84.1 dBµV | C/N 41.7 dB | MER 27.4 dB",
        ),
        (
            "Dime los parámetros actuales",
            "PAR?",
            "Standard DVB-T2 | BW 8.0 MHz | Guard Interval 1/32",
        ),
    ]

    for user_input, command, raw_response in cases:
        result = interpret_response(user_input, command, raw_response)
        print(f"Usuario: {user_input}")
        print(f"Comando: {command}")
        print(f"Respuesta cruda: {raw_response}")
        print(f"Interpretación: {result}")
        print("-" * 60)


if __name__ == "__main__":
    main()