import pytest

from src.models.config import PLC

@pytest.fixture
def plc() -> PLC:
    """ Initialize PLC fixture """
    return PLC(
        name="test",
        spec={
            "base": "modbus+tcp://10.0.9.10:502/1/",
            "properties": {
                "silo2Humidity": {
                    "forms": [
                        {
                            "href": "400702",
                            "modbus:entity": "HoldingRegister",
                            "modbus:pollingTime": 5,
                            "op": ["observeproperty", "readproperty"],
                            "scale": 0.1,
                        }
                    ],
                    "readOnly": True,
                    "title": "Starboard Silo Relative Humidity",
                    "type": "number",
                    "unit": "% RH",
                },
                "silo2Temp": {
                    "forms": [
                        {
                            "href": "400701",
                            "modbus:entity": "HoldingRegister",
                            "modbus:pollingTime": 15,
                            "op": ["observeproperty", "readproperty"],
                            "scale": 0.1,
                        }
                    ],
                    "readOnly": True,
                    "title": "Starboard Silo Temperature",
                    "type": "number",
                    "unit": "C",
                },
            },
            "title": "Cerberus Control Panel",
            "version": "0.0.1",
        },
    )

def test_plc_get_port(plc: PLC):
    assert plc.get_port() == 502

def test_plc_get_host(plc: PLC):
    assert plc.get_host() == "10.0.9.10"
