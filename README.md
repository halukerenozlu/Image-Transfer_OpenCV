# LiveCast-UDP

LiveCast-UDP is a Python + OpenCV + GStreamer project for **real-time video streaming over UDP**.

- `sender.py` captures frames from a local camera, encodes them as H.264, and sends them over RTP/UDP.
- `receiver.py` listens on UDP port `6000`, decodes the stream, shows live preview, and records to `.mkv`.

## Architecture

```mermaid
flowchart LR
    CAM[Camera Device] --> SENDER[sender.py]
    SENDER -->|OpenCV frames| GST_ENC[GStreamer: x264enc / avenc_h264]
    GST_ENC -->|RTP H264 over UDP :6000| NET[(UDP Loopback / Network)]
    NET --> GST_DEC[GStreamer: rtph264depay + avdec_h264]
    GST_DEC --> RECEIVER[receiver.py]
    RECEIVER --> PREVIEW[OpenCV Live Preview]
    RECEIVER --> FILE[MKV Recording]
```

## Streaming Pipelines

### Sender (OpenCV VideoWriter)

```bash
appsrc ! videoconvert ! x264enc tune=zerolatency bitrate=500 speed-preset=superfast ! rtph264pay config-interval=1 pt=96 ! udpsink host=127.0.0.1 port=6000 sync=false
```

Fallback encoder:

```bash
appsrc ! videoconvert ! avenc_h264 ! rtph264pay config-interval=1 pt=96 ! udpsink host=127.0.0.1 port=6000 sync=false
```

### Receiver (OpenCV VideoCapture)

```bash
udpsrc port=6000 caps="application/x-rtp,media=video,encoding-name=H264,payload=96" ! rtpjitterbuffer ! rtph264depay ! avdec_h264 ! videoconvert ! appsink sync=false
```

## Protocols and Formats

- **Transport:** UDP
- **Packetization:** RTP (`rtph264pay` / `rtph264depay`)
- **Video codec:** H.264
- **Recording container:** MKV

## Installation

### 1) System Dependencies (Linux)

Install GStreamer and codec plugins.

#### Ubuntu / Debian

```bash
sudo apt update
sudo apt install -y \
  python3 python3-pip \
  gstreamer1.0-tools \
  gstreamer1.0-plugins-base \
  gstreamer1.0-plugins-good \
  gstreamer1.0-plugins-bad \
  gstreamer1.0-plugins-ugly \
  gstreamer1.0-libav
```

#### Fedora

```bash
sudo dnf install -y \
  python3 python3-pip \
  gstreamer1 \
  gstreamer1-plugins-base \
  gstreamer1-plugins-good \
  gstreamer1-plugins-bad-free \
  gstreamer1-plugins-ugly \
  gstreamer1-libav
```

### 2) Python Dependencies

```bash
python3 -m pip install -r requirements.txt
```

## Usage

Run sender (it starts receiver automatically):

```bash
python3 sender.py
```

Or run receiver manually in a separate terminal:

```bash
python3 receiver.py
```

Press `q` in preview windows to stop.
