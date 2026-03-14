#!/usr/bin/env python
# coding: utf-8

import os
import json
import logging
import random
from time import sleep
from urllib.parse import quote

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException, NoSuchElementException

os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler("logs/freework_prod.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
log = logging.getLogger()

COOKIES_FILE = "freework_cookies.json"
# Credentials from environment variables
EMAIL = os.environ.get("FREEWORK_EMAIL")
PASSWORD = os.environ.get("FREEWORK_PASSWORD")

if not EMAIL or not PASSWORD:
    log.error("❌ Erreur: FREEWORK_EMAIL et FREEWORK_PASSWORD doivent être définis dans .env")
    exit(1)

QUERYS = [
  "Full stack developper",  "java", "angular", "spring boot", "Backend Java", "Développeur Java",
    "Java Spring Boot", "Tech Lead Java", "Lead Backend Java", "technical leader", "tech lead",
]

DRY_RUN = False  # The script will now actually click the submit button

TEXT_TEMPLATE = os.environ.get("FREEWORK_TEMPLATE")
if not TEXT_TEMPLATE:
    log.error("❌ Erreur: FREEWORK_TEMPLATE doit être défini dans .env")
    exit(1)

# OpenAI configuration
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
openai_client = None
if OPENAI_AVAILABLE and OPENAI_API_KEY:
    openai_client = OpenAI(api_key=OPENAI_API_KEY)
    log.info("🤖 OpenAI activé – les messages seront personnalisés")
else:
    log.warning("⚠️ OpenAI non disponible – utilisation du template statique")

# Charger le CV pour personnalisation AI
CV_TEXT = ""
try:
    cv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cv.txt")
    with open(cv_path, "r", encoding="utf-8") as f:
        CV_TEXT = f.read()
    log.info(f"📎 CV chargé ({len(CV_TEXT)} chars)")
except FileNotFoundError:
    log.warning("⚠️ Fichier cv.txt non trouvé – utilisation du template de base")

REJECTED_KEYWORDS = [
    "DevSecOps", "Devsec", "frontend", "react", "vue",
    "qa", "test", "automation", "data", "python", "php", ".net", "golang", "rust",
    "sap", "salesforce", "stagiaire", "intern", "stage", "devops",
    "scrum master", "product owner"
]

def generate_personalized_message(job_title, job_description):
    """Génère un message de candidature personnalisé via OpenAI basé sur le CV"""
    if not openai_client:
        return TEXT_TEMPLATE

    # Utiliser le CV complet si disponible, sinon le template
    profile_context = CV_TEXT if CV_TEXT else TEXT_TEMPLATE

    try:
        prompt = f"""Tu es IMAD EL MALLAHI, un Ingénieur Logiciel Fullstack senior qui postule à des missions freelance.

Voici ton CV complet :
---
{profile_context}
---

Voici le titre et la description de l'offre à laquelle tu postules :
Titre : {job_title}
Description : {job_description[:3000]}
---

Rédige un message de candidature court et percutant (max 800 caractères) en français.
Règles strictes :
- Commence par "Bonjour,"
- Mentionne 2-3 expériences ou compétences PRÉCISES de ton CV qui correspondent directement aux exigences de l'offre
- Cite des technologies spécifiques de l'offre que tu maîtrises (ex: Spring Boot 3.X, Angular 16, Kubernetes...)
- Si l'offre mentionne un secteur (bancaire, télédiffusion...), mentionne ton expérience dans ce secteur
- Sois concis, professionnel et enthousiaste
- Termine par "Cordialement, IMAD EL MALLAHI"
- Ne mets PAS de guillemets autour du message
- N'invente JAMAIS de compétences ou d'expériences qui ne sont pas dans ton CV"""

        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=400,
            temperature=0.7,
        )
        message = response.choices[0].message.content.strip()
        # Supprimer les guillemets si le modèle en ajoute
        if message.startswith('"') and message.endswith('"'):
            message = message[1:-1]
        log.info(f"🤖 Message personnalisé généré ({len(message)} chars)")
        return message
    except Exception as e:
        log.warning(f"⚠️ Fallback au template statique: {e}")
        return TEXT_TEMPLATE

