import json
import os

class Persona:
    def __init__(self, groq_client, co_client, name, system_prompt, temperature, chat_history):
        self.name = name
        self.messages = []
        self.system_prompt = system_prompt
        self.groq_client = groq_client
        self.co_client = co_client
        self.temperature = temperature
        self.is_active = False
        self.chat_history = chat_history
    
    
    def pick_system_prompt(self):
        with open(f"/root/projects/echo_rework/prompts/bot_prompts/txt/{self.name}_system_prompt.txt", "r") as file:
            return file.read()

    def pick_chat_history(self):
        with open(f"/root/projects/echo_rework/data/bot_history/chat_{self.name}_history.json", "r") as file:
            return file.read()
    
    def chat_history_append(self, message):
        self.chat_history = json.dumps({"conversation": json.loads(self.chat_history)['conversation'] + [message]})
        with open(f"/root/projects/echo_rework/data/bot_history/chat_{self.name}_history.json", "w") as file:
            file.write(self.chat_history)

    async def use_persona(self, message):
        self.messages.append({"role": "user", "content": message})
        response = self.groq_client.chat.completions.create(
            model="llama-3.1-70b-versatile",
            messages=[
                {"role": "system", "content": self.system_prompt},
                *json.loads(self.chat_history)['conversation'][-10:],
                *self.messages
            ],
            temperature=self.temperature,
        )
        self.messages.append({"role": "assistant", "content": response.choices[0].message.content})
        self.chat_history_append({"role": "user", "content": message})
        self.chat_history_append({"role": "assistant", "content": response.choices[0].message.content})
        return response.choices[0].message.content

    @classmethod
    def pick_system_prompt(cls, name):
        with open(f"/root/projects/echo_rework/prompts/bot_prompts/txt/{name}_system_prompt.txt", "r") as file:
            return file.read()

    @classmethod
    def pick_chat_history(cls, name):
        with open(f"/root/projects/echo_rework/data/bot_history/chat_{name}_history.json", "r") as file:
            return file.read()

    @classmethod
    def chat_history_append(cls, name, message):
        chat_history = cls.pick_chat_history(name)
        chat_history = json.dumps({"conversation": json.loads(chat_history)['conversation'] + [message]})
        with open(f"/root/projects/echo_rework/data/bot_history/chat_{name}_history.json", "w") as file:
            file.write(chat_history)