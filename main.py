from time import sleep
from oauth2client.service_account import ServiceAccountCredentials
from googleapiclient.discovery import build
import requests
import os
from datetime import datetime

UPS_API_BASE_URL = "https://onlinetools.ups.com/"
DHL_API_URL="https://api-eu.dhl.com/track/shipments"
GOOGLE_SHEET_SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
GOOGLE_SHEET_NAME = 'Sociétés'
GOOGLE_SERVICE_ACCOUNT_FILE = 'GOOGLE_SERVICE_ACCOUNT_FILE.json'
PALAM_TRESOR_GOOGLE_SHEET_ID = os.environ.get('PALAM_TRESOR_GOOGLE_SHEET_ID')

def get_google_sheet_service():
    try:
        # logging.info("Configuration de l'API Google Sheets")
        creds = ServiceAccountCredentials.from_json_keyfile_name(GOOGLE_SERVICE_ACCOUNT_FILE,GOOGLE_SHEET_SCOPES)
        return build('sheets', 'v4', credentials=creds)
    except Exception as e:
        # logging.error("Erreur lors de la configuration de l'API Google Sheets : %s", e, exc_info=True)
        raise

def fetch_sheet_data_and_get_adresse(service):
    try:
        # logging.info("Chargement des données de la feuille Expéditions du fichier Google Sheets PALAM")
        result = service.spreadsheets().values().get(
            spreadsheetId=PALAM_TRESOR_GOOGLE_SHEET_ID,
            range=GOOGLE_SHEET_NAME
        ).execute()
        raw_data = result.get('values', [])
        societe_data = []
        raw_data = raw_data[0:30]
        for row in raw_data[1:]:
            sleep(0.3)
            if len(row) >= 7 and len(row[7])>0:
                siret = row[7]
                url = f"https://recherche-entreprises.api.gouv.fr/search?q={siret}&page=1&per_page=1"
                response = requests.request("GET", url)
                siege = response.json()['results'][0]['siege']
                adresse_array = [siege.get('complement_adresse'),
                                 siege.get('numero_voie'),
                                 siege.get('indice_repetition'),
                                 siege.get('type_voie'),
                                 siege.get('libelle_voie')]
                adresse_clean_array = []
                for adresse in adresse_array:
                    if adresse is not None:
                        adresse_clean_array.append(str(adresse))
                societe_data.append({
                    'siret': siret,
                    'adresse': ' '.join(adresse_clean_array).strip(),
                    'code_postal': siege['code_postal'],
                    'libelle_commune': siege['libelle_commune']
                })
        return raw_data,societe_data
    except Exception as e:
        # logging.error("Erreur lors de la récupération des données de la feuille Expéditions du fichier Google Sheets PALAM : %s", e, exc_info=True)
        raise

def update_google_sheet(sheet_data, societe_data, service):
    try:
        # logging.info("Mise à jour des status des expéditions de la feuille Expéditions du fichier Google Sheets PALAM")
        requests = []
        for row_index, row in enumerate(sheet_data):
            if row_index == 0:
                continue
            if len(row) > 7 and row[7]:
                siret = row[7]
                for societe in societe_data:
                    if siret == societe['siret']:
                        requests.append({
                            'range': f"{GOOGLE_SHEET_NAME}!I{row_index + 1}",
                            'values': [[societe['adresse']]]
                        })
                        requests.append({
                            'range': f"{GOOGLE_SHEET_NAME}!J{row_index + 1}",
                            'values': [[societe['code_postal']]]
                        })
                        requests.append({
                            'range': f"{GOOGLE_SHEET_NAME}!K{row_index + 1}",
                            'values': [[societe['libelle_commune']]]
                        })
        if len(requests)>0:
            body = {'data': requests, 'valueInputOption': 'RAW'}
            service.spreadsheets().values().batchUpdate(
                spreadsheetId=PALAM_TRESOR_GOOGLE_SHEET_ID,
                body=body
            ).execute()
    except Exception as e:
        # logging.error("Erreur lors de la mise à jour des status des expéditions de la feuille Expéditions du fichier Google Sheets PALAM : %s", e, exc_info=True)
        raise

service = get_google_sheet_service()
sheet_data, societe_data = fetch_sheet_data_and_get_adresse(service)
print(societe_data)
update_google_sheet(sheet_data, societe_data, service)