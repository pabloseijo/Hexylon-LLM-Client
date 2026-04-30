from llm.core.scpi_generator import generate_response


def test_knowledge_queries():
    assert "##" in generate_response("qué hace MER")
    assert "##" in generate_response("para qué sirve CN")
    assert "##" in generate_response("explícame FREQ")


def test_command_queries():
    assert generate_response("dame el MER") == "MER?"
    assert generate_response("consulta el BER previo") == "CBER?"
    assert generate_response("pon el VBW a 10 KHz") == "VBW 10 KHz"


def test_out_of_domain():
    response = generate_response("cuéntame un chiste")
    assert "##" in response or "no" in response.lower()