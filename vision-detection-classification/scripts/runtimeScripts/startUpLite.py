#!/usr/bin/env python3
import subprocess
import time
import os

# Imposta il percorso del log sul Desktop (modifica se necessario)
LOG_FILE = "~/Desktop/log.log"

def log(message):
    """Scrive il messaggio sia sullo stdout che nel file di log."""
    timestamp = time.strftime("[%Y-%m-%d %H:%M:%S]")
    full_message = f"{timestamp} {message}"
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

# Lista di comandi con attesa, per il caso ONLINE
commands_online = [
    ("echo -e '\e[33mAggiornamento da public repo...\e[0m'", 0),
    ("cd projectDayProject && git pull", 10),
    ("sudo shutdown -h now", 0)
]

# Lista di comandi con attesa, per il caso OFFLINE
commands_offline = [
    ("echo -e '\e[33mOFFLINE!, la scheda non tenterà di aggiornare il codice\e[0m'", 0),
    ("echo -e '\e[33mRUN codice principale...\e[0m'", 0),
    ("sudo ~/projectDayProject/vision-detection-classification/scripts/runtimeScripts/setupScript/setupIP.sh", 5),
    ("echo -e '\e[35m publish to mqtt inizializzato\e[0m'", 0),
    ("python3 ~/projectDayProject/vision-detection-classification/scripts/runtimeScripts/startUp.py", 5),
    ("echo -e '\e[35m publish to mqtt inizializzato\e[0m'", 0),
    ("sudo ~/projectDayProject/vision-detection-classification/scripts/runtimeScripts/setupScript/setupHotspot.sh", 5),
    ("echo -e '\e[35msetup hotspot inizializzato\e[0m'", 0),
]

def run_commands(commands):
    """Esegue ogni comando con gestione degli errori e logging."""
    for cmd, delay in commands:
        try:
            proc = subprocess.Popen(
                cmd, 
                shell=True, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                text=True  # Gestisce automaticamente la decodifica UTF-8
            )
            
            # Imposta un timeout di 60 secondi per l'esecuzione del comando
            try:
                stdout, stderr = proc.communicate(timeout=60)
            except subprocess.TimeoutExpired:
                proc.kill()
                log(f"ERRORE: Timeout nell'esecuzione del comando: {cmd}")
                continue

            # Controlla il codice di uscita
            if proc.returncode != 0:
                log(f"AVVISO: Comando fallito con codice {proc.returncode}: {cmd}")
                if stderr:
                    log(f"Errore: {stderr.strip()}")
                # Continua con il prossimo comando invece di bloccarsi
                continue

            # Logga output solo se presente
            if stdout:
                log(f"Output: {stdout.strip()}")
            
            # Attendi il delay specificato
            if delay > 0:
                time.sleep(delay)

        except Exception as e:
            log(f"ERRORE CRITICO durante l'esecuzione di {cmd}: {str(e)}")
            # Continua con il prossimo comando
            continue

def main():
    log("========== Avvio script di startup ==========")
    if not is_online():
        log("non online")
        run_commands(commands_offline)
    else:
        log("online")
        run_commands(commands_online)
    log("========== Fine esecuzione script ==========")

if __name__ == "__main__":
    main()
