import json
import os
from pathlib import Path
from openai import OpenAI

class Persona:
    def __init__(self, openrouter_api_key, co_client, name, system_prompt, temperature, chat_history):
        self.name = name
        self.messages = []
        self.system_prompt = system_prompt
        self.client = OpenAI(
            api_key=openrouter_api_key,
            base_url="https://openrouter.ai/api/v1",
        )
        self.co_client = co_client
        self.temperature = temperature
        self.is_active = False
        self.chat_history = chat_history
    
    def pick_system_prompt(self):
        prompt_path = Path(f"prompts/bot_prompts/txt/{self.name}_system_prompt.txt")
        with open(prompt_path, "r") as file:
            return file.read()

    def pick_chat_history(self):
        history_path = Path(f"data/bot_history/chat_{self.name}_history.json")
        with open(history_path, "r") as file:
            return file.read()
    
    def chat_history_append(self, message):
        self.chat_history = json.dumps({"conversation": json.loads(self.chat_history)['conversation'] + [message]})
        history_path = Path(f"data/bot_history/chat_{self.name}_history.json")
        with open(history_path, "w") as file:
            file.write(self.chat_history)

    async def use_persona(self, message):
        self.messages.append({"role": "user", "content": message})
        chat_completion = self.client.chat.completions.create(
            model="nousresearch/hermes-3-llama-3.1-405b",
            messages=[
                {"role": "system", "content": self.system_prompt},
                *json.loads(self.chat_history)['conversation'][-10:],
                *self.messages
            ],
            temperature=self.temperature,
        )
        response_content = chat_completion.choices[0].message.content
        self.messages.append({"role": "assistant", "content": response_content})
        self.chat_history_append({"role": "user", "content": message})
        self.chat_history_append({"role": "assistant", "content": response_content})
        return response_content

    @classmethod
    def pick_system_prompt(cls, name):
        prompt_path = Path(f"prompts/bot_prompts/txt/{name}_system_prompt.txt")
        with open(prompt_path, "r") as file:
            return file.read()

    @classmethod
    def pick_chat_history(cls, name):
        history_path = Path(f"data/bot_history/chat_{name}_history.json")
        with open(history_path, "r") as file:
            return file.read()

    @classmethod
    def chat_history_append(cls, name, message):
        chat_history = cls.pick_chat_history(name)
        chat_history = json.dumps({"conversation": json.loads(chat_history)['conversation'] + [message]})
        history_path = Path(f"data/bot_history/chat_{name}_history.json")
        with open(history_path, "w") as file:
            file.write(chat_history)