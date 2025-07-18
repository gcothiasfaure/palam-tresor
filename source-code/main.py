import logging
import datetime
import os
import schedule
from pytz import timezone
import time
from functions import (
    get_google_sheet_service,       
    fetch_sheet_data_and_get_adresses,
    update_google_sheet
)

log_file_path=os.path.join(os.path.join(os.path.abspath(os.path.join(os.getcwd(), "..")), "output"), "app.log")
with open(log_file_path, "w", encoding="utf-8"):
    pass
def timetz(*args):
    return datetime.datetime.now(timezone('Europe/Paris')).timetuple()
logging.Formatter.converter = timetz
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_file_path, encoding="utf-8")
    ]
)
logger = logging.getLogger(__name__)
logging.getLogger("oauth2client").setLevel(logging.WARNING)
logging.getLogger('googleapiclient.discovery_cache').setLevel(logging.WARNING)

def process_adresses_update(force_full_reload=False):
    try:
        logging.info("Début du programme")
        service = get_google_sheet_service()
        if datetime.date.today().isoweekday() == 7 or force_full_reload:
            logging.info("Nous sommes le dimanche (ou le full reload a été forcé), on effectue une recherche des adresses sur toutes les sociétés")
            sheet_data, societe_data = fetch_sheet_data_and_get_adresses(service,full_reload=True)
        else:
            logging.info("Nous ne sommes pas le dimanche, on effectue une recherche des adresses sur les sociétés qui n'ont pas d'adresse renseignée")
            sheet_data, societe_data = fetch_sheet_data_and_get_adresses(service,full_reload=False)
        if len(societe_data)>0:
            logging.info("%d société(s) à mettre à jour",len(societe_data))
            update_google_sheet(sheet_data, societe_data, service)
        else:
            logging.info("Aucune société à mettre à jour")
        logging.info("Fin du programme")
        logging.info("")
    except Exception as e:
        pass

# Programmer l'exécution tous les jours à 03:00
schedule.every().day.at("03:00").do(process_adresses_update)

logging.info("Lancement initial du programme")
logging.info("")
# Première exécution immédiate
process_adresses_update()
while True:
    schedule.run_pending()
    time.sleep(1)