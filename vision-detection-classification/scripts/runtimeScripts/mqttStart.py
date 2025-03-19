#!/usr/bin/env python3
import argparse
import subprocess
import signal
import sys

def main():
    parser = argparse.ArgumentParser(description="Avvia Mosquitto come processo figlio.")
    parser.add_argument('--port', type=int, default=1883, help="Porta su cui avviare il broker Mosquitto.")
    args = parser.parse_args()

    # Costruiamo il comando per avviare Mosquitto su una porta specifica
    command = ["mosquitto", "-p", str(args.port)]
    print(f"[BROKER] Avvio Mosquitto sulla porta {args.port}...")

    # Avviamo Mosquitto come processo figlio
    process = subprocess.Popen(command)

    # Definiamo un handler per catturare SIGINT (Ctrl+C) e terminare Mosquitto pulitamente
    def handle_signal(signum, frame):
        print("[BROKER] Arresto di Mosquitto...")
        process.terminate()  # Invia un segnale di terminazione al processo
        sys.exit(0)

    # Catturiamo SIGINT e SIGTERM
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    # Rimaniamo in attesa finché il processo mosquitto non esce
    try:
        process.wait()
    except KeyboardInterrupt:
        handle_signal(None, None)

if __name__ == '__main__':
    main()
