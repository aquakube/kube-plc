import threading
import json
import logging

from kafka import KafkaProducer

import clients.events as events
from config import config

class EventsConsumer(threading.Thread):


    def __init__(self):
        super().__init__(daemon=True, name='events_consumer')

        logging.info(f'initializing kafka producer at {config.kafka.brokers}')

        self.producer = KafkaProducer(
            bootstrap_servers=config.kafka.brokers,
            max_block_ms=config.kafka.max_block_ms,
            retries=config.kafka.retries,
            acks='all',
        )
        self.stop_event = threading.Event()


    def stop(self):
        self.stop_event.set()


    def run(self):
        while not self.stop_event.is_set():
            try:
                event = events.listen()
                if event is not None:

                    logging.info(f'event received: {event}')

                    # publish event to kafka
                    cloudevent = bytes(json.dumps(event), 'utf-8')
                    future = self.producer.send(config.kafka.events_topic, cloudevent)
                    future.get()
            except:
                logging.exception('failed to publish event to kafka')