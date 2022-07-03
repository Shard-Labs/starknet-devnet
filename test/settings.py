"""Constants used in test files."""

from glob import glob


HOST = "127.0.0.1"
PORT = "5050"
L1_HOST = "localhost"
L1_PORT = "8545"

APP_URL = f"http://{HOST}:{PORT}"
GATEWAY_URL = APP_URL
FEEDER_GATEWAY_URL = APP_URL
L1_URL = f"http://{L1_HOST}:{L1_PORT}/"

def get_app_url():
    '''return gateway url'''
    return f"http://{HOST}:{PORT}"

def set_port(port):
    '''set port'''
    global PORT 
    PORT = port  
