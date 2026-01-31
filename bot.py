# ---------------- bot.py ---------------- #

import sqlite3
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
import os
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from apscheduler.schedulers.background import BackgroundScheduler
import time
from telegram import InputMediaPhoto
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler


TOKEN = "8280647779:AAFlMuHeEg1pULxFuzHqR5FzX4gMQuJLSvU"

# ---------------- DATABASE ---------------- #
conn = sqlite3.connect("bot.db", check_same_thread=False)
cur = conn.cursor()

# Create tables
cur.execute("""CREATE TABLE IF NOT EXISTS users(
    uid INTEGER PRIMARY KEY,
    name TEXT,
    deposit_total REAL DEFAULT 0,
    profit_total REAL DEFAULT 0,
    join_date TEXT,
    referral_count INTEGER DEFAULT 0,
    referral_income REAL DEFAULT 0,
    referred_by INTEGER DEFAULT NULL
)""")

cur.execute("""CREATE TABLE IF NOT EXISTS deposits(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uid INTEGER,
    amount REAL,
    proof TEXT,
    status TEXT DEFAULT 'pending'
)""")

cur.execute("""CREATE TABLE IF NOT EXISTS withdraws(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uid INTEGER,
    amount REAL,
    method TEXT,
    number TEXT,
    status TEXT DEFAULT 'pending'
)""")

# add withdraw_type column if not exists
try:
    cur.execute("ALTER TABLE withdraws ADD COLUMN withdraw_type TEXT")
except:
    pass


# ---------------- EXTRA TABLES (ADDED) ---------------- #

cur.execute("""CREATE TABLE IF NOT EXISTS deposit_dates(
    uid INTEGER PRIMARY KEY,
    last_deposit_date TEXT
)""")

cur.execute("""CREATE TABLE IF NOT EXISTS transactions(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uid INTEGER,
    type TEXT,
    amount REAL,
    note TEXT,
    date TEXT DEFAULT CURRENT_TIMESTAMP
)""")



# ---------------- VERIFICATION TABLE ---------------- #
cur.execute("""CREATE TABLE IF NOT EXISTS verification(
    uid INTEGER PRIMARY KEY,
    name TEXT,
    phone TEXT,
    dob TEXT,
    nid_front TEXT,
    nid_back TEXT,
    selfie TEXT,
    status TEXT DEFAULT 'pending'
)""")


conn.commit()

# ---------------- DAILY PROFIT ---------------- #
def add_daily_profit():
    users = cur.execute("SELECT uid, deposit_total FROM users").fetchall()
    for user in users:
        uid, deposit_total = user
        daily_profit = round(deposit_total * 0.19 / 30, 2)  # 19% monthly profit divided by 30
        # Add daily profit ONLY to profit_total
        cur.execute("UPDATE users SET profit_total = profit_total + ? WHERE uid=?", (daily_profit, uid))
    conn.commit()
    print("✅ Daily profit added to all users")


# ---------------- ADMINS ---------------- #
ADMIN_IDS = [7135321510, 8385404993, 7711788828]  # Replace with your Telegram ID

def is_admin(uid: int) -> bool:
    return uid in ADMIN_IDS

# ---------------- KEYBOARDS ---------------- #
MAIN_KB = ReplyKeyboardMarkup([
     ["👤 প্রোফাইল", "💰 ডিপোজিট"],
    ["💸 Withdraw", "👥 Referral"],
    ["📜 শর্তাবলী", "🛡 Security", "❓ সহায়তা"],
    ["🧾 লেনদেন"]
], resize_keyboard=True)



ADMIN_KB = ReplyKeyboardMarkup([
    ["📥 Pending Deposits", "📤 Pending Withdraws"],
    ["📝 Pending Verification", "👥 Users"],
    ["✏️ Edit Balance"],
    ["Back"]
], resize_keyboard=True)

# ---------------- START ---------------- #
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    name = update.effective_user.first_name
    context.user_data["state"] = None  # Reset state on start

    args = context.args  # gets start parameters like /start 12345
    referred_by = int(args[0]) if args and args[0].isdigit() else None

    # ---------------- USER CREATE ---------------- #
    if not cur.execute("SELECT uid FROM users WHERE uid=?", (uid,)).fetchone():
        cur.execute(
            "INSERT INTO users(uid, name, join_date, referred_by) VALUES(?,?,DATE('now'),?)",
            (uid, name, referred_by)
        )

        # ---- Initialize deposit date (NEW) ----
        cur.execute(
            "INSERT OR IGNORE INTO deposit_dates(uid, last_deposit_date) VALUES(?, DATE('now'))",
            (uid,)
        )

        # ---- Update referral count ----
        if referred_by:
            cur.execute(
                "UPDATE users SET referral_count = referral_count + 1 WHERE uid=?",
                (referred_by,)
            )

        conn.commit()

    # ---------------- WELCOME MESSAGE (UNCHANGED) ---------------- #
    welcome_msg = f"""👋 স্বাগতম {name}, Yahoo! Finance BD-তে!

এখানে বিনিয়োগ করুন এবং উপভোগ করুন নিচের সুবিধাগুলো:
💰 আপনার ডিপোজিট করা টাকার উপর মাসিক ১৯% লাভ।
👥 বন্ধুদের ইনভাইট করুন এবং তারা বিনিয়োগ করলে পান ৫% Referral বোনাস।
💸 প্রয়োজন অনুযায়ী নিরাপদে আপনার লাভ Withdraw করতে পারবেন।
📈 সহজেই আপনার আয় ও বিনিয়োগ ট্র্যাক করুন।

নিয়ম ও নির্দেশিকা:
1️⃣ সর্বনিম্ন ডিপোজিট: ৳৫০০  
2️⃣ সর্বোচ্চ ডিপোজিট: ৳৫০,০০০  
3️⃣ লাভ: মাসিক ১৯%  
4️⃣ Referral বোনাস: বন্ধুর ডিপোজিটের ৫%  
5️⃣ বিনিয়োগকৃত টাকা ৩ মাস পর Withdraw করা যাবে  
6️⃣ সর্বনিম্ন Withdraw লাভের পরিমাণ: ৳৫০০  
7️⃣ সকল ডিপোজিট ও Withdraw এজেন্ট দ্বারা যাচাই করা হয়  
8️⃣ আপনার UID বা সংবেদনশীল তথ্য কারো সাথে শেয়ার করবেন না  


অন্যান্য তথ্য:
🛡 নিরাপত্তা আমাদের সর্বোচ্চ অগ্রাধিকার; সকল লেনদেন ম্যানুয়ালি যাচাই করা হয়।
📜 শর্তাবলী ও সহায়তা মেনু থেকে যেকোনো সময় পাওয়া যাবে।
আজই বিনিয়োগ শুরু করুন এবং আপনার অর্থ বাড়তে দেখুন!
"""


    await update.message.reply_text(welcome_msg, reply_markup=MAIN_KB)


