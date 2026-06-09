import requests
from typing import List, Dict, Any
from config import Config


class APIClient:
    
    def __init__(self, base_url: str = None):
        self.base_url = base_url or Config.QURAN_API_URL
        self.mushaf = Config.MUSHAF
        self.page_size = Config.PAGE_SIZE if Config.PAGE_SIZE > 0 else 200
        self.debug_limit = Config.DEBUG_VERSE_LIMIT if Config.DEBUG else None
    
    def get_verses(self) -> List[Dict[str, Any]]:
        all_verses = []
        offset = 0
        
        if Config.DEBUG:
            print(f"🔧 [DEBUG MODE] Getting only {self.debug_limit} verses...")
        else:
            print("📥 Get verses (with pagination)...")
        
        while True:
            response = requests.get(
                f"{self.base_url}/ayahs/",
                params={
                    "mushaf": self.mushaf,
                    "offset": offset
                }
            )
            response.raise_for_status()
            verses = response.json()
            
            if not verses:
                break
            
            all_verses.extend(verses)
            
            if self.debug_limit and len(all_verses) >= self.debug_limit:
                all_verses = all_verses[:self.debug_limit]
                print(f"   ⚠️ [DEBUG] Stopped at {len(all_verses)} verses (limit reached)")
                break
            
            if len(verses) < self.page_size:
                break
            
            offset += self.page_size
            print(f"   📄 offset {offset} → {len(all_verses)} The verse was received")
        
        return all_verses
    
    def get_translations(self, translator_uuid: str) -> List[Dict[str, Any]]:
        all_translations = []
        offset = 0
        
        if Config.DEBUG:
            print(f"🔧 [DEBUG MODE] Getting only {self.debug_limit} translations...")
        else:
            print("📥 Get translations (with pagination)...")
        
        while True:
            response = requests.get(
                f"{self.base_url}/translations/{translator_uuid}/ayahs/",
                params={
                    "mushaf": self.mushaf,
                    "offset": offset
                }
            )
            response.raise_for_status()
            translations = response.json()
            
            if not translations:
                break
            
            all_translations.extend(translations)

            if self.debug_limit and len(all_translations) >= self.debug_limit:
                all_translations = all_translations[:self.debug_limit]
                print(f"   ⚠️ [DEBUG] Stopped at {len(all_translations)} translations (limit reached)")
                break
            
            if len(translations) < self.page_size:
                break
            
            offset += self.page_size
            print(f"   📄 offset {offset} → {len(all_translations)} Translation received")
        
        return all_translations
