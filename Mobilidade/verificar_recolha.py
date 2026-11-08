"""Verifica por SSH se a recolha de autocarros na VPS está viva (só leitura).

Uso: python verificar_recolha.py <ip> [--chave ~/.ssh/hetzner_recolha]
O IP não fica no repositório (público); passa-se como argumento.
"""
import argparse
import os
import subprocess
import sys

REMOTO = (
    "systemctl is-active recolher-autocarros; "
    "f=$(ls -t /var/lib/recolha/posicoes_*.csv 2>/dev/null | head -1); "
    "echo ficheiro=$f; echo linhas=$(wc -l < \"$f\"); "
    "echo ultima=$(tail -1 \"$f\" | cut -d, -f1); echo agora=$(date -u +%FT%TZ); "
    "echo falhas_24h=$(journalctl -u recolher-autocarros --since '24 hours ago' "
    "--no-pager | grep -c FALHA); df -h /var/lib/recolha | tail -1; "
    "ls /var/lib/recolha | wc -l"
)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ip")
    ap.add_argument("--chave", default="~/.ssh/hetzner_recolha")
    a = ap.parse_args()
    cmd = ["ssh", "-i", os.path.expanduser(a.chave), "-o", "BatchMode=yes",
           "-o", "ConnectTimeout=15", f"root@{a.ip}", REMOTO]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    print(r.stdout)
    if r.returncode != 0:
        print("ERRO SSH:", r.stderr.strip(), file=sys.stderr)
        sys.exit(1)
    if not r.stdout.startswith("active"):
        print("ATENÇÃO: serviço não está activo", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
