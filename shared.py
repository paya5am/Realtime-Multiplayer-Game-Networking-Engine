import json
import random
import time
from config import PACKET_LOSS_SIMULATION, LATENCY_SIMULATION


def encode_packet(data):
    return json.dumps(data).encode()


def decode_packet(data):
    return json.loads(data.decode())


def simulate_network():
    if random.random() < PACKET_LOSS_SIMULATION:
        return False
    if LATENCY_SIMULATION > 0:
        time.sleep(LATENCY_SIMULATION)
    return True
