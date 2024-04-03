import os

from jinja2 import Template, StrictUndefined


def load_template(path: str) -> Template:
    """
    Loads a jinja2 template from a file
    """
    with open(path, 'rt') as f:
        return Template(f.read(), undefined=StrictUndefined)


def load_deployment_template() -> Template:
    """
    Loads the deployment template and renders it
    """
    if os.getenv("ENVIRONMENT", "dev") == "dev":
        path = './apps/operator/kubernetes/deployment.yaml'
    else:
        path = '/usr/app/kubernetes/deployment.yaml'

    return load_template(path)


def load_service_template() -> Template:
    """
    Loads the service template and renders it
    """
    if os.getenv("ENVIRONMENT", "dev") == "dev":
        path = './apps/operator/kubernetes/service.yaml'
    else:
        path = '/usr/app/kubernetes/service.yaml'

    return load_template(path)