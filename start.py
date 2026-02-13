import threading
import time
from app import app
from scraper_exito import ExitoScraper
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Configuración
API_KEY = os.getenv('SCRAPER_API_KEY')
EMAILS_ADMIN = [os.getenv('EMAIL_ADMIN_1'), os.getenv('EMAIL_ADMIN_2')]

def run_flask():
    """Corre el servidor Flask"""
    print("🌐 Iniciando servidor Flask...")
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)

def run_scraper():
    """Corre el scraper de monitoreo"""
    # Esperar 10 segundos para que Flask inicie primero
    time.sleep(10)
    
    print("🤖 Iniciando scraper de monitoreo...")
    scraper = ExitoScraper(API_KEY, email_destinatario=EMAILS_ADMIN)
    scraper.monitorear_inteligente()

if __name__ == '__main__':
    print("="*60)
    print("INICIANDO SISTEMA COMPLETO")
    print("="*60)
    print("Flask: http://localhost:5000")
    print("Scraper: Monitoreo automático")
    print("="*60)
    
    # Iniciar Flask en un thread separado
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    
    # Iniciar scraper en el thread principal
    run_scraper()
