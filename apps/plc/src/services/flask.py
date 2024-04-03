import logging
import threading
import json

from flask import Flask, Response, request, jsonify
from http import HTTPStatus

import clients.events as events
import clients.modbus_events as modbus_events
from clients.opentelemetry import OpenTelemetryClient
import services
from config import config
from utilities.ping import fast_ping

app = Flask(__name__)
logger = logging.getLogger()


class HttpServer(threading.Thread):
    """
    Creates a new flask HTTP server.
    """

    def __init__(self):
        super().__init__(daemon=True, name='http_server')


    def run(self):
        # if debug is set to True, you can't access
        # flask across a network
        app.debug = False

        try:
            app.run(
                host=config.flask.host,
                port=config.flask.port,
                threaded=True,
                debug=False
            )
        except KeyboardInterrupt:
            logger.info('Flask got interrupt. Quitting.')


@app.route("/livez")
def liveness():
    """
    Checks if the service is alive.
    Pod will be restarted if this endpoint returns an error.
    """
    return Response('Service is alive!', status=HTTPStatus.OK)


@app.route("/readyz")
def readiness():
    """
    Checks if the service is ready to accept requests.
    If the PLC device is not connected, then the service is not ready as any requests received during this period will result in an error.
    Pod will not be restarted if this endpoint returns an error

    This is readiness probe will be invoked by kubelet on some period interval configured by the PLC operator in the deployment manifest.
    This endpoint will manage the lifecycle of the opentelemetry provider because of error handling issues with the package
    The jist of it is that if the PLC is not reachable then the PLC timeout could lead to an overflow on the metric readers collect()
    Current Otel pacakge handling of this is to raise an exception thats handled internally, this results in that metric reader never being called again
    """

    if fast_ping(ip_address=config.plc.get_host()):
        if services.plc.opentelemetry_client is None:
            logger.info(f"Recreating opentelemetry client now that plc {config.plc.name} - {config.plc.get_host()} is reachable!")
            services.plc.opentelemetry_client = OpenTelemetryClient()
            services.plc.observeallproperties()
        return Response('Service is ready!', status=HTTPStatus.OK)

    # if the plc is not reachable, then the service is not ready and we will shutdown the opentelemtry provider
    if services.plc.opentelemetry_client is not None:
        logger.warning(f"Shutting down the opentelemetry client because the plc {config.plc.name} - {config.plc.get_host()} is unreachable!")
        services.plc.opentelemetry_client.shutdown()
        services.plc.opentelemetry_client = None
    return Response('PLC connection is down, service is not ready!', status=HTTPStatus.SERVICE_UNAVAILABLE)


@app.route("/api/events", methods=["GET"])
def subevents():
    """
    Listen to the event stream of the observable properties
    as SSE (Server-Sent Events).
    """

    def _events():
        thread_id = threading.current_thread().ident
        logger.info(f"Subscribing to events for thread {thread_id}")
        try:
            while True:
                event = modbus_events.subscribe(thread_id)
                if event is not None:
                    name, value, timestamp = event
                    package = json.dumps({
                        'name': name,
                        'value': value,
                        'timestamp': timestamp,
                    })
                    yield f"data: {package}\n\n"
        except:
            pass
        finally:
            logger.info(f"Unsubscribing from events for thread {thread_id}")
            modbus_events.unsubscribe(thread_id)

    return Response(_events(), mimetype='text/event-stream')


@app.route("/api/plc/<property>", methods=["GET"])
def read(property: str) -> Response:
    """
    Endpoint to read a property from the PLC.
    """

    # confirm that the property exists
    if property not in config.plc.spec['properties']:
        return Response(f"Property {property} not found", status=HTTPStatus.NOT_FOUND)

    # confirm that the property is readable
    form: dict = config.plc.spec['properties'][property]['forms'][0]
    if 'readproperty' not in form['op']:
        return Response(f"Property {property} is not readable", status=HTTPStatus.METHOD_NOT_ALLOWED)

    # confirm that the PLC resource is available
    if not services.plc.modbus_client.client.is_socket_open():
        return Response(f"PLC resource is not available, service is not ready!", status=HTTPStatus.SERVICE_UNAVAILABLE)

    # if all checks pass, then attempt to read the property
    value = services.plc.readproperty(property)
    thread = threading.current_thread()
    logger.info(f"[{thread.name}] Read {property} => {value}")

    # if the value is None, then the read failed
    if value is None:
        return Response(f"Failed to read property {property}", status=HTTPStatus.INTERNAL_SERVER_ERROR)

    # success
    return jsonify({ "value": value }), HTTPStatus.OK


