import socket
import threading
import time
import ssl
import secrets
from config import *
from shared import *

server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server.bind((SERVER_IP, SERVER_PORT))
print("UDP Server started")

clients = {}       # addr -> pid
players = {}       # pid -> state
last_seen = {}     # addr -> timestamp
last_seq = {}      # pid -> last seq
session_keys = {}  # addr -> session key

lock = threading.Lock()

COLORS = [
    (255, 0, 0), (0, 255, 0), (0, 0, 255),
    (255, 255, 0), (255, 0, 255), (0, 255, 255)
]

def ssl_handshake_server():
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(certfile="server.pem", keyfile="server.key")
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((SERVER_IP, HANDSHAKE_PORT))
    s.listen(5)
    print("SSL Handshake server running")

    while True:
        conn, addr = s.accept()
        try:
            secure_conn = context.wrap_socket(conn, server_side=True)
            session_key = secrets.token_hex(16)
            with lock:
                session_keys[addr] = session_key

                # Immediately add player to players dict for immediate STATE broadcast
                if addr not in clients:
                    pid = str(len(clients) + 1)
                    color = COLORS[len(clients) % len(COLORS)]
                    clients[addr] = pid
                    players[pid] = {"x": 100, "y": 100, "r": color[0], "g": color[1], "b": color[2]}
                    last_seq[pid] = -1
                    last_seen[addr] = time.time()
                    print("New client:", pid)

            secure_conn.send(session_key.encode())
            print(f"Secure handshake with {addr}, session key: {session_key}")
        except ssl.SSLError as e:
            print(f"SSL handshake failed with {addr}: {e}")
        finally:
            conn.close()


def handle_packets():
    while True:
        data, addr = server.recvfrom(4096)
        if not simulate_network():
            continue
        packet = decode_packet(data)
        if not packet:
            continue
        try:
            ptype = packet[0]
            with lock:
                if addr not in clients:
                    continue  # ignore moves from unknown clients

                # Security check
                if addr not in session_keys or packet[-1] != session_keys[addr]:
                    continue

                pid = clients[addr]
                last_seen[addr] = time.time()

                if ptype == "MOVE":
                    seq_num = int(packet[4])
                    if seq_num <= last_seq[pid]:
                        continue
                    last_seq[pid] = seq_num

                    dx = int(packet[2])
                    dy = int(packet[3])
                    players[pid]["x"] += dx
                    players[pid]["y"] += dy

                elif ptype == "PING":
                    ts = packet[1]
                    pong = encode_pong(ts, session_keys[addr])
                    server.sendto(pong, addr)

        except Exception as e:
            print("Malformed packet ignored", e)


def broadcast_state():
    while True:
        time.sleep(SERVER_BROADCAST_RATE)
        with lock:
            for addr in clients:
                key = session_keys.get(addr)
                if key:
                    packet = encode_state(players, key)
                    server.sendto(packet, addr)


def cleanup_clients():
    while True:
        time.sleep(5)
        with lock:
            now = time.time()
            remove_addrs = [addr for addr, ts in last_seen.items() if now - ts > 10]
            for addr in remove_addrs:
                pid = clients.pop(addr)
                players.pop(pid)
                last_seq.pop(pid)
                session_keys.pop(addr)
                last_seen.pop(addr)
                print(f"Client {pid} removed due to timeout")


# Start threads
threading.Thread(target=handle_packets, daemon=True).start()
threading.Thread(target=broadcast_state, daemon=True).start()
threading.Thread(target=ssl_handshake_server, daemon=True).start()
threading.Thread(target=cleanup_clients, daemon=True).start()

while True:
    time.sleep(1)
