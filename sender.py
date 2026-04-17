# sender.py
# flake8: noqa
import cv2
import time
import os
import subprocess
import signal

# Settings
CAPTURE_DEVICE = 0
UDP_HOST = '127.0.0.1'
UDP_PORT = 6000

# receiver.py path (if in the same folder, "receiver.py")
RECEIVER_SCRIPT = "receiver.py"


def open_udp_writer(width, height, fps=20):
    """
    Encodes frames with H.264 through GStreamer and sends them over UDP.
    No local file write happens in this writer.
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
        print("[SENDER] Warning: x264enc is unavailable, trying avenc_h264...")
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
                "[SENDER] Error: Neither x264enc nor avenc_h264 could be opened. Live transmission cannot continue.")

    return writer


def start_receiver_process():
    cmd = ["python3", RECEIVER_SCRIPT]
    # Start receiver in background; it listens directly on UDP 6000.
    return subprocess.Popen(cmd, preexec_fn=os.setsid)


def sender():
    cap = cv2.VideoCapture(CAPTURE_DEVICE)
    if not cap.isOpened():
        print("❌ SENDER: Camera could not be opened.")
        return

    # Read the first frame to detect frame size.
    ret, frame = cap.read()
    if not ret:
        print("❌ SENDER: Initial frame could not be read.")
        cap.release()
        return

    height, width = frame.shape[:2]
    udp_writer = open_udp_writer(width, height, fps=20)
    if udp_writer.isOpened():
        print(
            f"[SENDER] UDP pipeline is ready. Packets will be sent to receiver on port {UDP_PORT}.")
    else:
        print("[SENDER] Warning: UDP writer could not be opened, live stream will not be sent.")

    # Send a short warmup stream (10 frames) so receiver can initialize.
    print("[SENDER] Sending warmup stream (10 frames), waiting for receiver...")
    for _ in range(10):
        ret, frame = cap.read()
        if not ret:
            break
        if udp_writer.isOpened():
            udp_writer.write(frame)
        time.sleep(0.05)

    # Start receiver process.
    print("[SENDER] Starting receiver process...")
    receiver_proc = start_receiver_process()
    time.sleep(1.0)  # Wait for receiver pipeline startup.

    print("[SENDER] Live stream started. Press 'q' to stop.")
    while True:
        ret, frame = cap.read()
        if not ret:
            print("❌ SENDER: Frame capture failed, exiting.")
            break

        cv2.imshow("Sender - Live Preview", frame)
        if udp_writer.isOpened():
            udp_writer.write(frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            print("[SENDER] 'q' pressed. Stopping stream...")
            break

    # Cleanup
    cap.release()
    if udp_writer.isOpened():
        udp_writer.release()
    cv2.destroyAllWindows()

    # Stop receiver process.
    try:
        os.killpg(os.getpgid(receiver_proc.pid), signal.SIGTERM)
        print("[SENDER] Receiver process terminated.")
    except Exception as e:
        print(f"[SENDER] Error while stopping receiver: {e}")

    print("[SENDER] Process completed.")


if __name__ == "__main__":
    sender()
