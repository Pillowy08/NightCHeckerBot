from aiogram.types import ReplyKeyboardMarkup, InlineKeyboardMarkup
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder


def main_menu_keyboard(is_admin: bool = False) -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardBuilder()
    kb.button(text="📋 Мои каналы")
    kb.button(text="✅ Статус")
    kb.button(text="🔑 Ввести код")
    kb.button(text="❓ Помощь")
    kb.button(text="📞 Администрация")
    kb.adjust(2)
    if is_admin:
        kb.button(text="⚙️ Админ панель")
        kb.adjust(2, 2)
    else:
        kb.adjust(2, 2, 1)
    return kb.as_markup(resize_keyboard=True)


def admin_panel_keyboard() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="➕ Создать код", callback_data="admin:add_code")
    kb.button(text="📄 Список кодов", callback_data="admin:codes")
    kb.button(text="❌ Отозвать код", callback_data="admin:revoke_code")
    kb.button(text="➕ Канал к коду", callback_data="admin:add_channel")
    kb.button(text="📊 Статистика", callback_data="admin:stats")
    kb.button(text="📢 Рассылка", callback_data="admin:broadcast")
    kb.button(text="↩️ Назад", callback_data="admin:back")
    kb.adjust(2)
    return kb.as_markup()
