import socket
import threading
import time
import pygame
import ssl
from config import *
from shared import *

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server_addr = (SERVER_IP, SERVER_PORT)

players = {}
latency = 0
latency_history = [] 
seq = 0
jitter = 0  # global jitter variable

pygame.init()
screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
font = pygame.font.SysFont(None, 24)

player_x = 100
player_y = 100
lock = threading.Lock()

# -----------------client prediction -----------------
def smooth_move(local, server, alpha=0.5):
    """Blend local predicted position toward server position"""
    return local * (1 - alpha) + server * alpha
# ----------------------------------------------------

def ssl_handshake():
    context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
    context.check_hostname = False
    context.verify_mode = ssl.CERT_REQUIRED
    context.load_verify_locations(cafile=SSL_CERTFILE)

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    secure_sock = context.wrap_socket(s, server_hostname=SERVER_IP)
    try:
        secure_sock.connect((SERVER_IP, HANDSHAKE_PORT))
        print("SSL handshake done and server verified")
        secure_sock.close()
    except ssl.SSLError as e:
        print("SSL handshake failed:", e)
    except Exception as e:
        print("Connection failed:", e)

def receive_loop():
    global latency, players, latency_history, jitter 
    while True:
        data, _ = sock.recvfrom(4096)
        if not simulate_network():
            continue
        packet = decode_packet(data)
        if not packet:
            continue
        try:
            ptype = packet[0]
            if packet[-1] != SECURITY_KEY:
                continue
            if ptype == "STATE":
                new_players = {}
                for p in packet[1:-1]:
                    pid, x, y, r, g, b = p.split(",")
                    new_players[pid] = {
                        "x": int(x),
                        "y": int(y),
                        "r": int(r),
                        "g": int(g),
                        "b": int(b),
                    }
                with lock:
                    players = new_players
            elif ptype == "PONG":
                rtt = (time.time() - float(packet[1])) * 1000
                latency_history.append(rtt)
                if len(latency_history) > 50:
                    latency_history.pop(0)
                latency = sum(latency_history) / len(latency_history)
                jitter = calculate_jitter(latency_history)
        except:
            print("Bad packet")

def send_move(dx, dy):
    global seq
    packet = encode_move("0", dx, dy, seq, SECURITY_KEY)
    seq += 1
    sock.sendto(packet, server_addr)

def ping_server():
    while True:
        packet = encode_ping(time.time(), SECURITY_KEY)
        sock.sendto(packet, server_addr)
        time.sleep(1)

threading.Thread(target=receive_loop, daemon=True).start()
threading.Thread(target=ping_server, daemon=True).start()

ssl_handshake()

running = True
clock = pygame.time.Clock()

while running:
    dx = 0
    dy = 0
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
    keys = pygame.key.get_pressed()
    if keys[pygame.K_w]:
        dy = -MOVE_SPEED
    if keys[pygame.K_s]:
        dy = MOVE_SPEED
    if keys[pygame.K_a]:
        dx = -MOVE_SPEED
    if keys[pygame.K_d]:
        dx = MOVE_SPEED
    if keys[pygame.K_q]:
        running = False

    if dx or dy:
        player_x += dx
        player_y += dy
        send_move(dx, dy)

    screen.fill((30, 30, 30))
    with lock:
        for pid, p in players.items():
            # -----------------prediction-----------------
            if pid == "0":
                p_x = smooth_move(player_x, p["x"])
                p_y = smooth_move(player_y, p["y"])
            else:
                p_x = p["x"]
                p_y = p["y"]
            # ---------------------------------------------
            pygame.draw.rect(
                screen,
                (p["r"], p["g"], p["b"]),
                (p_x, p_y, PLAYER_SIZE, PLAYER_SIZE),
            )
            text = font.render(pid, True, (255, 255, 255))
            screen.blit(text, (p_x, p_y - 15))
    latency_text = font.render(f"Latency: {int(latency)} ms", True, (255, 255, 255))
    screen.blit(latency_text, (10, 10))
    jitter_text = font.render(f"Jitter: {int(jitter)} ms", True, (255, 255, 0)) 
    screen.blit(jitter_text, (10, 30))
    pygame.display.flip()
    clock.tick(60)

pygame.quit()
