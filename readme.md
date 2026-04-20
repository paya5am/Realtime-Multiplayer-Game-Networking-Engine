# UDP Real-Time Multiplayer Game Networking Demo

## Brief Overview

This project demonstrates a **basic real-time multiplayer game networking system using UDP sockets in Python**.
A central server maintains the positions of all players, while multiple clients connect to it and send movement commands.
TCP Handshake is estabilished first between server and clients, after which UDP is used to communicate packets as well as positions.

Each client controls a **player square in a simple pygame window**, and the server synchronizes player positions so that all clients can see other players moving in real time.

---

## Requirements

* Python 3.x
* pygame

Install pygame:

```
pip install pygame
```

---

## Running the Project

### 1. Start the Server

Run the server first:

```
python server.py
```

---

### 2. Run Clients

Open one or more terminals and start clients: ( ensure server ip address is present in config.py file ) 

```
python client.py
```

Each client opens a game window and represents a different player connected to the server.

---

## Player Controls

```
W  - Move Up
A  - Move Left
S  - Move Down
D  - Move Right
SPACE - Shoot Bullet
Q  - Quit
```

---

## Running on Multiple Computers

1. Find the server machine's IP address.
2. Update the `SERVER_IP` value in `config.py` on the client machines.
3. Start the server on the host machine.
4. Run clients from other machines using the server IP.

---

## Screenshots

Server Start


<img width="616" height="114" alt="image" src="https://github.com/user-attachments/assets/2f83830c-9248-4a4a-b740-d51fdb82b195" />


Client Initialization


<img width="1600" height="634" alt="image" src="https://github.com/user-attachments/assets/1247fce8-b2c1-40ca-aa45-b3dd2776d76b" />



Server Registering Clients


<img width="610" height="178" alt="image" src="https://github.com/user-attachments/assets/9a02cbfe-668e-492b-81e8-a1453348a16a" />



## Notes

* The system uses **UDP socket communication** for low-latency updates.
* **RFC 3550** is used to calculate jitter values, and latency using exponential weighted moving average.
* The server handles **player registration, state synchronization and broadcasting client positions to each other**.
* Clients send movement commands and render the updated game state.
* Different jitter and latency values can be used to effectively check performance of game under different network conditions on client side.
