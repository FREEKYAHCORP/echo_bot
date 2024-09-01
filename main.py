import os
from dotenv import load_dotenv
import discord
import asyncio
import json
import itertools
import ijson
import cohere
import requests
from discord.ui import Modal, TextInput, View, Button
from discord import ButtonStyle, Interaction
from util.util import (
    load_messages_from_json, save_messages_to_json, format_conversation,
    use_emoji_llm, send_response_in_chunks, load_prompt, load_context
)
from util.persona import Persona
from openai import AsyncOpenAI
from pathlib import Path
from openai import OpenAI

# Load environment variables from .env file
load_dotenv('config/.env')

openrouter_api_key = os.getenv("OPENROUTER_API_KEY")

# Ensure the API key is set
if not openrouter_api_key:
    raise ValueError("OPENROUTER_API_KEY is not set in the environment variables")

# Initialize OpenAI client with OpenRouter API
client = OpenAI(
    api_key=openrouter_api_key,
    base_url="https://openrouter.ai/api/v1",
)

async_client = AsyncOpenAI(
    api_key=openrouter_api_key,
    base_url="https://openrouter.ai/api/v1",
)

co = cohere.Client(
    api_key=os.getenv("COHERE_API_KEY"),
)

groq_client = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=os.environ.get("GROQ_API_KEY")
)

personas = [
    Persona(openrouter_api_key, co, "echo", Persona.pick_system_prompt("echo"), 0.3, Persona.pick_chat_history("echo")),
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

async def use_persona(persona, message, channel_id):
    persona.messages.append({"role": "user", "content": message})
    
    # Determine which messages to include based on the channel
    if channel_id == 1101508960328102010:
        context_messages = json.loads(persona.chat_history)['conversation'][-10:]
    else:
        context_messages = persona.messages[-10:]  # Only use the last 10 messages for ephemeral contexts
    
    try:
        chat_completion = await async_client.chat.completions.create(
            model="nousresearch/hermes-3-llama-3.1-405b",
            messages=[
                {"role": "system", "content": persona.system_prompt},
                *context_messages,
                {"role": "user", "content": message}
            ],
            temperature=persona.temperature,
        )
        
        if chat_completion and chat_completion.choices:
            assistant_message = {"role": "assistant", "content": chat_completion.choices[0].message.content}
            persona.messages.append(assistant_message)
            
            # Only save chat history for the specific channel
            if channel_id == 1101508960328102010:
                persona.chat_history_append(persona.name, message={"role": "user", "content": message})
                persona.chat_history_append(persona.name, message=assistant_message)
            
            return assistant_message['content']
        else:
            return "I apologize, but I couldn't generate a response at the moment. Please try again later."
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        if isinstance(e, openai.RateLimitError):
            return "I apologize, but the engine's rate limit has been exceeded. We are no longer able to generate responses with the free quota. Please try again later or contact the administrator."
        return "I encountered an error while processing your request. Please try again later."

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
        print("No reaction warranted")
    else:
        worth_replying_prompt = load_prompt("worth_replying")
        worth_replying_context = load_context("worth_replying")
        worth_replying_messages = worth_replying_context["messages"] + [
            {"role": "user", "content": f"Message: {message.content}\n\n{worth_replying_prompt}"}
        ]
        worth_replying_completion = groq_client.chat.completions.create(
            model="llama3-8b-8192",
            messages=worth_replying_messages,
            max_tokens=5
        )
        worth_replying = worth_replying_completion.choices[0].message.content.lower() == "yes"
        print(worth_replying)
        if worth_replying:
            personas[0].is_active = True
            response = await use_persona(personas[0], message.content, message.channel.id)
            try:
                await message.reply(response)  # Changed to reply instead of send
            except discord.errors.HTTPException as e:
                if e.status == 400 and e.code == 50035:  # Invalid Form Body (content too long)
                    # Split the response into chunks of 2000 characters or less
                    chunks = [response[i:i+2000] for i in range(0, len(response), 2000)]
                    for chunk in chunks:
                        await message.channel.send(chunk)
                else:
                    raise  # Re-raise the exception if it's not the specific error we're handling

    if message.author.name == "echo dev#9070":
        print("No reaction warranted")
    else:
        # Load worth reacting prompt and context
        worth_reacting_prompt = load_prompt("worth_reacting")
        worth_reacting_context = load_context("worth_reacting")

        # Prepare messages for worth reacting completion
        worth_reacting_messages = worth_reacting_context["messages"] + [
            {"role": "user", "content": f"Message: {message.content}\n\n{worth_reacting_prompt}"}
        ]

        worth_reacting_completion = groq_client.chat.completions.create(
            model="llama3-8b-8192",
            messages=worth_reacting_messages,
            max_tokens=5
        )
        worth_reacting = worth_reacting_completion.choices[0].message.content.lower() == "yes"

        if worth_reacting:
            # Load emoji prompt and context
            emoji_prompt = load_prompt("emoji")
            emoji_context = load_context("emoji_completion")

            # Prepare messages for emoji completion
            emoji_messages = emoji_context["messages"] + [
                {"role": "user", "content": f"Message: {message.content}\n\n{emoji_prompt}"}
            ]

            emoji_completion = client.chat.completions.create(
                model="meta-llama/llama-3.1-8b-instruct:free",
                messages=emoji_messages,
                max_tokens=5
            )
            suggested_emoji = emoji_completion.choices[0].message.content

            if suggested_emoji:
                try:
                    await message.add_reaction(suggested_emoji)
                except discord.errors.HTTPException as e:
                    if e.status == 400 and e.code == 10014:  # Unknown Emoji
                        print(f"Unknown emoji: {suggested_emoji}")
                    else:
                        raise  # Re-raise the exception if it's not the specific error we're handling

    if isinstance(message.channel, discord.channel.DMChannel) or (discord_client.user and discord_client.user.mentioned_in(message)):
        user_message = f"{message.author.display_name}: {message.content.replace(f'@{discord_client.user.name} ', '').replace(f'<@{discord_client.user.id}> ', '')}"
        print("User message: ", user_message)
        print(f"Message from: {message.author.display_name}")

        active_persona = next((persona for persona in personas if persona.is_active), None)
        if active_persona:
            response = await use_persona(active_persona, user_message, message.channel.id)
            await send_response_in_chunks(message, response)  # Changed to pass message instead of channel
        else:
            # If no persona is active, activate the first one in the list
            if personas:
                personas[0].is_active = True
                response = await use_persona(personas[0], user_message, message.channel.id)
                print(f"Persona response: {response}")
                await send_response_in_chunks(message, response)  # Changed to pass message instead of channel
            else:
                await message.reply("No personas available.")  # Changed to reply instead of send

async def send_response_in_chunks(message, response):
    chunk_size = 2000  # Discord's character limit per message
    for i in range(0, len(response), chunk_size):
        chunk = response[i:i+chunk_size]
        await message.reply(chunk)  # Changed to reply instead of send

# Load the Discord API key from .env file
discord_token = os.getenv("DISCORD_TOKEN")

discord_client.run(discord_token)