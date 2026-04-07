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
bullets = []
lock = threading.Lock()
seq = 0

# --- Network Metrics Variables ---
latency = 0.0
ALPHA = 0.125
jitter = 0.0
last_rtt = 0.0  

sent_pings = {}
ping_seq = 0
packets_sent = 0
packets_lost = 0
packet_loss_rate = 0.0

bytes_received = 0
last_throughput_calc = time.time()
throughput_kbps = 0.0

# Open a CSV log file to demonstrate the math
demo_log = open("network_math_demo.csv", "w")
demo_log.write("Seq,RTT,Old_Latency,New_Latency,Transit_Diff,Old_Jitter,New_Jitter\n")
# ---------------------------------

pygame.init()
screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
font = pygame.font.SysFont(None, 24)

player_x = 100
player_y = 100

def smooth_move(local, server, alpha=0.5):
    """Blend local predicted position toward server position"""
    return local * (1 - alpha) + server * alpha

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
    global latency, players, bullets, jitter, last_rtt, bytes_received, sent_pings
    while True:
        data, _ = sock.recvfrom(4096)
        bytes_received += len(data)
        
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
                new_bullets = []
                parsing_bullets = False
                
                for p in packet[1:-1]:
                    if p == "BULLETS":
                        parsing_bullets = True
                        continue
                    
                    if not parsing_bullets:
                        pid, x, y, r, g, b = p.split(",")
                        new_players[pid] = {
                            "x": int(x),
                            "y": int(y),
                            "r": int(r),
                            "g": int(g),
                            "b": int(b),
                        }
                    else:
                        bx, by = p.split(",")
                        new_bullets.append({"x": float(bx), "y": float(by)})
                        
                with lock:
                    players = new_players
                    bullets = new_bullets
                    
            elif ptype == "PONG":
                recv_seq = int(packet[1])
                ts = float(packet[2])
                rtt = (time.time() - ts) * 1000
                
                # Mark packet as successfully received
                if recv_seq in sent_pings:
                    del sent_pings[recv_seq]

                # --- 1. Step-by-Step Latency (EWMA) ---
                old_latency = latency
                if latency == 0.0:
                    latency = rtt
                else:
                    latency = (rtt * ALPHA) + (old_latency * (1.0 - ALPHA))

                # --- 2. Step-by-Step Jitter (RFC 3550) ---
                old_jitter = jitter
                transit_diff = 0.0
                
                if last_rtt != 0.0:
                    transit_diff = abs(rtt - last_rtt)
                    jitter = old_jitter + (transit_diff - old_jitter) / 16.0
                
                last_rtt = rtt

                # --- 3. Log the Math ---
                demo_log.write(f"{recv_seq},{rtt:.4f},{old_latency:.4f},{latency:.4f},{transit_diff:.4f},{old_jitter:.4f},{jitter:.4f}\n")
                demo_log.flush() # Force write to disk immediately
        except:
            pass

def send_move(dx, dy):
    global seq
    packet = encode_move("0", dx, dy, seq, SECURITY_KEY)
    seq += 1
    sock.sendto(packet, server_addr)

def send_shoot(dx, dy):
    global seq
    packet = encode_shoot("0", dx, dy, seq, SECURITY_KEY)
    seq += 1
    sock.sendto(packet, server_addr)

def ping_server():
    global ping_seq, packets_sent
    while True:
        packet = encode_ping(ping_seq, time.time(), SECURITY_KEY)
        sock.sendto(packet, server_addr)
        sent_pings[ping_seq] = time.time()
        ping_seq += 1
        packets_sent += 1
        time.sleep(1)

threading.Thread(target=receive_loop, daemon=True).start()
threading.Thread(target=ping_server, daemon=True).start()

ssl_handshake()

running = True
clock = pygame.time.Clock()

# Track last faced direction for shooting (default face right)
last_dir_x = 1
last_dir_y = 0
shoot_cooldown = 0

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
        # Normalize direction for shooting
        last_dir_x = 1 if dx > 0 else (-1 if dx < 0 else 0)
        last_dir_y = 1 if dy > 0 else (-1 if dy < 0 else 0)
        
        player_x += dx
        player_y += dy
        send_move(dx, dy)

    # Shooting Logic (Spacebar)
    if keys[pygame.K_SPACE] and shoot_cooldown <= 0:
        send_shoot(last_dir_x, last_dir_y)
        shoot_cooldown = 15  # Cooldown frames (15 frames at 60 FPS = 0.25 seconds)

    if shoot_cooldown > 0:
        shoot_cooldown -= 1
        
    # --- Network Metric Calculations ---
    current_time = time.time()
    
    # 1. Packet Loss Tracking
    lost_this_frame = [s for s, ts in sent_pings.items() if current_time - ts > 1.0]
    for s in lost_this_frame:
        packets_lost += 1
        del sent_pings[s]

    if packets_sent > 0:
        packet_loss_rate = (packets_lost / packets_sent) * 100

    # 2. Throughput Calculation (kbps)
    if current_time - last_throughput_calc >= 1.0:
        throughput_kbps = (bytes_received * 8) / 1000
        bytes_received = 0
        last_throughput_calc = current_time
    # -----------------------------------

    screen.fill((30, 30, 30))
    with lock:
        # Draw Players
        for pid, p in players.items():
            if pid == "0":
                p_x = smooth_move(player_x, p["x"])
                p_y = smooth_move(player_y, p["y"])
            else:
                p_x = p["x"]
                p_y = p["y"]
                
            pygame.draw.rect(
                screen,
                (p["r"], p["g"], p["b"]),
                (p_x, p_y, PLAYER_SIZE, PLAYER_SIZE),
            )
            text = font.render(pid, True, (255, 255, 255))
            screen.blit(text, (p_x, p_y - 15))
            
        # Draw Bullets
        for b in bullets:
            pygame.draw.rect(
                screen,
                (255, 255, 255), # White bullets
                (b["x"], b["y"], 5, 5)
            )
            
    # Draw Metrics to UI
    latency_text = font.render(f"Latency (EWMA): {int(latency)} ms", True, (255, 255, 255))
    screen.blit(latency_text, (10, 10))
    
    jitter_text = font.render(f"Jitter (RFC 3550): {int(jitter)} ms", True, (255, 255, 0)) 
    screen.blit(jitter_text, (10, 30))
    
    kbps_text = font.render(f"Downlink: {throughput_kbps:.2f} kbps", True, (0, 255, 255))
    screen.blit(kbps_text, (10, 50))
    
    loss_text = font.render(f"Packet Loss: {packet_loss_rate:.1f}%", True, (255, 100, 100))
    screen.blit(loss_text, (10, 70))

    pygame.display.flip()
    clock.tick(60)

demo_log.close()
pygame.quit()
