'''import socket
import threading
import time
import ssl
from config import *
from shared import *

server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server.bind((SERVER_IP, SERVER_PORT))
print("UDP Server started")

clients = {}
players = {}
lock = threading.Lock()

COLORS = [
    (255, 0, 0),
    (0, 255, 0),
    (0, 0, 255),
    (255, 255, 0),
    (255, 0, 255),
    (0, 255, 255)
]

def ssl_handshake_server():
    context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((SERVER_IP, HANDSHAKE_PORT))
    s.listen(5)
    print("SSL Handshake server running")
    while True:
        conn, addr = s.accept()
        secure_conn = context.wrap_socket(conn, server_side=True)
        print("Secure handshake with", addr)
        secure_conn.close()

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
            # SECURITY CHECK
            if packet[-1] != SECURITY_KEY:
                continue
            with lock:
                if addr not in clients:
                    pid = str(len(clients) + 1)
                    color = COLORS[len(clients) % len(COLORS)]
                    clients[addr] = pid
                    players[pid] = {
                        "x": 100,
                        "y": 100,
                        "r": color[0],
                        "g": color[1],
                        "b": color[2],
                    }
                    print("New client:", pid)
                pid = clients[addr]
            if ptype == "MOVE":
                dx = int(packet[2])
                dy = int(packet[3])
                players[pid]["x"] += dx
                players[pid]["y"] += dy
            elif ptype == "PING":
                ts = packet[1]
                pong = encode_pong(ts, SECURITY_KEY)
                server.sendto(pong, addr)
        except:
            print("Malformed packet ignored")

def broadcast_state():
    while True:
        time.sleep(SERVER_BROADCAST_RATE)
        with lock:
            packet = encode_state(players, SECURITY_KEY)
            for addr in clients:
                server.sendto(packet, addr)

threading.Thread(target=handle_packets, daemon=True).start()
threading.Thread(target=broadcast_state, daemon=True).start()
threading.Thread(target=ssl_handshake_server, daemon=True).start()  # NEW

while True:
    time.sleep(1)'''
    
import socket
import threading
import time
import ssl
from config import *
from shared import *

server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server.bind((SERVER_IP, SERVER_PORT))
print("UDP Server started")

clients = {}
players = {}
lock = threading.Lock()
client_last_active = {}  # ADDED: track last packet time per client

COLORS = [
    (255, 0, 0),
    (0, 255, 0),
    (0, 0, 255),
    (255, 255, 0),
    (255, 0, 255),
    (0, 255, 255)
]

def ssl_handshake_server():
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(certfile=SSL_CERTFILE, keyfile=SSL_KEYFILE)
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((SERVER_IP, HANDSHAKE_PORT))
    s.listen(5)
    print("SSL Handshake server running")
    while True:
        conn, addr = s.accept()
        try:
            secure_conn = context.wrap_socket(conn, server_side=True)
            print("Secure handshake with", addr)
            secure_conn.close()
        except ssl.SSLError as e:
            print("SSL handshake failed:", e)

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
            if packet[-1] != SECURITY_KEY:
                continue
            with lock:
                if addr not in clients:
                    pid = str(len(clients) + 1)
                    color = COLORS[len(clients) % len(COLORS)]
                    clients[addr] = pid
                    players[pid] = {
                        "x": 100,
                        "y": 100,
                        "r": color[0],
                        "g": color[1],
                        "b": color[2],
                    }
                    print("New client:", pid)
                pid = clients[addr]
                client_last_active[addr] = time.time()  # ADDED: update last active
            if ptype == "MOVE":
                dx = int(packet[2])
                dy = int(packet[3])
                players[pid]["x"] += dx
                players[pid]["y"] += dy
            elif ptype == "PING":
                ts = packet[1]
                pong = encode_pong(ts, SECURITY_KEY)
                server.sendto(pong, addr)
        except:
            print("Malformed packet ignored")

def broadcast_state():
    while True:
        time.sleep(SERVER_BROADCAST_RATE)
        with lock:
            packet = encode_state(players, SECURITY_KEY)
            for addr in clients:
                server.sendto(packet, addr)

# Cleanup inactive clients
def cleanup_clients(timeout=5):  # ADDED
    while True:
        time.sleep(1)
        with lock:
            to_remove = [addr for addr, last in client_last_active.items()
                         if time.time() - last > timeout]
            for addr in to_remove:
                pid = clients.pop(addr)
                players.pop(pid, None)
                client_last_active.pop(addr, None)
                print(f"Client {pid} removed due to timeout")  # ADDED

threading.Thread(target=handle_packets, daemon=True).start()
threading.Thread(target=broadcast_state, daemon=True).start()
threading.Thread(target=ssl_handshake_server, daemon=True).start()
threading.Thread(target=cleanup_clients, daemon=True).start()  # ADDED

while True:
    time.sleep(1)
