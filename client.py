import socket
import threading
import pygame
import sys

# Konfigurasi Jaringan
HOST = '127.0.0.1'
PORT = 5555

# Inisialisasi Pygame
pygame.init()
SCREEN_WIDTH, SCREEN_HEIGHT = 1280, 720
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
    global koneksi_aktif
    while koneksi_aktif:
        try:
            pesan = client_socket.recv(1024).decode('utf-8')
            if not pesan:
                break
            # Simpan 10 pesan terakhir untuk ditampilkan di UI
            log_pesan.append(pesan.strip())
            if len(log_pesan) > 12:
                log_pesan.pop(0)
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
        y_offset += 25

    # Render Input Box
    pygame.draw.rect(screen, (50, 50, 50), (20, 340, 560, 40))
    input_surface = font.render(f"Input: {input_teks}", True, (255, 255, 255))
    screen.blit(input_surface, (30, 350))
    
    pygame.display.flip()

def main():
    global input_teks, koneksi_aktif
    
    # Setup Socket
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        client.connect((HOST, PORT))
    except:
        print("Gagal terhubung ke server.")
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
                        client.send(input_teks.encode('utf-8'))
                        input_teks = ""
                elif event.key == pygame.K_BACKSPACE:
                    input_teks = input_teks[:-1]
                else:
                    # Menangani input karakter
                    input_teks += event.unicode

        draw_ui()
        clock.tick(30) # Limit 30 FPS agar CPU tidak bekerja terlalu keras

    koneksi_aktif = False
    client.close()
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()