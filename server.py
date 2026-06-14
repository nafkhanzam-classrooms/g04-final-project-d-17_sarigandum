import socket
import threading
import random
import time

# Konfigurasi Jaringan
HOST = '127.0.0.1'
PORT = 5555
RECONNECT_PREFIX = "__RECONNECT__"
JOIN_PREFIX = "__JOIN__"
RECONNECT_TIMEOUT = 120
RECONNECT_HANDSHAKE_TIMEOUT = 3

# Struktur Data Game
list_kata_rahasia = ["GAJAH", "KUCING", "MOBIL", "RUMAH", "BUKU"]
daftar_client = []
nama_pemain = {}
penebak_conn = None

# Sistem lobby
room_master = None
game_started = False
player_count = 0

# Reconnect: simpan slot pemain yang terputus sementara
pemain_terputus = {}
reconnect_timers = {}

def random_word():
    return random.choice(list_kata_rahasia)

KATA_RAHASIA = random_word()

def broadcast(pesan, pengirim_conn=None, status_sistem=False):
    """Mengirim pesan ke semua client yang terhubung"""
    for client in list(daftar_client):
        try:
            client.send(pesan.encode('utf-8'))
        except:
            if client in daftar_client:
                daftar_client.remove(client)
            if client in nama_pemain:
                del nama_pemain[client]

def get_unique_name(requested_name):
    """Memastikan tidak ada duplikat nama di dalam server."""
    existing_names = list(nama_pemain.values()) + list(pemain_terputus.keys())
    if requested_name not in existing_names:
        return requested_name
    
    counter = 1
    while f"{requested_name}_{counter}" in existing_names:
        counter += 1
    return f"{requested_name}_{counter}"

def cancel_reconnect_timer(player_name):
    timer = reconnect_timers.pop(player_name, None)
    if timer:
        timer.cancel()

def on_reconnect_timeout(player_name):
    reconnect_timers.pop(player_name, None)
    if player_name not in pemain_terputus:
        return

    del pemain_terputus[player_name]
    if game_started:
        reset_game()
        broadcast(f"SISTEM: {player_name} tidak reconnect. Game di-reset ke LOBBY.\n")

def schedule_reconnect_timeout(player_name):
    cancel_reconnect_timer(player_name)
    timer = threading.Timer(RECONNECT_TIMEOUT, on_reconnect_timeout, args=[player_name])
    timer.daemon = True
    timer.start()
    reconnect_timers[player_name] = timer

def save_disconnected_player(conn, player_name):
    pemain_terputus[player_name] = {
        'disconnect_time': time.time(),
        'was_room_master': conn == room_master,
        'was_penebak': conn == penebak_conn and game_started,
    }
    if game_started:
        schedule_reconnect_timeout(player_name)
        broadcast(f"SISTEM: {player_name} terputus. Menunggu reconnect ({RECONNECT_TIMEOUT}s)...\n")
    else:
        broadcast(f"SISTEM: {player_name} terputus.\n")

def try_restore_player(conn, player_name):
    """Kembalikan pemain lama ke lobby/game dengan socket baru."""
    global room_master, penebak_conn

    if player_name not in pemain_terputus:
        return False

    info = pemain_terputus.pop(player_name)
    cancel_reconnect_timer(player_name)

    if time.time() - info['disconnect_time'] > RECONNECT_TIMEOUT:
        return False

    nama_pemain[conn] = player_name
    daftar_client.append(conn)

    if info['was_room_master']:
        room_master = conn
    if info['was_penebak'] and game_started:
        penebak_conn = conn

    try:
        conn.send(f"SISTEM: ID_PEMAIN={player_name}\n".encode('utf-8'))
        conn.send(f"SISTEM: Berhasil reconnect sebagai {player_name}!\n".encode('utf-8'))

        if game_started:
            if conn == penebak_conn:
                conn.send("SISTEM: Peran kamu adalah [PENEBAK]. Tebak kata rahasianya!\n".encode('utf-8'))
            else:
                conn.send(f"SISTEM: Peran kamu adalah [PENJAWAB]. Kata rahasia: {KATA_RAHASIA}\n".encode('utf-8'))
        elif conn == room_master:
            conn.send(f"SISTEM: Kamu tetap menjadi ROOM MASTER ({player_name}).\n".encode('utf-8'))
        else:
            conn.send(f"SISTEM: Selamat datang kembali {player_name} di Lobby.\n".encode('utf-8'))
    except Exception as e:
        print(f"[ERROR RECONNECT] Gagal mengirim status reconnect: {e}")
        if conn in daftar_client:
            daftar_client.remove(conn)
        if conn in nama_pemain:
            del nama_pemain[conn]
        return False

    broadcast(f"SISTEM: {player_name} telah reconnect. Total pemain: {len(daftar_client)}\n")
    return True

