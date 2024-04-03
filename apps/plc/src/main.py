import time
import logging

import config


if __name__ == '__main__':
    """
    This services acts as a single PLC servient.
    It hosts a consumed PLC resource that implements a Modbus protocol stack to interface with the PLC device.
    Multiple of these PLC servients work together to build the system that runs feed automations and manages IIoT data.
    """

    # initialize the configuration
    config.initialize()

    # configure logging
    logging.basicConfig(level=logging.DEBUG if config.get_config().debug else logging.INFO)
    logger = logging.getLogger()

    # start the services
    import services
    services.start()

    while True:
        logger.debug('PLC main loop')
        time.sleep(100)