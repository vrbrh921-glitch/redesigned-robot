import subprocess
import os
import sys
import logging
from typing import Optional

# Try to import telebot, install if not available
try:
    import telebot
except ImportError:
    print("Installing pyTelegramBotAPI...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pyTelegramBotAPI"])
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

# Security check - only admin can use the bot
def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID

# Function to execute shell commands safely
def execute_command(command: str, timeout: int = 30) -> tuple[str, bool]:
    """
    Execute a shell command and return output
    Returns: (output_string, success_bool)
    """
    try:
        # Basic security checks
        dangerous_patterns = ['rm -rf', 'format', 'dd', 'mkfs', ':(){:|:&};:', 'chmod 777']
        for pattern in dangerous_patterns:
            if pattern in command.lower():
                return f"⚠️ Command blocked for security reasons: contains '{pattern}'", False
        
        # Execute command
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=os.getcwd()  # Current working directory
        )
        
        output = ""
        if result.stdout:
            output += f"✅ STDOUT:\n{result.stdout}\n"
        if result.stderr:
            output += f"⚠️ STDERR:\n{result.stderr}\n"
        
        return output.strip() or "✅ Command executed (no output)", result.returncode == 0
        
    except subprocess.TimeoutExpired:
        return f"⏰ Command timed out after {timeout} seconds", False
    except Exception as e:
        return f"❌ Error executing command: {str(e)}", False

# Start command
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "⛔ Unauthorized access. You are not allowed to use this bot.")
        return
    
    help_text = """
🤖 *Terminal Bot* 🤖

*Available Commands:*
/start, /help - Show this help message
/cmd <command> - Execute a shell command
/pwd - Show current directory
/ls [path] - List directory contents
/python <code> - Execute Python code

*Examples:*
`/cmd ls -la`
`/cmd pwd`
`/python print("Hello World")`
`/ls /home`

⚠️ *Security Note:* Only you (admin) can use this bot.
"""
    bot.reply_to(message, help_text, parse_mode='Markdown')

# Execute any shell command
@bot.message_handler(commands=['cmd'])
def execute_shell_command(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "⛔ Unauthorized access.")
        return
    
    # Extract command from message
    command_text = message.text.replace('/cmd', '', 1).strip()
    
    if not command_text:
        bot.reply_to(message, "❌ Please provide a command. Example: `/cmd ls -la`", parse_mode='Markdown')
        return
    
    # Show typing indicator
    bot.send_chat_action(message.chat.id, 'typing')
    
    # Execute command
    output, success = execute_command(command_text)
    
    # Truncate if output is too long for Telegram (4096 chars limit)
    if len(output) > 4000:
        output = output[:4000] + "\n... (output truncated)"
    
    # Send result with status emoji
    status = "✅" if success else "❌"
    response = f"{status} *Command:* `{command_text}`\n\n{output}"
    
    bot.reply_to(message, response, parse_mode='Markdown')

# Show current directory
@bot.message_handler(commands=['pwd'])
def show_current_dir(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "⛔ Unauthorized access.")
        return
    
    current_dir = os.getcwd()
    bot.reply_to(message, f"📁 Current directory: `{current_dir}`", parse_mode='Markdown')

# List directory contents
@bot.message_handler(commands=['ls'])
def list_directory(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "⛔ Unauthorized access.")
        return
    
    # Extract path or use current directory
    args = message.text.split()
    path = args[1] if len(args) > 1 else "."
    
    try:
        # List directory
        items = os.listdir(path)
        if not items:
            response = f"📂 Directory `{path}` is empty"
        else:
            # Format nicely
            dirs = [f"📁 {item}/" for item in items if os.path.isdir(os.path.join(path, item))]
            files = [f"📄 {item}" for item in items if os.path.isfile(os.path.join(path, item))]
            
            response = f"📂 Contents of `{path}`:\n"
            if dirs:
                response += "\n*Directories:*\n" + "\n".join(dirs)
            if files:
                response += "\n\n*Files:*\n" + "\n".join(files)
        
        bot.reply_to(message, response, parse_mode='Markdown')
        
    except FileNotFoundError:
        bot.reply_to(message, f"❌ Directory not found: `{path}`", parse_mode='Markdown')
    except PermissionError:
        bot.reply_to(message, f"⛔ Permission denied: `{path}`", parse_mode='Markdown')
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")

# Execute Python code
@bot.message_handler(commands=['python'])
def execute_python_code(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "⛔ Unauthorized access.")
        return
    
    # Extract Python code
    code = message.text.replace('/python', '', 1).strip()
    
    if not code:
        bot.reply_to(message, "❌ Please provide Python code. Example: `/python print('Hello')`", parse_mode='Markdown')
        return
    
    bot.send_chat_action(message.chat.id, 'typing')
    
    try:
        # Create a temporary file to execute the code
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_file = f.name
        
        # Execute the Python code
        result = subprocess.run(
            [sys.executable, temp_file],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        # Clean up
        os.unlink(temp_file)
        
        output = ""
        if result.stdout:
            output += f"✅ Output:\n{result.stdout}\n"
        if result.stderr:
            output += f"⚠️ Errors:\n{result.stderr}\n"
        
        response = f"🐍 *Python Code Executed:*\n```python\n{code}\n```\n\n{output.strip()}"
        bot.reply_to(message, response, parse_mode='Markdown')
        
    except subprocess.TimeoutExpired:
        bot.reply_to(message, "⏰ Python code execution timed out after 30 seconds")
    except Exception as e:
        bot.reply_to(message, f"❌ Error executing Python code: {str(e)}")

# Handle non-command messages
@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "⛔ Unauthorized access.")
        return
    
    bot.reply_to(message, "❓ Unknown command. Use /help to see available commands.")

# Error handler
@bot.message_handler(func=lambda message: True, content_types=['text'])
def handle_errors(message):
    try:
        bot.process_new_messages([message])
    except Exception as e:
        logger.error(f"Error processing message: {e}")
        if is_admin(message.from_user.id):
            bot.reply_to(message, f"❌ Error processing command: {str(e)}")

# Main function
def main():
    logger.info("Starting Terminal Bot...")
    
    # Get bot info
    try:
        bot_info = bot.get_me()
        logger.info(f"Bot username: @{bot_info.username}")
        logger.info(f"Bot ID: {bot_info.id}")
        logger.info(f"Bot name: {bot_info.first_name}")
    except Exception as e:
        logger.error(f"Failed to get bot info: {e}")
    
    # Start polling
    logger.info("Bot is running. Press Ctrl+C to stop.")
    bot.infinity_polling(timeout=60, long_polling_timeout=60)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
