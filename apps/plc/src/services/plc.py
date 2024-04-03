import logging
import time
from collections.abc import Iterable, Callable

from opentelemetry.sdk.metrics import Meter
from opentelemetry.metrics import CallbackOptions, Observation, Histogram

from config import config
from clients.modbus import ModbusClient
from clients.opentelemetry import OpenTelemetryClient
import clients.modbus_events as modbus_events
from utilities.time import profile

logger = logging.getLogger()


class PLC:
    """
    The PLC class represents a consumed PLC resource.
    An instance of this class has all the details necessary to successfully interact with the PLC device.
    """

    latency: Histogram = None

    def __init__(self):
        """ Initialize the open telemetry client and the modbus client """
        self.modbus_client = ModbusClient()
        self.opentelemetry_client = None


    def observeallproperties(self):
        """ Observes all properties of the PLC device """
        for property in config.plc.get_all_observable_properties():
            self.observeproperty(property)


    def observeproperty(self, name: str):
        """ Observes a single property of the PLC device """
        property: dict = config.plc.get_property(name)
        meter: Meter = self.opentelemetry_client.get_meter(polling_time=property['forms'][0]['modbus:pollingTime'])
        meter.create_observable_gauge(
            name = name,
            unit = property.get('unit', ''),
            callbacks = [self.get_observable_callback(name)]
        )


    def get_observable_callback(self, name: str) -> Callable[[CallbackOptions], Iterable[Observation]]:
        """ Function for acquiring a cllback to read a property as an observable gauge"""
        def readproperty_callback(options: CallbackOptions) -> Iterable[Observation]:
            """ Callback function for reading a property """

            value = self.readproperty(name)

            modbus_events.publish_event(name, value, time.time())

            return [
                Observation(
                    value = value,
                    attributes = {}
                )
            ]

        return readproperty_callback

    @profile()
    def writeproperty(self, name: str, value: int):
        """ Writes a property value to the PLC resource """
        return self.modbus_client.write(
            form = config.plc.get_property_form(name),
            value = value
        )


    @profile()
    def readproperty(self, name: str):
        """ Reads a property value on the PLC resource """
        return self.modbus_client.read(
            form = config.plc.get_property_form(name)
        )