@app.route("/api/plc/<property>", methods=["PUT"])
def write(property: str) -> Response:
    """
    Endpoint to write a property to the PLC.
    """

    # confirm that the property exists
    if property not in config.plc.spec['properties']:
        return Response(f"Property {property} not found", status=HTTPStatus.NOT_FOUND)

    # confirm that the property is readable
    form: dict = config.plc.spec['properties'][property]['forms'][0]
    if 'writeproperty' not in form['op']:
        return Response(f"Property {property} is not writable", status=HTTPStatus.METHOD_NOT_ALLOWED)

    # confirm that the PLC resource is available
    if not services.plc.modbus_client.client.is_socket_open():
        return Response(f"PLC resource is not available, service is not ready!", status=HTTPStatus.SERVICE_UNAVAILABLE)

    # confirm that the request body is valid
    request_dict = request.get_json()

    logger.info('request_dict: %s', request_dict)
    if not request_dict or not type(request_dict.get("value")) is int:
        return Response("Invalid request body", status=HTTPStatus.BAD_REQUEST)

    # if all checks pass, then attempt to write value to the property
    result = services.plc.writeproperty(name=property, value=request_dict["value"])

    # if the result is None, then the write failed
    if result is None:
        return Response(f"Failed to write property {property}", status=HTTPStatus.INTERNAL_SERVER_ERROR)

    thread = threading.current_thread()
    logger.info(f"[{thread.name}] {result} (isError: {result.isError()})")

    # if the result error bit is set then the write failed
    if result.isError():
        return Response(f"Failed to write property {property}", status=HTTPStatus.INTERNAL_SERVER_ERROR)

    events.push_event(property, request_dict["value"])

    # success
    return Response(str(result), status=HTTPStatus.OK)


@app.route("/api/plc", methods=["POST"])
def form() -> Response:
    """
    Endpoint to process a form.
    https://w3c.github.io/wot-binding-templates/bindings/protocols/modbus/#examples
    """

    # confirm that the PLC resource is available
    if not services.plc.modbus_client.client.is_socket_open():
        return Response(f"PLC resource is not available, service is not ready!", status=HTTPStatus.SERVICE_UNAVAILABLE)

    # confirm that the request body is valid
    request_dict = request.get_json()
    logger.info('request_dict: %s', request_dict)
    if not request_dict or not type(request_dict.get("form")) is dict:
        return Response("Missing form in request body", status=HTTPStatus.BAD_REQUEST)

    # confirm that the form is valid
    form = request_dict["form"]
    op = form.get("op", [])
    op = [op] if type(op) is str else op

    if not all([field in form for field in ['href', 'modbus:entity', 'op']]):
        return Response("Invalid request body", status=HTTPStatus.BAD_REQUEST)

    if not any(['readproperty' in op, ('writeproperty' in op and 'value' in form)]):
        return Response("Invalid operation", status=HTTPStatus.BAD_REQUEST)

    # if all checks pass, then attempt to process the form
    readings = None
    responses = None
    if 'readproperty' in op:
        readings = services.plc.modbus_client.read(form)
    if 'writeproperty' in op:
        responses = services.plc.modbus_client.write(form, value=form['value'])

    thread = threading.current_thread()
    logger.info(f"[{thread.name}] {form} => readings: {readings}, responses: {responses}")

    # if the value is None, then the read failed
    if (readings is None and 'readproperty' in op) or (responses is None and 'writeproperty' in op):
        return Response(f"Failed to process form {form}", status=HTTPStatus.INTERNAL_SERVER_ERROR)

    # success
    if responses is not None:
        responses = [str(r) for r in responses] if type(responses) is list else str(responses)
    return jsonify({'properties': readings, 'responses': responses}), HTTPStatus.OK