def mulai_game_logik():
    """Menginisialisasi peran secara acak (plotting) dan memulai game"""
    global KATA_RAHASIA, penebak_conn, game_started

    if len(daftar_client) < 2:
        broadcast("SISTEM: Tidak dapat memulai game. Minimal dibutuhkan 2 pemain!\n")
        return False

    game_started = True
    KATA_RAHASIA = random_word()
    penebak_conn = random.choice(daftar_client)

    broadcast("\n=========================================\n")
    broadcast("🎮 GAME TELAH DIMULAI! Peran telah dibagikan secara acak.\n")

    for conn in daftar_client:
        try:
            nama = nama_pemain.get(conn, "Unknown Player")
            if conn == penebak_conn:
                peran = "PENEBAK"
                conn.send(f"\nSISTEM: Peran kamu adalah [{peran}]. Tebak kata rahasianya!\n".encode('utf-8'))
            else:
                peran = "PENJAWAB"
                conn.send(f"\nSISTEM: Peran kamu adalah [{peran}]. Kata rahasia: {KATA_RAHASIA}\n".encode('utf-8'))
        except Exception as e:
            pass

    broadcast("=========================================\n")
    return True

def proses_pesan(conn, current_player_name, data):
    """Memproses satu pesan dari client."""
    global room_master

    if not data:
        return False

    if not game_started:
        if conn == room_master and data.upper() == "PLAY":
            mulai_game_logik()
            return True
        if data.upper() == "PLAY":
            conn.send("SISTEM: Hanya ROOM MASTER yang dapat memulai game!\n".encode('utf-8'))
            return True

        format_pesan = f"[LOBBY] {current_player_name}: {data}\n"
        print(format_pesan.strip())
        broadcast(format_pesan)
        return True

    if conn == penebak_conn:
        if KATA_RAHASIA in data.upper():
            broadcast(f"\n🎉 [GAME OVER] {current_player_name} (PENEBAK) BERHASIL MENEBAK! Jawabannya adalah: {KATA_RAHASIA}\n")
            reset_game()
            return True
        nama_pengirim = "Penebak"
    else:
        nama_pengirim = "Penjawab"

    format_pesan = f"[{nama_pengirim} - {current_player_name}]: {data}\n"
    print(format_pesan.strip())
    broadcast(format_pesan)
    return True

