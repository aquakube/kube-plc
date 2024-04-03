import os
import yaml

import kopf
from kubernetes import client
from jinja2 import Template

from utilities.jinja import load_deployment_template, load_service_template


def deployment(spec, namespace, name, version, logger):
    """
    Creates the PLC Deployment
    """

    # load the template
    template: Template = load_deployment_template()

    # render the template with the CR's spec and some additional metadata
    # note: do not use the CRs body as an environment variable, the last-applied-configuration causes problems
    rendered_template: str = template.render(
        # SPEC is the PLC CR's spec so the PLC service can consume it
        spec=spec,
        # NAME is the PLC name
        name=name,
        # VERSION is the image tag to use
        version=version,
        # ENVIRONMENT is the environment (e.g dev, qa, prod)
        environment=os.getenv('ENVIRONMENT', 'default'),
        # DEBUG is the debug flag to development or debugging feature like console exporter
        debug = False,
        # KAFKA_BROKERS is the kafka brokers to connect to
        kafka_brokers = os.getenv('KAFKA_BROKERS'),
        # KAFKA_EVENTS_TOPIC is the kafka topic to publish events to
        kafka_events_topic = os.getenv('KAFKA_EVENTS_TOPIC'),
        # KAFKA_MAX_BLOCK_MS is the maximum time to block waiting for kafka to respond
        kafka_max_block_ms = os.getenv('KAFKA_MAX_BLOCK_MS', 5000),
        # KAFKA_RETRIES is the number of times the kafka producer will retry sending a message
        kafka_retries = os.getenv('KAFKA_RETRIES', 5),
        # PLC_TIMEOUT is the timeout to make a modbus request to the PLC device
        plc_timeout = spec.get('plc_timeout', 1.0),
        # OTEL_METRICS_EXPORTER is the exporter to use for metrics. valid values are 'otlp', 'console', or both e.g 'console,otlp'
        otel_metrics_exporter = os.getenv('OTEL_METRICS_EXPORTER', 'otlp'),
        # OTEL_EXPORTER_OTLP_METRICS_ENDPOINT is the target to which the metric exporter is going to send metrics
        otel_exporter_otlp_metrics_endpoint = os.getenv('OTEL_EXPORTER_OTLP_METRICS_ENDPOINT','telemetry-collector.opentelemetry.svc.cluster.local:4317'),
        # OTEL_EXPORTER_OTLP_METRICS_TIMEOUT is the maximum time the OTLP exporter will wait for each batch export for metrics.
        otel_exporter_otlp_metrics_timeout = os.getenv('OTEL_EXPORTER_OTLP_METRICS_TIMEOUT','2500'),
        # OTEL_EXPORTER_OTLP_METRICS_PROTOCOL represents the the transport protocol for metrics.
        otel_exporter_otlp_metrics_protocol = os.getenv('OTEL_EXPORTER_OTLP_METRICS_PROTOCOL', 'grpc'),
        # OTEL_EXPORTER_OTLP_METRICS_INSECURE` represents whether to enable client transport security for gRPC requests for metrics.
        otel_exporter_otlp_metrics_insecure = os.getenv('OTEL_EXPORTER_OTLP_METRICS_INSECURE', 'true')
    )

    # convert the rendered template to a dict
    deployment: dict = yaml.safe_load(rendered_template)

    # add the recommended kubernetes labels to the PLCs CR, Deployment, and Pod
    # note: labels are added to the deployments pod template through the nested parameter
    # https://kubernetes.io/docs/concepts/overview/working-with-objects/common-labels/
    kopf.label(
        objs=[deployment],
        labels={
            'app.kubernetes.io/name': name,
            'app.kubernetes.io/instance': f"{namespace}.{name}",
            'app.kubernetes.io/version': version,
            'app.kubernetes.io/component': 'plc',
            'app.kubernetes.io/part-of': 'foreveroceans',
            'app.kubernetes.io/managed-by': 'plc-operator'
        },
        nested='spec.template'
    )

    # add the CR's uid to the pod's owner references.
    kopf.adopt(deployment)

    # create the deployment
    k8s_apps_v1 = client.AppsV1Api()

    if not deployment_already_exists(name, namespace, logger):
        k8s_apps_v1.create_namespaced_deployment(
            body=deployment,
            namespace=namespace
        )


def service(name, namespace, logger, version: str):
    """
    Creates the PLC Service
    """
    template: Template = load_service_template()
    service: dict = yaml.safe_load(template.render(name=name))
    kopf.label(
        objs=[service],
        labels={
            'app.kubernetes.io/name': name,
            'app.kubernetes.io/instance': f"{namespace}.{name}",
            'app.kubernetes.io/version': version,
            'app.kubernetes.io/component': 'plc',
            'app.kubernetes.io/part-of': 'foreveroceans',
            'app.kubernetes.io/managed-by': 'plc-operator'
        }
    )
    kopf.adopt(service)
    core_v1_api = client.CoreV1Api()

    if not service_already_exists(name, namespace, logger):
        core_v1_api.create_namespaced_service(
            body=service,
            namespace=namespace,
        )


def deployment_already_exists(name, namespace, logger) -> bool:
    # create the deployment
    k8s_apps_v1 = client.AppsV1Api()

    api_response = k8s_apps_v1.list_namespaced_deployment(
        namespace,
    )
    for item in api_response.items:
        if item.metadata.name == name:
            logger.info("Found deployment: %s" % item.metadata.name)
            return True
    else:
        return False


def service_already_exists(name, namespace, logger) -> bool:
    # create the deployment
    core_v1_api = client.CoreV1Api()

    api_response = core_v1_api.list_namespaced_service(
        namespace,
    )

    for item in api_response.items:
        if item.metadata.name == name:
            logger.info("Found service: %s" % item.metadata.name)
            return True
    else:
        return False
