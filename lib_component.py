# Digunakan saat mengakses komponen sensor dan aktuator
# Masukan dapat berupa nomor pin GPIO, dsb

import requests
import RPi.GPIO as GPIO
import time

# Butuh RPi.GPIO (pip)
from hx711_multi import HX711
# Butuh python-smbus (apt) atau smbus2 (pip)
from RPLCD.i2c import CharLCD

class Kamera:
    def __init__(self, server, folder_simpan = "capture", format_file = "%Y-%m-%d %H:%M:%S"):
        # Alamat web server kamera
        self.server = server
        # Direktori untuk menyimpan gambar
        self.folder_simpan = folder_simpan
        # Format penamaan file gambar
        self.format_file = format_file

    def __waktu(self):
        # Berikan waktu saat ini sesuai format nama file gambar
        return time.strftime(self.format_file)
    
    def potret(self, jeda = 0):
        # Tunggu X detik sebelum potret
        if jeda > 0: time.sleep(jeda)
        # Tangkap gambar dari web server kamera
        gambar = requests.get(f"{self.server}/capture")
        if gambar.status_code == 200:
            # Simpan gambar ke folder destinasi sesuai format nama
            destinasi = f"{self.folder_simpan}/{self.__waktu()}.jpg"
            with open(destinasi, "wb") as file:
                try: file.write(gambar.content)
                except Exception:
                    # Beri tahu pengguna bila gagal menyimpan gambar
                    print("Destinasi gambar tidak bisa diakses atau ditulis...")
                    return None
            # Kembalikan path file gambar yang tersimpan
            return destinasi
        else:
            # Beri tahu pengguna bila server tidak dapat diakses
            print(f"Server kamera tidak dapat diakses (error {gambar.status_code})...")
            return None

class Buzzer:
    def __init__(self, pin):
        self.pin = pin
        # Nomor GPIO (bukan nomor pin) sebagai acuan
        GPIO.setmode(GPIO.BCM)
        # Set pin buzzer sebagai output
        GPIO.setup(self.pin, GPIO.OUT)

    def __del__(self):
        # Bersihkan GPIO setelah selesai
        try: GPIO.cleanup()
        except Exception: pass
    
    def bunyi(self, ulang = 1, jeda_nyala = 0.5, jeda_mati = 0.3):
        # Nyalakan buzzer berulang-ulang (jika dibutuhkan)
        for _ in range(ulang):
            # Nyalakan buzzer sesuai jeda nyala
            GPIO.output(self.pin, GPIO.HIGH)
            time.sleep(jeda_nyala)
            # Matikan buzzer sesuai jeda mati
            GPIO.output(self.pin, GPIO.LOW)
            time.sleep(jeda_mati)

class LoadCell:
    def __init__(self, dout_pin, sck_pin, rasio = 0):
        # Nomor GPIO (bukan nomor pin) sebagai acuan
        GPIO.setmode(GPIO.BCM)
        # Inisialisasi modul HX711
        self.hx711 = HX711(dout_pin, sck_pin, 128, "A", False, "CRITICAL")
        # Reset pin SCK sebelum memulai pembacaan
        self.hx711.reset()
        # Set berat yang terbaca saat ini sebagai titik nol
        input("Kosongkan beban pada timbangan dan tekan ENTER...")
        self.hx711.zero()

        if rasio == 0:
            # Kalibrasi sensor berat jika rasio belum diketahui
            kalibrasi = str(input("Ingin kalibrasi sensor berat (Y/N)? "))
            if kalibrasi == "Y" or kalibrasi == "y": self.kalibrasi()
        else:
            # Set rasio kalibrasi bila sudah diketahui
            self.hx711.set_weight_multiples(rasio)

    def __del__(self):
        # Bersihkan GPIO setelah selesai
        try: GPIO.cleanup()
        except Exception: pass
    
    def __timbang_mentah(self, hitung = 30):
        # Hitung performa (waktu) pengukuran berat
        mulai = time.perf_counter()
        # Ukur berat mentah dari beban saat ini sampai terbaca
        while self.hx711.read_raw(hitung) == None:
            durasi = int(round(time.perf_counter() - mulai))
            print(f"Berat tidak terbaca ({durasi} detik), mencoba ulang...")

    def kalibrasi(self):
        # Minta pengguna untuk meletakkan beban yang beratnya diketahui
        input("Letakkan beban pada timbangan dan tekan ENTER...")
        # Ukur berat mentah dari beban saat ini sampai terbaca
        self.__timbang_mentah()
        # Dapatkan hasil pengukuran berat mentah terakhir
        berat_mentah = self.hx711.get_raw()
        print(f"Berat mentah: {berat_mentah}")
        # Minta pengguna memasukkan berat beban sesungguhnya
        berat_asli = float(input("Masukkan berat sesungguhnya (gram): "))
        # Lakukan kalibrasi nilai berat untuk pengukuran selanjutnya
        rasio = round(berat_mentah / berat_asli, 3)
        self.hx711.set_weight_multiples(rasio)
        print(f"Rasio kalibrasi: {rasio}")

    def timbang(self):
        # Ukur berat mentah dari beban saat ini sampai terbaca
        self.__timbang_mentah()
        # Berikan hasil pengukuran berat terakhir (berat mentah dibagi rasio)
        return round(self.hx711.get_weight(), 3)

class LCD:
    # Jenis yang digunakan umumnya PCF8574 (lihat pada bagian chip I2C)
    def __init__(self, kolom = 16, baris = 2, alamat = 0x27, jenis = "PCF8574"):
        self.lcd = CharLCD(jenis, alamat, None, 1, kolom, baris, backlight_enabled = False)

    def __del__(self):
        # Bersihkan layar dan tutup koneksi
        self.lcd.close(True)

    def tulis(self, teks, baris = 1):
        # Tulis teks pada baris yang sesuai
        self.lcd.cursor_pos = (baris - 1, 0)
        self.lcd.write_string(teks)
    
    def tulis_nyala(self, teks, baris = 1, jeda = 5, hapus = True):
        # Tulis teks pada baris yang sesuai
        self.lcd.cursor_pos = (baris - 1, 0)
        self.lcd.write_string(teks)
        # Nyalakan backlight layar selama X detik
        self.nyala(jeda)
        # Hapus kembali layar bila diminta
        if hapus: self.lcd.clear()

    def nyala(self, jeda = 0):
        # Nyalakan backlight layar
        self.lcd.backlight_enabled = True
        # Matikan kembali setelah jeda tertentu (detik)
        if jeda > 0:
            time.sleep(jeda)
            self.lcd.backlight_enabled = False

    def mati(self, hapus = False):
        # Matikan backlight layar
        self.lcd.backlight_enabled = False
        if hapus: self.lcd.clear()