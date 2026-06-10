import time
import logging
import requests
from config import Config
from cache_manager import CacheManager
from scheduler import MessageScheduler

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BaleBot:
    
    def __init__(self):
        self.api_url = Config.get_bale_full_api_url()
        self.offset = 0
    
    def _request(self, endpoint: str, **kwargs):   
        url = f"{self.api_url}/{endpoint}"
        response = requests.post(url, **kwargs)
        return response.json()
    
    def get_updates(self) -> list:
        try:
            response = requests.get(
                f"{self.api_url}/getUpdates",
                params={"offset": self.offset, "timeout": 30},
                timeout=35
            )
            data = response.json()
            
            if data.get('ok'):
                return data.get('result', [])
            return []
        
        except Exception as e:
            logger.error(f"Error in receiving the update: {e}")
            return []
    
    def send_message(self, chat_id: int, text: str, reply_markup: dict = None, parse_mode: str = None):
        payload = {
            "chat_id": chat_id,
            "text": text
        }
        
        if reply_markup:
            payload["reply_markup"] = reply_markup
        
        if parse_mode:
            payload["parse_mode"] = parse_mode

        return self._request("sendMessage", json=payload)
    
    def send_verse(self, chat_id: int, cache: CacheManager):
        verse = cache.get_random_verse()
        message = cache.format_verse(verse)
        return self.send_message(chat_id, message, parse_mode="Markdown")
    
    def send_keyboard(self, chat_id: int, text: str):
        reply_markup = {
            "keyboard": [
                [{"text": "📖 ارسال آیه تصادفی"}]
            ],
            "resize_keyboard": True,
            "one_time_keyboard": False
        }
        return self.send_message(chat_id, text, reply_markup)
    
    def process_updates(self, updates: list, cache: CacheManager):
        for update in updates:
            self.offset = update['update_id'] + 1
            
            if 'message' not in update:
                continue
            
            message = update['message']
            chat_id = message['chat']['id']
            text = message.get('text', '')
            
            # Commands
            if text in ['/start', 'شروع']:
                self._handle_start(chat_id)
            
            elif text in ['/random', 'آیه تصادفی', '📖 ارسال آیه تصادفی']:
                self._handle_random(chat_id, cache)
            
            elif text in ['/help', 'راهنما']:
                self._handle_help(chat_id)
            
            elif text in ['/schedule', 'زمان']:
                self._handle_schedule(chat_id)
    
    def _handle_start(self, chat_id: int):
        text = (
            "🤖 *بازو قرآن ناطق*\n\n"
            "سلام! به بازو قرآن ناطق خوش اومدین.\n\n"
            "📚 این بازو آیاتی از قرآن شریف رو به صورت تصادفی\n"
            "به همراه ترجمه فارسی به کانال، گروه و یا شخص ارسال میکنه.\n\n"
            "برای دریافت آیه تصادفی روی دکمه آیه تصادفی کلیک کن"
        )
        self.send_keyboard(chat_id, text)
    
    def _handle_random(self, chat_id: int, cache: CacheManager):
        try:
            self.send_verse(chat_id, cache)
            logger.info(f"✅ Random Ayah send to chat_id: {chat_id}")
        except Exception as e:
            self.send_message(chat_id, "An error occurred!")
            logger.error(f"ERROR: {e}")
    
    def _handle_help(self, chat_id: int):
        text = (
            "📖 *راهنمای بازو*\n\n"
            "✨  *بازو به دو روش می‌تونه آیه بفرسته:*\n"
            " *۱.* هر وقت خواستی، دکمه رو بزن یا بنویس *آیه تصادفی*\n"
            " *۲.* روزانه، طبق ساعتی که مشخص شده به کانال،گروه و کاربر، آیه تصادفی ارسال میکنه.\n\n"
            "❓ *چطور داخل کانال یا گروه آیه روزانه داشته باشم؟*\n"
            "➖ بازو رو به لیست مدیران کانالت اضافه کن\n"
            "➖ هر روز یک آیه تصادفی به صورت خودکار ارسال می‌شه\n"
            "➖ با تایپ دستورات هم میتونی همون لحظه آیه تصادفی داخل گروه یا کانال دریافت کنی\n\n"
            "❓ *چطور داخل بازو آیه تصادفی بگیرم (بدون زمان‌بندی)؟*\n"
            "➖ دکمه *`📖 ارسال آیه تصادفی`* رو بزن\n"
            "➖ یا عبارت *آیه تصادفی* رو تایپ و ارسال کن\n"
            "➖ برات همینجا آيه تصادفی ارسال میشه\n\n"
            "📘 *دستورات (قابل تایپ)*\n"
            "• *(آیه تصادفی)* یا *(📖 ارسال آیه تصادفی)* →  دریافت آیه تصادفی\n"
            "• */schedule* یا *(زمان ارسال خودکار)* → مشاهده زمان ارسال روزانه\n"
            "• */help* یا *(راهنما)* → نمایش همین پیام"
        )
        self.send_message(chat_id, text)
    
    def _handle_schedule(self, chat_id: int):
        text = (
            "⏰ *زمان ارسال خودکار*\n\n"
            f"📢 کانال‌ها و گروه‌ها: ساعت "
            f"{Config.SCHEDULE_PUBLIC_HOUR:02d}:{Config.SCHEDULE_PUBLIC_MINUTE:02d}\n"
            f"👤 کاربران: ساعت "
            f"{Config.SCHEDULE_USER_HOUR:02d}:{Config.SCHEDULE_USER_MINUTE:02d}\n"
            f"🕒 به وقت {Config.SCHEDULE_TIMEZONE}\n\n"
            f"📢 کانال‌ها: {len(Config.get_channel_ids())}\n"
            f"👥 گروه‌ها: {len(Config.get_group_ids())}\n"
            f"👤 کاربران: {len(Config.get_user_ids())}"
        )
        self.send_message(chat_id, text)

def main():
    print("\n" + "=" * 60)
    print("🤖 Natiq Quran Bot - Bale Messenger")
    print("=" * 60)
    
    cache = CacheManager()
    cache.load()
    
    bot = BaleBot()
    
    scheduler = MessageScheduler(bot)
    scheduler.set_cache(cache)
    scheduler.start()
    
    print("\n ===Bot is Ready!===")
    print("-" * 60)
    
    # Main Loop
    while True:
        try:
            updates = bot.get_updates()
            
            if updates:
                bot.process_updates(updates, cache)
        
        except KeyboardInterrupt:
            print("\n\n Bot Stoped.")
            scheduler.stop()
            break
        
        except Exception as e:
            logger.error(f"ERROR: {e}")
            time.sleep(5)


if __name__ == "__main__":
    main()
