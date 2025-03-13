import subprocess
import time
import os

# Determina quale terminale usare
TERMINAL_CMD = None
if os.system("which gnome-terminal > /dev/null") == 0:
    TERMINAL_CMD = "gnome-terminal --"
elif os.system("which xfce4-terminal > /dev/null") == 0:
    TERMINAL_CMD = "xfce4-terminal -e"
elif os.system("which konsole > /dev/null") == 0:
    TERMINAL_CMD = "konsole -e"
elif os.system("which xterm > /dev/null") == 0:
    TERMINAL_CMD = "xterm -hold -e"
else:
    print("❌ Nessun terminale supportato trovato! Installa gnome-terminal o xterm.")
    exit(1)

# Lista di comandi con attesa
commands_with_wait = [
    ("source /home/laserlab/Desktop/Venv3/bin/activate", 1),
    ("echo 'inizializzazione server mqtt...'", 0),
    (f"{TERMINAL_CMD} python3 /home/laserlab/projectDayProject/software/parte_ai/mqttStart.py", 5),
    ("echo 'mqtt inizializzato'", 0),
    ("echo 'inizializzazione main script...'", 0),
    (f"{TERMINAL_CMD} python3 /home/laserlab/projectDayProject/software/parte_ai/raspMAIN.py", 5),
    ("echo 'MAIN inizializzato'", 0),
    (f"{TERMINAL_CMD} df -h", 0),
]

# Esegue ogni comando in un nuovo terminale se richiesto
for cmd, delay in commands_with_wait:
    print(f"Eseguendo: {cmd}")
    subprocess.Popen(cmd, shell=True)
    time.sleep(delay)