def get_driver():
    """Initialise le driver Chrome avec les options appropriées"""
    options = Options()
    
    # Support pour Docker / Chromium
    chrome_bin = os.environ.get("CHROME_BIN")
    if chrome_bin:
        options.binary_location = chrome_bin
        log.info(f"📍 Utilisation du binaire Chrome : {chrome_bin}")

    # Headless mode (par défaut désactivé pour voir le navigateur sur Mac, activé en Docker si HEADLESS=True)
    headless = os.environ.get("HEADLESS", "false").lower() == "true"
    if headless:
        options.add_argument("--headless=new")
        log.info("🌐 Mode headless activé")

    # Utiliser le profil utilisateur par défaut pour mieux passer les détections
    user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    options.add_argument(f"user-agent={user_agent}")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    
    # Désactiver les logs verbeux de Chrome
    options.add_argument("--log-level=3")
    options.add_argument("--silent")

    # Configurer le service Chromedriver si spécifié (ex: Docker)
    driver_service = None
    chromedriver_bin = os.environ.get("CHROMEDRIVER_BIN")
    if chromedriver_bin:
        driver_service = Service(executable_path=chromedriver_bin)

    driver = webdriver.Chrome(options=options, service=driver_service)
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument",
        {"source": "Object.defineProperty(navigator,'webdriver',{get:()=>undefined});"})
    return driver

def wait_for_modal_close(driver, timeout=10):
    """Attend la fermeture de la modale fw-modal"""
    try:
        WebDriverWait(driver, timeout).until(
            EC.invisibility_of_element_located((By.CSS_SELECTOR, "fw-modal"))
        )
        log.info("✓ Modale fermée")
        return True
    except TimeoutException:
        log.warning("⚠️ Modale non fermée dans le délai imparti")
        return False

def login(driver):
    """Effectue la connexion à free-work"""
    log.info("🔐 Connexion...")
    driver.get("https://www.free-work.com/fr/login")
    sleep(3)

    # Essayer de charger les cookies existants
    if os.path.exists(COOKIES_FILE):
        try:
            with open(COOKIES_FILE, "r") as f:
                cookies = json.load(f)
            for c in cookies:
                try:
                    driver.add_cookie(c)
                except:
                    pass
            driver.refresh()
            sleep(4)
            if "login" not in driver.current_url:
                log.info("✅ Connexion par cookies réussie")
                return True
        except Exception as e:
            log.warning(f"Erreur chargement cookies: {e}")

    try:
        # Attendre le champ email et le remplir
        email_field = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='email'], input#email"))
        )
        email_field.send_keys(EMAIL)
        sleep(1)
        
        # Remplir le mot de passe
        password_field = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='password'], input#password"))
        )
        password_field.send_keys(PASSWORD)
        sleep(1)
        
        submit_button = None
        submit_selectors = [
            "//button[@type='submit' and contains(., 'Se connecter')]",
            "//button[@type='submit']",
            "//div[@id='__layout']/div/fw-modal/div/form/div[5]/button"
        ]
        for selector in submit_selectors:
            try:
                submit_button = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, selector))
                )
                break
            except:
                continue
        
        if not submit_button:
            log.error("❌ Bouton de connexion introuvable")
            return False

        driver.execute_script("arguments[0].click();", submit_button)
        sleep(5)
        
        # Vérifier la connexion réussie
        if "login" not in driver.current_url:
            log.info("✅ Connexion réussie!")
            # Sauvegarder les cookies
            try:
                with open(COOKIES_FILE, "w") as f:
                    json.dump(driver.get_cookies(), f)
            except:
                pass
            return True
        else:
            log.error("❌ La connexion a échoué - page de login toujours affichée")
            return False
            
    except TimeoutException as e:
        log.error(f"❌ Timeout lors de la connexion: {e}")
        return False
    except Exception as e:
        log.error(f"❌ Erreur de connexion: {e}")
        return False

def get_search_url(query, page=1):
    """Génère l'URL de recherche pour une requête et une page données"""
    url = (
        f"https://www.free-work.com/fr/tech-it/jobs?"
        f"contracts=permanent&contracts=contractor"
        f"&locations=fr~ile-de-france~~"
        f"&query={quote(query)}"
        f"&remote=full&remote=partial"
    )
    if page > 1:
        url += f"&page={page}"
    return url

def navigate_to_search(driver, query):
    """Navigue vers la page de recherche avec la requête"""
    try:
        url = get_search_url(query)
        driver.get(url)
        sleep(5)
        
        # Attendre le chargement des offres
        WebDriverWait(driver, 15).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.mb-4.relative"))
        )
        log.info(f"✓ Page de recherche chargée pour: {query}")
        return True
    except TimeoutException:
        log.warning(f"⚠️ Timeout lors du chargement de la page pour: {query}")
        return False
    except Exception as e:
        log.error(f"❌ Erreur navigation: {e}")
        return False

