#!/usr/bin/env python3
import subprocess
import time
import os

# Imposta il percorso del log sul Desktop (modifica se necessario)
LOG_FILE = "/home/prototipo1/Desktop/startup.log"

def log(message):
    """Scrive il messaggio sia sullo stdout che nel file di log."""
    timestamp = time.strftime("[%Y-%m-%d %H:%M:%S]")
    full_message = f"{timestamp} {message}"
    print(full_message)
    with open(LOG_FILE, "a") as f:
        f.write(full_message + "\n")

def is_online():
    """Verifica la connessione a Internet eseguendo un ping a google.com."""
    try:
        result = subprocess.run("ping -c 1 google.com", shell=True,
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return result.returncode == 0
    except Exception as e:
        log(f"Errore nel controllo della connessione: {e}")
        return False

def set_static_ip():
    """Imposta un indirizzo IP statico su wlan0 o eth0 se non c'è connessione a Internet."""
    interface = "eth0"  # Cambia in "wlan0" se usi Wi-Fi
    static_ip = "192.168.1.100"
    gateway = "192.168.1.1"
    netmask = "255.255.255.0"

    log(f"Nessuna connessione rilevata! Assegnando IP statico {static_ip} a {interface}...")

    # Esegui comandi per impostare l'IP statico, redirigendo l'output (non visibile in cron)
    subprocess.run(f"sudo ip addr flush dev {interface}", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    subprocess.run(f"sudo ip addr add {static_ip}/{netmask} dev {interface}", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    subprocess.run(f"sudo ip route add default via {gateway}", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    log("IP statico impostato con successo.")

# Lista di comandi con attesa, per il caso ONLINE
commands_with_wait_online = [
    ("echo -e '\e[33mAggiornamento da public repo...\e[0m'", 0),
    ("cd projectDayProject && git pull", 10),
    ("sudo shutdown -h now", 0)
]

# Lista di comandi con attesa, per il caso OFFLINE
commands_with_wait_offline = [
    ("echo -e '\e[33mOFFLINE!, la scheda non tenterà di aggiornare il codice\e[0m'", 0),
    ("echo -e '\e[33mRUN codice principale...\e[0m'", 0),
    ("echo -e '\e[34mInizializzazione server MQTT...\e[0m'", 0),
    ("python3 setupScript/mqttStart.py", 5),
    ("echo -e '\e[32mMQTT inizializzato\e[0m'", 0),
    ("python3 publishToMqtt.py", 5),
    ("echo -e '\e[35m publish to mqtt inizializzato\e[0m'", 0),
    ("sudo setupScript/setupHotspot.sh", 5),
    ("echo -e '\e[35mcheckRete inizializzato\e[0m'", 0),
]

def run_commands(commands):
    """Esegue ogni comando, redirigendo output ed errori al log."""
    for cmd, delay in commands:
        log(f"Eseguendo: {cmd}")
        # Esegui il comando e cattura stdout e stderr
        proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = proc.communicate()
        if stdout:
            log("Output: " + stdout.decode("utf-8").strip())
        if stderr:
            log("Errori: " + stderr.decode("utf-8").strip())
        time.sleep(delay)

def main():
    log("========== Avvio script di startup ==========")
    if not is_online():
        set_static_ip()  # Imposta IP statico se offline
        run_commands(commands_with_wait_offline)
    else:
        run_commands(commands_with_wait_online)
    log("========== Fine esecuzione script ==========")

if __name__ == "__main__":
    main()
