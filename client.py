
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
seq = 0

pygame.init()
screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
font = pygame.font.SysFont(None, 24)

player_x = 100
player_y = 100

lock = threading.Lock()

def ssl_handshake():
    context = ssl.create_default_context()
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    secure_sock = context.wrap_socket(s, server_hostname=SERVER_IP)
    try:
        secure_sock.connect((SERVER_IP, HANDSHAKE_PORT))
        print("SSL handshake done")
    except:
        print("SSL handshake failed")
    secure_sock.close()


def receive_loop():
    global latency, players

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
                latency = (time.time() - float(packet[1])) * 1000

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
ssl_handshake()  # NEW

running = True
clock = pygame.time.Clock()

while running:

    dx = 0
    dy = 0

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    keys = pygame.key.get_pressed()

    if keys[pygame.K_w]: dy = -MOVE_SPEED
    if keys[pygame.K_s]: dy = MOVE_SPEED
    if keys[pygame.K_a]: dx = -MOVE_SPEED
    if keys[pygame.K_d]: dx = MOVE_SPEED
    if keys[pygame.K_q]: running = False

    if dx or dy:
        player_x += dx
        player_y += dy
        send_move(dx, dy)

    screen.fill((30, 30, 30))

    with lock:
        for pid, p in players.items():
            pygame.draw.rect(
                screen,
                (p["r"], p["g"], p["b"]),
                (p["x"], p["y"], PLAYER_SIZE, PLAYER_SIZE),
            )

            text = font.render(pid, True, (255, 255, 255))
            screen.blit(text, (p["x"], p["y"] - 15))

    latency_text = font.render(f"Latency: {int(latency)} ms", True, (255, 255, 255))
    screen.blit(latency_text, (10, 10))

    pygame.display.flip()
    clock.tick(60)

pygame.quit()
