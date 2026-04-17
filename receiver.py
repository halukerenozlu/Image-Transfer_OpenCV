# receiver.py
# flake8: noqa
import cv2
import os
import time
import sys

# UDP port to listen on
UDP_PORT = 6000


def create_output_filepath():
    """
    Creates the "receiver_records" folder (if missing) and
    returns a timestamped .mkv output path.
    """
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    folder = "receiver_records"
    if not os.path.exists(folder):
        os.makedirs(folder)
    filename = f"receiver_video_{timestamp}.mkv"
    return os.path.join(folder, filename)


def open_pipeline():
    """
    Creates the GStreamer pipeline string and returns VideoCapture.
    Caps indicate RTP/H264 video input.
    """
    gst_pipeline = (
        f'udpsrc port={UDP_PORT} caps="application/x-rtp,media=video,'
        'encoding-name=H264,payload=96" ! '
        'rtpjitterbuffer ! rtph264depay ! avdec_h264 ! videoconvert ! '
        'appsink sync=false'
    )
    cap = cv2.VideoCapture(gst_pipeline, cv2.CAP_GSTREAMER)
    return cap


def listen_and_record():
    """
    Main loop:
    - Try to open pipeline
    - Once first frame arrives, open preview window and writer
    - Display and record stream until stream stops or user presses 'q'
    - Cleanup and return to listening mode
    """
    print(
        f"[receiver.py] Listening on port {UDP_PORT}. (Press Ctrl+C to exit)")

    while True:
        # 1) Open pipeline
        cap = open_pipeline()
        opened = cap.isOpened()
        print(f"[receiver.py] cap.isOpened() -> {opened}")
        if not opened:
            cap.release()
            time.sleep(0.5)
            continue

        # 2) Wait for first frame
        print("[receiver.py] Waiting for stream...")
        start_wait = time.time()
        first_frame = None
        while True:
            ret, frame = cap.read()
            print(f"[receiver.py] cap.read() returned: ret={ret}")
            if ret:
                first_frame = frame
                break
            # If no frame arrives for 10 seconds, reopen pipeline.
            if time.time() - start_wait > 10.0:
                cap.release()
                print(
                    "[receiver.py] No frame for 10 seconds; reopening pipeline...")
                time.sleep(0.2)
                cap = open_pipeline()
                start_wait = time.time()
            else:
                time.sleep(0.1)

        # 3) First frame received: open writer and preview
        frame_h, frame_w = first_frame.shape[:2]
        out_path = create_output_filepath()
        print(
            f"[receiver.py] Stream detected. Recording started: {out_path}")

        fourcc = cv2.VideoWriter_fourcc(*"X264")
        writer = cv2.VideoWriter(out_path, fourcc, 20, (frame_w, frame_h))
        if not writer.isOpened():
            print("[receiver.py] Warning: X264 codec unavailable. Falling back to MJPG.")
            fourcc_mjpg = cv2.VideoWriter_fourcc(*"MJPG")
            writer = cv2.VideoWriter(
                out_path, fourcc_mjpg, 20, (frame_w, frame_h))
            if not writer.isOpened():
                print(
                    "[receiver.py] Error: No recording codec could be opened. Returning to listening mode.")
                cap.release()
                continue

        # Write first frame to preview and file.
        cv2.imshow("Receiver - Live Preview", first_frame)
        writer.write(first_frame)
        print("[receiver.py] Live preview opened. Press 'q' for early stop.")

        # 4) Stream loop: continue until ret=False or 'q'
        while True:
            ret, frame = cap.read()
            if not ret:
                print("[receiver.py] Stream ended or frame could not be read.")
                break

            cv2.imshow("Receiver - Live Preview", frame)
            writer.write(frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                print("[receiver.py] 'q' pressed. Closing recording and preview.")
                break

        # 5) Cleanup resources, close preview, finalize file
        cap.release()
        writer.release()
        cv2.destroyAllWindows()
        print(f"[receiver.py] Stream recorded: {out_path}")
        print("[receiver.py] Returning to listening mode...\n")


if __name__ == "__main__":
    try:
        listen_and_record()
    except KeyboardInterrupt:
        print("\n[receiver.py] Listening stopped. Exiting.")
        sys.exit(0)
