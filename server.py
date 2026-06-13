import socket
import threading
import random

# Konfigurasi Jaringan
HOST = '127.0.0.1'
PORT = 5555

# Struktur Data Game
list_kata_rahasia = ["GAJAH", "KUCING", "MOBIL", "RUMAH", "BUKU"] 
daftar_client = []
penebak_conn = None

#Sistem lobby
room_master = None
game_started = False

def random_word():
    return random.choice(list_kata_rahasia)

KATA_RAHASIA =  random_word() # Pilih kata rahasia secara acak saat server mulai

def broadcast(pesan, pengirim_conn=None, status_sistem=False):
    """Mengirim pesan ke semua client yang terhubung"""
    for client in daftar_client:
        try:
            # Server mengirim teks dengan encoding UTF-8
            client.send(pesan.encode('utf-8'))
        except:
            # Hapus client jika koneksi terputus
            if client in daftar_client:
                daftar_client.remove(client)

def mulai_game_logik():
    """Menginisialisasi peran dan memulai game"""
    global KATA_RAHASIA, penebak_conn, game_started
    
    if len(daftar_client) < 2:
        broadcast("SISTEM: Tidak dapat memulai game. Minimal dibutuhkan 2 pemain!\n")
        return False

    game_started = True
    KATA_RAHASIA = random_word()
    
    # Client kedua yang join (atau acak) menjadi Penebak, sisanya Penjawab
    # Di sini kita set client selain Room Master sebagai Penebak pertama agar adil, 
    # atau bisa disesuaikan dengan kebutuhan Anda.
    penebak_conn = daftar_client[1] if len(daftar_client) > 1 else daftar_client[0]

    broadcast("\n=========================================\n")
    broadcast("GAME TELAH DIMULAI! Peran telah dibagikan.\n")
    
    for conn in daftar_client:
        try:
            if conn == penebak_conn:
                peran = "PENEBAK"
                conn.send(f"\nSISTEM: Peran kamu adalah [{peran}]. Tebak kata rahasianya!\n".encode('utf-8'))
            else:
                peran = "PENJAWAB"
                conn.send(f"\nSISTEM: Peran kamu adalah [{peran}]. Kata rahasia: {KATA_RAHASIA}\n".encode('utf-8'))
        except:
            pass
            
    broadcast("=========================================\n")
    return True

def handle_client(conn, addr):
    global penebak_conn, room_master, game_started
    print(f"[KONEKSI BARU] {addr} terhubung.")
    
    # Penentuan Room Master (Pemain pertama yang masuk lobby)
    if room_master is None:
        room_master = conn
        conn.send("SISTEM: Kamu adalah ROOM MASTER. Ketik 'PLAY' untuk memulai game jika pemain sudah cukup!\n".encode('utf-8'))
    else:
        conn.send("SISTEM: Selamat datang di Lobby. Menunggu Room Master memulai game...\n".encode('utf-8'))

    broadcast(f"SISTEM: Pemain baru bergabung dari {addr}. Total pemain di lobby: {len(daftar_client)}\n", conn)

    # Loop utama untuk menerima input dari client
    while True:
        try:
            data = conn.recv(1024).decode('utf-8').strip()
            if not data:
                break
            
            # --- FASE LOBBY ---
            if not game_started:
                if conn == room_master and data.upper() == "PLAY":
                    if mulai_game_logik():
                        continue
                elif data.upper() == "PLAY":
                    conn.send("SISTEM: Hanya ROOM MASTER yang dapat memulai game!\n".encode('utf-8'))
                    continue
                else:
                    # Chatting biasa di dalam lobby
                    format_pesan = f"[LOBBY] {addr}: {data}\n"
                    print(format_pesan.strip())
                    broadcast(format_pesan)
                    continue

            # --- FASE GAME (Setelah PLAY ditekan) ---
            if game_started:
                if conn == penebak_conn:
                    if KATA_RAHASIA in data.upper():
                        broadcast(f"\n🎉 [GAME OVER] PENEBAK BERHASIL MENEBAK! Jawabannya adalah: {KATA_RAHASIA}\n")
                        reset_game()
                        continue
                    nama_pengirim = "Penebak"
                else:
                    nama_pengirim = "Penjawab"

                format_pesan = f"[{nama_pengirim}]: {data}\n"
                print(format_pesan.strip()) 
                broadcast(format_pesan)
            
        except:
            break

    # Penanganan jika client keluar (Disconnect)
    print(f"[LEAVE] {addr} terputus.")
    if conn in daftar_client:
        daftar_client.remove(conn)
    
    # Jika Room Master keluar, alihkan jabatan ke orang berikutnya yang tersedia
    if conn == room_master:
        if daftar_client:
            room_master = daftar_client[0]
            room_master.send("SISTEM: Room Master sebelumnya keluar. Kamu sekarang adalah ROOM MASTER yang baru!\n".encode('utf-8'))
            broadcast(f"SISTEM: Room Master dialihkan ke pemain lain. Total pemain: {len(daftar_client)}\n")
        else:
            room_master = None

    # Jika game sedang berjalan dan ada yang keluar, reset ke lobby
    if game_started:
        broadcast(f"SISTEM: Pemain {addr} keluar di tengah game. Game di-reset kembali ke Lobby.\n")
        reset_game()
        
    conn.close()

def reset_game():
    global KATA_RAHASIA, penebak_conn
    KATA_RAHASIA = random_word()
    penebak_conn = None
    broadcast("SISTEM: Game di-reset. Penebak baru akan dipilih saat pemain baru bergabung.\n")

def start_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen()
    print(f"[SERVER BERJALAN] Menunggu koneksi di {HOST}:{PORT}...")

    while True:
        conn, addr = server.accept()
        daftar_client.append(conn)
        
        # Jalankan thread baru untuk setiap client agar server tidak macet
        thread = threading.Thread(target=handle_client, args=(conn, addr))
        thread.start()

if __name__ == "__main__":
    start_server()