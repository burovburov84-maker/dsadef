import os
import asyncio
import discord
from discord.ext import commands
from google import genai
from google.genai import types

TARGET_CHANNEL_ID = 1535672154946019438
ALLOWED_ROLE_ID = 1502023032271671497

# Настройка интентов
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

# Используем префикс ! для команд (работает 100% без слэш-меню)
bot = commands.Bot(command_prefix="!", intents=intents)

# Инициализация Gemini
gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

PROMPTS = {
    "dobri": (
        "Ты — максимально вежливый, дружелюбный и отзывчивый собеседник. "
        "Отвечай тепло, с уважением и готовым помочь тоном."
    ),
    "motiontox": (
        "Ты — максимально токсичный, агрессивный и злой игрок/админ проекта Motion Project CRMP. "
        "Отвечай с жестким матом (нахуй, захуй и т.д.), поливай грязью, рофли над игроками, "
        "унижай за любой вопрос о Motion Project CRMP и общайся в стиле самых сгоревших игроков CRMP."
    ),
    "motiondobri": (
        "Ты — самый добрый, позитивный и любящий фанат и помощник проекта Motion Project CRMP. "
        "С любовью и энтузиазмом рассказывай про Motion Project CRMP, хвали игровое сообщество и помогай всем."
    ),
    "toxic": (
        "Ты — максимально токсичный, агрессивный и грубый собеседник. "
        "Твоя единственная цель — жестко обкладывать матом (нахуй, захуй и т.д.), стебать, унижать "
        "и посылать пользователя в ответ на абсолютно любое его сообщение на любую тему."
    )
}

current_mode = "toxic"
chat_session = None

def get_or_create_chat():
    global chat_session
    if chat_session is None:
        chat_session = gemini_client.chats.create(
            model="gemini-2.5-flash",
            config=types.GenerateContentConfig(
                system_instruction=PROMPTS[current_mode]
            )
        )
    return chat_session

def check_permission(ctx: commands.Context) -> bool:
    if not isinstance(ctx.author, discord.Member):
        return False
    return any(role.id == ALLOWED_ROLE_ID for role in ctx.author.roles)

async def change_mode(ctx: commands.Context, new_mode: str, mode_name: str):
    global current_mode, chat_session
    if not check_permission(ctx):
        await ctx.send("❌ У вас нет прав для изменения режима бота.")
        return

    current_mode = new_mode
    chat_session = gemini_client.chats.create(
        model="gemini-2.5-flash",
        config=types.GenerateContentConfig(
            system_instruction=PROMPTS[current_mode]
        )
    )
    await ctx.send(f"✅ Режим общения изменен на: **{mode_name}**")

# --- Команды через префикс ! ---

@bot.command(name="dobri")
async def cmd_dobri(ctx: commands.Context):
    await change_mode(ctx, "dobri", "Обычное доброе общение")

@bot.command(name="motiontox")
async def cmd_motiontox(ctx: commands.Context):
    await change_mode(ctx, "motiontox", "Токсичное общение (Motion Project CRMP)")

@bot.command(name="motiondobri")
async def cmd_motiondobri(ctx: commands.Context):
    await change_mode(ctx, "motiondobri", "Доброе общение (Motion Project CRMP)")

@bot.command(name="toxic")
async def cmd_toxic(ctx: commands.Context):
    await change_mode(ctx, "toxic", "Токсичное общение с жестким матом")

@bot.command(name="cc")
async def cmd_cc(ctx: commands.Context):
    global chat_session
    if not check_permission(ctx):
        await ctx.send("❌ У вас нет прав для очистки истории.")
        return

    chat_session = gemini_client.chats.create(
        model="gemini-2.5-flash",
        config=types.GenerateContentConfig(
            system_instruction=PROMPTS[current_mode]
        )
    )
    await ctx.send("🧹 История диалога полностью очищена!")

# --- Обработка сообщений ---

@bot.event
async def on_ready():
    print(f"Бот {bot.user} успешно запущен и готов к работе!")

@bot.event
async def on_message(message: discord.Message):
    if message.author == bot.user:
        return

    # Обязательно сначала обрабатываем команды (!toxic, !cc и т.д.)
    await bot.process_commands(message)

    # Общение только в целевом канале
    if message.channel.id == TARGET_CHANNEL_ID and not message.content.startswith("!"):
        try:
            async with message.channel.typing():
                chat = get_or_create_chat()
                prompt = f"{message.author.display_name}: {message.content}"
                
                # Вызываем генерацию ответа в отдельном потоке (asyncio.to_thread), 
                # чтобы не блокировать выполнение бота
                response = await asyncio.to_thread(chat.send_message, prompt)

                if response.text:
                    await message.channel.send(response.text)
        except Exception as e:
            print(f"Ошибка при ответе Gemini: {e}")

bot.run(os.getenv("DISCORD_TOKEN"))
