python3 imx500_script.py \
  --model /usr/share/imx500-models/imx500_network_ssd_mobilenetv2_fpnlite_320x320_pp.rpk \
  --threshold 0.5 \
  --mqtt-host broker.mqtt.example \
  --mqtt-port 1883 \
  --mqtt-topic imx500/detections \
  --mqtt-username myuser \
  --mqtt-password mypass
