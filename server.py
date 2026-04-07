import socket
import threading
import time
import ssl
import random
from config import *
from shared import *

server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server.bind((SERVER_IP, SERVER_PORT))
print("UDP Server started")

clients = {}
players = {}
bullets = []
lock = threading.Lock()
client_last_active = {}  # packet time per client

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
            secure_conn = context.wrap_socket(conn, server_side=True)       # TLS HANDSHAKE 
            print("Secure handshake with", addr)
            secure_conn.close()
        except ssl.SSLError as e:
            print("SSL handshake failed:", e)

def handle_packets():
    global bullets
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
                        "x": random.randint(50, WINDOW_WIDTH - 50),
                        "y": random.randint(50, WINDOW_HEIGHT - 50),
                        "r": color[0],
                        "g": color[1],
                        "b": color[2],
                    }
                    print("New client:", pid)
                pid = clients[addr]
                client_last_active[addr] = time.time()  # last active
            
            if ptype == "MOVE":
                dx = int(packet[2])
                dy = int(packet[3])
                players[pid]["x"] += dx
                players[pid]["y"] += dy
            elif ptype == "SHOOT":
                dx = int(packet[2])
                dy = int(packet[3])
                b_x = players[pid]["x"] + (PLAYER_SIZE // 2)
                b_y = players[pid]["y"] + (PLAYER_SIZE // 2)
                bullets.append({"x": b_x, "y": b_y, "dx": dx, "dy": dy, "owner": pid})
            elif ptype == "PING":
                seq = packet[1]
                ts = packet[2]
                pong = encode_pong(seq, ts, SECURITY_KEY)
                server.sendto(pong, addr)
        except:
            print("Malformed packet ignored")

def update_game_logic():
    global bullets, players
    bullet_speed = 15
    bullet_size = 5
    while True:
        time.sleep(1/60.0) # Run at 60 ticks per second
        with lock:
            surviving_bullets = []
            for b in bullets:
                b['x'] += b['dx'] * bullet_speed
                b['y'] += b['dy'] * bullet_speed
                
                # Check bounds
                if 0 <= b['x'] <= WINDOW_WIDTH and 0 <= b['y'] <= WINDOW_HEIGHT:
                    hit = False
                    # Simple AABB Collision Check
                    for pid, p in players.items():
                        if pid != b['owner']:
                            if (p['x'] < b['x'] < p['x'] + PLAYER_SIZE) and \
                               (p['y'] < b['y'] < p['y'] + PLAYER_SIZE):
                                hit = True
                                # Basic consequence: teleport hit player to random spawn
                                p['x'] = random.randint(50, WINDOW_WIDTH - 50)
                                p['y'] = random.randint(50, WINDOW_HEIGHT - 50)
                                print(f"Player {pid} was hit!")
                                break
                    if not hit:
                        surviving_bullets.append(b)
            bullets = surviving_bullets

def broadcast_state():
    while True:
        time.sleep(SERVER_BROADCAST_RATE)
        with lock:
            packet = encode_state(players, bullets, SECURITY_KEY)
            for addr in clients:
                server.sendto(packet, addr)

def cleanup_clients(timeout=5):
    while True:
        time.sleep(1)
        with lock:
            to_remove = [addr for addr, last in client_last_active.items()
                         if time.time() - last > timeout]
            for addr in to_remove:
                pid = clients.pop(addr)
                players.pop(pid, None)
                client_last_active.pop(addr, None)
                # Remove bullets owned by disconnected player
                bullets[:] = [b for b in bullets if b['owner'] != pid]
                print(f"Client {pid} removed due to timeout") 

threading.Thread(target=handle_packets, daemon=True).start()
threading.Thread(target=update_game_logic, daemon=True).start()
threading.Thread(target=broadcast_state, daemon=True).start()
threading.Thread(target=ssl_handshake_server, daemon=True).start()
threading.Thread(target=cleanup_clients, daemon=True).start()

while True:
    time.sleep(1)
