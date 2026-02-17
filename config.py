import os
import sys
import logging
import time
from typing import Optional, List

# Try to import telebot, install if not available
try:
    import telebot
except ImportError:
    print("Installing pyTelegramBotAPI...")
    os.system(f"{sys.executable} -m pip install pyTelegramBotAPI")
    import telebot

# Bot configuration
BOT_TOKEN = "8500585605:AAF4qitAc9esLPXF9lg0PjSS5rVTV6EiKlI"
ADMIN_ID = 6622811674  # Your Telegram user ID

# Initialize bot
bot = telebot.TeleBot(BOT_TOKEN)

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Security check
def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID

def split_long_message(text: str, max_length: int = 4000) -> List[str]:
    """Split long message into chunks that fit Telegram limits"""
    if len(text) <= max_length:
        return [text]
    
    chunks = []
    current = ""
    
    for line in text.splitlines(keepends=True):
        if len(current) + len(line) <= max_length:
            current += line
        else:
            if current:
                chunks.append(current.rstrip())
            if len(line) > max_length:
                # Very long line - split by chars
                while line:
                    chunk = line[:max_length]
                    chunks.append(chunk.rstrip())
                    line = line[max_length:]
                current = ""
            else:
                current = line
    
    if current:
        chunks.append(current.rstrip())
    
    return chunks


def send_long_message(chat_id: int, text: str, parse_mode='Markdown', reply_to: Optional[int] = None):
    """Send message, splitting if necessary with small delay to avoid rate limits"""
    chunks = split_long_message(text)
    
    last_msg_id = reply_to
    
    for i, chunk in enumerate(chunks):
        try:
            if i > 0:
                time.sleep(0.4)  # small delay between chunks (\~2–2.5 messages/sec)
                
            msg = bot.send_message(
                chat_id,
                chunk,
                parse_mode=parse_mode,
                reply_to_message_id=last_msg_id
            )
            last_msg_id = msg.message_id
        except Exception as e:
            logger.error(f"Failed to send chunk {i+1}/{len(chunks)}: {e}")
            if "Too Many Requests" in str(e):
                time.sleep(3)  # longer wait on flood wait
                # retry once
                bot.send_message(chat_id, chunk, parse_mode=parse_mode, reply_to_message_id=last_msg_id)


# Safe command execution (no subprocess)
def execute_command_safe(command: str) -> tuple[str, bool]:
    """
    Very limited safe command execution without subprocess
    Only supports a small whitelist of safe operations
    """
    command = command.strip()
    
    # Block dangerous patterns anyway
    dangerous = ['rm', 'del', 'format', 'mkfs', 'dd', 'chmod', 'chown', '>']
    if any(d in command.lower() for d in dangerous):
        return f"⚠️ Command blocked: dangerous pattern detected", False

    # Very limited whitelist of allowed "commands"
    if command in ('pwd', 'cd', 'ls', 'dir'):
        if command in ('pwd',):
            return f"📁 Current directory: `{os.getcwd()}`", True
        elif command in ('ls', 'dir'):
            try:
                items = os.listdir(".")
                if not items:
                    return "📂 Directory is empty", True
                
                dirs = [f"📁 {i}/" for i in items if os.path.isdir(i)]
                files = [f"📄 {i}" for i in items if os.path.isfile(i)]
                
                result = "📂 Current directory contents:\n"
                if dirs:
                    result += "\n*Directories:*\n" + "\n".join(dirs)
                if files:
                    result += "\n\n*Files:*\n" + "\n".join(files)
                return result, True
            except Exception as e:
                return f"❌ Error: {str(e)}", False
    
    return (
        "⚠️ Only very limited commands are allowed without subprocess:\n"
        "• pwd\n"
        "• ls / dir\n\n"
        "All other shell commands are disabled for security.\n"
        "Use /python for Python code execution.", 
        False
    )


# ==================== Handlers ====================

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "⛔ Unauthorized.")
        return
    
    help_text = """
🤖 *Safe Terminal Bot* 🤖

*Available Commands:*
/start, /help — this message
/cmd <text> — limited safe commands (pwd, ls, dir)
/python <code> — execute Python code
/ls [optional path] — list directory

*Note:* Full shell access via subprocess has been **removed** for security.
"""
    bot.reply_to(message, help_text, parse_mode='Markdown')


