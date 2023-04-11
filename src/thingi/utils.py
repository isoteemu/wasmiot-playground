import socket

def get_hostname() -> str:
    """Get the hostname of the system."""
    return socket.gethostname()
