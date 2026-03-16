import socket
import threading
import time
from config import *
from shared import *

server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server.bind((SERVER_IP, SERVER_PORT))

print("Server started on", SERVER_IP, SERVER_PORT)

clients = {}
players = {}

lock = threading.Lock()
#threading lock to prevent simultaneous player/client access and to prevent corruption 

def handle_packets():
    while True:
        data, addr = server.recvfrom(4096)

        if not simulate_network():
            continue

        packet = decode_packet(data)

        if packet.get("token") != SECRET_TOKEN:
            continue

        with lock:

            if addr not in clients:
                pid = str(len(clients) + 1)
                clients[addr] = pid
                players[pid] = {"x": 100, "y": 100}
                print("New client:", pid)

            pid = clients[addr]

            if packet["type"] == "move":
                dx = packet["dx"]
                dy = packet["dy"]

                players[pid]["x"] += dx
                players[pid]["y"] += dy

            if packet["type"] == "ping":
                pong = {
                    "type": "pong",
                    "timestamp": packet["timestamp"],
                    "token": SECRET_TOKEN
                }
                server.sendto(encode_packet(pong), addr)


def broadcast_state():
    while True:
        time.sleep(SERVER_BROADCAST_RATE)

        with lock:

            packet = {
                "type": "state",
                "players": players,
                "token": SECRET_TOKEN
            }

            data = encode_packet(packet)

            for addr in clients:
                server.sendto(data, addr)


threading.Thread(target=handle_packets, daemon=True).start()
threading.Thread(target=broadcast_state, daemon=True).start()

while True:
    time.sleep(1)
