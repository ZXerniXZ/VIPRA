import psutil
import time
import subprocess

INTERFACCIA = "eth0"  
IP_STATICO = "192.168.1.100"
NETMASK = "255.255.255.0"
GATEWAY = "192.168.1.1"

def verifica_connessione_ethernet():
    net_if_stats = psutil.net_if_stats()
    return net_if_stats.get(INTERFACCIA, None) and net_if_stats[INTERFACCIA].isup

def imposta_ip_statico():
    #Questa funzione imposta Indirizzo IP statico tramite subprocess di Linux
    print("[INFO] Imposto IP statico...")
    subprocess.run(f"sudo ip addr flush dev {INTERFACCIA}", shell=True)
    subprocess.run(f"sudo ip addr add {IP_STATICO}/{NETMASK} dev {INTERFACCIA}", shell=True)
    subprocess.run(f"sudo ip route add default via {GATEWAY}", shell=True)

def main():
    ethernet_attiva = verifica_connessione_ethernet()

    while True:
        connesso = verifica_connessione_ethernet()

        if not connesso and ethernet_attiva:
            print("[ATTENZIONE] Rete Ethernet disconnessa. Impostando IP statico...")
            imposta_ip_statico()
            ethernet_attiva = False

        elif connesso and not ethernet_attiva:
            print("[INFO] Rete Ethernet riconnessa. Ripristinando DHCP...")
            ethernet_attiva = True

        time.sleep(5)  #Controlla lo stato della rete ogni 5 secondi

if __name__ == "__main__":
    main()