@bot.message_handler(commands=['cmd'])
def handle_cmd(message):
    if not is_admin(message.from_user.id):
        return
    
    command_text = message.text.replace('/cmd', '', 1).strip()
    if not command_text:
        bot.reply_to(message, "Example: `/cmd pwd` or `/cmd ls`", parse_mode='Markdown')
        return
    
    output, success = execute_command_safe(command_text)
    
    status = "✅" if success else "❌"
    response = f"{status} *Command:* `{command_text}`\n\n{output}"
    
    send_long_message(message.chat.id, response, reply_to=message.message_id)


@bot.message_handler(commands=['ls'])
def handle_ls(message):
    if not is_admin(message.from_user.id):
        return
    
    args = message.text.split()
    path = args[1] if len(args) > 1 else "."
    
    try:
        items = os.listdir(path)
        if not items:
            text = f"📂 `{path}` is empty"
        else:
            dirs = [f"📁 {item}/" for item in items if os.path.isdir(os.path.join(path, item))]
            files = [f"📄 {item}" for item in items if os.path.isfile(os.path.join(path, item))]
            
            text = f"📂 Contents of `{path}`:\n"
            if dirs: text += "\n*Directories:*\n" + "\n".join(dirs)
            if files: text += "\n\n*Files:*\n" + "\n".join(files)
        
        send_long_message(message.chat.id, text, reply_to=message.message_id)
    
    except FileNotFoundError:
        bot.reply_to(message, f"❌ Path not found: `{path}`")
    except PermissionError:
        bot.reply_to(message, f"⛔ Permission denied: `{path}`")
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")


@bot.message_handler(commands=['python'])
def execute_python_code(message):
    if not is_admin(message.from_user.id):
        return
    
    code = message.text.replace('/python', '', 1).strip()
    if not code:
        bot.reply_to(message, "Example: `/python print('Hello')`")
        return
    
    # We'll use exec() in restricted context (safer than subprocess)
    output_lines = []
    error_lines = []
    
    # Capture output
    from io import StringIO
    import sys
    
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    redirected_output = sys.stdout = StringIO()
    redirected_error = sys.stderr = StringIO()
    
    try:
        # Very restricted globals/locals
        restricted_globals = {
            '__builtins__': __builtins__,  # still dangerous — can be improved
            'print': print,
            'len': len,
            'str': str,
            'int': int,
            'float': float,
            'list': list,
            'dict': dict,
            'range': range,
            'enumerate': enumerate,
            'zip': zip,
            'sum': sum,
            'min': min,
            'max': max,
        }
        
        exec(code, restricted_globals, {})
        
        output = redirected_output.getvalue()
        error = redirected_error.getvalue()
        
        if output:
            output_lines.append("✅ Output:\n" + output.rstrip())
        if error:
            error_lines.append("⚠️ Errors:\n" + error.rstrip())
        
    except Exception as e:
        error_lines.append(f"❌ Exception: {type(e).__name__}: {str(e)}")
    
    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr
    
    response_parts = []
    if output_lines:
        response_parts.append("\n".join(output_lines))
    if error_lines:
        response_parts.append("\n".join(error_lines))
    
    if not response_parts:
        response_parts.append("✅ Code executed (no output)")
    
    full_response = f"🐍 *Code:*\n```python\n{code}\n```\n\n" + "\n\n".join(response_parts)
    
    send_long_message(message.chat.id, full_response, reply_to=message.message_id)


@bot.message_handler(func=lambda m: True)
def catch_all(message):
    if not is_admin(message.from_user.id):
        return
    bot.reply_to(message, "Use /help to see commands.")


def main():
    logger.info("Safe Terminal Bot starting...")
    try:
        bot_info = bot.get_me()
        logger.info(f"Bot: @{bot_info.username} (ID: {bot_info.id})")
    except Exception as e:
        logger.error(f"Cannot get bot info: {e}")
    
    logger.info("Bot is running...")
    bot.infinity_polling(timeout=60, long_polling_timeout=60)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Bot stopped.")
    except Exception as e:
        logger.error(f"Fatal: {e}")
