import subprocess
import time

def is_online():
    """
    Verifica la connettività pingando google.com.
    Restituisce True se il ping ha successo (returncode == 0), altrimenti False.
    """
    try:
        result = subprocess.run("ping -c 1 google.com", shell=True,
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return result.returncode == 0
    except Exception as e:
        print(f"Errore nel controllo della connettività: {e}")
        return False

# Lista di comandi con attesa
commands_with_wait = [
    ("echo tentativo aggiornamento da public repo...", 0),
    # Prima di eseguire il git pull, verrà verificato lo stato online
    ("cd projectDayProject && git pull", 10),
    ("echo 'inizializzazione server mqtt...'", 0),
    ("gnome-terminal -- bash -c 'python3 /home/laserlab/projectDayProject/software/parte_ai/mqttStart.py; exec bash'", 5),
    ("echo -e '\e[32mmqtt inizializzato'", 0),
    ("echo 'run MAIN script...'", 0),
    ("gnome-terminal -- bash -c 'python3 /home/laserlab/projectDayProject/software/parte_ai/raspMAIN.py; exec bash'", 5),
    ("echo -e '\e[32mMAIN inizializzato'", 0),
]

# Esegui ogni comando in sequenza
for cmd, delay in commands_with_wait:
    # Se il comando contiene "git pull", controlla prima se siamo online
    if "git pull" in cmd:
        if is_online():
            print("Online: procedo con il git pull...")
        else:
            print("Offline: il codice non verrà aggiornato")
            # Salta questo comando e passa al successivo
            time.sleep(delay)
            continue
    subprocess.Popen(cmd, shell=True)
    time.sleep(delay)
