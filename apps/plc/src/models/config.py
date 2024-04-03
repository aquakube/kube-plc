import re

from dataclasses import dataclass


@dataclass(frozen=True)
class PLC:
    """The PLC resource configurations"""

    name: str
    """ The name of the PLC device """

    spec: dict
    """ The spec of the PLC which defines the base URI and properties """

    def __str__(self):
        return self.name

    def get_property(self, property_name: str) -> dict:
        """ Returns the property with the given name """
        return self.spec['properties'][property_name]

    def get_property_form(self, property_name: str) -> dict:
        """ Returns the form for the property with the given name """
        return self.get_property(property_name)['forms'][0]

    def get_all_observable_properties(self) -> list[dict]:
        """ Returns a list of names for all properties that are observed """
        return [
            name
            for name, property in self.spec['properties'].items()
            if 'observeproperty' in property['forms'][0]['op']
        ]

    def get_polling_times(self) -> set[int]:
        """ Returns the polling times of the PLC device """

        polling_times = []
        for property in self.spec['properties'].values():
            if 'modbus:pollingTime' in property['forms'][0]:
                polling_times.append(int(property['forms'][0]['modbus:pollingTime']))

        return set(polling_times)

    def get_host(self) -> str:
        """ Returns the host IP address of the PLC device """
        return re.search(pattern=r"//(.+):", string=self.spec["base"]).group(1)

    def get_port(self) -> int:
        """ Returns the port of the PLC device """
        return int(re.search(pattern=r":(\d+)", string=self.spec["base"]).group(1))

    def get_base(self) -> str:
        """
        Returns the base URI of the PLC device
        example full URI: modbus+tcp://{address}:{port}/{unitID}/{address}?quantity={?quantity}
        example base URI: modbus+tcp://10.0.9.40:502/1/
        """
        base_uri = self.spec["base"]
        base_uri += '/' if self.spec["base"][-1] != '/' else ''
        return base_uri


@dataclass(frozen=True)
class ModbusClient:
    """ The Modbus client configurations """

    single_word_start_register: int
    """ The start register for single word registers """

    single_word_end_register: int
    """ The end register for single word registers """

    double_word_start_register: int
    """ The start register for double word registers """

    double_word_end_register: int
    """ The end register for double word registers """

    coil_table: str
    """ The enum for coil modbus entities """

    holding_register_table: str
    """ The enum for holding register modbus entities """

    timeout: float
    """ The timeout for the modbus client """


@dataclass(frozen=True)
class KubernetesAttributes:
    """Defines kubernets attributes for the service producing the metrics"""

    pod_uid: str
    """ The UID of the Pod. (e.g '275ecb36-5aa8-4c2a-9c47-d8bb681b9aff') """

    pod_name: str
    """ The name of the Pod. (e.g 'mccp-pod-68bbc4fbfd') """

    namespace: str
    """ The name of the namespace that the pod is running in. (e.g 'plc') """

    # deployment_uid: str
    # """ The UID of the Deployment (e.g '275ecb36-5aa8-4c2a-9c47-d8bb681b9aff') """

    # deployment_name: str
    # """ The name of the Deployment (e.eg 'mccp') """

    # replica_set_uid: str
    # """ The UID of the ReplicaSet.	(e.g '275ecb36-5aa8-4c2a-9c47-d8bb681b9aff' """

    # replica_set_name: str
    # """ The name of the ReplicaSet. (e.g 'mccp-68bbc4fbfd') """

    # container_name: str
    # """
    # The name of the Container from Pod specification, must be unique within a Pod. 
    # Container runtime usually uses different globally unique name (container.name).
    # (e.g 'mccp-container')
    # """


@dataclass(frozen=True)
class Flask:
    """The Flask configuration"""

    port: int
    """ the port to expose the flask api on """

    host: str = "0.0.0.0"
    """
    the hostname to listen on. 
    defaults to ``'0.0.0.0'`` to have the server available externally
    """

@dataclass(frozen=True)
class KafkaConfig:
    """The Kafka configuration"""

    brokers: str
    """ The Kafka brokers """

    events_topic: str
    """ The Kafka events topic """

    max_block_ms: int
    """ The Kafka max block ms """

    retries: int
    """ The Kafka retries """


@dataclass(frozen=True)
class Config:
    """The configuration for the service"""

    debug: bool
    """ Enable for development and debugging tasks """

    environment: str
    """ The environment where the service is deployed. (e.g 'dev') """

    kafka: KafkaConfig
    """ The Kafka configurations """

    plc: PLC
    """ The PLC CR configurations """

    k8s: KubernetesAttributes
    """ The kubernetes attributes associated with the service """

    flask: Flask
    """ The flask configurations"""

    modbus_client: ModbusClient
    """ The modbus client configurations """
