from services.plc import PLC
from services.flask import HttpServer
from services.events import EventsConsumer

plc = None
http_server = None
events = None

def start():
    """ starts the flask server and the PLC servient """
    global http_server, plc, events

    events = EventsConsumer()
    events.start()

    # start the flask server
    http_server = HttpServer()
    http_server.start()

    # start monitoring all properties of the PLC
    plc = PLC()

