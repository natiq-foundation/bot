import random
from typing import List, Dict, Any
from api_client import APIClient
from config import Config


class CacheManager:
    
    def __init__(self):
        self.api_client = APIClient()
        # Cached data
        self.verses: List[Dict[str, Any]] = []
        self.ayah_uuid_to_translation: Dict[str, str] = {}
        self.verse_to_surah: Dict[str, Dict] = {}

        self.is_loaded = False
    
    def load(self):
        print("=" * 50)
        print("Getting data from API...")
        print("=" * 50)
        
        self._load_verses()
        self._load_translations()
        
        self.is_loaded = True
        print("=" * 50)
        print(f"✅ Loading complete!")
        print(f"   - Number of verses: {len(self.verses)}")
        print(f"   - Number of translations: {len(self.ayah_uuid_to_translation)}")
        print("=" * 50)
    
    def _load_verses(self):
        print("📥 Receiving verses...")
        
        verses = self.api_client.get_verses()
        self.verses = verses
        
        current_surah = None
        
        for verse in verses:
            if verse.get('surah') is not None:
                current_surah = verse['surah']
            
            self.verse_to_surah[verse['uuid']] = current_surah
        
        print(f"   ✓ {len(self.verses)} The verse was deleted")
    
    def _load_translations(self):
        print("📥 Get translations...")
        
        translations = self.api_client.get_translations(Config.TRANSLATOR_UUID)
        
        for item in translations:
            self.ayah_uuid_to_translation[item['ayah_uuid']] = item['text']
        
        print(f"   ✓ {len(self.ayah_uuid_to_translation)} The translation was cached")
    
    def get_random_verse(self) -> Dict[str, Any]:
        if not self.is_loaded:
            raise ValueError("Data not loaded.!")
        
        verse = random.choice(self.verses)
        surah = self.verse_to_surah.get(verse['uuid'], {})
        translation = self.ayah_uuid_to_translation.get(
            verse['uuid'], 
            "ترجمه موجود نیست"
        )
        
        return {
            'surah_name': surah.get('names', [{}])[0].get('name', 'نامشخص'),
            'surah_number': surah.get('number', 0),
            'verse_number': verse['number'],
            'verse_text': verse['text'],
            'translation': translation,
            'uuid': verse['uuid']
        }
    
    def format_verse(self, data: Dict[str, Any]) -> str:
        return (
            f"سوره {data['surah_name']}، آیه {data['verse_number']}\n\n"
            f"{data['verse_text']}\n\n"
            f"{data['translation']}"
        )
