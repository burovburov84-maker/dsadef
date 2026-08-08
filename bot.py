import os
import asyncio
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
gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

PROMPTS = {
    "dobri": (
        "Ты — максимально вежливый, дружелюбный и отзывчивый собеседник. "
        "Отвечай тепло, с уважением и готовым помочь тоном."
    ),
    "motiontox": (
        "Ты — сгоревший и злой игрок/админ проекта Motion Project CRMP. "
        "Отвечай агрессивно, с сарказмом, завуалированным матом, используй геймерский и CRMP сленг, "
        "высмеивай пользователей и их вопросы."
    ),
    "motiondobri": (
        "Ты — самый добрый фанат и помощник проекта Motion Project CRMP. "
        "С любовью и энтузиазмом рассказывай про Motion Project CRMP, хвали игровое сообщество и помогай всем."
    ),
    "toxic": (
        "Ты — токсичный, грубый и дерзкий собеседник. "
        "Отвечай с сарказмом, подколами, жестким стебом, используй грубый сленг и завуалированный мат. "
        "Унижай собеседника в ответ на абсолютно любое его сообщение."
    )
}

SAFETY_SETTINGS = [
    types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_HARASSMENT, threshold=types.HarmBlockThreshold.BLOCK_NONE),
    types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH, threshold=types.HarmBlockThreshold.BLOCK_NONE),
    types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT, threshold=types.HarmBlockThreshold.BLOCK_NONE),
    types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT, threshold=types.HarmBlockThreshold.BLOCK_NONE),
]

current_mode = "toxic"
history_contents = []

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
    await change_mode(ctx, "toxic", "Токсичное общение")

@bot.command(name="cc")
async def cmd_cc(ctx: commands.Context):
    global history_contents
    if not check_permission(ctx):
        await ctx.send("❌ У вас нет прав для очистки истории.")
        return

    history_contents.clear()
    await ctx.send("🧹 История диалога полностью очищена!")

@bot.event
async def on_ready():
    print(f"Бот {bot.user} запущен и ready!")

@bot.event
async def on_message(message: discord.Message):
    if message.author == bot.user:
        return

    await bot.process_commands(message)

    if message.channel.id == TARGET_CHANNEL_ID and not message.content.startswith("!"):
        user_text = f"{message.author.display_name}: {message.content}"
        
        # Заносим сообщение в историю
        history_contents.append(
            types.Content(role="user", parts=[types.Part.from_text(text=user_text)])
        )

        config = types.GenerateContentConfig(
            system_instruction=PROMPTS[current_mode],
            safety_settings=SAFETY_SETTINGS,
        )

        try:
            # Прямой вызов API с ограничением по времени
            response = await asyncio.wait_for(
                gemini_client.aio.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=history_contents,
                    config=config
                ),
                timeout=10.0
            )

            reply_text = response.text if response and response.text else None

            if reply_text:
                history_contents.append(
                    types.Content(role="model", parts=[types.Part.from_text(text=reply_text)])
                )
                for i in range(0, len(reply_text), 1900):
                    await message.channel.send(reply_text[i:i+1900])
            else:
                if history_contents:
                    history_contents.pop()
                await message.channel.send("*(Пустой ответ или отклонён фильтром)*")

        except asyncio.TimeoutError:
            if history_contents:
                history_contents.pop()
            await message.channel.send("⚠️ Таймаут: Gemini не ответила за 10 секунд.")
        except Exception as e:
            if history_contents:
                history_contents.pop()
            print(f"[ОШИБКА]: {e}")
            await message.channel.send(f"⚠️ Ошибка: `{e}`")

bot.run(os.getenv("DISCORD_TOKEN"))