# ---------------- PROFILE ---------------- #
async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["state"] = None

    uid = update.effective_user.id
    user = cur.execute(
        "SELECT uid, name, deposit_total, profit_total, join_date, referral_count, referral_income FROM users WHERE uid=?",
        (uid,)
    ).fetchone()

    if not user:
        await update.message.reply_text("Profile not found.")
        return

    deposit_total = user[2]       # Capital
    profit_total = user[3]        # Profit
    total_balance = deposit_total + profit_total

    monthly_profit = round(deposit_total * 0.19, 2)
    daily_profit = round(monthly_profit / 30, 2)

    deposit_date = cur.execute(
        "SELECT last_deposit_date FROM deposit_dates WHERE uid=?",
        (uid,)
    ).fetchone()
    deposit_date = deposit_date[0] if deposit_date else "N/A"

    
    msg = f"""👤 প্রোফাইল:
UID: `{user[0]}`
নাম: {user[1]}

💵 মূলধন: ৳ {deposit_total}
💰 লাভ: ৳ {profit_total}
📊 মোট ব্যালেন্স: ৳ {total_balance}

📅 দৈনিক লাভ (মূলধন থেকে): ৳ {daily_profit}
📆 মাসিক লাভ (মূলধন থেকে): ৳ {monthly_profit}

যোগদানের তারিখ: {user[4]}
Refer সংখ্যা: {user[5]}
Referral আয়: ৳ {user[6]}"""


    await update.message.reply_text(
        msg,
        parse_mode="Markdown"
    )


# ---------------- USER TRANSACTION HISTORY ---------------- #
async def transactions_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id

    txs = cur.execute(
        """
        SELECT type, amount, date
        FROM transactions
        WHERE uid=?
          AND type IN ('deposit', 'withdraw')
        ORDER BY id DESC
        LIMIT 15
        """,
        (uid,)
    ).fetchall()

    if not txs:
        await update.message.reply_text(
            "🧾 Transaction History:\n\nকোনো Approved লেনদেন পাওয়া যায়নি।",
            reply_markup=MAIN_KB
        )
        return

    msg = "🧾 Transaction History:\n\n"

    for t_type, amount, date in txs:
        emoji = "💰" if t_type == "deposit" else "💸"
        label = "Deposit" if t_type == "deposit" else "Withdraw"

        msg += (
            f"{emoji} {label}\n"
            f"Amount: Tk{amount}\n"
            
        )

    await update.message.reply_text(msg, reply_markup=MAIN_KB)


# ---------------- DEPOSIT FLOW ---------------- #
async def deposit_start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    kb = InlineKeyboardMarkup([
    [
        InlineKeyboardButton("📋 Copy UID", callback_data=f"copy_uid_{update.effective_user.id}"),
        InlineKeyboardButton("📋 Copy Number", callback_data="copy_phone_01845810269")
    ]
])
    await update.message.reply_text(
    
    "💰 ডিপোজিট প্রক্রিয়া (ধাপে ধাপে)\n\n"
        "1️⃣ ডিপোজিট নির্বাচন করুন\n"
        "মেনু থেকে 💰 ডিপোজিট বাটনে ক্লিক করে আপনার ডিপোজিট অনুরোধ শুরু করুন।\n\n"
        "2️⃣ টাকা পাঠান:\n"
        "বিকাশ অথবা নগদের মাধ্যমে:\n"
        "📞 নাম্বার: `01845810269`\n"
        "📌 পেমেন্ট টাইপ: শুধুমাত্র Sent Money\n\n"
        "❌ Cash Out / Payment / ভুল পদ্ধতিতে পাঠানো হলে বাতিল করা হবে\n\n"
        "3️⃣ ডিপোজিট পরিমাণ লিখুন\n"
        "আপনি যে পরিমাণ টাকা পাঠিয়েছেন ঠিক সেই পরিমাণ লিখুন।\n"
        "সর্বনিম্ন ও সর্বোচ্চ সীমা অবশ্যই মানতে হবে।\n\n"
        "4️⃣ পেমেন্ট প্রমাণ আপলোড করুন\n"
        "পেমেন্ট সফল হওয়ার পর একটি পরিষ্কার স্ক্রিনশট নিন।\n"
        "স্ক্রিনশটে অবশ্যই নিচের তথ্যগুলো স্পষ্ট থাকতে হবে:\n"
        "• ট্রানজেকশন আইডি\n"
        "• পরিমাণ\n"
        "• তারিখ ও সময়\n\n"
        "5️⃣ UID জমা দিন\n"
        "আপনার সঠিক UID লিখুন (শুধুমাত্র সংখ্যা)।\n"
        "⚠️ ভুল UID দিলে ডিপোজিট যোগ করা হবে না।\n\n"
        "6️⃣ অ্যাডমিন যাচাই\n"
        "আমাদের এজেন্ট ম্যানুয়ালি আপনার ডিপোজিট যাচাই করবেন।\n"
        "অনুমোদনের পর আপনার ব্যালেন্স স্বয়ংক্রিয়ভাবে আপডেট হবে।\n\n"
        "⚠️ গুরুত্বপূর্ণ নির্দেশনা\n"
        "• অস্পষ্ট বা ভুয়া স্ক্রিনশট বাতিল করা হবে\n"
        "• প্রসেসিং সময় এজেন্ট যাচাইয়ের উপর নির্ভর করে\n"
        "• জমা দেওয়ার আগে সব তথ্য ভালোভাবে যাচাই করুন"
    )
    await update.message.reply_text("ডিপোজিটের পরিমাণ লিখুন (সর্বনিম্ন ৫০০, সর্বোচ্চ ৫০,০০০):")
    context.user_data["state"] = "deposit_amount"


async def deposit_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        amount = float(update.message.text)
        if amount < 500 or amount > 50000:
            raise ValueError
        context.user_data["deposit_amount"] = amount
        await update.message.reply_text("ডিপোজিটের স্ক্রিনশট পাঠান:")
        context.user_data["state"] = "deposit_proof"
    except:
        await update.message.reply_text("ভুল পরিমাণ দেওয়া হয়েছে, আবার চেষ্টা করুন:")


