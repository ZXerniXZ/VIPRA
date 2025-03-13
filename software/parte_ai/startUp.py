import subprocess
import time

# Lista di comandi da eseguire in parallelo
commands_with_wait = [
    ("source /home/laserlab/Desktop/Venv3/bin/activate", 1),
    ("echo 'inizializzazione server mqtt...'", 0),
    ("python3 /home/laserlab/projectDayProject/software/parte_ai/mqttStart.py", 5),
    ("echo 'mqtt inizializzto'", 0),
    ("echo 'inizializzazione main script...'",0),
    ("python3 /home/laserlab/projectDayProject/software/parte_ai/raspMAIN.py",5),
    ("echo 'MAIN inizializzato'", 0),
    ("df -h",)
]

# Attendi che tutti i processi terminino
for cmd, delay in commands_with_wait:

    subprocess.run(cmd, shell=True)

    time.sleep(delay)