def handle_client(conn, addr, is_reconnect=False, custom_name=None, leftover_data=""):
    global penebak_conn, room_master, game_started, player_count

    if is_reconnect:
        current_player_name = nama_pemain.get(conn)
        if not current_player_name:
            conn.close()
            return
    else:
        if not custom_name:
            player_count += 1
            custom_name = f"Player {player_count}"
        
        current_player_name = get_unique_name(custom_name)
        nama_pemain[conn] = current_player_name

        print(f"[KONEKSI BARU] {addr} terhubung sebagai {current_player_name}.")
        conn.send(f"SISTEM: ID_PEMAIN={current_player_name}\n".encode('utf-8'))

        if room_master is None:
            room_master = conn
            conn.send(f"SISTEM: Kamu adalah ROOM MASTER ({current_player_name}). \nKetik 'PLAY' untuk memulai game jika pemain sudah cukup!\n".encode('utf-8'))
        else:
            conn.send(f"SISTEM: Selamat datang {current_player_name} di Lobby. Menunggu Room Master memulai game...\n".encode('utf-8'))

        broadcast(f"SISTEM: {current_player_name} bergabung ke lobby. Total pemain: {len(daftar_client)}\n", conn)

    # Tangani sisa data yang terbawa saat initial handshake
    if leftover_data:
        for data in leftover_data.split('\n'):
            data = data.strip()
            if not data: continue
            if data.startswith("__PING__"):
                pong_response = data.replace("__PING__", "__PONG__") + "\n"
                try: conn.send(pong_response.encode('utf-8'))
                except: pass
            else:
                proses_pesan(conn, current_player_name, data)

    while True:
        try:
            raw_data = conn.recv(1024).decode('utf-8')
            if not raw_data:
                break
                
            for data in raw_data.split('\n'):
                data = data.strip()
                if not data:
                    continue
                # Intercept paket ping agar tidak mencemari chat
                if data.startswith("__PING__"):
                    pong_response = data.replace("__PING__", "__PONG__") + "\n"
                    conn.send(pong_response.encode('utf-8'))
                else:
                    proses_pesan(conn, current_player_name, data)
        except:
            break

    print(f"[LEAVE] {current_player_name} terputus.")
    if conn in daftar_client:
        daftar_client.remove(conn)

    was_room_master = conn == room_master
    save_disconnected_player(conn, current_player_name)

    if conn in nama_pemain:
        del nama_pemain[conn]

    if was_room_master:
        if daftar_client:
            room_master = daftar_client[0]
            master_name = nama_pemain.get(room_master, "Player")
            room_master.send(f"SISTEM: Room Master sebelumnya keluar. Kamu ({master_name}) sekarang adalah ROOM MASTER yang baru!\n".encode('utf-8'))
            broadcast(f"SISTEM: Room Master dialihkan ke {master_name}. Total pemain: {len(daftar_client)}\n")
        else:
            room_master = None

    conn.close()

def reset_game():
    global KATA_RAHASIA, penebak_conn, game_started
    KATA_RAHASIA = random_word()
    penebak_conn = None
    game_started = False
    broadcast("SISTEM: Game di-reset ke LOBBY. Menunggu Room Master mengetik 'PLAY' untuk ronde baru.\n")

def read_initial_handshake(conn):
    """Membaca data dari client dan mengamankan pemisahan baris untuk menghindari clumping."""
    conn.settimeout(RECONNECT_HANDSHAKE_TIMEOUT)
    buffer = ""
    try:
        while "\n" not in buffer:
            chunk = conn.recv(1024).decode('utf-8')
            if not chunk: break
            buffer += chunk
    except (socket.timeout, OSError):
        pass
    finally:
        conn.settimeout(None)
    
    if "\n" in buffer:
        handshake, rest = buffer.split("\n", 1)
        return handshake.strip(), rest
    return buffer.strip(), ""

def start_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen()
    print(f"[SERVER BERJALAN] Menunggu koneksi di {HOST}:{PORT}...")

    while True:
        try:
            conn, addr = server.accept()
            initial_data, leftover_data = read_initial_handshake(conn)

            # Request Reconnect
            if initial_data.startswith(RECONNECT_PREFIX):
                player_name = initial_data[len(RECONNECT_PREFIX):].strip()
                if try_restore_player(conn, player_name):
                    print(f"[RECONNECT] {player_name} dari {addr} kembali online.")
                    thread = threading.Thread(
                        target=handle_client,
                        args=(conn, addr),
                        kwargs={'is_reconnect': True, 'leftover_data': leftover_data},
                    )
                    thread.start()
                else:
                    try: conn.send("SISTEM: Reconnect gagal. Slot sudah kadaluarsa atau tidak ditemukan.\n".encode('utf-8'))
                    except: pass
                    conn.close()
                continue

            if game_started:
                try:
                    conn.send("SISTEM: Game sudah dimulai. Silakan tunggu ronde berikutnya!\n".encode('utf-8'))
                    conn.close()
                except: pass
                continue
            
            # Request Join Baru
            custom_name = None
            if initial_data.startswith(JOIN_PREFIX):
                custom_name = initial_data[len(JOIN_PREFIX):].strip()

            daftar_client.append(conn)
            thread = threading.Thread(
                target=handle_client,
                args=(conn, addr),
                kwargs={'custom_name': custom_name, 'leftover_data': leftover_data},
            )
            thread.start()

        except KeyboardInterrupt:
            print("\n[SERVER] Mematikan server secara aman...")
            break
        except Exception as e:
            print(f"[SERVER ERROR] Terjadi masalah pada koneksi: {e}")
            break

    server.close()

if __name__ == "__main__":
    start_server()