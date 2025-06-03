# alici.py
# flake8: noqa
import cv2
import os
import time
import sys

# Dinlenecek UDP portu
UDP_PORT = 6000


def create_output_filepath():
    """
    "alici_kayitlar" adlı klasörü oluşturur (yoksa) ve
    zaman damgalı bir .mkv dosya yolu döner.
    """
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    folder = "alici_kayitlar"
    if not os.path.exists(folder):
        os.makedirs(folder)
    filename = f"alici_video_{timestamp}.mkv"
    return os.path.join(folder, filename)


def open_pipeline():
    """
    GStreamer pipeline string’i oluşturur ve VideoCapture döner.
    Caps, RTP/H264 olduğunu belirtir.
    """
    gst_pipeline = (
        f'udpsrc port={UDP_PORT} caps="application/x-rtp,media=video,'
        'encoding-name=H264,payload=96" ! '
        'rtpjitterbuffer ! rtph264depay ! avdec_h264 ! videoconvert ! '
        'appsink sync=false'
    )
    cap = cv2.VideoCapture(gst_pipeline, cv2.CAP_GSTREAMER)
    return cap


def dinle_ve_kaydet():
    """
    Sürekli döngü: pipeline açmaya çalış, ilk kare geldiğinde pencere ve VideoWriter aç,
    canlı akışı ekrana yansıt ve dosyaya kaydet. Yayın durunca pencereyi kapat, dosyayı kapat,
    tekrar dinlemeye dön.
    """
    print(
        f"[alici.py] Port {UDP_PORT} üzerinde yayın dinleme moduna geçildi. (Çıkmak için Ctrl+C)")

    while True:
        # 1) Pipeline'ı aç
        cap = open_pipeline()
        opened = cap.isOpened()
        print(f"[alici.py] cap.isOpened() → {opened}")
        if not opened:
            cap.release()
            time.sleep(0.5)
            continue

        # 2) İlk kareyi almaya çalış
        print("[alici.py] Yayın gelmesini bekliyorum...")
        start_wait = time.time()
        first_frame = None
        while True:
            ret, frame = cap.read()
            print(f"[alici.py] cap.read() döndü: ret={ret}")
            if ret:
                first_frame = frame
                break
            # 10 sn boyunca kare gelmezse pipeline'ı yeniden aç
            if time.time() - start_wait > 10.0:
                cap.release()
                print(
                    "[alici.py] 10 saniyedir kare gelmedi; pipeline yeniden açılıyor...")
                time.sleep(0.2)
                cap = open_pipeline()
                start_wait = time.time()
            else:
                time.sleep(0.1)

        # 3) İlk kare alındı: kayıt ve pencereyi aç
        frame_h, frame_w = first_frame.shape[:2]
        out_path = create_output_filepath()
        print(
            f"[alici.py] Yayın başladığı tespit edildi. Kayıt açılıyor: {out_path}")

        fourcc = cv2.VideoWriter_fourcc(*"X264")
        writer = cv2.VideoWriter(out_path, fourcc, 20, (frame_w, frame_h))
        if not writer.isOpened():
            print("[alici.py] Uyarı: X264 codec açılamadı. MJPG ile kaydedilecek.")
            fourcc_mjpg = cv2.VideoWriter_fourcc(*"MJPG")
            writer = cv2.VideoWriter(
                out_path, fourcc_mjpg, 20, (frame_w, frame_h))
            if not writer.isOpened():
                print(
                    "[alici.py] Hata: Kayıt için hiçbir codec açılamadı. Dinleme moduna dönülüyor.")
                cap.release()
                continue

        # İlk kareyi pencereye ve dosyaya yaz
        cv2.imshow("Alici - Live Preview", first_frame)
        writer.write(first_frame)
        print("[alici.py] Canlı yayın penceresi açıldı. 'q' tuşuna basarak erken sonlandırabilirsiniz.")

        # 4) Canlı akış döngüsü: ret=False olana veya 'q' tuşu gelene kadar devam
        while True:
            ret, frame = cap.read()
            if not ret:
                print("[alici.py] Yayın sona erdi veya kare alınamıyor.")
                break

            cv2.imshow("Alici - Live Preview", frame)
            writer.write(frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                print("[alici.py] 'q' tuşuna basıldı. Kayıt ve pencere kapanıyor.")
                break

        # 5) Kaynakları temizle, pencereyi kapat, dosyayı tamamla
        cap.release()
        writer.release()
        cv2.destroyAllWindows()
        print(f"[alici.py] Yayın kaydedildi: {out_path}")
        print("[alici.py] Dinleme moduna geri dönülüyor...\n")


if __name__ == "__main__":
    try:
        dinle_ve_kaydet()
    except KeyboardInterrupt:
        print("\n[alici.py] Dinleme sonlandırıldı. Çıkılıyor.")
        sys.exit(0)

