# VIPRA Vision – Object Detection & Classification (Docker Edition)

> **Branch:** `prototipo2/vision-detection-classification`
> **Hardware target:** Raspberry Pi 4 B / Pi 3 B + (64‑bit Raspberry Pi OS Bookworm)

This module runs real‑time **object detection** and **image classification** entirely inside a **Docker container**—no more native install scripts. Follow the steps below to deploy it on a Raspberry Pi.

---

## 1 · Prerequisites

| Component            | Minimum requirement                                  |
| -------------------- | ---------------------------------------------------- |
| **Raspberry Pi**     | pi 5 8gb min                                         |
| **Operating system** | Raspberry Pi OS 64‑bit headless (Bookworm or later)  |
| **Docker Engine**    | 24.x                                                 |
| **Docker Compose**   | latest (outdated)                                    |
| **Camera**           | [rpi ai cam](https://www.raspberrypi.com/products/ai-camera/) (imx500 processor)                        |

### 1.1 Install Docker on a Raspberry Pi

```bash
# Official installation script
aeval $(curl -fsSL https://get.docker.com)

# Add the current user to the docker group and refresh credentials
sudo usermod -aG docker "$USER"
newgrp docker  # reload group without reboot

# Install the Compose plugin
sudo apt-get install -y docker-compose-plugin
```

---

## 2 · Clone the latest release (tag)

```bash
git clone https://github.com/ZXerniXZ/VIPRA.git --branch latest_tag_here  #ex v0.1.08
cd VIPRA/vision-detection-classification
```


da finire da qui in giù


---

## 3 · Build or pull the Docker image

### 3.1 Build locally

> **Time required:** \~ 5–7 min on a Pi 5.

```bash
docker compose build -t vipra-vision:latest .
```

### 3.2 Pull a pre‑built image (if published)

```bash
docker pull ghcr.io/zxernixz/vipra-vision:latest
```

---

## 4 · Run a single container

```bash
docker run -it --rm \
  --name vipra-vision \
  --device /dev/video0:/dev/video0 \
  -v "$(pwd)/config:/app/config:ro" \
  -v /etc/localtime:/etc/localtime:ro \
  -e IMG_SIZE=640 \   # optional environment variable
  vipra-vision:latest
```

| Option                       | Purpose                                                 |
| ---------------------------- | ------------------------------------------------------- |
| `--device /dev/video0`       | Pass the camera device into the container               |
| `-v ./config:/app/config:ro` | Provide custom configuration files (labels, YAML, etc.) |
| `-e IMG_SIZE=640`            | Override the YOLO input size                            |
| `--rm`                       | Remove the container when it exits                      |

If you want an OpenCV preview window on a **Pi 4 with the VC4 GPU**, add `--device /dev/vchiq` and `--privileged`.

---

## 5 · Docker Compose (recommended)

A ready‑made `docker-compose.yml` is included. Start the service in the background:

```bash
docker compose up -d
```

<details>
<summary><strong>Example <code>docker-compose.yml</code></strong></summary>

```yaml
version: "3.9"
services:
  vision:
    build: .  # or: image: ghcr.io/zxernixz/vipra-vision:latest
    container_name: vipra-vision
    restart: unless-stopped
    devices:
      - /dev/video0:/dev/video0
    volumes:
      - ./config:/app/config:ro
    environment:
      - IMG_SIZE=640
      - DISPLAY=0
```

</details>

### 5.1 Update to the latest image

```bash
git pull                         # fetch new commits
docker compose build --pull      # rebuild with the latest base image
docker compose up -d             # restart the container
```

### 5.2 Tail the logs

```bash
docker compose logs -f
```

---

## 6 · Environment variables

| Variable      | Default   | Description                                          |
| ------------- | --------- | ---------------------------------------------------- |
| `IMG_SIZE`    | `640`     | Input resolution for YOLO                            |
| `DISPLAY`     | `0`       | Set to `1` to show an OpenCV preview window (debug)  |
| `SAVE_FRAMES` | `0`       | Set to `1` to save processed frames in `/app/output` |
| `RTSP_OUT`    | *(empty)* | Publish an RTSP stream on the specified port if set  |

---

## 7 · Directory layout

```text
vision-detection-classification/
├── Dockerfile
├── docker-compose.yml
├── config/
│   └── labels.txt
├── weights/
│   ├── yolov5nano.onnx
│   └── resnet18.pt
├── src/
│   ├── detection.py
│   ├── classification.py
│   └── ...
└── main.py
```

---

## 8 · Troubleshooting

| Problem                                    | Possible solution                                                         |
| ------------------------------------------ | ------------------------------------------------------------------------- |
| **`/dev/video0: Operation not permitted`** | Add `--device /dev/video0` and/or run the container with `--privileged`.  |
| **Low FPS**                                | Reduce `IMG_SIZE` (e.g., `320`) or disable the GUI preview (`DISPLAY=0`). |
| **Dark / blue image**                      | Adjust white balance with `v4l2-ctl`.                                     |
| **`libcblas.so` not found**                | Rebuild the image; the base image is missing BLAS libraries.              |
| **Out‑of‑memory errors**                   | Enable memory cgroups (`cgroup_enable=memory` in `/boot/cmdline.txt`).    |

---

## 9 · Contributing

1. Fork the repo and create a branch named `feature/<topic>`.
2. Make sure `docker compose test` (unit + integration) passes locally.
3. Open a pull request against `prototipo2` with a concise description of your changes.

---

## 10 · License

Released under the **MIT License**. See the `LICENSE` file for details.

---

### Have fun containerising! 🚀
