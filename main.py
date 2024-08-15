import os
from dotenv import load_dotenv
from groq import Groq
import groq
import discord
import asyncio
import json
import itertools
import ijson
import cohere
from discord.ui import Modal, TextInput, View, Button
from discord import ButtonStyle, Interaction
from util.util import (
    load_messages_from_json, save_messages_to_json, format_conversation,
    use_emoji_llm, send_response_in_chunks, load_prompt, load_context
)
from util.persona import Persona
from pathlib import Path

# Load environment variables from .env file
load_dotenv('config/.env')

groq_client = Groq(
    api_key=os.getenv("GROQ_API_KEY"),
)

co = cohere.Client(
    api_key=os.getenv("COHERE_API_KEY"),
)

personas = [
  #  Persona(groq_client, co, "jekyll", Persona.pick_system_prompt("jekyll"), 0.1, Persona.pick_chat_history("jekyll")),
#    Persona(groq_client, co, "Hyde", Persona.pick_system_prompt("hyde"), 0.3),
    Persona(groq_client, co, "echo", Persona.pick_system_prompt("echo"), 0.3, Persona.pick_chat_history("echo")),
    # Add more personas here
]

for persona in personas:
    print(f"Name: {persona.name}")
    print(f"System Prompt: {persona.system_prompt[:50]}...")  # Print first 50 characters of system prompt
    print(f"Temperature: {persona.temperature}")
    print(f"Is Active: {persona.is_active}")
    print("---")  # Separator between personas

async def get_active_personas():
    return [persona for persona in personas if persona.is_active]

async def use_persona(persona, message):
    persona.messages.append({"role": "user", "content": message})
    response = persona.groq_client.chat.completions.create(
        model="llama-3.1-70b-versatile",  # Assuming this is the model you want to use
        messages=[
            {"role": "system", "content": persona.system_prompt},
            *json.loads(persona.chat_history)['conversation'][-10:],
            *persona.messages
        ],
        temperature=persona.temperature,
    )
    persona.messages.append({"role": "assistant", "content": response.choices[0].message.content})
    persona.chat_history_append(persona.name, message={"role": "user", "content": message})
    persona.chat_history_append(persona.name, message={"role": "assistant", "content": response.choices[0].message.content})
    return response.choices[0].message.content

intents = discord.Intents.default()
intents.message_content = True

discord_client = discord.Client(intents=intents)

@discord_client.event
async def on_ready():
    print(f"Logged in as {discord_client.user}")
    
@discord_client.event
async def on_message(message):
    if message.author == discord_client.user:
        return
    
    if message.author.name == "echo dev#9070":
        print("No reaction waranteed")
    else:
        worth_replying_prompt = load_prompt("worth_replying")
        worth_replying_context = load_context("worth_replying")
        worth_replying_messages = worth_replying_context["messages"] + [
            {"role": "user", "content": f"Message: {message.content}\n\n{worth_replying_prompt}"}
        ]
        worth_replying = await use_emoji_llm(groq_client, worth_replying_messages, "llama3-8b-8192", 5)
        worth_replying = worth_replying.lower() == "yes"
        print(worth_replying)
        if worth_replying:
            personas[0].is_active = True
            response = await use_persona(personas[0], message.content)
            await message.channel.send(response)

    if message.author.name == "echo dev#9070":
        print("No reaction waranteed")
    else:
        # Load worth reacting prompt and context
        worth_reacting_prompt = load_prompt("worth_reacting")
        worth_reacting_context = load_context("worth_reacting")

        # Prepare messages for worth reacting completion
        worth_reacting_messages = worth_reacting_context["messages"] + [
            {"role": "user", "content": f"Message: {message.content}\n\n{worth_reacting_prompt}"}
        ]

        worth_reacting = await use_emoji_llm(groq_client, worth_reacting_messages, "llama3-70b-8192", 5)
        worth_reacting = worth_reacting.lower() == "yes"

        if worth_reacting:
            # Load emoji prompt and context
            emoji_prompt = load_prompt("emoji")
            emoji_context = load_context("emoji_completion")

            # Prepare messages for emoji completion
            emoji_messages = emoji_context["messages"] + [
                {"role": "user", "content": f"Message: {message.content}\n\n{emoji_prompt}"}
            ]

            suggested_emoji = await use_emoji_llm(groq_client, emoji_messages, "gemma2-9b-it", 5)

            if suggested_emoji:
                await message.add_reaction(suggested_emoji)

    if isinstance(message.channel, discord.channel.DMChannel) or (discord_client.user and discord_client.user.mentioned_in(message)):
        user_message = message.content.replace(f"@{discord_client.user.name} ", "").replace(f"<@{discord_client.user.id}> ", "")
        print("User message: ", user_message)
        print(f"Message from: {message.author.display_name}")

        active_persona = next((persona for persona in personas if persona.is_active), None)
        if active_persona:
            response = await use_persona(active_persona, user_message)
            await send_response_in_chunks(message.channel, response)
        else:
            # If no persona is active, activate the first one in the list
            if personas:
                personas[0].is_active = True
                response = await use_persona(personas[0], user_message)
                print(f"Persona response: {response}")
                await send_response_in_chunks(message.channel, response)
            else:
                await message.channel.send("No personas available.")

async def send_response_in_chunks(channel, response):
    chunk_size = 2000  # Discord's character limit per message
    for i in range(0, len(response), chunk_size):
        chunk = response[i:i+chunk_size]
        await channel.send(chunk)



# Load the Discord API key from .env file
discord_token = os.getenv("DISCORD_TOKEN")

discord_client.run(discord_token)