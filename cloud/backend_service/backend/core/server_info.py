import socket
import requests


def get_local_ip():

    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    finally:
        s.close()

    return ip


def get_public_ip():

    try:
        ip = requests.get("https://api.ipify.org").text
        return ip
    except:
        return None


def get_server_addresses():

    return {
        "local_ip": get_local_ip(),
        "public_ip": get_public_ip()
    }
