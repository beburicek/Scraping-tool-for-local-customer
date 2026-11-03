import requests
from bs4 import BeautifulSoup
import time
import schedule
import random
import os
from dotenv import load_dotenv
load_dotenv()

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
DATABASE_ID = os.getenv("DATABASE_ID")
NOTION_VERSION = "2022-06-28"


INTERVAL_MINUTY = 5  
URL_BAZOS = "https://auto.bazos.sk/?hledat=&rubriky=auto&hlokalita=91101&humkreis=75&cenaod=15000&cenado=&order=4&crp=&kitx=ano"


USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15"
]

def nahodne_hlavicky():
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept-Language": "sk-SK,sk;q=0.9,cs;q=0.8,en-US;q=0.7,en;q=0.6",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
    }

def get_notion_headers():
    """Vráti hlavičky potrebné pre komunikáciu s Notion API."""
    return {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Content-Type": "application/json",
        "Notion-Version": NOTION_VERSION
    }

def ziskaj_ulozene_linky_z_notionu():
    """Načíta všetky existujúce linky z Notion databázy, aby sme predišli duplikátom."""
    url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
    ulozene_linky = set()
    has_more = True
    next_cursor = None
    
    while has_more:
        payload = {}
        if next_cursor:
            payload["start_cursor"] = next_cursor
            
        try:
            response = requests.post(url, headers=get_notion_headers(), json=payload, timeout=15)
            if response.status_code != 200:
                print(f" ⚠️ Chyba pri čítaní z Notionu: {response.text}")
                break
                
            data = response.json()
            for result in data.get("results", []):
                props = result.get("properties", {})
                if "link" in props:
                    link_prop = props["link"]
                    # Notion API ukladá URL dáta do kľúča "url"
                    if link_prop.get("type") == "url" and link_prop.get("url"):
                        ulozene_linky.add(link_prop["url"])
                        
            has_more = data.get("has_more", False)
            next_cursor = data.get("next_cursor")
            
        except Exception as e:
            print(f" ⚠️ Zlyhalo pripojenie na Notion: {e}")
            break
            
    return ulozene_linky

def pridaj_do_notionu(nazov, link, lokalita, cena, cas_pridania):
    """Vytvorí nový záznam (stránku) v Notion databáze."""
    url = "https://api.notion.com/v1/pages"
    
    data = {
        "parent": {"database_id": DATABASE_ID},
        "properties": {
            "nazov": {
                "title": [
                    {
                        "text": {
                            "content": nazov
                        }
                    }
                ]
            },
            "link": {
                "url": link
            },
            "cena": {
                "rich_text": [
                    {
                        "text": {
                            "content": cena
                        }
                    }
                ]
            },
            "lokalita": {
                "rich_text": [
                    {
                        "text": {
                            "content": lokalita
                        }
                    }
                ]
            },
            "cas_pridania": {
                "rich_text": [
                    {
                        "text": {
                            "content": cas_pridania
                        }
                    }
                ]
            }
        }
    }
    
    try:
        response = requests.post(url, headers=get_notion_headers(), json=data, timeout=15)
        if response.status_code not in [200, 201]:
            print(f" ⚠️ Chyba pri zápise do Notionu: {response.text}")
            return False
        return True
    except Exception as e:
        print(f" ⚠️ Zlyhalo odoslanie do Notionu: {e}")
        return False

def stiahni_inzeraty():
    print(f"\n[{time.strftime('%H:%M:%S')}] Kontrolujem autá na Bazoši (Odosielam do Notionu)...")
    
    # 1. KROK: Stiahneme z Notionu, čo už máme
    ulozene_linky = ziskaj_ulozene_linky_z_notionu()
    nove_pocet = 0
    
    # 2. KROK: Pozrieme Bazoš
    try:
        odpoved = requests.get(URL_BAZOS, headers=nahodne_hlavicky(), timeout=10)
        
        if odpoved.status_code != 200:
            print(f" ❌ Chyba pripojenia na Bazoš. Status kód: {odpoved.status_code}")
            return
            
        soup = BeautifulSoup(odpoved.text, "html.parser")
        inzeraty = soup.find_all("div", class_="inzeratyflex")
        
        for inzerat in inzeraty:
            nadpis = inzerat.find("h2", class_="nadpis")
            if not nadpis:
                continue
                
            odkaz_element = nadpis.find("a")
            if not odkaz_element or not odkaz_element.has_attr("href"):
                continue
                
            link = f"https://auto.bazos.sk{odkaz_element['href']}"
            
            # Ak tento inzerát ešte v Notione nie je
            if link not in ulozene_linky:
                # Rozdelenie názvu (prvé dve slová)
                plny_nazov = odkaz_element.text.strip()
                nazov_kratky = " ".join(plny_nazov.split()[:2])
                
                # Získanie ceny
                cena_element = inzerat.find("div", class_="inzeratycena")
                cena = cena_element.text.strip() if cena_element else "Neznáma cena"
                
                # Získanie lokality
                lokalita_element = inzerat.find("div", class_="inzeratylok")
                lokalita = lokalita_element.get_text(separator=" ", strip=True) if lokalita_element else "Neznáma lokalita"
                
                # Aktuálny čas
                aktualny_cas = time.strftime('%Y-%m-%d %H:%M:%S')
                
                # Odoslanie dát priamo do API Notionu
                uspesne = pridaj_do_notionu(nazov_kratky, link, lokalita, cena, aktualny_cas)
                
                if uspesne:
                    ulozene_linky.add(link)
                    nove_pocet += 1
                    print(f"✅ Pridané do Notionu: {nazov_kratky} | {lokalita} | {cena}")
                    time.sleep(1) # Krátka pauza, aby sme neposlali priveľa requestov do Notionu naraz
                
    except Exception as e:
        print(f" ❌ Nastala chyba pri kontrole: {e}")
        
    if nove_pocet == 0:
        print(f"[{time.strftime('%H:%M:%S')}] Žiadne nové inzeráty.")
    else:
        print(f"[{time.strftime('%H:%M:%S')}] Pridaných {nove_pocet} nových inzerátov do Notionu.")

if __name__ == "__main__":
    # Skript naštartujeme hneď
    stiahni_inzeraty()
    
    # A potom v 5-minútových intervaloch
    schedule.every(INTERVAL_MINUTY).minutes.do(stiahni_inzeraty)
    
    while True:
        schedule.run_pending()
        time.sleep(1)