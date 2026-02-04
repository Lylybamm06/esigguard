#!/bin/bash

# 1. On va dans le dossier (ADAPTE LE CHEMIN SI BESOIN)
cd /home/azureuser/esigguard/services/cyber/Microservices_application/aggregator

# 2. On lance le service de l'aggrégateur
# -u pour voir les logs en direct
/usr/bin/python3 -u aggregator.py
