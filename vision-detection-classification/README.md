# VIPRA Vision – Object Detection & Classification (Docker Edition)

> **Branch:** `prototipo2/vision-detection-classification`
> **Hardware target:** Raspberry Pi  5 8gb(64‑bit Raspberry Pi OS Bookworm)

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

sudo apt install -y \
    ca-certificates \
    curl \
    gnupg \
    lsb-release
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/debian/gpg \
  | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://downlsudo apt update
sudo apt install -y \
    docker-ce \
    docker-ce-cli \
    containerd.io \
    docker-buildx-plugin \
    docker-compose-plugin   # <-- Compose v2
oad.docker.com/linux/debian \
  $(lsb_release -cs) stable" \
  | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo systemctl enable dosudo usermod -aG docker $USER
# logout / login (o: newgrp docker)
docker run hello-world
cker --now
```
---


## 2 · Install necessary dependency

```bash
#apt update
sudo apt update
#installing git
sudo apt install git
# imx-500 dependency for cam compatibility
sudo apt install imx500-all
```

---

## 3 · Clone the latest release (tag)

```bash
git clone https://github.com/ZXerniXZ/VIPRA.git --branch latest_tag_here  #ex v0.1.08
cd VIPRA/vision-detection-classification
```
---

## 4 · Docker Compose 

A ready‑made `docker-compose.yml` is included. Start and build the service in the background:

```bash
cd VIPRA/vision-detection-classification
docker compose up -d --build
```

---

## 5 · Set up container with external resources

modello moondream https://drive.google.com/drive/folders/1vvD3g_ZfrhedtCNqnTiiuytrxVO7Xpwj?usp=sharing
container ollama con gemma3:1b

---

## 6 · Directory layout

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

## 7 · Troubleshooting

| Problem                                    | Possible solution                                                         |
| ------------------------------------------ | ------------------------------------------------------------------------- |
| **`/dev/video0: Operation not permitted`** | Add `--device /dev/video0` and/or run the container with `--privileged`.  |
| **Low FPS**                                | Reduce `IMG_SIZE` (e.g., `320`) or disable the GUI preview (`DISPLAY=0`). |
| **Dark / blue image**                      | Adjust white balance with `v4l2-ctl`.                                     |
| **`libcblas.so` not found**                | Rebuild the image; the base image is missing BLAS libraries.              |
| **Out‑of‑memory errors**                   | Enable memory cgroups (`cgroup_enable=memory` in `/boot/cmdline.txt`).    |

---

## 8 · Contributing

1. Fork the repo and create a branch named `feature/<topic>`.
2. Make sure `docker compose test` (unit + integration) passes locally.
3. Open a pull request against `prototipo2` with a concise description of your changes.

---

## 9 · License

Released under the **MIT License**. See the `LICENSE` file for details.

---

### Have fun containerising! 🚀