async def deposit_proof(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.photo:
        file_id = update.message.photo[-1].file_id
    elif update.message.document:
        file_id = update.message.document.file_id
    else:
        await update.message.reply_text("অনুগ্রহ করে স্ক্রিনশট ছবি অথবা ডকুমেন্ট পাঠান!")
        return

    context.user_data["deposit_proof"] = file_id
    await update.message.reply_text("আপনার UID লিখুন (শুধুমাত্র সংখ্যা):")
    context.user_data["state"] = "deposit_uid"


async def deposit_uid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid_input = update.message.text
    if not uid_input.isdigit():
        await update.message.reply_text("ভুল UID, শুধুমাত্র সংখ্যা ব্যবহার করুন!")
        return

    deposit_amount_val = context.user_data.get("deposit_amount")
    deposit_proof_val = context.user_data.get("deposit_proof")

    # ---------------- SAVE DEPOSIT ---------------- #
    cur.execute(
        "INSERT INTO deposits(uid, amount, proof) VALUES(?,?,?)",
        (int(uid_input), deposit_amount_val, deposit_proof_val)
    )
    conn.commit()

    # ---------------- TRANSACTION LOG (ADDED) ---------------- #
    cur.execute(
        "INSERT INTO transactions(uid, type, amount, note) VALUES(?,?,?,?)",
        (int(uid_input), "deposit_request", deposit_amount_val, "Deposit submitted")
    )
    conn.commit()

    # ---------------- NOTIFY ADMINS ---------------- #
    for admin_id in ADMIN_IDS:
        await context.bot.send_message(
            admin_id,
            f"💰 New Diposit Request!\nUID: {uid_input}\nAmount: ৳{deposit_amount_val}"
        )

    await update.message.reply_text(
        "✅ আপনার ডিপোজিট অনুরোধ সফলভাবে জমা হয়েছে। এজেন্টের অনুমোদনের অপেক্ষায় থাকুন।",
        reply_markup=MAIN_KB
    )
    context.user_data["state"] = None


# ---------------- WITHDRAW FLOW ---------------- #

# Function to validate withdraw amount
def is_valid_withdraw_amount(amount):
    return 500 <= amount <= 50000


async def withdraw_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id

    # ---------------- PENDING WITHDRAW PROTECTION ---------------- #
    pending = cur.execute(
        "SELECT id FROM withdraws WHERE uid=? AND status='pending'",
        (uid,)
    ).fetchone()

    if pending:
        await update.message.reply_text(
            "❌ আপনার একটি Withdraw অনুরোধ ইতিমধ্যে Pending অবস্থায় আছে।\n"
            "অনুগ্রহ করে সেটি সম্পন্ন হওয়া পর্যন্ত অপেক্ষা করুন।",
            reply_markup=MAIN_KB
        )
        return

    await update.message.reply_text(

    "💸 Withdraw প্রক্রিয়া (ধাপে ধাপে)\n\n"

    "1️⃣ Withdraw নির্বাচন করুন\n"
    "মেইন মেনু থেকে 💸 Withdraw বাটনে ক্লিক করে আপনার Withdraw অনুরোধ শুরু করুন।\n\n"

    "2️⃣ Withdraw ধরন নির্বাচন করুন\n"
    "আপনি Profit অথবা Capital Withdraw করতে পারবেন।\n\n"

    "3️⃣ Withdraw পরিমাণ লিখুন\n"
    "⚠️ সর্বনিম্ন Withdraw পরিমাণ: ৳৫০০\n\n"

    "4️⃣ পেমেন্ট মাধ্যম নির্বাচন করুন\n"
    "• বিকাশ\n"
    "• নগদ\n\n"

    "5️⃣ পেমেন্ট নাম্বার লিখুন\n\n"

    "6️⃣ এজেন্ট যাচাই\n"
    "এজেন্ট যাচাইয়ের পর পেমেন্ট পাঠানো হবে।"
    )

    kb = ReplyKeyboardMarkup(
        [
            ["💰 Withdraw Profit"],
            ["🏦 Withdraw Capital"],
            ["Back"]
        ],
        resize_keyboard=True
    )

    await update.message.reply_text(
        "Withdraw ধরন নির্বাচন করুন:",
        reply_markup=kb
    )

    context.user_data["state"] = "withdraw_type"


async def withdraw_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    uid = update.effective_user.id

    if text == "💰 Withdraw Profit":
        context.user_data["withdraw_type"] = "profit"
        context.user_data["state"] = "withdraw_amount"
        await update.message.reply_text(
            "💸 আপনার লাভ থেকে Withdraw পরিমাণ লিখুন (সর্বনিম্ন ৫০০, সর্বোচ্চ ৫০,০০০):"
        )

    elif text == "🏦 Withdraw Capital":
        last_date = cur.execute(
            "SELECT last_deposit_date FROM deposit_dates WHERE uid=?",
            (uid,)
        ).fetchone()

        if not last_date:
            await update.message.reply_text(
                "❌ ডিপোজিট তথ্য পাওয়া যায়নি।",
                reply_markup=MAIN_KB
            )
            context.user_data["state"] = None
            return

        months_passed = cur.execute(
            "SELECT (julianday('now') - julianday(?)) / 30",
            (last_date[0],)
        ).fetchone()[0]

        if months_passed < 3:
            await update.message.reply_text(
                "❌ আপনার মূলধন ৩ মাস পূর্ণ না হওয়ায় Withdraw করা যাবে না।",
                reply_markup=MAIN_KB
            )
            context.user_data["state"] = None
            return

        context.user_data["withdraw_type"] = "capital"
        context.user_data["state"] = "withdraw_amount"
        await update.message.reply_text(
            "🏦 আপনার মূলধন থেকে Withdraw পরিমাণ লিখুন (সর্বনিম্ন ৫০০, সর্বোচ্চ ৫০,০০০):"
        )

    else:
        await update.message.reply_text("অনুগ্রহ করে বাটন ব্যবহার করুন!")


async def withdraw_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.text.isdigit():
        await update.message.reply_text("শুধুমাত্র সংখ্যা লিখুন!")
        return

    amount = float(update.message.text)
    uid = update.effective_user.id
    withdraw_type = context.user_data.get("withdraw_type")

    if withdraw_type == "profit":
        user = cur.execute(
            "SELECT profit_total FROM users WHERE uid=?",
            (uid,)
        ).fetchone()
        available = user[0]

    elif withdraw_type == "capital":
        user = cur.execute(
            "SELECT deposit_total FROM users WHERE uid=?",
            (uid,)
        ).fetchone()
        available = user[0]

    else:
        await update.message.reply_text("❌ Withdraw টাইপ সনাক্ত করা যায়নি।")
        return

    if amount > available:
        await update.message.reply_text(
            f"❌ আপনার প্রাপ্য ব্যালেন্সের বেশি Withdraw করা যাবে না। সর্বোচ্চ: ৳{available}"
        )
        return

    if not is_valid_withdraw_amount(amount):
        await update.message.reply_text(
            "❌ ভুল পরিমাণ! সর্বনিম্ন ৫০০ এবং সর্বোচ্চ ৫০,০০০। আবার চেষ্টা করুন:"
        )
        return

    context.user_data["withdraw_amount"] = amount
    kb = ReplyKeyboardMarkup([["Bkash", "Nagad"]], resize_keyboard=True)
    await update.message.reply_text("পেমেন্ট মাধ্যম নির্বাচন করুন:", reply_markup=kb)
    context.user_data["state"] = "withdraw_method"


async def withdraw_method(update: Update, context: ContextTypes.DEFAULT_TYPE):
    method = update.message.text
    if method not in ["Bkash", "Nagad"]:
        await update.message.reply_text("অনুগ্রহ করে বাটন থেকে নির্বাচন করুন!")
        return

    context.user_data["withdraw_method"] = method
    await update.message.reply_text("আপনার বিকাশ / নগদ নাম্বার লিখুন:")
    context.user_data["state"] = "withdraw_number"


async def withdraw_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    number = update.message.text.strip()

    if not number.isdigit():
        await update.message.reply_text("শুধুমাত্র সংখ্যা লিখুন!")
        return

    withdraw_amount_val = context.user_data.get("withdraw_amount")
    method_val = context.user_data.get("withdraw_method")
    withdraw_type = context.user_data.get("withdraw_type")
    uid = update.effective_user.id

    cur.execute(
        "INSERT INTO withdraws(uid, amount, method, number, withdraw_type) VALUES(?,?,?,?,?)",
        (uid, withdraw_amount_val, method_val, number, withdraw_type)
    )
    conn.commit()

    cur.execute(
        "INSERT INTO transactions(uid, type, amount, note) VALUES(?,?,?,?)",
        (uid, "withdraw_request", withdraw_amount_val, f"{withdraw_type} withdraw submitted")
    )
    conn.commit()

    for admin_id in ADMIN_IDS:
        await context.bot.send_message(
            admin_id,
            f"💸 New Withdraw Request!\n"
            f"UID: {uid}\n"
            f"Type: {withdraw_type.upper()}\n"
            f"Amount: ৳{withdraw_amount_val}\n"
            f"Method: {method_val}\n"
            f"Number: {number}"
        )

    context.user_data["state"] = None

    await update.message.reply_text(
        "✅ আপনার Withdraw অনুরোধ সফলভাবে জমা হয়েছে। এজেন্টের অনুমোদনের অপেক্ষায় থাকুন।",
        reply_markup=MAIN_KB
    )



# ---------------- REFERRAL BUTTON ---------------- #
async def referral(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["state"] = None
    uid = update.effective_user.id
    user = cur.execute(
        "SELECT referral_count, referral_income, profit_total FROM users WHERE uid=?",
        (uid,)
    ).fetchone()
    if not user:
        await update.message.reply_text("প্রোফাইল পাওয়া যায়নি।", reply_markup=MAIN_KB)
        return

    referral_count, referral_income, profit_total = user
    total_referral = referral_income  # Already included in profit_total

    msg = f"""👥 Referral তথ্য:

✅ আপনার Refer সংখ্যা: {referral_count}
💰 আপনার Referral আয়: ৳{total_referral}
🔗 আপনার Referral লিংক: https://t.me/YahooFinanceBD_bot?start={uid}

বন্ধুদের আমন্ত্রণ জানান এবং তাদের ডিপোজিটের উপর ৫% বোনাস আয় করুন!"""
    await update.message.reply_text(msg, reply_markup=MAIN_KB)



# ---------------- TERMS BUTTON ---------------- #
async def terms(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["state"] = None
    msg = (
    "📜 শর্তাবলী – Yahoo! Finance BD\n\n"
    "Yahoo! Finance BD ব্যবহার করার মাধ্যমে আপনি নিচের শর্তাবলীতে সম্মত হচ্ছেন। "
    "বিনিয়োগ করার আগে অনুগ্রহ করে শর্তগুলো মনোযোগ দিয়ে পড়ুন।\n\n"

    "1️⃣ যোগ্যতা\n"
    "- ব্যবহারকারীকে অবশ্যই সঠিক ও বৈধ তথ্য প্রদান করতে হবে।\n\n"
    
    "2️⃣ ডিপোজিট\n"
    "- সর্বনিম্ন ডিপোজিট: ৳৫০০\n"
    "- সর্বোচ্চ ডিপোজিট: ৳৫০,০০০\n"
    "- শুধুমাত্র অনুমোদিত পেমেন্ট মাধ্যমের মাধ্যমে ডিপোজিট গ্রহণ করা হয়।\n"
    "- সকল ডিপোজিট সক্রিয় করার আগে এজেন্ট দ্বারা ম্যানুয়ালি যাচাই করা হয়।\n\n"

    "3️⃣ লাভ নীতিমালা\n"
    "- পরিকল্পনার শর্ত অনুযায়ী মাসিক ১৯% হারে লাভ গণনা করা হয়।\n"
    "- লাভ সিস্টেম পারফরম্যান্স ও সক্রিয় বিনিয়োগ সময়ের উপর নির্ভরশীল।\n\n"
    
    "4️⃣ বিনিয়োগ লক পিরিয়ড\n"
    "- বিনিয়োগকৃত মূলধন ৩ মাসের আগে Withdraw করা যাবে না।\n"
    "- আগাম Withdraw অনুরোধ স্বয়ংক্রিয়ভাবে বাতিল করা হবে।\n\n"

    "5️⃣ Withdraw\n"
    "- সর্বনিম্ন Withdraw লাভ: ৳৫০০\n"
    "- এজেন্ট যাচাইয়ের পর Withdraw অনুরোধ প্রসেস করা হয়।\n"
    "- নিরাপত্তা যাচাইয়ের কারণে প্রসেসিং সময় পরিবর্তিত হতে পারে।\n\n"

    "6️⃣ Referral প্রোগ্রাম\n"
    "- Referral বোনাস: রেফার করা ইউজারের ডিপোজিটের ৫%।\n"
    "- রেফার করা ইউজারের ডিপোজিট যাচাই হওয়ার পরই বোনাস যোগ করা হয়।\n\n"
    
    "7️⃣ নিরাপত্তা ও গোপনীয়তা\n"
    "- আপনার UID, পাসওয়ার্ড বা পেমেন্ট সংক্রান্ত তথ্য কারো সাথে শেয়ার করবেন না।\n"
    "- ব্যবহারকারীর অবহেলার কারণে হওয়া ক্ষতির জন্য Yahoo! Finance BD দায়ী নয়।\n\n"
    
    "8️⃣ এজেন্টের অধিকার\n"
    "- এজেন্ট যেকোনো লেনদেন যাচাই বা বাতিল করার অধিকার রাখে।\n"
    "- জালিয়াতি বা অপব্যবহারের ক্ষেত্রে অ্যাকাউন্ট স্থগিত করা হতে পারে।\n"
    "- প্রয়োজনে এজেন্ট পরিকল্পনা, নিয়ম বা লাভের হার পরিবর্তন করতে পারে।\n\n"

    "🔟 নীতিমালা আপডেট\n"
    "- শর্তাবলী যেকোনো সময় পূর্ব নোটিশ ছাড়াই পরিবর্তন হতে পারে।\n"
    "- Yahoo! Finance BD ব্যবহার চালিয়ে যাওয়া মানে আপডেটকৃত শর্তাবলীতে সম্মতি।"
    )

    await update.message.reply_text(msg, reply_markup=MAIN_KB)


# ---------------- SECURITY BUTTON ---------------- #
async def security(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["state"] = None
    msg = (
    "🛡 নিরাপত্তা নির্দেশনা – Yahoo! Finance BD\n\n"
    "আপনার অ্যাকাউন্টের নিরাপত্তা আমাদের জন্য অত্যন্ত গুরুত্বপূর্ণ। "
    "অ্যাকাউন্ট নিরাপদ রাখতে অনুগ্রহ করে নিচের নিয়মগুলো অনুসরণ করুন।\n\n"

    "1️⃣ অ্যাকাউন্ট নিরাপত্তা\n"
    "- আপনার UID, পাসওয়ার্ড, OTP বা পেমেন্ট সংক্রান্ত তথ্য কারো সাথে শেয়ার করবেন না।\n"
    "- Yahoo! Finance BD-এর কোনো এজেন্ট কখনোই আপনার পাসওয়ার্ড বা ব্যক্তিগত তথ্য চাইবে না।\n"
    "- আপনার অ্যাকাউন্ট ব্যবহার করে করা সব কার্যক্রমের দায়িত্ব আপনার।\n\n"

    "2️⃣ লেনদেন নিরাপত্তা\n"
    "- সকল ডিপোজিট ও Withdraw এজেন্ট দ্বারা ম্যানুয়ালি যাচাই করা হয়।\n"
    "- অফিসিয়াল চ্যানেলের বাইরে কাউকে এজেন্ট দাবি করে টাকা পাঠাবেন না।\n\n"
    
    "4️⃣ ডিভাইস ও অ্যাক্সেস\n"
    "- শেয়ারড বা পাবলিক ডিভাইস ব্যবহার করলে অবশ্যই লগ আউট করুন।\n"
    "- Yahoo! Finance BD-এর সাথে কোনো পরিবর্তিত অ্যাপ, বট বা থার্ড-পার্টি টুল ব্যবহার করবেন না।\n"
    "- আপনার ডিভাইসকে ম্যালওয়্যার ও অননুমোদিত অ্যাক্সেস থেকে সুরক্ষিত রাখুন।\n\n"

    "⚠️ গুরুত্বপূর্ণ নোটিস\n"
    "নিরাপত্তা নিয়ম অনুসরণ না করলে সাময়িক বা স্থায়ীভাবে অ্যাকাউন্ট স্থগিত করা হতে পারে।\n\n"
    "সতর্ক থাকুন। নিরাপদ থাকুন। Yahoo! Finance BD-এর সাথে দায়িত্বশীলভাবে বিনিয়োগ করুন।"
)

    await update.message.reply_text(msg, reply_markup=MAIN_KB)

# ---------------- HELP BUTTON ---------------- #
async def help_center(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["state"] = None
    msg = (
    "🆘 সহায়তা ও সাপোর্ট – Yahoo! Finance BD\n\n"
    "আপনার যেকোনো প্রয়োজনে আমরা আপনাকে সহায়তা করতে প্রস্তুত। "
    "দ্রুত সেবা পাওয়ার জন্য নিচের নির্দেশনাগুলো অনুগ্রহ করে পড়ুন।\n\n"

    "1️⃣ সাপোর্টের প্রাপ্যতা\n"
    "- ডিপোজিট, Withdraw, Referral এবং অ্যাকাউন্ট সংক্রান্ত যেকোনো সমস্যার জন্য সহায়তা পাওয়া যায়।\n"
    "- সাপোর্ট শুধুমাত্র অফিসিয়াল Yahoo! Finance BD চ্যানেলের মাধ্যমেই প্রদান করা হয়।\n\n"

    "2️⃣ সহায়তা পাওয়ার উপায়\n"
    "- যেকোনো সমস্যা বা প্রশ্নের জন্য আমাদের অফিসিয়াল সাপোর্ট এজেন্টের সাথে যোগাযোগ করুন।\n"
    "- সাপোর্ট এজেন্ট: @Agent_Rafsan\n"
    "- সাপোর্টে যোগাযোগ করার সময় অবশ্যই আপনার UID এবং সমস্যার বিস্তারিত উল্লেখ করুন।\n\n"

    "3️⃣ উত্তর দেওয়ার সময়\n"
    "- অনুরোধের সংখ্যার উপর নির্ভর করে সাপোর্ট রিপ্লাই দিতে কিছুটা সময় লাগতে পারে।\n"
    "- একই সমস্যার জন্য বারবার মেসেজ পাঠানো থেকে বিরত থাকুন।\n\n"

    "4️⃣ সাপোর্ট নিয়মাবলি\n"
    "- গালিগালাজ বা স্প্যাম করলে সাপোর্ট বিলম্বিত বা বন্ধ করা হতে পারে।\n"
    "- ভুয়া দাবি বা বিভ্রান্তিকর তথ্য দিলে অ্যাকাউন্ট পর্যালোচনা করা হবে।\n"
    "- যাচাই শেষে সাপোর্টের সিদ্ধান্ত চূড়ান্ত বলে গণ্য হবে।\n\n"

    "5️⃣ নিরাপত্তা সতর্কতা\n"
    "- আপনার পাসওয়ার্ড, OTP বা গোপন পেমেন্ট তথ্য কারো সাথে শেয়ার করবেন না।\n"
    "- সংবেদনশীল তথ্য শেয়ার করার ফলে হওয়া ক্ষতির জন্য Yahoo! Finance BD দায়ী নয়।\n\n"

    "📌 গুরুত্বপূর্ণ\n"
    "শুধুমাত্র অফিসিয়াল Yahoo! Finance BD সাপোর্ট থেকে আসা মেসেজে বিশ্বাস করুন। "
    "কেউ সাপোর্ট সেজে যোগাযোগ করলে দ্রুত রিপোর্ট করুন।\n\n"
    "Yahoo! Finance BD বেছে নেওয়ার জন্য ধন্যবাদ। আপনাকে সহায়তা করতে পেরে আমরা আনন্দিত।"
)

    await update.message.reply_text(msg, reply_markup=MAIN_KB)




# ---------------- ADMIN PANEL ---------------- #
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    context.user_data["state"] = None

    if not is_admin(uid):
        await update.message.reply_text("You are not authorized.")
        return

    await update.message.reply_text(
        "Admin Panel:",
        reply_markup=ReplyKeyboardMarkup([
            ["📥 Pending Deposits", "📤 Pending Withdraws"],
            ["📝 Pending Verification", "👥 Users"],
            ["✏️ Edit Balance"],
            ["Back"]
        ], resize_keyboard=True)
    )


# ---------------- ADMIN BUTTONS ---------------- #
async def admin_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    context.user_data["state"] = None

    # ---------------- PENDING DEPOSITS ---------------- #
    if text == "📥 Pending Deposits":
        pending = cur.execute(
            "SELECT id, uid, amount, proof FROM deposits WHERE status='pending'"
        ).fetchall()

        if not pending:
            await update.message.reply_text("No pending deposits.")
            return

        for dep_id, uid, amount, proof in pending:
            kb = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("✅ Approve", callback_data=f"approve_dep_{dep_id}"),
                    InlineKeyboardButton("❌ Reject", callback_data=f"reject_dep_{dep_id}")
                ]
            ])
            await update.message.reply_photo(
                photo=proof,
                caption=f"Deposit ID: {dep_id}\nUID: {uid}\nAmount: Tk{amount}",
                reply_markup=kb
            )

    # ---------------- PENDING WITHDRAWS ---------------- #
    elif text == "📤 Pending Withdraws":
        pending = cur.execute(
            "SELECT id, uid, amount, method, number, withdraw_type "
            "FROM withdraws WHERE status='pending'"
        ).fetchall()

        if not pending:
            await update.message.reply_text("No pending withdraws.")
            return

        for wd_id, uid, amount, method, number, withdraw_type in pending:
            user = cur.execute(
                "SELECT deposit_total, profit_total FROM users WHERE uid=?",
                (uid,)
            ).fetchone()

            deposit_total = user[0]
            profit_total = user[1]

            kb = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("✅ Approve", callback_data=f"approve_wd_{wd_id}"),
                    InlineKeyboardButton("❌ Reject", callback_data=f"reject_wd_{wd_id}")
                ]
            ])

            await update.message.reply_text(
                f"Withdraw ID: {wd_id}\n"
                f"UID: {uid}\n"
                f"Type: {withdraw_type.upper()}\n"
                f"Amount: Tk{amount}\n"
                f"Method: {method}\n"
                f"Number: {number}\n\n"
                f"User Deposit: Tk{deposit_total}\n"
                f"User Profit: Tk{profit_total}",
                reply_markup=kb
            )

    # ---------------- PENDING VERIFICATION ---------------- #
    elif text == "📝 Pending Verification":
        pending_users = cur.execute(
            "SELECT uid, name, phone, dob, nid_front, nid_back, selfie "
            "FROM verification WHERE status='pending'"
        ).fetchall()

        if not pending_users:
            await update.message.reply_text("No users pending verification.")
            return

        for uid, name, phone, dob, nid_front, nid_back, selfie in pending_users:
            await update.message.reply_text(
                f"📝 Pending Verification\n\nUID: {uid}\nName: {name}\nPhone: {phone}\nDOB: {dob}"
            )

            media = [
                InputMediaPhoto(media=nid_front, caption="Document: NID Front"),
                InputMediaPhoto(media=nid_back, caption="Document: NID Back"),
                InputMediaPhoto(media=selfie, caption="Document: Selfie")
            ]
            await context.bot.send_media_group(
                chat_id=update.effective_chat.id,
                media=media
            )

            kb = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("✅ Approve", callback_data=f"approve_user_{uid}"),
                    InlineKeyboardButton("❌ Reject", callback_data=f"reject_user_{uid}")
                ]
            ])
            await update.message.reply_text("Approve or Reject this user:", reply_markup=kb)

    # ---------------- USERS LIST ---------------- #
    elif text == "👥 Users":
        users = cur.execute(
            "SELECT uid, name, deposit_total, profit_total, join_date, referral_count, referral_income FROM users"
        ).fetchall()

        if not users:
            await update.message.reply_text("No users found.")
            return

        for uid, name, deposit, profit, join_date, ref_count, ref_income in users:
            phone = cur.execute(
                "SELECT phone FROM verification WHERE uid=?",
                (uid,)
            ).fetchone()
            phone = phone[0] if phone else "N/A"

            await update.message.reply_text(
                f"UID: {uid}\nName: {name}\nPhone: {phone}\n"
                f"Deposit: Tk{deposit}\nProfit: Tk{profit}\n"
                f"Join Date: {join_date}\n"
                f"Referral Count: {ref_count}\nReferral Income: Tk{ref_income}"
            )

    # ---------------- EDIT BALANCE ---------------- #
    elif text == "✏️ Edit Balance":
        await update.message.reply_text("Enter UID:")
        context.user_data["state"] = "admin_edit_uid"

    # ---------------- BACK ---------------- #
    elif text == "Back":
        await update.message.reply_text("Returning to main menu.", reply_markup=MAIN_KB)

