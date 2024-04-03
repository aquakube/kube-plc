import os

import kopf

from handlers import create, update
from utilities.tunnel import ServiceTunnel


@kopf.on.startup()
def startup(logger, settings, **kwargs):
    """
    Execute this handler when the operator starts.
    No call to the API server is made until this handler
    completes successfully.
    """
    settings.execution.max_workers = 5
    settings.networking.request_timeout = 30
    settings.networking.connect_timeout = 10
    settings.persistence.finalizer = 'plc.foreveroceans.io/finalizer'
    settings.persistence.progress_storage = kopf.AnnotationsProgressStorage(prefix='plc.foreveroceans.io')
    settings.persistence.diffbase_storage = kopf.AnnotationsDiffBaseStorage(prefix='plc.foreveroceans.io')
    settings.admission.server = kopf.WebhookAutoTunnel()
    settings.admission.managed = 'plc.foreveroceans.io'

    # default to using a tunnel to the service. This will start ngrok.
    # You need to have kopf[dev] installed for this to work.
    if os.getenv("ENVIRONMENT", "dev") == "dev":
        settings.admission.server = kopf.WebhookAutoTunnel()

    # if we are in production, use a service tunnel. This will use the self-signed
    # cert that is created by the operator.
    else:
        settings.admission.server = ServiceTunnel(
            namespace=os.getenv("NAMESPACE", "plc"),
            service_name=os.getenv("SERVICE_NAME"),
            service_port=int(os.getenv("SERVICE_PORT", 443)),
            container_port=int(os.getenv("CONTAINER_PORT", 9443))
        )


@kopf.on.cleanup()
def cleanup(logger, **kwargs):
    logger.info("im shutting down. Goodbye!")


@kopf.on.resume('plcs.foreveroceans.io')
@kopf.on.create('plcs.foreveroceans.io')
def on_create(spec, name, namespace, patch, logger, **kwargs):
    """ Create the PLC Deployment and Service """
    version = spec.get('version', 'latest')
    create.deployment(spec, namespace, name, version, logger)
    create.service(name, namespace, logger, version)


@kopf.on.update("plcs.foreveroceans.io")
def on_update(spec, name, namespace, **kwargs):
    """ Update the PLC Deployment and Service"""
    version = spec.get('version', 'latest')
    update.deployment(spec, name, namespace, version)
    update.service(name, namespace, version)


@kopf.on.delete("plcs.foreveroceans.io")
def on_delete(logger, **kwargs):
    """ Owner reference will delete the deployment and service."""
    logger.info("on_delete plcs.foreveroceans.io")


@kopf.on.mutate("plcs.foreveroceans.io", operation="CREATE")
def k8slabel(spec, name, namespace, patch, **kwargs):
    """ On admission attach the k8s labels to the PLC CR """
    kopf.label(
        objs=[patch],
        labels={
            'app.kubernetes.io/name': name,
            'app.kubernetes.io/instance': f"{namespace}.{name}",
            'app.kubernetes.io/version': f"{spec.get('version', 'latest')}",
            'app.kubernetes.io/component': 'plc',
            'app.kubernetes.io/part-of': 'foreveroceans',
            'app.kubernetes.io/managed-by': 'plc-operator'
        },
    )


def is_deployment_available(condition) -> bool:
    """ Returns true if the deployment is available, False otherwise """
    return condition["type"] == "Available" and condition["status"] == "True"


@kopf.on.field(
    'deployments',
    field='status.conditions',
    labels={'app.kubernetes.io/managed-by': 'plc-operator'},
)
def deployment_status_changed(name, old, new, logger, **kwargs):
    """
    When the deployment status changes, update the PLC CR status if it has changed.
    The deployment status reflects the pod being ready.
    The readiness probe reflects if the PLC is online.
    """
    was_available: bool = any(map(is_deployment_available, old)) if old else None
    is_available: bool = any(map(is_deployment_available, new))

    if was_available != is_available:
        logger.info(f"[plc/status] {name} deployment status changed to {is_available}")
        update.status(name, is_available, logger=logger)
