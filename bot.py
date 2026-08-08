import os
import asyncio
import discord
from discord.ext import commands
from openai import OpenAI

TARGET_CHANNEL_ID = 1535672154946019438
ALLOWED_ROLE_ID = 1502023032271671497

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Инициализация OpenAI-клиента с эндпоинтом DeepSeek
deepseek_client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com"
)

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

current_mode = "toxic"
history_messages = []

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
    global history_messages
    if not check_permission(ctx):
        await ctx.send("❌ У вас нет прав для очистки истории.")
        return

    history_messages.clear()
    await ctx.send("🧹 История диалога полностью очищена!")

@bot.event
async def on_ready():
    print(f"Бот {bot.user} запущен и готов к работе через DeepSeek API!")

@bot.event
async def on_message(message: discord.Message):
    if message.author == bot.user:
        return

    await bot.process_commands(message)

    if message.channel.id == TARGET_CHANNEL_ID and not message.content.startswith("!"):
        user_text = f"{message.author.display_name}: {message.content}"
        
        # Добавляем сообщение в историю
        history_messages.append({"role": "user", "content": user_text})

        # Собираем массив сообщений с системным промптом
        messages_payload = [
            {"role": "system", "content": PROMPTS[current_mode]}
        ] + history_messages

        try:
            # Вызов DeepSeek API
            response = await asyncio.to_thread(
                deepseek_client.chat.completions.create,
                model="deepseek-chat",
                messages=messages_payload,
                temperature=1.0,
                max_tokens=1024
            )

            reply_text = response.choices[0].message.content

            if reply_text:
                history_messages.append({"role": "assistant", "content": reply_text})
                
                # Делим слишком длинные ответы на части по 1900 символов
                for i in range(0, len(reply_text), 1900):
                    await message.channel.send(reply_text[i:i+1900])
            else:
                if history_messages:
                    history_messages.pop()
                await message.channel.send("*(Пустой ответ)*")

        except Exception as e:
            if history_messages:
                history_messages.pop()
            print(f"[ОШИБКА DEEPSEEK]: {e}")
            await message.channel.send(f"⚠️ Ошибка API DeepSeek: `{e}`")

bot.run(os.getenv("DISCORD_TOKEN"))
