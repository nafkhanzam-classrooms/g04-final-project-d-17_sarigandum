import socket
import threading
import pygame
import sys
import time

# Konfigurasi Jaringan
HOST = '127.0.0.1'
PORT = 5555
RECONNECT_PREFIX = "__RECONNECT__"
JOIN_PREFIX = "__JOIN__"
RECONNECT_INTERVAL = 3

# Inisialisasi Pygame
pygame.init()
SCREEN_WIDTH, SCREEN_HEIGHT = 800, 500
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Tebak Kata - Multiplayer Lobby")
font = pygame.font.SysFont("Arial", 20)
clock = pygame.time.Clock()

# State Global
log_pesan = []
input_teks = ""
koneksi_aktif = False
sedang_reconnect = False
status_koneksi = "Terputus"
nama_pemain_lokal = ""
client_socket = None
client_lock = threading.Lock()
receiver_thread = None
ping_ms = 0
app_state = "LOGIN" 

def tambah_log(pesan):
    global log_pesan
    log_pesan.append(pesan)
    if len(log_pesan) > 18:
        log_pesan = log_pesan[-18:]

def terima_pesan(sock):
    """Thread untuk menerima data dari server."""
    global koneksi_aktif, nama_pemain_lokal, status_koneksi, ping_ms, app_state

    while koneksi_aktif:
        try:
            pesan = sock.recv(1024).decode('utf-8')
            if not pesan:
                print("[INFO] Server memutuskan koneksi.")
                break

            for baris in pesan.split('\n'):
                baris = baris.strip()
                if not baris:
                    continue
                
                # Handling jika server baru saja direstart secara penuh
                if baris.startswith("SISTEM: Reconnect gagal"):
                    tambah_log(baris)
                    app_state = "LOGIN"
                    koneksi_aktif = False
                    break

                # Tangkap respon PONG untuk kalkulasi latensi
                if baris.startswith("__PONG__"):
                    try:
                        ts = float(baris.split("__PONG__")[1])
                        ping_ms = int((time.time() - ts) * 1000)
                    except ValueError:
                        pass
                    continue

                if baris.startswith("SISTEM: ID_PEMAIN="):
                    nama_pemain_lokal = baris.split("ID_PEMAIN=", 1)[1].strip()
                    continue
                
                tambah_log(baris)
        except OSError:
            break

    if koneksi_aktif:
        koneksi_aktif = False
        status_koneksi = "Terputus"
        ping_ms = 0
        tambah_log("[INFO] Koneksi terputus. Mencoba reconnect otomatis...")

def start_receiver(sock):
    global receiver_thread
    receiver_thread = threading.Thread(target=terima_pesan, args=(sock,))
    receiver_thread.daemon = True
    receiver_thread.start()

def ping_loop():
    """Thread background untuk mengirim ping berkala."""
    global ping_ms
    while True:
        if koneksi_aktif and client_socket:
            try:
                with client_lock:
                    client_socket.send(f"__PING__{time.time()}\n".encode('utf-8'))
            except OSError:
                ping_ms = 0
        time.sleep(2)

def connect_to_server(is_reconnect=False):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((HOST, PORT))
    if is_reconnect and nama_pemain_lokal:
        sock.send(f"{RECONNECT_PREFIX}{nama_pemain_lokal}\n".encode('utf-8'))
    elif nama_pemain_lokal:
        sock.send(f"{JOIN_PREFIX}{nama_pemain_lokal}\n".encode('utf-8'))
    return sock

def attempt_reconnect():
    """Coba hubungkan ulang ke server sampai berhasil."""
    global client_socket, koneksi_aktif, sedang_reconnect, status_koneksi

    if sedang_reconnect:
        return

    sedang_reconnect = True
    while sedang_reconnect and not koneksi_aktif:
        status_koneksi = "Menghubungkan ulang..."
        try:
            new_sock = connect_to_server(is_reconnect=True)
            with client_lock:
                if client_socket:
                    try:
                        client_socket.close()
                    except OSError:
                        pass
                client_socket = new_sock

            koneksi_aktif = True
            status_koneksi = "Terhubung"
            start_receiver(new_sock)
            if nama_pemain_lokal:
                tambah_log(f"[INFO] Reconnect berhasil sebagai {nama_pemain_lokal}.")
            else:
                tambah_log("[INFO] Terhubung ke server.")
            sedang_reconnect = False
            return
        except OSError:
            time.sleep(RECONNECT_INTERVAL)

    sedang_reconnect = False

