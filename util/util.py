import json
import ijson
from pathlib import Path

def save_messages_to_json(messages, file_name):
    with open(file_name, 'w') as f:
        json.dump(messages, f)

def load_messages_from_json(file_name):
    try:
        with open(file_name, 'rb') as f:
            return list(ijson.items(f, 'item'))
    except FileNotFoundError:
        return []

def format_conversation(chat_history, limit=10):
    formatted_conversation = "<conversation>\n"
    for message in chat_history[-limit:]:
        role = "echo" if message['role'] == "assistant" else message['role']
        formatted_conversation += f"  <message>\n    <role>{role}</role>\n    <content>{message['content']}</content>\n  </message>\n"
    formatted_conversation += "</conversation>"
    return formatted_conversation

async def use_emoji_llm(client, messages, model, max_tokens):
    response = client.chat.completions.create(
        messages=messages,
        model=model,
        max_tokens=max_tokens
    )
    return response.choices[0].message.content.strip()

async def send_response_in_chunks(channel, response):
    chunk_size = 1000
    for i in range(0, len(response), chunk_size):
        chunk = response[i:i+chunk_size]
        await channel.send(chunk)

def load_prompt(prompt_name):
    prompt_path = Path(f"/root/projects/echo_rework/prompts/emoji_prompts/{prompt_name}_prompt.txt")
    with open(prompt_path, "r") as f:
        return f.read().strip()

def load_context(context_name):
    context_path = Path(f"/root/projects/echo_rework/prompts/emoji_prompts/{context_name}_context.json")
    with open(context_path, "r") as f:
        return json.load(f)