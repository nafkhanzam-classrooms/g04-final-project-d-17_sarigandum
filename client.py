import socket
import threading
import pygame
import sys

# Konfigurasi Jaringan
HOST = '127.0.0.1'
PORT = 5555

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
koneksi_aktif = True

def terima_pesan(client_socket):
    """Thread untuk menerima data dari server"""
    global koneksi_aktif, log_pesan
    while koneksi_aktif:
        try:
            pesan = client_socket.recv(1024).decode('utf-8')
            if not pesan:
                print("[INFO] Server memutuskan koneksi secara sengaja.")
                break
            
            # Pecah pesan jika mengandung \n
            baris_pesan = pesan.split('\n')
            for baris in baris_pesan:
                if baris.strip() or baris == "": 
                    log_pesan.append(baris)
            
            # MODIFIKASI: Ditingkatkan kapasitasnya menjadi 18 baris karena layar sekarang lebih tinggi (500px)
            if len(log_pesan) > 18:
                log_pesan = log_pesan[-18:]
                
        except:
            break
    koneksi_aktif = False

def draw_ui():
    screen.fill((30, 30, 30)) # Background gelap
    
    # Render Log Pesan (Chat Box)
    y_offset = 20
    for pesan in log_pesan:
        text_surface = font.render(pesan, True, (200, 200, 200))
        screen.blit(text_surface, (20, y_offset))
        y_offset += 22 # Jarak antar baris baru (line spacing)

    # === PERBAIKAN UTAMA: KOORDINAT DINAMIS BERDASARKAN SCREEN_HEIGHT ===
    # Membuat tinggi kotak input adaptif di posisi bawah layar (Y = 440)
    input_box_y = SCREEN_HEIGHT - 60
    
    # Gambar background kotak input agar teks chat di belakangnya tertutup rapi
    pygame.draw.rect(screen, (30, 30, 30), (0, input_box_y - 10, SCREEN_WIDTH, 70))
    
    # Kotak Input Fisik
    pygame.draw.rect(screen, (50, 50, 50), (20, input_box_y, SCREEN_WIDTH - 40, 40))
    input_surface = font.render(f"Input: {input_teks}", True, (255, 255, 255))
    screen.blit(input_surface, (30, input_box_y + 10))
    
    pygame.display.flip()

def main():
    global input_teks, koneksi_aktif
    
    # Setup Socket
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        client.connect((HOST, PORT))
    except:
        print("[ERROR] Gagal terhubung ke server. Pastikan Server sudah dinyalakan!")
        return

    # Threading untuk receiver
    thread_penerima = threading.Thread(target=terima_pesan, args=(client,))
    thread_penerima.daemon = True
    thread_penerima.start()

    running = True
    while running and koneksi_aktif:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    # Kirim pesan ke server saat Enter ditekan
                    if input_teks.strip():
                        try:
                            client.send(input_teks.encode('utf-8'))
                        except:
                            print("[ERROR] Gagal mengirim data, koneksi terputus.")
                        input_teks = ""
                elif event.key == pygame.K_BACKSPACE:
                    input_teks = input_teks[:-1]
                else:
                    # Menangani input karakter (Membatasi panjang ketikan agar tidak meluap keluar kotak)
                    if len(input_teks) < 70:
                        input_teks += event.unicode

        draw_ui()
        clock.tick(30) # Limit 30 FPS

    koneksi_aktif = False
    client.close()
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