def draw_login_ui():
    screen.fill((40, 45, 50))
    title_surface = font.render("Selamat Datang di Tebak Kata", True, (255, 255, 255))
    prompt_surface = font.render("Masukkan Nama Anda:", True, (200, 200, 200))
    
    screen.blit(title_surface, (SCREEN_WIDTH//2 - title_surface.get_width()//2, 150))
    screen.blit(prompt_surface, (SCREEN_WIDTH//2 - prompt_surface.get_width()//2, 220))

    # Input Box
    input_box_rect = pygame.Rect(SCREEN_WIDTH//2 - 150, 260, 300, 40)
    pygame.draw.rect(screen, (30, 30, 30), input_box_rect)
    pygame.draw.rect(screen, (100, 150, 255), input_box_rect, 2)
    
    name_surface = font.render(input_teks, True, (255, 255, 255))
    screen.blit(name_surface, (input_box_rect.x + 10, input_box_rect.y + 10))

    info_surface = font.render("Tekan ENTER untuk bergabung", True, (150, 150, 150))
    screen.blit(info_surface, (SCREEN_WIDTH//2 - info_surface.get_width()//2, 320))

    pygame.display.flip()

def draw_lobby_ui():
    screen.fill((30, 30, 30))

    # Status & Ping Bar
    status_surface = font.render(f"Status: {status_koneksi} | Nama: {nama_pemain_lokal}", True, (150, 200, 255))
    ping_warna = (100, 255, 100) if ping_ms < 100 else (255, 200, 50) if ping_ms < 200 else (255, 100, 100)
    ping_surface = font.render(f"Ping: {ping_ms} ms", True, ping_warna)
    
    screen.blit(status_surface, (20, 10))
    screen.blit(ping_surface, (SCREEN_WIDTH - ping_surface.get_width() - 20, 10))

    # Pemisah atas
    pygame.draw.line(screen, (100, 100, 100), (20, 40), (SCREEN_WIDTH - 20, 40))

    # Log Area
    y_offset = 50
    for pesan in log_pesan:
        text_surface = font.render(pesan, True, (200, 200, 200))
        screen.blit(text_surface, (20, y_offset))
        y_offset += 22

    # Input Area
    input_box_y = SCREEN_HEIGHT - 60
    pygame.draw.rect(screen, (30, 30, 30), (0, input_box_y - 10, SCREEN_WIDTH, 70))
    pygame.draw.rect(screen, (50, 50, 50), (20, input_box_y, SCREEN_WIDTH - 40, 40))
    input_surface = font.render(f"Input: {input_teks}", True, (255, 255, 255))
    screen.blit(input_surface, (30, input_box_y + 10))

    pygame.display.flip()

def kirim_pesan(teks):
    global koneksi_aktif
    with client_lock:
        if not client_socket or not koneksi_aktif:
            tambah_log("[ERROR] Tidak terhubung ke server.")
            return False
        try:
            client_socket.send((teks + "\n").encode('utf-8'))
            return True
        except OSError:
            koneksi_aktif = False
            tambah_log("[ERROR] Gagal mengirim data, koneksi terputus.")
            return False

def mulai_koneksi(nama_yang_dipilih):
    global client_socket, koneksi_aktif, status_koneksi, app_state, nama_pemain_lokal
    nama_pemain_lokal = nama_yang_dipilih
    try:
        client_socket_local = connect_to_server(is_reconnect=False)
        with client_lock:
            client_socket = client_socket_local
        koneksi_aktif = True
        status_koneksi = "Terhubung"
        start_receiver(client_socket_local)
        app_state = "LOBBY"
    except OSError:
        tambah_log("[ERROR] Gagal terhubung ke server. Pastikan server aktif.")
        app_state = "LOBBY"
        threading.Thread(target=attempt_reconnect, daemon=True).start()

def main():
    global input_teks, app_state, sedang_reconnect, koneksi_aktif

    # Background ping berjalan permanen
    threading.Thread(target=ping_loop, daemon=True).start()

    running = True
    while running:
        if app_state == "LOBBY" and not koneksi_aktif and not sedang_reconnect:
            threading.Thread(target=attempt_reconnect, daemon=True).start()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                sedang_reconnect = False

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    if input_teks.strip():
                        perintah = input_teks.strip()
                        
                        if app_state == "LOGIN":
                            mulai_koneksi(perintah)
                        elif app_state == "LOBBY":
                            if perintah.upper() == "/RECONNECT":
                                if koneksi_aktif:
                                    tambah_log("[INFO] Sudah terhubung ke server.")
                                else:
                                    tambah_log("[INFO] Mencoba reconnect manual...")
                                    threading.Thread(target=attempt_reconnect, daemon=True).start()
                            else:
                                kirim_pesan(perintah)
                        
                        input_teks = ""
                elif event.key == pygame.K_BACKSPACE:
                    input_teks = input_teks[:-1]
                elif len(input_teks) < 50:
                    input_teks += event.unicode

        if app_state == "LOGIN":
            draw_login_ui()
        else:
            draw_lobby_ui()
            
        clock.tick(30)

    sedang_reconnect = False
    koneksi_aktif = False
    with client_lock:
        if client_socket:
            try:
                client_socket.close()
            except OSError:
                pass
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()