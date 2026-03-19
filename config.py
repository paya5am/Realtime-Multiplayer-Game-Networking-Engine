
SERVER_IP = "0.0.0.0"  # Listen on all interfaces
SERVER_PORT = 9999
HANDSHAKE_PORT = 9998
SECURITY_KEY = "secure123"

CLIENT_UPDATE_RATE = 0.05 
SERVER_BROADCAST_RATE = 0.05 

PACKET_LOSS_SIMULATION = 0.0  # Simulated packet loss (0.0 to 1.0)
LATENCY_SIMULATION = 0.0     # Simulated latency in seconds
JITTER_SIMULATION = 0.1       # Maximum jitter in seconds

MOVE_SPEED = 10
WINDOW_WIDTH = 800
WINDOW_HEIGHT = 600
PLAYER_SIZE = 15

SSL_CERTFILE = "server.pem"  # ADDED
SSL_KEYFILE = "server.key"   # ADDED
