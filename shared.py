import random
import time
from config import PACKET_LOSS_SIMULATION, LATENCY_SIMULATION, JITTER_SIMULATION

def encode_move(pid, dx, dy, seq, key):
    return f"MOVE|{pid}|{dx}|{dy}|{seq}|{key}".encode()

def encode_shoot(pid, dx, dy, seq, key):
    return f"SHOOT|{pid}|{dx}|{dy}|{seq}|{key}".encode()

def encode_state(players, bullets, key):
    parts = ["STATE"]
    for pid, p in players.items():
        parts.append(f"{pid},{p['x']},{p['y']},{p['r']},{p['g']},{p['b']}")
    parts.append("BULLETS")
    for b in bullets:
        parts.append(f"{b['x']},{b['y']}")
    parts.append(key)
    return "|".join(parts).encode()

def encode_ping(seq, ts, key):
    return f"PING|{seq}|{ts}|{key}".encode()

def encode_pong(seq, ts, key):
    return f"PONG|{seq}|{ts}|{key}".encode()

def decode_packet(data):
    try:
        return data.decode().split("|")
    except:
        return None

def simulate_network():
    if random.random() < PACKET_LOSS_SIMULATION:
        return False
    if LATENCY_SIMULATION > 0 or JITTER_SIMULATION > 0:
        base = LATENCY_SIMULATION
        jitter = random.uniform(-JITTER_SIMULATION, JITTER_SIMULATION)
        delay = max(0, base + jitter)
        time.sleep(delay)
    return True
