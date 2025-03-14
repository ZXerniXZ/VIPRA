import subprocess
import time

# Lista di comandi con attesa
commands_with_wait = [
    ("echo aggiornamento da public repo...", 0),
    ("cd projectDayProject && git pull", 10),
    ("echo 'inizializzazione server mqtt...'", 0),
    ("gnome-terminal -- bash -c 'python3 /home/laserlab/projectDayProject/software/parte_ai/mqttStart.py; exec bash'", 5),
    ("echo 'mqtt inizializzato'", 0),
    ("gnome-terminal -- bash -c 'python3 /home/laserlab/projectDayProject/software/parte_ai/raspMAIN.py; exec bash'", 5),
    ("echo 'MAIN inizializzato'", 0),
]

# Esegui ogni comando in una nuova finestra
for cmd, delay in commands_with_wait:
    print(f"Eseguendo: {cmd}")
    subprocess.Popen(cmd, shell=True)
    time.sleep(delay)
