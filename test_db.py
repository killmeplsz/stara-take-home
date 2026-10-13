
from database import test_connection

if __name__ == "__main__":
    try:
        result = test_connection()
        print(f"Koneksi database berhasil! Hasil: {result}")
    except Exception as error:
        print("Koneksi database gagal.")
        print(f"Detail error: {error}")
