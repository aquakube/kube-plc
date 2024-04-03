import os
import subprocess
import logging

logger = logging.getLogger(__name__)

def fast_ping(ip_address):
        '''
        Floods the host with ping messages 
        concurrently that will timeout quickly.
        Useful for quickly checking if device is up, 
        routable, and network is in optimal state.

        Linux Docs: https://linux.die.net/man/8/ping
        -f => flood the pings. Cocurrent
        -n => numeric output only
        -W => Wait time in seconds for each ping
        -w => absolute timeout in seconds
        -c => how many pings to send

        returns:
            bool => true if status code of 0, false otherwise
            None => if exception occurs
        '''
        try:
            command = ['ping', '-n', '-f', '-W 2', '-w 2', '-c 1', '-i 1', ip_address]
            status_code = subprocess.call(command, stdout=open(os.devnull, 'wb'))
            return status_code == 0
        except Exception:
            logger.exception('Failed to execute fast ping')

        return None