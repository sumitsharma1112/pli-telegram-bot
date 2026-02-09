# ============================================
# PLI SANTOSH CALCULATOR - FINAL PRODUCTION BOT
# ============================================

import json
import logging
from datetime import datetime, date

from telegram import (
    Update,
    ReplyKeyboardMarkup,
    KeyboardButton
)

from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

# ============================================
# SETTINGS
# ============================================

BOT_TOKEN = "8333006279:AAHfw9hr2dT1ABZm8SGRPv2JmdMqADSWHaM"
BONUS_RATE = 52   # per 1000 per year

TABLE_FILE = "pli_tables_complete.json"

# ============================================
# LOAD TABLES
# ============================================

with open(TABLE_FILE, "r") as f:
    tables = json.load(f)

# ============================================
# STATES
# ============================================

MENU, DOB, SUM_ASSURED, MATURITY = range(4)

# ============================================
# BUTTON MENUS
# ============================================

main_menu = ReplyKeyboardMarkup(
    [
        ["Calculate Premium"],
        ["Restart", "Share Bot"]
    ],
    resize_keyboard=True
)

restart_menu = ReplyKeyboardMarkup(
    [
        ["Restart", "Share Bot"]
    ],
    resize_keyboard=True
)

# ============================================
# AGE CALCULATION (PLI METHOD)
# ============================================

def calculate_age(dob_str):

    dob = datetime.strptime(dob_str, "%d-%m-%Y").date()
    today = date.today()

    age = today.year - dob.year

    next_birthday = dob.replace(year=today.year)

    if next_birthday <= today:
        age += 1

    return age

# ============================================
# VALIDATIONS
# ============================================

def validate_sum_assured(sa):

    if sa < 20000:
        return False

    if sa > 5000000:
        return False

    if sa % 5000 != 0:
        return False

    return True


def get_valid_maturities(age):

    age_str = str(age)

    if age_str not in tables["monthly"]:
        return []

    return list(tables["monthly"][age_str].keys())

# ============================================
# PREMIUM CALCULATION
# ============================================

def calculate_premium(age, maturity, sa):

    age_str = str(age)
    maturity_str = str(maturity)

    valid = get_valid_maturities(age)

    if maturity_str not in valid:
        raise ValueError("Invalid maturity")

    units = sa / 5000
    rebate_unit = sa / 20000

    monthly_base = tables["monthly"][age_str][maturity_str]
    quarterly_base = tables["quarterly"][age_str][maturity_str]
    half_base = tables["half_yearly"][age_str][maturity_str]
    yearly_base = tables["yearly"][age_str][maturity_str]

    monthly = round(monthly_base * units) - rebate_unit
    quarterly = round(quarterly_base * units) - rebate_unit * 3
    half = round(half_base * units) - rebate_unit * 6
    yearly = round(yearly_base * units) - rebate_unit * 12

    term = maturity - age

    bonus = (sa / 1000) * BONUS_RATE * term
    maturity_value = sa + bonus

    return (
        int(monthly),
        int(quarterly),
        int(half),
        int(yearly),
        int(bonus),
        int(maturity_value),
        term
    )

# ============================================
# HANDLERS
# ============================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "Welcome to PLI Santosh Calculator Bot",
        reply_markup=main_menu
    )

    return MENU


async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = update.message.text

    if text == "Calculate Premium":

        await update.message.reply_text(
            "Enter Date of Birth (DD-MM-YYYY):",
            reply_markup=restart_menu
        )

        return DOB

    elif text == "Restart":

        return await start(update, context)

    elif text == "Share Bot":

        await update.message.reply_text(
            "Share this bot:\nhttps://t.me/pli_santosh_calculator_bot"
        )

        return MENU

    return MENU


async def get_dob(update: Update, context: ContextTypes.DEFAULT_TYPE):

    dob = update.message.text

    try:

        age = calculate_age(dob)

    except:
        await update.message.reply_text("Invalid DOB format")
        return DOB

    if age < 19 or age > 55:

        await update.message.reply_text(
            f"Age {age} not allowed\nAllowed age: 19–55"
        )
        return DOB

    context.user_data["age"] = age

    await update.message.reply_text(
        f"Age calculated: {age}\n\nEnter Sum Assured:"
    )

    return SUM_ASSURED


async def get_sum_assured(update: Update, context: ContextTypes.DEFAULT_TYPE):

    try:
        sa = int(update.message.text)
    except:
        await update.message.reply_text("Enter valid number")
        return SUM_ASSURED

    if not validate_sum_assured(sa):

        await update.message.reply_text(
            "Invalid Sum Assured\n"
            "• Minimum ₹20,000\n"
            "• Maximum ₹50,00,000\n"
            "• Multiple of ₹5,000"
        )

        return SUM_ASSURED

    context.user_data["sa"] = sa

    age = context.user_data["age"]

    valid = get_valid_maturities(age)

    await update.message.reply_text(
        f"Select Maturity Age:\n{', '.join(valid)}"
    )

    return MATURITY


async def get_maturity(update: Update, context: ContextTypes.DEFAULT_TYPE):

    maturity = update.message.text

    age = context.user_data["age"]

    valid = get_valid_maturities(age)

    if maturity not in valid:

        await update.message.reply_text(
            f"Invalid maturity\nValid: {', '.join(valid)}"
        )

        return MATURITY

    maturity = int(maturity)
    sa = context.user_data["sa"]

    monthly, quarterly, half, yearly, bonus, maturity_value, term = calculate_premium(
        age, maturity, sa
    )

    result = (
        f"PLI Santosh Plan Result\n\n"
        f"Age: {age}\n"
        f"Term: {term} years\n"
        f"Sum Assured: ₹{sa}\n\n"
        f"Monthly: ₹{monthly}\n"
        f"Quarterly: ₹{quarterly}\n"
        f"Half-Yearly: ₹{half}\n"
        f"Yearly: ₹{yearly}\n\n"
        f"Bonus: ₹{bonus}\n"
        f"Maturity Value: ₹{maturity_value}"
    )

    await update.message.reply_text(
        result,
        reply_markup=main_menu
    )

    return MENU

# ============================================
# MAIN
# ============================================

def main():

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    conv = ConversationHandler(

        entry_points=[CommandHandler("start", start)],

        states={

            MENU: [MessageHandler(filters.TEXT, menu_handler)],

            DOB: [MessageHandler(filters.TEXT, get_dob)],

            SUM_ASSURED: [MessageHandler(filters.TEXT, get_sum_assured)],

            MATURITY: [MessageHandler(filters.TEXT, get_maturity)],

        },

        fallbacks=[CommandHandler("start", start)],
    )

    app.add_handler(conv)

    print("PLI Santosh Production Bot Running...")

    app.run_polling()


if __name__ == "__main__":
    main()

