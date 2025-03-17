ATTENZIONE: le raspberry py sono configurate in tal modo da prendere i codici in questa sezione della repository all'avvio, per favore NON modificare in alcun modo il path di questi script

installazione su rasp pi 4 fresh

-generare chiavi pubbliche ssh per connessione autorizzata a github

-pull repo su /home

-installare ultima versione di python con

sudo apt install python

verificare con:

python --version

-installare dependency

pip install -r /home/usr/projectDayProject/software/parte-ai/dependency.txt

-impostare ip statico standard su impostazioni

manual: ipv4 192.168.1.100/24

-connettere la scheda ad internet tramite eth se non lo è già ed eseguire il reboot della scheda, se la scheda dopo qualche minuto dell'accensione si spegne, allora il setup è andato a buon fine
