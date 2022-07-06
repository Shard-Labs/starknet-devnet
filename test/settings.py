"""Constants used in test files."""
import socket

class Settings(object):
    '''settings'''
    HOST = "127.0.0.1"
    PORT = ""
    APP_URL = ""

    L1_HOST = "localhost"
    L1_PORT = ""
    L1_URL = ""

    def __init__(self):
        '''Setup app endpoints for testing'''
        sock = socket.socket()
        sock.bind(('', 0))
        self.PORT = str(sock.getsockname()[1])
        self.APP_URL = f"http://{self.HOST}:{self.PORT}"

        l1_sock = socket.socket()
        l1_sock.bind(('', 0))
        self.L1_PORT = str(l1_sock.getsockname()[1])
        self.L1_URL = f"http://{self.L1_HOST}:{self.L1_PORT}/"

settings = Settings()