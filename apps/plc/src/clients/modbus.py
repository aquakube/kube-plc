import logging
import threading
from typing import List, Union

from pymodbus.constants import Endian
from pymodbus.payload import BinaryPayloadDecoder
from pymodbus.payload import BinaryPayloadBuilder
from pymodbus.client import ModbusTcpClient
from pymodbus.bit_read_message import ReadCoilsResponse
from pymodbus.bit_write_message import WriteSingleCoilResponse
from pymodbus.register_read_message import ReadHoldingRegistersResponse
from pymodbus.register_write_message import WriteSingleRegisterResponse, WriteMultipleRegistersResponse

from config import config
from utilities.modbus import is_coil, is_single_word, is_double_word, parse_href

class ModbusClient():
    """
    This class is responsible for communicating with the PLC via Modbus TCP.
    """

    def __init__(self):
        """ Initializes the modbus client """
        self.lock = threading.Lock()
        self.client = ModbusTcpClient(
            host = config.plc.get_host(),
            port = config.plc.get_port(),
            timeout = config.modbus_client.timeout,
        )


    def close(self):
        """ Closes the underlying socket connection """
        self.client.close()


    def read_coil(self, register: int, address_offset: int = 1) -> int:
        """
        Read the coil and return the result if successful
        Raises: exception if a modbus error occurs. The exception will be raised with the error message
        """
        result: ReadCoilsResponse = self.client.read_coils(address = register - address_offset)
        if result.isError():
            uri = config.plc.get_base() + str(register)
            raise Exception(f"[ModbusClient] unable to read coil at {uri}, response: {result}")
        return int(result.getBit(0))


    def write_single_coil(self, register: int, value: int, address_offset: int = 1) -> WriteSingleCoilResponse:
        """ Writes the 1-bit value to the register """
        return self.client.write_coil(
            address = register - address_offset,
            value = value
        )


    def read_single_holding_register(self, register: int, address_offset: int = 400001) -> int:
        """
        Returns the value at the holding register
        Raises: exception if a modbus error occurs. The exception will be raised with
        the error message
        """
        result: ReadHoldingRegistersResponse = self.client.read_holding_registers(
            address = register - address_offset,
            count = 1
        )
        if result.isError():
            uri = config.plc.get_base() + str(register)
            raise Exception(f"[ModbusClient] unable to read single holding register at {uri}, response: {result}")

        decoder = BinaryPayloadDecoder.fromRegisters(
            registers = result.registers,
            byteorder = Endian.Big,
            wordorder = Endian.Little
        )
        return decoder.decode_16bit_int()


    def read_double_holding_register(self, register: int, address_offset: int = 400001) -> int:
        """
        Returns the value at the double holding register.
        Raises: exception if a modbus error occurs. The exception will be raised with the error message
        """
        result: ReadHoldingRegistersResponse  = self.client.read_holding_registers(
            address = register - address_offset,
            count = 2
        )
        if result.isError():
            uri = config.plc.get_base() + str(register)
            raise Exception(f"[ModbusClient] unable to read double holding register at {uri}, response: {result}")
        decoder = BinaryPayloadDecoder.fromRegisters(
            registers = result.registers,
            byteorder = Endian.Big,
            wordorder = Endian.Little
        )
        return decoder.decode_32bit_int()


    def write_single_holding_register(self, register: int, value: int, address_offset: int = 400001) -> WriteSingleRegisterResponse:
        """ Write the 16-bit int to the holding register """
        return self.client.write_register(
            address = register - address_offset,
            value = value
        )


    def write_double_holding_register(self, register: int, value: int, address_offset: int = 400001) -> WriteMultipleRegistersResponse:
        """ Write the 32-bit int to a pair of holding registers """
        builder = BinaryPayloadBuilder(byteorder=Endian.Big, wordorder=Endian.Little)
        builder.add_32bit_int(value)
        return self.client.write_registers(
            address = register - address_offset,
            values = builder.build(),
            skip_encode = True
        )


    def read(self, form: dict) -> None | int | List[int]:
        """
        Method used to read a value from a plc telemetry endpoint
        """
        with self.lock:
            try:
                # Open or reconnect to modbus+tcp server
                if not self.client.connect() or not self.client.is_socket_open():
                    logging.error(f"[ModbusClient] unable to connect to {config.plc.get_base()}")
                    return

                # Parse the form attributes for reading the property
                table: str = form['modbus:entity']
                register, quantity = parse_href(form['href'])
                scale = form.get('scale', 1)

                # Read the specified quantity of registers from the PLC. Default is 1.
                readings = []
                for index in range(quantity):
                    # Calculate the current register to read from given starting address and index
                    _register = register + index
                    # Read a single coil (i.e. boolean/bit access) value. Usually in the adress range 00001-09999
                    if is_coil(table):
                        readings.append(self.read_coil(register=_register))
                    # Read single word holding register (16 bit access). Usually in the address range 40001-404500
                    elif is_single_word(table, register=_register):
                        readings.append(self.read_single_holding_register(register=_register) * scale)
                    # reading double word holding register (32 bit access). Usually in the address range 416385-418383
                    elif is_double_word(table, register=_register):
                        # double words require 2 registers to be read, so need to perform skip if this is not the first index
                        _register += index + 1 if index > 0 else 0
                        readings.append(self.read_double_holding_register(register=_register) * scale)

                # Return the reading(s) requested in the form
                return readings[0] if len(readings) == 1 else readings
            except Exception:
                uri = config.plc.get_base() + str(form.get('href'))
                logging.exception(f"[ModbusClient] Error reading {uri}")


    def write(self, form: dict, value: int) -> None | WriteSingleCoilResponse | WriteSingleRegisterResponse | WriteMultipleRegistersResponse | List[Union[ None, WriteSingleCoilResponse, WriteSingleRegisterResponse, WriteMultipleRegistersResponse]]:
        """
        Method used to set a value at a plc telemetry endpoint
        """
        with self.lock:
            try:
                # Open or reconnect to modbus+tcp server
                if not self.client.connect() or not self.client.is_socket_open():
                    logging.error(f"[ModbusClient] unable to connect to {config.plc.get_base()}")
                    return

                # Parse the form attributes for writing the property
                table: str = form['modbus:entity']
                register, quantity = parse_href(form['href'])

                # Write the value provided to the specified number of registers. Default is 1.
                responses = []
                for index in range(quantity):
                    # Calculate the current register to write the value to given the starting address and index
                    _register = register if index == 0 else register + index
                    # Write the value to a single coil (i.e. boolean/bit access) value. Usually in the adress range 00001-09999
                    if is_coil(table):
                        responses.append(self.write_single_coil(_register, value))
                    # Write the value to a single word holding register (16 bit access). Usually in the address range 40001-404500
                    elif is_single_word(table, _register):
                        responses.append(self.write_single_holding_register(_register, value))
                    # Write the value to a double word holding register (32 bit access). Usually in the address range 416385-418383
                    elif is_double_word(table, _register):
                        responses.append(self.write_double_holding_register(_register, value))

                # Return the responses(s) generated from the requests in the form
                return responses[0] if len(responses) == 1 else responses
            except Exception:
                uri = config.plc.get_base() + str(form.get('href'))
                logging.exception(f"[ModbusClient] Error writing value {value} to {uri}")
