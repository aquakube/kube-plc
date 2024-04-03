from typing import Tuple
from urllib.parse import urlparse, parse_qs

from config import config


def is_coil(table: str) -> bool:
    """ Returns true if table is a coil. False otherwise. Coils are 1-bit registers for discrete input ON(1) or OFF(0) """
    return table == config.modbus_client.coil_table


def is_single_word(table: str, register: int) -> bool:
    """ Returns True if the provided register is a single holding register (16-bit int).  False otherwise. """
    return (
        table == config.modbus_client.holding_register_table
        and config.modbus_client.single_word_start_register <= register <= config.modbus_client.single_word_end_register
    )


def is_double_word(table: str, register: int) -> bool:
    """ Returns True if the provided register is a double holding register (32-bit int). False otherwise """
    return (
        table == config.modbus_client.holding_register_table
        and config.modbus_client.double_word_start_register <= register <= config.modbus_client.double_word_end_register
    )


def parse_href(href) -> Tuple[int, int]:
    """ Parses the href and returns the register and quantity """
    parsed_url = urlparse(href)
    query_params = parse_qs(parsed_url.query)
    quantity = int(query_params.get('quantity', ['1'])[0])
    register = int(parsed_url.path.split('/')[-1])
    return (register, quantity)
