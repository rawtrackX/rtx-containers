#!/bin/bash
# v1.0 (05.11.2026): startet optional den Salad-Queue-Worker (nur wenn RTX_QUEUE=1) neben dem Dienst.
# Ohne RTX_QUEUE bleibt alles wie bisher (Gateway-Betrieb). Der Worker schickt Auftraege der Salad Job Queue per HTTP an den Dienst (Port/Pfad in der Gruppe: queue_connection).
if [ "$RTX_QUEUE" = "1" ]; then /usr/local/bin/salad-http-job-queue-worker & fi
"$@" &
wait -n
exit $?
