import argparse, json, logging, os, random, asyncio, openai
from telegram import Update
from telegram.constants import ChatAction, ParseMode
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
openai.api_key = os.getenv('OPENAI_API_KEY')

SESSION_DATA = {}

# Load configuration
def load_configuration():
    with open('configuration.json', 'r') as file:
        return json.load(file)

CONFIG = load_configuration()
VALID_MODELS = CONFIG.get('valid_models', {})
VISION_MODELS = CONFIG.get('vision_models', [])

# Decorators
def get_session_id(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        session_id = str(update.effective_chat.id if update.effective_chat.type in ['group', 'supergroup'] else update.effective_user.id)
        return await func(update, context, session_id, *args, **kwargs)
    return wrapper

def check_trigger(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        message = update.message.text.lower()
        if (update.message.chat.type in ['group', 'supergroup']) and ("aleeya" not in message and "admin" not in message and not any(greet in message for greet in ['assalamualaikum', 'salam'])):
            return
        return await func(update, context, *args, **kwargs)
    return wrapper

# Response from OpenAI
async def get_openai_response(messages):
    try:
        response = await openai.ChatCompletion.acreate(
            model=CONFIG['default_session_values']['model'],
            messages=messages,
            temperature=CONFIG['default_session_values']['temperature'],
            max_tokens=CONFIG['default_session_values']['max_tokens']
        )
        return response.choices[0].message.content
    except Exception as e:
        return "Maaf, ada masalah sambungan. Sila cuba lagi."

# Main handler
@check_trigger
@get_session_id
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE, session_id):
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    if session_id not in SESSION_DATA:
        SESSION_DATA[session_id] = {"chat_history": []}

    user_message = update.message.text
    SESSION_DATA[session_id]['chat_history'].append({"role": "user", "content": user_message})

    # Apply system prompt at beginning
    messages = [{"role": "system", "content": CONFIG['default_session_values']['system_prompt']}] + SESSION_DATA[session_id]['chat_history']

    # Delay natural 33–60s
    await asyncio.sleep(random.randint(33, 60))

    # Get response
    reply_text = await get_openai_response(messages)

    # Remove symbol —
    reply_text = reply_text.replace("—", "-")

    # Reply short and natural
    await update.message.reply_text(reply_text, parse_mode=ParseMode.HTML)

# Simple commands
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hai! Saya Aleeya. 😊 Taip 'Hi Aleeya' kalau nak tanya apa-apa!")

# Register handlers
def register_handlers(app):
    app.add_handler(CommandHandler('start', start_command))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))

# Main runner
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--debug', action='store_true')
    args = parser.parse_args()
    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.disable(logging.CRITICAL)

    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    register_handlers(application)

    print("Bot is running...")
    application.run_polling()

if __name__ == '__main__':
    main()