# ---------------- ADMIN CALLBACK ---------------- #
async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    # ---------------- APPROVE DEPOSIT ---------------- #
    if data.startswith("approve_dep_"):
        dep_id = int(data.split("_")[-1])

        dep = cur.execute(
            "SELECT uid, amount FROM deposits WHERE id=?",
            (dep_id,)
        ).fetchone()

        if not dep:
            await query.edit_message_caption("❌ Deposit not found.")
            return

        uid, amount = dep

        cur.execute(
            "UPDATE users SET deposit_total = deposit_total + ? WHERE uid=?",
            (amount, uid)
        )

        cur.execute(
            "INSERT OR REPLACE INTO deposit_dates(uid, last_deposit_date) VALUES(?, DATE('now'))",
            (uid,)
        )

        cur.execute(
            "UPDATE deposits SET status='approved' WHERE id=?",
            (dep_id,)
        )

        referrer = cur.execute(
            "SELECT referred_by FROM users WHERE uid=?",
            (uid,)
        ).fetchone()[0]

        if referrer:
            bonus = round(amount * 0.05, 2)
            cur.execute(
                "UPDATE users SET profit_total = profit_total + ?, referral_income = referral_income + ? WHERE uid=?",
                (bonus, bonus, referrer)
            )
            await context.bot.send_message(
                referrer,
                f"💰 আপনি UID {uid} এর ডিপোজিট থেকে Tk{bonus} Referral বোনাস পেয়েছেন!"
            )

        conn.commit()

        cur.execute(
            "INSERT INTO transactions(uid, type, amount, note) VALUES(?,?,?,?)",
            (uid, "deposit", amount, "Deposit approved")
        )
        conn.commit()

        await query.edit_message_caption("✅ Deposit approved.")
        await context.bot.send_message(
            uid,
            f"✅ আপনার Tk{amount} ডিপোজিট সফলভাবে অনুমোদিত হয়েছে!"
        )

    # ---------------- REJECT DEPOSIT ---------------- #
    elif data.startswith("reject_dep_"):
        dep_id = int(data.split("_")[-1])

        cur.execute(
            "UPDATE deposits SET status='rejected' WHERE id=?",
            (dep_id,)
        )
        conn.commit()

        await query.edit_message_caption("❌ Deposit rejected.")
        await context.bot.send_message(
            uid,
            "❌ আপনার ডিপোজিট অনুরোধটি বাতিল করা হয়েছে। বিস্তারিত জানতে সাপোর্টে যোগাযোগ করুন।"
        )

    # ---------------- APPROVE WITHDRAW ---------------- #
    elif data.startswith("approve_wd_"):
        wd_id = int(data.split("_")[-1])

        wd = cur.execute(
            "SELECT uid, amount, withdraw_type FROM withdraws WHERE id=?",
            (wd_id,)
        ).fetchone()

        if not wd:
            await query.edit_message_text("❌ Withdraw not found.")
            return

        uid, amount, withdraw_type = wd

        deposit_total, profit_total = cur.execute(
            "SELECT deposit_total, profit_total FROM users WHERE uid=?",
            (uid,)
        ).fetchone()

        # ---------- PROFIT WITHDRAW ---------- #
        if withdraw_type == "profit":
            if amount > profit_total:
                await query.edit_message_text("❌ Insufficient profit balance.")
                await context.bot.send_message(
                    uid,
                    "❌ আপনার লাভের ব্যালেন্স পর্যাপ্ত নয়।"
                )
                return

            cur.execute(
                "UPDATE users SET profit_total = profit_total - ? WHERE uid=?",
                (amount, uid)
            )

        # ---------- CAPITAL WITHDRAW ---------- #
        elif withdraw_type == "capital":
            last_date = cur.execute(
                "SELECT last_deposit_date FROM deposit_dates WHERE uid=?",
                (uid,)
            ).fetchone()

            if not last_date:
                await query.edit_message_text("❌ Capital withdraw locked (3 months not completed).")
                await context.bot.send_message(
                    uid,
                    "❌ আপনার মূলধন এখনও ৩ মাস লক অবস্থায় আছে।"
                )
                return

            months_passed = cur.execute(
                "SELECT (julianday('now') - julianday(?)) / 30",
                (last_date[0],)
            ).fetchone()[0]

            if months_passed < 3:
                await query.edit_message_text("❌ Capital withdraw locked (3 months not completed).")
                await context.bot.send_message(
                    uid,
                    "❌ আপনার মূলধন এখনও ৩ মাস পূর্ণ করেনি।"
                )
                return

            if amount > deposit_total:
                await query.edit_message_text("❌ Insufficient capital balance.")
                await context.bot.send_message(
                    uid,
                    "❌ আপনার মূলধনের ব্যালেন্স পর্যাপ্ত নয়।"
                )
                return

            cur.execute(
                "UPDATE users SET deposit_total = deposit_total - ? WHERE uid=?",
                (amount, uid)
            )

        cur.execute(
            "UPDATE withdraws SET status='approved' WHERE id=?",
            (wd_id,)
        )

        conn.commit()

        cur.execute(
            "INSERT INTO transactions(uid, type, amount, note) VALUES(?,?,?,?)",
            (uid, "withdraw", amount, f"{withdraw_type} withdraw approved")
        )
        conn.commit()

        await query.edit_message_text("✅ Withdraw approved.")
        await context.bot.send_message(
            uid,
            f"✅ আপনার Tk{amount} Withdraw সফলভাবে অনুমোদিত হয়েছে!"
        )

    # ---------------- REJECT WITHDRAW ---------------- #
    elif data.startswith("reject_wd_"):
        wd_id = int(data.split("_")[-1])

        cur.execute(
            "UPDATE withdraws SET status='rejected' WHERE id=?",
            (wd_id,)
        )
        conn.commit()

        await query.edit_message_text("❌ Withdraw rejected.")
        await context.bot.send_message(
            uid,
            "❌ আপনার Withdraw অনুরোধটি বাতিল করা হয়েছে। বিস্তারিত জানতে সাপোর্টে যোগাযোগ করুন।"
        )

    # ---------------- APPROVE USER VERIFICATION ---------------- #
    elif data.startswith("approve_user_"):
        uid_to_approve = int(data.split("_")[-1])

        cur.execute(
            "UPDATE verification SET status='approved' WHERE uid=?",
            (uid_to_approve,)
        )
        conn.commit()

        await query.edit_message_text(
            f"✅ User {uid_to_approve} verified successfully."
        )
        await context.bot.send_message(
            uid_to_approve,
            "✅ আপনার অ্যাকাউন্ট সফলভাবে ভেরিফাই হয়েছে! এখন আপনি ডিপোজিট ও Withdraw করতে পারবেন।"
        )

    # ---------------- REJECT USER VERIFICATION ---------------- #
    elif data.startswith("reject_user_"):
        uid_to_reject = int(data.split("_")[-1])

        cur.execute(
            "UPDATE verification SET status='rejected' WHERE uid=?",
            (uid_to_reject,)
        )
        conn.commit()

        await query.edit_message_text(
            f"❌ User {uid_to_reject} verification rejected."
        )
        await context.bot.send_message(
            uid_to_reject,
            "❌ আপনার ভেরিফিকেশন বাতিল করা হয়েছে। অনুগ্রহ করে সঠিক ডকুমেন্ট দিয়ে আবার জমা দিন।"
        )

    # ---------------- COPY UID and Number CALLBACK ---------------- #
    elif data.startswith("copy_uid_"):
        uid_copy = data.split("_")[-1]
        await query.answer(text=f"UID: {uid_copy}", show_alert=True)

    elif data.startswith("copy_phone_"):
        phone = data.split("_")[-1]
        await query.answer(text=f"Number: {phone}", show_alert=True)




