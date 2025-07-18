from time import sleep
from oauth2client.service_account import ServiceAccountCredentials
from googleapiclient.discovery import build
import requests
import os
import logging

UPS_API_BASE_URL = "https://onlinetools.ups.com/"
DHL_API_URL="https://api-eu.dhl.com/track/shipments"
GOOGLE_SHEET_SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
GOOGLE_SHEET_NAME = 'Sociétés'
GOOGLE_SERVICE_ACCOUNT_FILE = 'GOOGLE_SERVICE_ACCOUNT_FILE.json'
PALAM_TRESOR_GOOGLE_SHEET_ID = os.environ.get('PALAM_TRESOR_GOOGLE_SHEET_ID')

def get_google_sheet_service():
    try:
        logging.info("Configuration de l'API Google Sheets")
        creds = ServiceAccountCredentials.from_json_keyfile_name(GOOGLE_SERVICE_ACCOUNT_FILE,GOOGLE_SHEET_SCOPES)
        return build('sheets', 'v4', credentials=creds)
    except Exception as e:
        logging.error("Erreur lors de la configuration de l'API Google Sheets : %s", e, exc_info=True)
        raise

def get_adress_with_lat_lon(latitude, longitude, geo_id):
    try:
        logging.info("Tentative de récupération de l'adresse de l'établissement avec latitude %s et longitude %s (géo id %s)", latitude, longitude, geo_id)
        url = f"https://data.geopf.fr/geocodage/reverse?lon={longitude}&lat={latitude}&index=address&limit=50"
        response = requests.request("GET", url)
        
        if response.status_code != 200 or not response.json().get('features') or len(response.json()['features']) == 0:
            return None
        
        if not geo_id:
            return response.json()['features'][0]['properties'].get('name').upper()

        for feature in response.json()['features']:
            properties = feature['properties']
            if properties.get('id') == geo_id:
                return properties.get('name').upper()

        logging.warning("Aucune adresse trouvée correspondant au geo_id %s pour latitude %s et longitude %s", geo_id, latitude, longitude)
        return None
    except Exception as e:
        logging.error("Erreur lors de la récupération de l'adresse avec latitude et longitude : %s", e, exc_info=True)
        raise

def get_adress_with_siret(siret):
    try:
        logging.info("Tentative de récupération de l'adresse du SIRET "+ siret)
        url = f"https://recherche-entreprises.api.gouv.fr/search?q={siret}&page=1&per_page=1"
        response = requests.request("GET", url)

        results = response.json()['results']
        if response.status_code != 200 or not results or len(results) == 0:
            return None

        siege = results[0]['siege']
        matching_etablissements = results[0]['matching_etablissements']

        if siret == siege.get('siret'):
            entity = siege

            adresses_array = [entity.get('complement_adresse'),
                entity.get('numero_voie'),
                entity.get('indice_repetition'),
                entity.get('type_voie'),
                entity.get('libelle_voie')
            ]

            adresses_clean_array = []
            for adress in adresses_array:
                if adress is not None:
                    adresses_clean_array.append(str(adress))
            
            if entity.get('code_postal') == '[NON-DIFFUSIBLE]':
                adress = '[NON-DIFFUSIBLE]'
            else:
                adress = ' '.join(adresses_clean_array).strip()

        elif len(matching_etablissements)>0 and siret == matching_etablissements[0].get('siret'):
            entity = matching_etablissements[0]
            if entity.get('code_postal') == '[NON-DIFFUSIBLE]':
                adress = '[NON-DIFFUSIBLE]'
            else:
                adress = get_adress_with_lat_lon(entity.get('latitude'), entity.get('longitude'), entity.get('geo_id'))
        else:
            return None

        code_postal = entity.get('code_postal')

        if entity.get('libelle_commune_etranger'):
            libelle_commune = entity.get('libelle_commune_etranger')
        else:
            libelle_commune = entity.get('libelle_commune')
        if entity.get('libelle_pays_etranger'):
            libelle_pays = entity.get('libelle_pays_etranger')
        else:
            libelle_pays = 'FRANCE'

        return_data = {
            'siret': siret,
            'adresse': adress,
            'code_postal': code_postal,
            'libelle_commune': libelle_commune,
            'libelle_pays': libelle_pays
        }
        return return_data
    except Exception as e:
        logging.error("Erreur lors de la récupération de l'adresse pour le SIRET %s : %s", siret, e, exc_info=True)
        raise

def fetch_sheet_data_and_get_adresses(service,full_reload):
    try:
        logging.info("Chargement des données de la feuille Sociétés du fichier Google Sheets TRESOR")
        result = service.spreadsheets().values().get(
            spreadsheetId=PALAM_TRESOR_GOOGLE_SHEET_ID,
            range=GOOGLE_SHEET_NAME
        ).execute()
        
        raw_data = result.get('values', [])
        siret_array = []
        for row in raw_data[1:]:
            if len(row) > 7 and len(row[7])>0:
                if full_reload:
                    siret_array.append(row[7])
                else:
                    if len(row) <= 8 or (len(row) > 8 and len(row[8])==0):
                        siret_array.append(row[7])
        societe_data = []

        logging.info("Début de la récupération des adresses des sociétés")
        for siret in siret_array:
            sleep(0.3)
            societe = get_adress_with_siret(siret)
            if societe:
                societe_data.append(societe)
        return raw_data,societe_data
    except Exception as e:
        logging.error("Erreur lors de la récupération des données de la feuille Sociétés du fichier Google Sheets TRESOR : %s", e, exc_info=True)
        raise

def update_google_sheet(sheet_data, societe_data, service):
    try:
        logging.info("Mise à jour des adresses de la feuille Sociétés du fichier Google Sheets TRESOR")
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
                        requests.append({
                            'range': f"{GOOGLE_SHEET_NAME}!E{row_index + 1}",
                            'values': [[societe['libelle_pays']]]
                        })
        if len(requests)>0:
            body = {'data': requests, 'valueInputOption': 'RAW'}
            service.spreadsheets().values().batchUpdate(
                spreadsheetId=PALAM_TRESOR_GOOGLE_SHEET_ID,
                body=body
            ).execute()
    except Exception as e:
        logging.error("Erreur lors de la mise à jour des adresses de la feuille Sociétés du fichier Google Sheets TRESOR : %s", e, exc_info=True)
        raise