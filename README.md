[![Review Assignment Due Date](https://classroom.github.com/assets/deadline-readme-button-22041afd0340ce965d47ae6ef1cefeee28c7c493a6346c4f15d667ab976d596c.svg)](https://classroom.github.com/a/4SHtB1vz)

```
# 🎮 BlindGuesser: Party Game Menebak Kata

**BlindGuesser** is a real-time, multiplayer party game built with Python where players rely on deduction, communication, and custom social rules to guess a secret word. 

In this game, the server acts as the Game Master. It randomly assigns one player as the **[PENEBAK]** (Guesser) and the rest as **[PENJAWAB]** (Answerers). The Guesser must figure out the secret word by asking questions in the global chat, while the Answerers guide them. Players are encouraged to create their own custom rules socially (e.g., limiting the number of questions, setting a timer, or strictly answering with "Yes/No").

---

## ✨ Features

* **Real-Time Multiplayer Chat:** Built entirely on TCP sockets for instant messaging and guessing.
* **Graphical User Interface:** A lightweight, interactive UI built with `pygame`.
* **Automated Game Master:** The server automatically handles lobby creation, assigns the `Room Master`, distributes roles randomly, and validates the winning guess.
* **Network Resilience:** Includes an automated background Ping/Pong system to track latency (ms) and a robust **Reconnect System** that saves a disconnected player's state for up to 120 seconds so they can rejoin mid-game without disruption.
* **Dynamic Role Reassignment:** If the Room Master disconnects, the server seamlessly passes the leadership role to the next connected player.

---

## 🛠️ Requirements & Setup

Before running the game, ensure you have Python 3.x installed on your machine. You will also need to install the required GUI library.

**1. Install Dependencies**
```bash
pip install pygame

```

**2. Network Configuration (Optional)**
By default, the game runs locally. If you want to play over a LAN or the Internet, open both `server.py` and `client.py` and change the `HOST` variable from `'127.0.0.1'` to your local IPv4 address or public IP.

```python
HOST = '192.168.x.x' # Example for LAN play
PORT = 5555

```

---

## 🚀 How to Play

To start the game, you must run the server first, followed by multiple client instances.

1. **Start the Server:**
Open a terminal and run the server script. It will run silently in the background and wait for players.
```bash
python server.py

```


2. **Start the Clients (Players):**
Open separate terminals for each player and run the client script.
```bash
python client.py

```


3. **The Lobby:**
Enter your name on the login screen. The first player to join becomes the **Room Master**.
4. **Starting the Game:**
Once at least 2 players are in the lobby, the Room Master types `PLAY` in the chat and hits Enter.
5. **Gameplay:**
* **[PENEBAK]** uses the chat to ask questions and attempt to guess the word.
* **[PENJAWAB]** use the chat to answer the questions based on the group's agreed-upon social rules.
* If the **[PENEBAK]** types the exact secret word in the chat, the server detects it, announces the winner, and resets the lobby for the next round.



---

## File Architecture

### 1. `server.py`

This script is completely headless (runs in the console) and manages the central state of the game.

* **Connection Handling (`start_server` & `handle_client`):** Listens on port `5555`. It manages initial handshakes, ensures player names are unique, and isolates protocol messages (like `__PING__` or `__JOIN__`) from the chat relay.
* **Game Logic (`mulai_game_logik` & `proses_pesan`):** Selects a random word from `list_kata_rahasia`, assigns the `PENEBAK` and `PENJAWAB` roles, and reads incoming chat messages from the `PENEBAK` to check if it contains the `KATA_RAHASIA` (Secret Word).
* **Fault Tolerance (`save_disconnected_player` & `try_restore_player`):** Temporarily stores the state of players who drop connection (e.g., whether they were the Guesser or Room Master) in a dictionary and starts a background thread timer. If they reconnect within the `RECONNECT_TIMEOUT`, their session is fully restored.

### 2. `client.py`

This script handles what the player sees and interacts with. It separates network blocking operations from UI rendering to prevent the application from freezing.

* **Threaded Networking:**
* `terima_pesan`: A daemon thread that constantly listens for server broadcasts, chat messages, and `__PONG__` replies.
* `ping_loop`: A daemon thread that sends a timestamped `__PING__` to the server every 2 seconds to calculate real-time latency.
* `attempt_reconnect`: A fallback thread that attempts to re-establish a dropped connection automatically.


* **Pygame UI (`draw_login_ui` & `draw_lobby_ui`):** A 30 FPS rendering loop that displays the login box, the live chat history, player connection status, and ping.
* **Input Handling (`main`):** Captures keyboard inputs seamlessly and sends them directly to the server via the `kirim_pesan` function. Includes manual reconnect commands (`/RECONNECT`) if needed.
```
