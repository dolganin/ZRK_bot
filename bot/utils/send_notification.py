async def send_notification(bot, text):
    """Отправляет сообщение всем студентам"""
    db = await get_db()
    users = await db.fetch("SELECT id FROM students")
    for user in users:
        await bot.send_message(user['id'], text)
