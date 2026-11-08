# Recolha na VPS (Ubuntu/Debian)

Pré-requisito: VPS com Python 3.9+ e acesso SSH (chave, não palavra-passe).

1. Copiar o script e criar o utilizador e as pastas (na VPS, como root):
   ```
   adduser --system --group recolha
   mkdir -p /opt/recolha /var/lib/recolha
   chown recolha:recolha /var/lib/recolha
   ```
   Do PC: `scp recolher_autocarros.py root@<ip>:/opt/recolha/` e `scp deploy/recolher-autocarros.service root@<ip>:/etc/systemd/system/`
2. Arrancar:
   ```
   systemctl daemon-reload
   systemctl enable --now recolher-autocarros
   journalctl -u recolher-autocarros -n 20
   ```
   Esperado: linhas `recebidos=… novos=…`, com `novos` > 0 cerca de 1 vez por minuto.
3. **Primeiro dia = teste de bloqueio de IP:** se o log mostrar `FALHA` repetida (403, timeout), o broker pode estar a recusar o IP do datacentre; nesse caso, manter a recolha no PC.
4. Descarregar os dados para o PC (fora do OneDrive), por exemplo a cada semana:
   `scp -r root@<ip>:/var/lib/recolha/ C:/Users/quent/dados_autocarros/`
   Os dias anteriores ficam em `.csv.gz`; o dia em curso está em `.csv`.

Intervalo de 30 s: o broker actualiza todos os veículos em bloco, cerca de 1 vez por minuto (a confirmar no teste de 1 h).
