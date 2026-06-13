import socket
import threading
import random

# Konfigurasi Jaringan
HOST = '127.0.0.1'
PORT = 5555

# Struktur Data Game
list_kata_rahasia = ["GAJAH", "KUCING", "MOBIL", "RUMAH", "BUKU"] 
daftar_client = []
nama_pemain = {} # KAMUS BARU: Untuk memetakan socket client ke nama (contoh: {conn: "Player 1"})
penebak_conn = None

# Sistem lobby
room_master = None
game_started = False
player_count = 0 # Digunakan untuk increment penamaan otomatis

def random_word():
    return random.choice(list_kata_rahasia)

KATA_RAHASIA = random_word() # Pilih kata rahasia secara acak saat server mulai

def broadcast(pesan, pengirim_conn=None, status_sistem=False):
    """Mengirim pesan ke semua client yang terhubung"""
    for client in list(daftar_client): # Menggunakan list() agar aman dari race condition
        try:
            # Server mengirim teks dengan encoding UTF-8
            client.send(pesan.encode('utf-8'))
        except:
            # Hapus client jika koneksi terputus
            if client in daftar_client:
                daftar_client.remove(client)
            if client in nama_pemain:
                del nama_pemain[client]

def mulai_game_logik():
    """Menginisialisasi peran secara acak (plotting) dan memulai game"""
    global KATA_RAHASIA, penebak_conn, game_started
    
    if len(daftar_client) < 2:
        broadcast("SISTEM: Tidak dapat memulai game. Minimal dibutuhkan 2 pemain!\n")
        return False

    game_started = True
    KATA_RAHASIA = random_word()
    
    # === RANDOMIZE PEMAIN ===
    # Mengacak salah satu client dari daftar secara adil untuk menjadi Penebak
    penebak_conn = random.choice(daftar_client)

    broadcast("\n=========================================\n")
    broadcast("🎮 GAME TELAH DIMULAI! Peran telah dibagikan secara acak.\n")
    
    # === PLOTTING & LOGGING PEMAIN ===
    for conn in daftar_client:
        try:
            # Mengambil nama kustom dari dictionary berdasarkan koneksi client saat ini
            nama = nama_pemain.get(conn, "Unknown Player")
            
            if conn == penebak_conn:
                peran = "PENEBAK"
                print(f"[PLOT PERAN] {nama} di-plot sebagai PENEBAK") # Log Server
                conn.send(f"\nSISTEM: Peran kamu adalah [{peran}]. Tebak kata rahasianya!\n".encode('utf-8'))
            else:
                peran = "PENJAWAB"
                print(f"[PLOT PERAN] {nama} di-plot sebagai PENJAWAB") # Log Server
                conn.send(f"\nSISTEM: Peran kamu adalah [{peran}]. Kata rahasia: {KATA_RAHASIA}\n".encode('utf-8'))
        except Exception as e:
            print(f"[ERROR PLOTTING] Gagal mengirim peran ke client: {e}")
            
    broadcast("=========================================\n")
    return True

def handle_client(conn, addr):
    global penebak_conn, room_master, game_started, player_count
    
    # Menentukan nama player berdasarkan urutan increment player_count
    player_count += 1
    current_player_name = f"Player {player_count}"
    nama_pemain[conn] = current_player_name # Simpan ke dictionary
    
    print(f"[KONEKSI BARU] {addr} terhubung sebagai {current_player_name}.")

    # Penentuan Room Master (Pemain pertama yang masuk lobby)
    if room_master is None:
        room_master = conn
        conn.send(f"SISTEM: Kamu adalah ROOM MASTER ({current_player_name}). \nKetik 'PLAY' untuk memulai game jika pemain sudah cukup!\n".encode('utf-8'))
    else:
        conn.send(f"SISTEM: Selamat datang {current_player_name} di Lobby. Menunggu Room Master memulai game...\n".encode('utf-8'))

    broadcast(f"SISTEM: {current_player_name} bergabung ke lobby. Total pemain: {len(daftar_client)}\n", conn)

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
                    # Chatting biasa di dalam lobby menggunakan nama kustom
                    format_pesan = f"[LOBBY] {current_player_name}: {data}\n"
                    print(format_pesan.strip())
                    broadcast(format_pesan)
                    continue

            # --- FASE GAME (Setelah PLAY ditekan) ---
            if game_started:
                if conn == penebak_conn:
                    if KATA_RAHASIA in data.upper():
                        broadcast(f"\n🎉 [GAME OVER] {current_player_name} (PENEBAK) BERHASIL MENEBAK! Jawabannya adalah: {KATA_RAHASIA}\n")
                        reset_game()
                        continue
                    nama_pengirim = "Penebak"
                else:
                    nama_pengirim = "Penjawab"

                # Menampilkan gabungan peran dan nama urutan player agar info lebih jelas
                format_pesan = f"[{nama_pengirim} - {current_player_name}]: {data}\n"
                print(format_pesan.strip()) 
                broadcast(format_pesan)
            
        except:
            break

    # Penanganan jika client keluar (Disconnect)
    print(f"[LEAVE] {current_player_name} terputus.")
    if conn in daftar_client:
        daftar_client.remove(conn)
    
    # Hapus data nama dari kamus agar hemat memori
    if conn in nama_pemain:
        del nama_pemain[conn]
    
    # Jika Room Master keluar, alihkan jabatan ke orang berikutnya yang tersedia
    if conn == room_master:
        if daftar_client:
            room_master = daftar_client[0]
            master_name = nama_pemain.get(room_master, "Player")
            room_master.send(f"SISTEM: Room Master sebelumnya keluar. Kamu ({master_name}) sekarang adalah ROOM MASTER yang baru!\n".encode('utf-8'))
            broadcast(f"SISTEM: Room Master dialihkan ke {master_name}. Total pemain: {len(daftar_client)}\n")
        else:
            room_master = None

    # Jika game sedang berjalan dan ada yang keluar, reset ke lobby
    if game_started:
        broadcast(f"SISTEM: {current_player_name} keluar di tengah game. Game di-reset kembali ke Lobby.\n")
        reset_game()
        
    conn.close()

def reset_game():
    global KATA_RAHASIA, penebak_conn, game_started
    KATA_RAHASIA = random_word()
    penebak_conn = None
    game_started = False  
    broadcast("SISTEM: Game di-reset ke LOBBY. Menunggu Room Master mengetik 'PLAY' untuk ronde baru.\n")

def start_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen()
    print(f"[SERVER BERJALAN] Menunggu koneksi di {HOST}:{PORT}...")

    while True:
        try:
            conn, addr = server.accept()
            
            # Jika game sudah berjalan, langsung tolak client baru
            if game_started:
                try:
                    conn.send("SISTEM: Game sudah dimulai. Silakan tunggu ronde berikutnya!\n".encode('utf-8'))
                    conn.close()
                except:
                    pass
                continue 
                
            # Tambahkan ke daftar_client SEBELUM menjalankan thread handle_client
            daftar_client.append(conn)
            thread = threading.Thread(target=handle_client, args=(conn, addr))
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
