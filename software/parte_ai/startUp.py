import subprocess
import os
import time

# Controlla quale terminale è installato
if os.system("which lxterminal > /dev/null") == 0:
    TERMINAL_CMD = "lxterminal -e"
elif os.system("which xterm > /dev/null") == 0:
    TERMINAL_CMD = "xterm -hold -e"
elif os.system("which gnome-terminal > /dev/null") == 0:
    TERMINAL_CMD = "gnome-terminal --"
else:
    print("❌ Nessun terminale compatibile trovato!")
    exit(1)

# Comandi da eseguire in nuove finestre di terminale
commands_with_wait = [
    (f"{TERMINAL_CMD} python3 /home/pi/mqttStart.py", 5),
    (f"{TERMINAL_CMD} python3 /home/pi/raspMAIN.py", 5),
]

# Esegui ogni comando in una nuova finestra
for cmd, delay in commands_with_wait:
    print(f"Eseguendo: {cmd}")
    subprocess.Popen(cmd, shell=True)
    time.sleep(delay)
