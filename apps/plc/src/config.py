import os
import ast
from distutils.util import strtobool

from utilities.config import required_env
from models.config import Config, KubernetesAttributes, PLC, Flask, ModbusClient, KafkaConfig

config = None


def get_config() -> Config:
    return config


def initialize():
    global config

    plc_config = PLC(
        name = required_env('NAME'),
        spec = ast.literal_eval(required_env('SPEC')),
    )

    modbus_client_config = ModbusClient(
        single_word_start_register= int(os.getenv('PLC_SINGLE_WORD_START_REGISTER', 400001)),
        single_word_end_register = int(os.getenv('PLC_SINGLE_WORD_END_REGISTER', 404500)),
        double_word_start_register = int(os.getenv('PLC_DOUBLE_WORD_START_REGISTER', 416385)),
        double_word_end_register = int(os.getenv('PLC_DOUBLE_WORD_END_REGISTER', 418383)),
        coil_table = os.getenv('PLC_COIL_TABLE', 'Coil'),
        holding_register_table = os.getenv('PLC_HOLDING_REGISTER_TABLE', 'HoldingRegister'),
        timeout = float(os.getenv('PLC_TIMEOUT', 1.0)),
    )

    flask_config = Flask(
        port = int(os.getenv('FLASK_PORT', 5000)),
    )

    k8s_attributes = KubernetesAttributes(
        pod_uid = required_env('KUBERNETES_POD_UID') ,
        pod_name = required_env('KUBERNETES_POD_NAME'),
        namespace = required_env('KUBERNETES_NAMESPACE_NAME')
    )

    kafka_config = KafkaConfig(
        brokers = required_env('KAFKA_BROKERS'),
        events_topic = required_env('KAFKA_EVENTS_TOPIC'),
        max_block_ms = int(os.getenv('KAFKA_MAX_BLOCK_MS', 5000)),
        retries = int(os.getenv('KAFKA_RETRIES', 5)),
    )

    config = Config(
        plc = plc_config,
        flask = flask_config,
        k8s = k8s_attributes,
        kafka = kafka_config,
        modbus_client = modbus_client_config,
        debug = strtobool(os.getenv('DEBUG', 'False')),
        environment = required_env('ENVIRONMENT'),
    )