def postuler(driver, url, title):
    """Postule à une offre d'emploi"""
    # Vérifier les mots-clés rejetés
    for keyword in REJECTED_KEYWORDS:
        if keyword.lower() in title.lower():
            log.info(f"⭐️ Ignorée (keyword rejeté): {title}")
            return False
    
    log.info(f"📝 {title}")
    try:
        driver.get(url)
        sleep(6)

        # Vérifier si déjà postulé
        try:
            already_applied = driver.find_elements(
                By.XPATH,
                "//*[contains(text(), 'Vous avez déjà postulé')]"
            )
            if already_applied:
                log.info("⚠️ Déjà postulé")
                return False
        except:
            pass

        # Scraper la description de l'offre pour la personnalisation AI
        job_description = ""
        try:
            # Essayer plusieurs sélecteurs spécifiques à Free-Work
            for selector in [
                "section.description",
                "div[class*='description']",
                "div[class*='Detail']",
                "div[class*='content'] div[class*='prose']",
                "article",
                "main",
            ]:
                try:
                    desc_element = driver.find_element(By.CSS_SELECTOR, selector)
                    text = desc_element.text.strip()
                    if len(text) > 100:  # S'assurer qu'on a du contenu significatif
                        job_description = text[:3000]
                        log.info(f"📄 Description trouvée ({len(job_description)} chars)")
                        break
                except:
                    continue
            if not job_description:
                log.warning("⚠️ Description non trouvée, utilisation du titre seul")
        except Exception as e:
            log.warning(f"⚠️ Erreur scraping description: {e}")

        # Générer le message personnalisé via AI
        message = generate_personalized_message(title, job_description)

        # Attendre et trouver le formulaire de candidature
        form = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.ID, "job-application"))
        )
        driver.execute_script("arguments[0].scrollIntoView();", form)
        sleep(2)

        # Remplir le textarea du message
        textarea = WebDriverWait(driver, 15).until(
            EC.visibility_of_element_located((By.ID, "job-application-message"))
        )
        
        # Nettoyer et remplir le champ
        textarea.clear()
        sleep(0.5)
        textarea.send_keys(message)
        sleep(1)
        log.info("✏️ Message rempli")

        # Trouver et cliquer sur le bouton de soumission
        # Utiliser plusieurs stratégies de recherche pour plus de robustesse
        selectors = [
            "//button[@type='submit' and contains(., 'Je postule')]",
            "//button[contains(text(), 'Je postule')]",
            "//div[@id='job-application']//button[@type='submit']",
            "//button[contains(., 'postule')]"
        ]
        
        submit = None
        for selector in selectors:
            try:
                submit = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, selector))
                )
                log.info(f"✓ Bouton de soumission trouvé avec: {selector}")
                break
            except:
                continue
        
        if not submit:
            log.warning("❌ Bouton de soumission introuvable")
            return False

        if DRY_RUN:
            log.info("🧪 [DRY RUN] Bouton trouvé, mais non cliqué (mode test)")
            return True

        # Cliquer sur le bouton
        driver.execute_script("arguments[0].click();", submit)
        sleep(3)
        
        # Attendre la confirmation
        try:
            success_message = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'postulat')]"))
            )
            log.info("✅ Envoyée")
            return True
        except TimeoutException:
            log.info("✅ Envoyée (pas de confirmation visible)")
            return True
        
    except Exception as e:
        log.error(f"❌ Erreur: {e}")
        return False

def run():
    """Fonction principale"""
    driver = get_driver()
    sent = 0

    try:
        # Connexion
        if not login(driver):
            log.error("❌ Impossible de se connecter")
            return

        # Parcourir les recherches
        for query in QUERYS:
            log.info(f"🔍 Recherche : {query}")

            for page in range(1, 11):
                log.info(f"📄 Page {page}")

                url = get_search_url(query, page)
                driver.get(url)
                sleep(6)

                # Attendre les offres
                try:
                    cards = WebDriverWait(driver, 15).until(
                        EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.mb-4.relative"))
                    )
                except TimeoutException:
                    log.info("❌ Aucune offre trouvée (timeout)")
                    break
                
                if not cards:
                    log.info("❌ Aucune offre trouvée")
                    break
                
                log.info(f"📌 {len(cards)} offres trouvées")

                # COLLECTER les liens pour éviter StaleElementReferenceException
                jobs_to_apply = []
                for card in cards:
                    try:
                        a = card.find_element(By.CSS_SELECTOR, "h2 a")
                        title = a.text.strip()
                        href = a.get_attribute("href").split("?")[0]
                        jobs_to_apply.append({"title": title, "href": href})
                    except:
                        continue

                # Traiter chaque offre collectée
                for job in jobs_to_apply:
                    try:
                        if postuler(driver, job["href"], job["title"]):
                            sent += 1
                            # Random sleep pour éviter les blocages
                            sleep(random.uniform(5, 8))
                        else:
                            sleep(2)
                    except Exception as e:
                        log.warning(f"Erreur traitement offre '{job['title']}': {e}")
                        continue

                sleep(4)
        
        log.info(f"🎉 Terminé! {sent} candidatures envoyées")

    except Exception as e:
        log.error(f"💥 Erreur: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    while True:
        log.info("🚀 Démarrage du cycle")
        run()
        log.info("💤 Attente 4 heures...")
        sleep(14400)  # 4 heures
