import subprocess
import time

def is_online():
    """
    Verifica la connessione a Internet eseguendo un ping a google.com.
    Se il ping ha successo (returncode == 0), ritorna True.
    """
    try:
        result = subprocess.run("ping -c 1 google.com", shell=True,
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return result.returncode == 0
    except Exception as e:
        print(f"Errore nel controllo della connessione: {e}")
        return False

def set_static_ip():
    """
    Imposta un indirizzo IP statico su wlan0 o eth0 se non c'è connessione a Internet.
    """
    interface = "eth0" 
    static_ip = "192.168.1.100"
    gateway = "192.168.1.1"
    netmask = "255.255.255.0"

    print(f"Nessuna connessione rilevata! Assegnando IP statico {static_ip} a {interface}...")

    # Esegui comandi per impostare l'IP statico
    subprocess.run(f"sudo ip addr flush dev {interface}", shell=True)  # Pulisce eventuali IP assegnati
    subprocess.run(f"sudo ip addr add {static_ip}/{netmask} dev {interface}", shell=True)
    subprocess.run(f"sudo ip route add default via {gateway}", shell=True)

    print("IP statico impostato con successo.")

# Controlliamo se siamo online
if not is_online():
    set_static_ip()
    for cmd, delay in commands_with_wait_online:
        print(f"Eseguendo: {cmd}")
        subprocess.Popen(cmd, shell=True)
        time.sleep(delay)

else:
    for cmd, delay in commands_with_wait_offline:
        print(f"Eseguendo: {cmd}")
        subprocess.Popen(cmd, shell=True)
        time.sleep(delay)

# Lista di comandi con attesa, con messaggi colorati
commands_with_wait_online = [
    ("echo -e '\e[33mAggiornamento da public repo...\e[0m'", 0),
    ("cd projectDayProject && git pull", 10),
    ("sudo shutdown -h now", 0)
     
]
commands_with_wait_offline = [
    ("echo -e '\e[33mOFFLINE!, la scheda non tenterà di aggiornare il coddice\e[0m'", 0),
    ("echo -e '\e[33mRUN codice principale...\e[0m'", 0),
    ("echo -e '\e[34mInizializzazione server MQTT...\e[0m'", 0),
    ("gnome-terminal -- bash -c 'python3 /home/laserlab/projectDayProject/software/parte_ai/mqttStart.py; exec bash'", 5),
    ("echo -e '\e[32mMQTT inizializzato\e[0m'", 0),
    ("gnome-terminal -- bash -c 'python3 /home/laserlab/projectDayProject/software/parte_ai/raspMAIN.py; exec bash'", 5),
    ("echo -e '\e[35mMAIN inizializzato\e[0m'", 0),
]


# Esegui ogni comando in sequenza
