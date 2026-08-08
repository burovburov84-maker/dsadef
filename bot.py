import os
import discord
from discord import app_commands
from google import genai
from google.genai import types

TARGET_CHANNEL_ID = 1535672154946019438
ALLOWED_ROLE_ID = 1502023032271671497

# Определение системных инструкций
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

class MotionBot(discord.Client):
    def __init__(self):
        # Используем безопасный набор интентов, чтобы не падало с ошибкой
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

bot = MotionBot()

# Инициализация Gemini
gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# Хранилище настроек и истории
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

def check_permission(interaction: discord.Interaction) -> bool:
    if not isinstance(interaction.user, discord.Member):
        return False
    return any(role.id == ALLOWED_ROLE_ID for role in interaction.user.roles)

async def change_mode(interaction: discord.Interaction, new_mode: str, mode_name: str):
    global current_mode, chat_session
    if not check_permission(interaction):
        await interaction.response.send_message("❌ У вас нет прав для изменения режима бота.", ephemeral=True)
        return

    current_mode = new_mode
    
    # Смена режима и пересоздание чата
    chat_session = gemini_client.chats.create(
        model="gemini-2.5-flash",
        config=types.GenerateContentConfig(
            system_instruction=PROMPTS[current_mode]
        )
    )
    
    await interaction.response.send_message(f"✅ Режим общения изменен на: **{mode_name}**")

# --- Слэш-команды ---

@bot.tree.command(name="dobri", description="Переключить на нормальное/доброе общение")
async def cmd_dobri(interaction: discord.Interaction):
    await change_mode(interaction, "dobri", "Обычное доброе общение")

@bot.tree.command(name="motiontox", description="Переключить на токсичное общение про Motion Project CRMP")
async def cmd_motiontox(interaction: discord.Interaction):
    await change_mode(interaction, "motiontox", "Токсичное общение (Motion Project CRMP)")

@bot.tree.command(name="motiondobri", description="Переключить на доброе общение про Motion Project CRMP")
async def cmd_motiondobri(interaction: discord.Interaction):
    await change_mode(interaction, "motiondobri", "Доброе общение (Motion Project CRMP)")

@bot.tree.command(name="toxic", description="Переключить на токсичное общение с матами")
async def cmd_toxic(interaction: discord.Interaction):
    await change_mode(interaction, "toxic", "Токсичное общение с жестким матом")

@bot.tree.command(name="cc", description="Очистить историю контекста диалога")
async def cmd_cc(interaction: discord.Interaction):
    global chat_session
    if not check_permission(interaction):
        await interaction.response.send_message("❌ У вас нет прав для очистки истории.", ephemeral=True)
        return

    chat_session = gemini_client.chats.create(
        model="gemini-2.5-flash",
        config=types.GenerateContentConfig(
            system_instruction=PROMPTS[current_mode]
        )
    )
    await interaction.response.send_message("🧹 История диалога полностью очищена!")

# --- События ---

@bot.event
async def on_ready():
    # Принудительная синхронизация команд при старте
    try:
        synced = await bot.tree.sync()
        print(f"Успешно синхронизировано {len(synced)} слэш-команд.")
    except Exception as e:
        print(f"Ошибка синхронизации команд: {e}")
        
    print(f"Бот {bot.user} полностью запущен и готов к работе!")

@bot.event
async def on_message(message: discord.Message):
    if message.author == bot.user:
        return

    if message.channel.id == TARGET_CHANNEL_ID:
        try:
            async with message.channel.typing():
                chat = get_or_create_chat()
                prompt = f"{message.author.display_name}: {message.content}"
                response = chat.send_message(prompt)

                if response.text:
                    await message.channel.send(response.text)
        except Exception as e:
            print(f"Ошибка генерации ответа: {e}")

bot.run(os.getenv("DISCORD_TOKEN"))
