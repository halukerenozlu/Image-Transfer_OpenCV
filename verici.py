# verici.py
# flake8: noqa
import cv2
import time
import os
import subprocess
import signal

# Ayarlar
CAPTURE_DEVICE = 0
UDP_HOST = '127.0.0.1'
UDP_PORT = 6000

# alici.py'nin yolu (aynı klasördeyse "alici.py")
ALICI_SCRIPT = "alici.py"


def open_udp_writer(width, height, fps=20):
    """
    GStreamer pipeline ile H.264 encode edip UDP'ye gönderir.
    Yerel yazma (VideoWriter) kesinlikle YOK.
    """
    gst_pipeline = (
        f'appsrc ! videoconvert ! '
        f'x264enc tune=zerolatency bitrate=500 speed-preset=superfast ! '
        f'rtph264pay config-interval=1 pt=96 ! '
        f'udpsink host={UDP_HOST} port={UDP_PORT} sync=false'
    )
    writer = cv2.VideoWriter(
        gst_pipeline,
        cv2.CAP_GSTREAMER,
        0,
        fps,
        (width, height),
        True
    )
    if not writer.isOpened():
        print("[VERICI] Uyarı: x264enc açılmadı, avenc_h264 ile denenecek...")
        gst_pipeline_fallback = (
            f'appsrc ! videoconvert ! '
            f'avenc_h264 ! '
            f'rtph264pay config-interval=1 pt=96 ! '
            f'udpsink host={UDP_HOST} port={UDP_PORT} sync=false'
        )
        writer = cv2.VideoWriter(
            gst_pipeline_fallback,
            cv2.CAP_GSTREAMER,
            0,
            fps,
            (width, height),
            True
        )
        if not writer.isOpened():
            print(
                "[VERICI] Hata: Hem x264enc hem avenc_h264 açılamadı. Canlı gönderim aktarılamayacak.")

    return writer


def start_alici_process():
    cmd = ["python3", ALICI_SCRIPT]
    # Alıcıyı arkada başlatıyoruz, kendi pipeline'ı direkt UDP 6000’i dinleyecek
    return subprocess.Popen(cmd, preexec_fn=os.setsid)


def verici():
    cap = cv2.VideoCapture(CAPTURE_DEVICE)
    if not cap.isOpened():
        print("❌ VERICI: Kamera açılamadı.")
        return

    # İlk kare ile çözünürlüğü öğrenelim
    ret, frame = cap.read()
    if not ret:
        print("❌ VERICI: İlk kare alınamadı.")
        cap.release()
        return

    height, width = frame.shape[:2]
    udp_writer = open_udp_writer(width, height, fps=20)
    if udp_writer.isOpened():
        print(
            f"[VERICI] UDP pipeline açıldı. Alici’ye {UDP_PORT} portundan paket yollanacak.")
    else:
        print("[VERICI] Uyarı: UDP writer açılamadı, canlı yayın gitmeyecek.")

    # Kısa test (10 kare) yollayarak alıcının hazır olmasını sağlıyoruz
    print("[VERICI] Test yayını (10 kare) yollanıyor, alici’yi bekliyoruz...")
    for _ in range(10):
        ret, frame = cap.read()
        if not ret:
            break
        if udp_writer.isOpened():
            udp_writer.write(frame)
        time.sleep(0.05)

    # Alici process’ini başlat
    print("[VERICI] Alici süreci başlatılıyor...")
    alici_proc = start_alici_process()
    time.sleep(1.0)  # Alici’nın pipeline kurması için bekleme

    print("[VERICI] Canlı yayın başladı. 'q' ile sonlandırabilirsiniz.")
    while True:
        ret, frame = cap.read()
        if not ret:
            print("❌ VERICI: Kare alınamıyor, çıkılıyor.")
            break

        cv2.imshow("Verici - Live Preview", frame)
        if udp_writer.isOpened():
            udp_writer.write(frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            print("[VERICI] 'q' tuşuna basıldı. Yayın durduruluyor...")
            break

    # Temizlik
    cap.release()
    if udp_writer.isOpened():
        udp_writer.release()
    cv2.destroyAllWindows()

    # Alici sürecini kapat
    try:
        os.killpg(os.getpgid(alici_proc.pid), signal.SIGTERM)
        print("[VERICI] Alici süreci sonlandırıldı.")
    except Exception as e:
        print(f"[VERICI] Alici kapanırken hata: {e}")

    print("[VERICI] İşlem tamamlandı.")


if __name__ == "__main__":
    verici()

