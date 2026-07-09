import logging
from typing import List

import requests

from services.messengers.base import (
    MessengerAdapter,
    NormalizedMessage,
)

logger = logging.getLogger(__name__)


class Adapter(MessengerAdapter):

    supports_polling = True


    def __init__(
        self,
        token: str,
        api_base_url: str,
        platform: str,
        timeout: int = 30,
    ):

        self.platform = platform

        api_base_url = api_base_url.rstrip("/")

        self.api_url = (
            f"{api_base_url}/bot{token}"
        )

        self.timeout = timeout
        self.offset = 0

        logger.info(
            "Messenger initialized: %s",
            self.platform,
        )


    def get_updates(self) -> List[NormalizedMessage]:

        try:

            response = requests.get(
                f"{self.api_url}/getUpdates",
                params={
                    "offset": self.offset,
                    "timeout": 30,
                },
                timeout=self.timeout + 5,
            )

            data = response.json()


            if not data.get("ok"):
                return []


            messages = []


            for update in data.get("result", []):

                self.offset = (
                    update["update_id"] + 1
                )


                if "message" not in update:
                    continue


                message = update["message"]
                chat = message["chat"]


                messages.append(
                    NormalizedMessage(

                        platform=self.platform,

                        chat_id=str(
                            chat["id"]
                        ),

                        chat_type=chat.get(
                            "type",
                            "private",
                        ),

                        text=message.get(
                            "text",
                            "",
                        ),

                        username=chat.get(
                            "username"
                        ),

                        first_name=chat.get(
                            "first_name"
                        ),

                        title=chat.get(
                            "title"
                        ),

                        raw=update,
                    )
                )


            return messages


        except Exception as e:

            logger.error(
                "[%s] get_updates error: %s",
                self.platform,
                e,
            )

            return []



    def send_message(
        self,
        chat_id: str,
        text: str,
        reply_markup: dict = None,
        parse_mode: str = None,
    ) -> bool:


        payload = {
            "chat_id": chat_id,
            "text": text,
        }


        if reply_markup:
            payload["reply_markup"] = reply_markup


        if parse_mode:
            payload["parse_mode"] = parse_mode



        try:

            response = requests.post(
                f"{self.api_url}/sendMessage",
                json=payload,
                timeout=self.timeout,
            )


            data = response.json()


            if not data.get("ok"):

                logger.error(
                    "[%s] send failed: %s",
                    self.platform,
                    data,
                )

                return False


            return True


        except Exception as e:

            logger.error(
                "[%s] send_message error: %s",
                self.platform,
                e,
            )

            return False
