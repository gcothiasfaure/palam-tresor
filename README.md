# :moneybag: palam-tresor

Robot de récupération des adresses des sociétés clientes de [**Paris L'après-midi**](www.parislapresmidi.com/).

## Description du processus

Le robot s'exécute tous les jours à 03:00 depuis mon VPS hébergé chez [OVH](https://www.ovhcloud.com/).

ÉTAPE 1. Authentification à l'API Google Sheets.

ÉTAPE 2. Récupération des SIRET des sociétés clientes de Paris L'après midi dans le fichier TRESOR (feuille Sociétés). On ne récupère que les SIRET des sociétés qui n'ont pas déjà une adresse renseignée (colonne I vide). Une fois par semaine le dimanche, 

ÉTAPE 3. Récupération des adresses des sociétés clientes à partir de leur SIRET. On utilise l'[API Recherche d'entreprises](https://recherche-entreprises.api.gouv.fr/docs/).

ÉTAPE 6. Remplissage dans le fichier TRESOR (feuille Sociétés) des adresses des sociétés.
On rempli les colonnes :
- Adresse (I)
- Code Postal (J)
- Ville (K)
- Pays (E)

## Installation locale

#### MACOS

```
mkdir -p output
cd source-code
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
sh .env.sh
```

#### WINDOWS

```
New-Item -Path ".\output" -ItemType Directory -Force
cd source-code
python -m venv .venv
.venv/Scripts/Activate.ps1
pip install -r requirements.txt
./env.ps1
```