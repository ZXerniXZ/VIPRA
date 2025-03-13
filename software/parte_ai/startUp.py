import subprocess

# Lista di comandi da eseguire in parallelo
commands = [
    "source /home/laserlab/Desktop/Venv3/bin/activate",
    "",
    "df -h",
]

processes = [subprocess.Popen(cmd, shell=True) for cmd in commands]

# Attendi che tutti i processi terminino
for p in processes:
    p.wait()
