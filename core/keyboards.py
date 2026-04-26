from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

def admin_wd_keyboard(wid):
    b = InlineKeyboardBuilder()
    b.row(
        InlineKeyboardButton(text="✅ Pagado",   callback_data=f"adm_pay:{wid}"),
        InlineKeyboardButton(text="❌ Rechazar", callback_data=f"adm_rej:{wid}"),
    )
    return b.as_markup()
