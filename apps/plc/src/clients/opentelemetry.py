import time
import logging

from collections.abc import Iterable, Callable

from opentelemetry.metrics import CallbackOptions, Observation, Histogram
from opentelemetry.sdk.metrics import MeterProvider, Meter
from opentelemetry.sdk.resources import Resource, SERVICE_NAME, KUBERNETES_POD_UID, KUBERNETES_POD_NAME, KUBERNETES_NAMESPACE_NAME
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import (
    OTLPMetricExporter,
)
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader, ConsoleMetricExporter

from config import config
from utilities.config import required_env

logger = logging.getLogger()


class OpenTelemetryClient:
    """
    This class is responsible for configuring the OpenTelemetry SDK and API for use in the application.
    Codes against the OpenTelemetry Metrics API to collect telemetry data from the PLC
    Sends its telemetry to the OpenTelemetry Collector via OTLP.
    """

    def __init__(self):
        """
        configures the OpenTelemetry SDK and API for use in the application
        """

        resource = Resource(
            attributes = {
                SERVICE_NAME: config.plc.name,
                KUBERNETES_POD_UID: config.k8s.pod_uid,
                KUBERNETES_POD_NAME: config.k8s.pod_name,
                KUBERNETES_NAMESPACE_NAME: config.k8s.namespace,
                'com.aquakube.app': 'plc',
            }
        )
        """
        A Resource is an immutable representation of the entity producing telemetry as Attributes.
        In this scenario, a PLC process is producing telemetry that is running in a container on Kubernetes,
        it has a Pod, it is in a namespace and possibly is part of a Deployment which also has a name. 
        All three of these attributes can be included in the Resource.
        """

        exporters: list[ConsoleMetricExporter, OTLPMetricExporter] = []
        """
        The exporters are responsible for sending the collected metrics to the configured destination.
        The environment variable OTEL_METRICS_EXPORTER is used to configure one or more exporters.
        """

        if 'console' in required_env('OTEL_METRICS_EXPORTER'):
            exporters.append(ConsoleMetricExporter())
            """
            The console exporter console exporter is useful for development and debugging tasks
            """
            
        if 'otlp' in required_env('OTEL_METRICS_EXPORTER'):
            exporters.append(OTLPMetricExporter())
            """
            This sends data to an OTLP endpoint or the OpenTelemetry Collector according to the environnment variables set.
            endpoint = os.getenv('OTEL_EXPORTER_OTLP_METRICS_ENDPOINT')
            insecure = os.getenv('OTEL_EXPORTER_OTLP_METRICS_INSECURE')
            """

        if not exporters:
            raise Exception("No exporters configured! Please set OTEL_METRICS_EXPORTER to 'console' or 'otlp' or both 'console,otlp'")  

        self.providers: dict[int, MeterProvider] = {}
        """
        MeterProvider is the entry point of the API. It provides access to Meters.
        The providers are tied to the resource and the configured PeriodicExportingMetricReader(s)
        The providers inherit the interval of each metric reader so we need to provide a unique provider for each polling time the PLC will sample over
        note: using a single provider with multiple periodic metric readers will result in the metrics being collected on each periodic readers interval (i.e this would break the configured polling times)
        """

        for polling_time in config.plc.get_polling_times():

            metric_readers = [
                PeriodicExportingMetricReader(
                    exporter = exporter,
                    export_interval_millis = int(polling_time * 1E3),
                    export_timeout_millis= int(polling_time * 1E3),
                )
                for exporter in exporters
            ]
            """ The metric readers collect metrics based on a user-configurable time interval, and passes the metrics to the configured exporter """

            self.providers[polling_time] = MeterProvider(
                metric_readers = metric_readers,
                resource = resource,
            )
            """ The MeterProvider is the entry point of the API. It provides access to Meters. """

        self.meters: dict[int, Meter] = {
            polling_time: provider.get_meter(
                name = config.plc.name,
                version = config.plc.spec['version'],
            )
            for (polling_time, provider) in self.providers.items()
        }
        """
        The meter is responsible for creating instruments which are then used to produce measurements
        The meters are also unique to each polling time the PLC will sample over as they inherit the MeterProvider
        """

        self.record_uptime()
        """ The service uptime is reported in seconds as a health metric """

        self.histogram: Histogram = self.record_latency()
        """ The service will profile response times / latency  of the modbus+tcp client requests """


    def get_meter(self, polling_time: int) -> Meter:
        """
        returns the meter for the given polling time
        """
        return self.meters[polling_time]


    def record_uptime(self):
        """ Records the uptime of the PLC service as a metric to observe system health """
        self.start_time = time.time()
        meter = self.get_meter(polling_time=max(config.plc.get_polling_times()))
        meter.create_observable_gauge(
            name = f'{config.plc.name}.uptime',
            description = f'The uptime of the {config.plc.name} plc service measured in seconds',
            unit = 's',
            callbacks = [self.get_uptime_callback()]
        )


    def get_uptime_callback(self) -> Callable[[CallbackOptions], Iterable[Observation]]:
        """ Function for acquiring a cllback to read a property as an observable gauge"""
        def uptime_callback(options: CallbackOptions) -> Iterable[Observation]:
            """ Callback function for reading a property """
            return [Observation(value = time.time() - self.start_time)]

        return uptime_callback


    def record_latency(self) -> Histogram:
        """ Creates a histogram to record the latency of the modbus client """
        meter = self.get_meter(polling_time=max(config.plc.get_polling_times()))
        # global latency
        return meter.create_histogram(
            name=f'{config.plc.name}.modbus.latency',
            unit="ms",
            description=f"The latency of the {config.plc.name} modbus client measured in milliseconds"
        )


    def shutdown(self):
        """
        Shutdown the clients provider
        """
        try:
            provider: MeterProvider
            for provider in self.providers.values():
                provider.shutdown()
        except:
            logger.exception("Failed to shutdown the opentelemetry client!")