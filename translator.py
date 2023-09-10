import json

class Translator():

    __slots__ = ("data")

    def __init__(self):
        with open('ietf_langs.json', 'r', encoding='utf-8') as f:
            self.data = json.load(f)

    def get_message(self, lang: str, msg: str) -> str:
        """
        Returns the translated message according to file 'ietf_langs.json'.

        :param lang: The language_code (string) provided by the telegram bot
        :param msg: The message (string) that's being required.
            Example: 'start' for the introduction message or 'help' for the informational message

        The translation for all supported languages was made using chat-gpt
        """
        return self.data[lang]["messages"][msg]