# ---------------- ROUTER ---------------- #
async def router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    text = update.message.text if update.message else None
    state = context.user_data.get("state")

    
    if text == "Back":
        context.user_data.clear()
        await update.message.reply_text(
            "মেইন মেনুতে ফিরে আসা হয়েছে।",
            reply_markup=MAIN_KB
        )
        return

    # ---------------- RESET STATE ON MAIN BUTTONS ---------------- #
    main_buttons = [
        "👤 প্রোফাইল",
        "💰 ডিপোজিট",
        "💸 Withdraw",
        "👥 Referral",
        "🧾 লেনদেন",
        "📜 শর্তাবলী",
        "🛡 Security",
        "❓ সহায়তা"
    ]

    admin_buttons_list = [
        "📥 Pending Deposits",
        "📤 Pending Withdraws",
        "📝 Pending Verification",
        "👥 Users",
        "✏️ Edit Balance"
    ]

    if text in main_buttons + admin_buttons_list:
        context.user_data["state"] = None
        state = None

    # ---------------- ADMIN BUTTONS ---------------- #
    if is_admin(uid) and text in admin_buttons_list:
        await admin_buttons(update, context)
        return

    # ================= ADMIN EDIT BALANCE ================= #

    if state == "admin_edit_uid":
        if not update.message.text.isdigit():
            await update.message.reply_text("শুধু সংখ্যা লিখুন!")
            return

        edit_uid = int(update.message.text)

        user = cur.execute(
            "SELECT deposit_total, profit_total, join_date FROM users WHERE uid=?",
            (edit_uid,)
        ).fetchone()

        if not user:
            await update.message.reply_text("❌ User not found!")
            return

        deposit, profit, join_date = user
        context.user_data["edit_uid"] = edit_uid

        await update.message.reply_text(
            f"""👤 User Information

UID: {edit_uid}
🏦 Capital: ৳ {deposit}
💰 Profit: ৳ {profit}
📅 Join Date: {join_date}
"""
        )

        kb = ReplyKeyboardMarkup(
            [
                ["🏦 Edit Capital", "💰 Edit Profit"],
                ["📅 Edit Join Date"],
                ["📆 Edit Deposit Date"],
                ["Back"]
            ],
            resize_keyboard=True
        )

        await update.message.reply_text("কি এডিট করতে চান?", reply_markup=kb)
        context.user_data["state"] = "admin_edit_type"
        return

    elif state == "admin_edit_type":
        if update.message.text == "🏦 Edit Capital":
            context.user_data["edit_field"] = "deposit_total"
            await update.message.reply_text("নতুন Capital লিখুন:")
            context.user_data["state"] = "admin_edit_amount"
            return

        elif update.message.text == "💰 Edit Profit":
            context.user_data["edit_field"] = "profit_total"
            await update.message.reply_text("নতুন Profit লিখুন:")
            context.user_data["state"] = "admin_edit_amount"
            return

        elif update.message.text == "📅 Edit Join Date":
            await update.message.reply_text("নতুন Join Date লিখুন (YYYY-MM-DD):")
            context.user_data["state"] = "admin_edit_join_date"
            return

        elif update.message.text == "📆 Edit Deposit Date":
            await update.message.reply_text("নতুন Deposit Date লিখুন (YYYY-MM-DD):")
            context.user_data["state"] = "admin_edit_deposit_date"
            return

        else:
            await update.message.reply_text("বাটন থেকে নির্বাচন করুন!")
            return

    elif state == "admin_edit_amount":
        try:
            amount = float(update.message.text)
        except:
            await update.message.reply_text("সঠিক পরিমাণ লিখুন!")
            return

        edit_uid = context.user_data["edit_uid"]
        field = context.user_data["edit_field"]

        cur.execute(
            f"UPDATE users SET {field}=? WHERE uid=?",
            (amount, edit_uid)
        )
        conn.commit()

        cur.execute(
            "INSERT INTO transactions(uid, type, amount, note) VALUES(?,?,?,?)",
            (edit_uid, "admin_edit", amount, f"Admin updated {field}")
        )
        conn.commit()

        await update.message.reply_text("✅ ব্যালেন্স আপডেট হয়েছে।", reply_markup=ADMIN_KB)
        context.user_data["state"] = None
        return

    elif state == "admin_edit_join_date":
        new_date = update.message.text.strip()
        edit_uid = context.user_data["edit_uid"]

        try:
            cur.execute(
                "UPDATE users SET join_date=? WHERE uid=?",
                (new_date, edit_uid)
            )
            conn.commit()

            cur.execute(
                "INSERT INTO transactions(uid, type, amount, note) VALUES(?,?,?,?)",
                (edit_uid, "admin_edit", 0, f"Admin updated join_date to {new_date}")
            )
            conn.commit()

            await update.message.reply_text("✅ Join Date আপডেট হয়েছে।", reply_markup=ADMIN_KB)
            context.user_data["state"] = None

        except:
            await update.message.reply_text("❌ ভুল তারিখ ফরম্যাট! (YYYY-MM-DD)")
        return

    elif state == "admin_edit_deposit_date":
        new_date = update.message.text.strip()
        edit_uid = context.user_data["edit_uid"]

        try:
            cur.execute(
                "INSERT OR REPLACE INTO deposit_dates(uid, last_deposit_date) VALUES(?, ?)",
                (edit_uid, new_date)
            )
            conn.commit()

            cur.execute(
                "INSERT INTO transactions(uid, type, amount, note) VALUES(?,?,?,?)",
                (edit_uid, "admin_edit", 0, f"Admin updated deposit_date to {new_date}")
            )
            conn.commit()

            await update.message.reply_text(
                "✅ Deposit Date আপডেট হয়েছে। এখন Capital Withdraw আনলক।",
                reply_markup=ADMIN_KB
            )
            context.user_data["state"] = None

        except:
            await update.message.reply_text("❌ ভুল তারিখ ফরম্যাট! (YYYY-MM-DD)")
        return

    # ================= END ADMIN EDIT ================= #

    # ---------------- DEPOSIT FLOW ---------------- #
    if state == "deposit_amount":
        await deposit_amount(update, context)
        return

    elif state == "deposit_proof":
        await deposit_proof(update, context)
        return

    elif state == "deposit_uid":
        await deposit_uid(update, context)
        return

    # ---------------- WITHDRAW FLOW ---------------- #
    elif state == "withdraw_type":
        await withdraw_type(update, context)
        return

    elif state == "withdraw_amount":
        await withdraw_amount(update, context)
        return

    elif state == "withdraw_method":
        await withdraw_method(update, context)
        return

    elif state == "withdraw_number":
        await withdraw_number(update, context)
        return

    # ---------------- VERIFICATION FLOW ---------------- #
    elif text == "✅ Verify Account":
        await update.message.reply_text("আপনার পূর্ণ নাম লিখুন:")
        context.user_data["state"] = "verify_name"
        return

    elif state == "verify_name":
        context.user_data["verify_name"] = update.message.text
        await update.message.reply_text("আপনার ফোন নম্বর লিখুন:")
        context.user_data["state"] = "verify_phone"
        return

    elif state == "verify_phone":
        context.user_data["verify_phone"] = update.message.text
        await update.message.reply_text("আপনার জন্ম তারিখ লিখুন (DD/MM/YYYY):")
        context.user_data["state"] = "verify_dob"
        return

    elif state == "verify_dob":
        context.user_data["verify_dob"] = update.message.text
        await update.message.reply_text("NID সামনের দিকের ছবি পাঠান:")
        context.user_data["state"] = "verify_nid_front"
        return

    elif state == "verify_nid_front":
        if update.message.photo or update.message.document:
            context.user_data["verify_nid_front"] = (
                update.message.photo[-1].file_id
                if update.message.photo else update.message.document.file_id
            )
            await update.message.reply_text("NID পেছনের দিকের ছবি পাঠান:")
            context.user_data["state"] = "verify_nid_back"
        else:
            await update.message.reply_text("অনুগ্রহ করে NID সামনের দিকের ছবি বা ডকুমেন্ট পাঠান!")
        return

    elif state == "verify_nid_back":
        if update.message.photo or update.message.document:
            context.user_data["verify_nid_back"] = (
                update.message.photo[-1].file_id
                if update.message.photo else update.message.document.file_id
            )
            await update.message.reply_text("আপনার সেলফি / নিজের ছবি পাঠান:")
            context.user_data["state"] = "verify_selfie"
        else:
            await update.message.reply_text("অনুগ্রহ করে NID পেছনের দিকের ছবি বা ডকুমেন্ট পাঠান!")
        return

    elif state == "verify_selfie":
        if update.message.photo or update.message.document:
            context.user_data["verify_selfie"] = (
                update.message.photo[-1].file_id
                if update.message.photo else update.message.document.file_id
            )

            cur.execute(
                """INSERT OR REPLACE INTO verification
                   (uid, name, phone, dob, nid_front, nid_back, selfie, status)
                   VALUES(?,?,?,?,?,?,?, 'pending')""",
                (
                    uid,
                    context.user_data["verify_name"],
                    context.user_data["verify_phone"],
                    context.user_data["verify_dob"],
                    context.user_data["verify_nid_front"],
                    context.user_data["verify_nid_back"],
                    context.user_data["verify_selfie"]
                )
            )
            conn.commit()

            context.user_data["state"] = None
            await update.message.reply_text(
                "✅ আপনার ভেরিফিকেশন সফলভাবে জমা হয়েছে! অ্যাডমিন শীঘ্রই আপনার অ্যাকাউন্ট অনুমোদন করবেন।",
                reply_markup=MAIN_KB
            )

            for admin_id in ADMIN_IDS:
                await context.bot.send_message(
                    admin_id,
                    f"📝 নতুন ভেরিফিকেশন অনুরোধ!\nUID: {uid}\nনাম: {context.user_data['verify_name']}"
                )
        else:
            await update.message.reply_text("অনুগ্রহ করে একটি সেলফি / নিজের ছবি পাঠান!")
        return

    # ---------------- PROFILE ---------------- #
    elif text == "👤 প্রোফাইল":
        verification = cur.execute(
            "SELECT status FROM verification WHERE uid=?",
            (uid,)
        ).fetchone()

        if not verification or verification[0] != "approved":
            verify_kb = ReplyKeyboardMarkup([["✅ Verify Account"], ["Back"]], resize_keyboard=True)
            await update.message.reply_text(
                "❌ আপনার অ্যাকাউন্ট এখনো ভেরিফাই করা হয়নি। অনুগ্রহ করে ভেরিফাই করুন।",
                reply_markup=verify_kb
            )
            return

        await profile(update, context)
        return

    # ---------------- TRANSACTIONS ---------------- #
    elif text == "🧾 লেনদেন":
        verification = cur.execute(
            "SELECT status FROM verification WHERE uid=?",
            (uid,)
        ).fetchone()

        if not verification or verification[0] != "approved":
            verify_kb = ReplyKeyboardMarkup([["✅ Verify Account"], ["Back"]], resize_keyboard=True)
            await update.message.reply_text(
                "❌ আপনার অ্যাকাউন্ট এখনো ভেরিফাই করা হয়নি।",
                reply_markup=verify_kb
            )
            return

        await transactions_history(update, context)
        return

    # ---------------- DEPOSIT ---------------- #
    elif text == "💰 ডিপোজিট":
        verification = cur.execute(
            "SELECT status FROM verification WHERE uid=?",
            (uid,)
        ).fetchone()

        if not verification or verification[0] != "approved":
            verify_kb = ReplyKeyboardMarkup([["✅ Verify Account"], ["Back"]], resize_keyboard=True)
            await update.message.reply_text(
                "❌ আপনার অ্যাকাউন্ট এখনো ভেরিফাই করা হয়নি।",
                reply_markup=verify_kb
            )
            return

        await deposit_start(update, context)
        return

    # ---------------- WITHDRAW ---------------- #
    elif text == "💸 Withdraw":
        verification = cur.execute(
            "SELECT status FROM verification WHERE uid=?",
            (uid,)
        ).fetchone()

        if not verification or verification[0] != "approved":
            verify_kb = ReplyKeyboardMarkup([["✅ Verify Account"], ["Back"]], resize_keyboard=True)
            await update.message.reply_text(
                "❌ আপনার অ্যাকাউন্ট এখনো ভেরিফাই করা হয়নি।",
                reply_markup=verify_kb
            )
            return

        await withdraw_start(update, context)
        return

    # ---------------- REFERRAL ---------------- #
    elif text == "👥 Referral":
        verification = cur.execute(
            "SELECT status FROM verification WHERE uid=?",
            (uid,)
        ).fetchone()

        if not verification or verification[0] != "approved":
            verify_kb = ReplyKeyboardMarkup([["✅ Verify Account"], ["Back"]], resize_keyboard=True)
            await update.message.reply_text(
                "❌ আপনার অ্যাকাউন্ট এখনো ভেরিফাই করা হয়নি।",
                reply_markup=verify_kb
            )
            return

        await referral(update, context)
        return

    # ---------------- TERMS ---------------- #
    elif text == "📜 শর্তাবলী":
        await terms(update, context)
        return

    # ---------------- SECURITY ---------------- #
    elif text == "🛡 Security":
        await security(update, context)
        return

    # ---------------- HELP ---------------- #
    elif text == "❓ সহায়তা":
        await help_center(update, context)
        return

    # ---------------- UNKNOWN ---------------- #
    else:
        await update.message.reply_text("ফিচারটি শীঘ্রই আসছে।", reply_markup=MAIN_KB)


# ---------------- RUN BOT ---------------- #
def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, router))
    app.add_handler(MessageHandler(filters.PHOTO | filters.Document.ALL, router))
    app.add_handler(CallbackQueryHandler(admin_callback))
    
    # ---------------- START DAILY PROFIT JOB ---------------- #
    scheduler = BackgroundScheduler()
    scheduler.add_job(add_daily_profit, 'interval', hours=24)
    scheduler.start()
    
    print("✅ Bot Running...")
    app.run_polling()


if __name__ == "__main__":
    main()






