import os
import discord
from discord.ext import commands
from google import genai
from google.genai import types

TARGET_CHANNEL_ID = 1535672154946019438
ALLOWED_ROLE_ID = 1502023032271671497

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Инициализация клиента Gemini
gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

PROMPTS = {
    "dobri": (
        "Ты — максимально вежливый, дружелюбный и отзывчивый собеседник. "
        "Отвечай тепло, с уважением и готовым помочь тоном."
    ),
    "motiontox": (
        "Ты — максимально токсичный, агрессивный и злой игрок/админ проекта Motion Project CRMP. "
        "Отвечай с жестким матом, поливай грязью, рофли над игроками, "
        "унижай за любой вопрос о Motion Project CRMP и общайся в стиле сгоревших игроков."
    ),
    "motiondobri": (
        "Ты — самый добрый, позитивный и любящий фанат и помощник проекта Motion Project CRMP. "
        "С любовью и энтузиазмом рассказывай про Motion Project CRMP, хвали игровое сообщество и помогай всем."
    ),
    "toxic": (
        "Ты — максимально токсичный, агрессивный и грубый собеседник. "
        "Твоя цель — жестко обкладывать матом, стебать, унижать и посылать пользователя в ответ на абсолютно любое его сообщение."
    )
}

SAFETY_SETTINGS = [
    types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_HARASSMENT, threshold=types.HarmBlockThreshold.BLOCK_NONE),
    types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH, threshold=types.HarmBlockThreshold.BLOCK_NONE),
    types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT, threshold=types.HarmBlockThreshold.BLOCK_NONE),
    types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT, threshold=types.HarmBlockThreshold.BLOCK_NONE),
]

current_mode = "toxic"
history_contents = []  # Массив для хранения истории диалога

def check_permission(ctx: commands.Context) -> bool:
    if not isinstance(ctx.author, discord.Member):
        return False
    return any(role.id == ALLOWED_ROLE_ID for role in ctx.author.roles)

async def change_mode(ctx: commands.Context, new_mode: str, mode_name: str):
    global current_mode
    if not check_permission(ctx):
        await ctx.send("❌ У вас нет прав для изменения режима бота.")
        return

    current_mode = new_mode
    await ctx.send(f"✅ Режим общения изменен на: **{mode_name}**")

# --- Команды ---

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
    await change_mode(ctx, "toxic", "Токсичное общение с матом")

@bot.command(name="cc")
async def cmd_cc(ctx: commands.Context):
    global history_contents
    if not check_permission(ctx):
        await ctx.send("❌ У вас нет прав для очистки истории.")
        return

    history_contents.clear()
    await ctx.send("🧹 История диалога полностью очищена!")

# --- Обработка сообщений ---

@bot.event
async def on_ready():
    print(f"Бот {bot.user} успешно запущен и готов к работе!")

@bot.event
async def on_message(message: discord.Message):
    if message.author == bot.user:
        return

    await bot.process_commands(message)

    if message.channel.id == TARGET_CHANNEL_ID and not message.content.startswith("!"):
        try:
            async with message.channel.typing():
                user_text = f"{message.author.display_name}: {message.content}"
                
                # Добавляем сообщение пользователя в историю
                history_contents.append(
                    types.Content(role="user", parts=[types.Part.from_text(text=user_text)])
                )

                # Настройка генерации с учетом инструкции, фильтров и модели
                config = types.GenerateContentConfig(
                    system_instruction=PROMPTS[current_mode],
                    safety_settings=SAFETY_SETTINGS,
                )

                # Используем нативный асинхронный клиент gemini_client.aio
                response = await gemini_client.aio.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=history_contents,
                    config=config
                )

                reply_text = response.text if response.text else ""

                if reply_text:
                    # Добавляем ответ бота в историю диалога
                    history_contents.append(
                        types.Content(role="model", parts=[types.Part.from_text(text=reply_text)])
                    )

                    # Отправляем ответ частями, если он больше 1900 символов
                    for i in range(0, len(reply_text), 1900):
                        await message.channel.send(reply_text[i:i+1900])
                else:
                    print("Ошибок нет, но модель вернула пустой результат.")

        except Exception as e:
            print(f"[КРИТИЧЕСКАЯ ОШИБКА GEMINI]: {e}")

bot.run(os.getenv("DISCORD_TOKEN"))
