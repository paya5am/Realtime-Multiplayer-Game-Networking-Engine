import socket
import threading
import time
import pygame
from config import *
from shared import *

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

server_addr = (SERVER_IP, SERVER_PORT)

players = {}
latency = 0
seq = 0
last_seq = 0

pygame.init()

screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
pygame.display.set_caption("UDP Multiplayer Demo")

font = pygame.font.SysFont(None, 24)

player_x = 100
player_y = 100

lock = threading.Lock()


def receive_loop():
    global latency, players

    while True:
        data, _ = sock.recvfrom(4096)

        if not simulate_network():
            continue

        packet = decode_packet(data)

        if packet.get("token") != SECRET_TOKEN:
            continue

        if packet["type"] == "state":
            with lock:
                players = packet["players"]

        if packet["type"] == "pong":
            latency = (time.time() - packet["timestamp"]) * 1000


def send_move(dx, dy):
    global seq

    packet = {
        "type": "move",
        "dx": dx,
        "dy": dy,
        "seq": seq,
        "token": SECRET_TOKEN
    }

    seq += 1

    sock.sendto(encode_packet(packet), server_addr)


def ping_server():
    while True:
        packet = {
            "type": "ping",
            "timestamp": time.time(),
            "token": SECRET_TOKEN
        }

        sock.sendto(encode_packet(packet), server_addr)

        time.sleep(1)


threading.Thread(target=receive_loop, daemon=True).start()
threading.Thread(target=ping_server, daemon=True).start()

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

    if dx != 0 or dy != 0:
        player_x += dx
        player_y += dy
        send_move(dx, dy)

    screen.fill((30, 30, 30))

    with lock:
        for pid, pos in players.items():
            pygame.draw.rect(
                screen,
                (0, 200, 0),
                (pos["x"], pos["y"], PLAYER_SIZE, PLAYER_SIZE),
            )

            text = font.render(pid, True, (255, 255, 255))
            screen.blit(text, (pos["x"], pos["y"] - 15))

    latency_text = font.render(f"Latency: {int(latency)} ms", True, (255, 255, 255))
    screen.blit(latency_text, (10, 10))

    pygame.display.flip()
    clock.tick(60)

pygame.quit()
