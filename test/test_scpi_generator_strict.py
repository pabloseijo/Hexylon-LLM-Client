from llm.core.scpi_generator import generate_scpi, is_valid_scpi_output


def test_invalid_commands_are_rejected():
    assert is_valid_scpi_output("CHC?") is False
    assert is_valid_scpi_output("IDCN?") is False
    assert is_valid_scpi_output("BERPRE?") is False
    assert is_valid_scpi_output("VBW basura") is False
    assert is_valid_scpi_output("FREQ hola") is False


def test_valid_commands_are_accepted():
    assert is_valid_scpi_output("MER?") is True
    assert is_valid_scpi_output("CBER?") is True
    assert is_valid_scpi_output("VBW 10 KHz") is True
    assert is_valid_scpi_output("FREQ 650 MHz") is True
    assert is_valid_scpi_output("RBW 300 HzW") is True


def test_generate_scpi_known_cases():
    assert generate_scpi("dame el MER") == "MER?"
    assert generate_scpi("consulta el BER previo") == "CBER?"
    assert generate_scpi("pon el VBW en 10 KHz") == "VBW 10 KHz"
    assert generate_scpi("pon la frecuencia en 650 MHz") == "FREQ 650 MHz"