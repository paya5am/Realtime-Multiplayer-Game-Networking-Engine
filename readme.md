# UDP Real-Time Multiplayer Game Networking Demo

## Brief Overview

This project demonstrates a **basic real-time multiplayer game networking system using UDP sockets in Python**.
A central server maintains the positions of all players, while multiple clients connect to it and send movement commands.

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

Open one or more terminals and start clients:

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
Q  - Quit
```

---

## Running on Multiple Computers

1. Find the server machine's IP address.
2. Update the `SERVER_IP` value in `config.py` on the client machines.
3. Start the server on the host machine.
4. Run clients from other machines using the server IP.

---

## Notes

* The system uses **UDP socket communication** for low-latency updates.
* The server handles **player registration and state synchronization**.
* Clients send movement commands and render the updated game state.
