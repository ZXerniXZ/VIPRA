#Installazione su Raspberry Pi 4 (Fresh Setup)

⚠️ **IMPORTANTE**  
Le Raspberry Pi sono configurate per eseguire automaticamente gli script da questa sezione della repository all'avvio. **Non modificare il percorso degli script.**

---

## Installazione su rasp fresh

### **Esegui questi comandi in sequenza sulla tua Raspberry Pi 4**:

```bash
# 1️⃣ Generare chiavi SSH per connessione sicura a GitHub
ssh-keygen -t rsa -b 4096 -C "your_email@example.com"

# 2️⃣ Clonare la repository nella directory /home
cd /home
git clone git@github.com:your-repo/projectDayProject.git

# 3️⃣ Aggiornare i pacchetti e installare Python
sudo apt update
sudo apt install python

# 4️⃣ Verificare l’installazione di Python
python --version

# 5️⃣ Installare le dipendenze
pip install -r /home/usr/projectDayProject/software/parte-ai/dependency.txt

# 6️⃣ Configurare un IP statico manualmente (IPv4: 192.168.1.100/24)

# 7️⃣ Connettere la scheda a Internet tramite Ethernet e riavviare
sudo reboot

#verifica:
se la scheda al reboot connessa ad internet dopo qualche minuto si spegne, il setup è avvenuto in modo corretto