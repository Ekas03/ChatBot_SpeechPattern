import logging
from aiogram import Bot, Dispatcher, types
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy import Column, Integer, String, ForeignKey

API_TOKEN = ""
DB_URL = ""

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

login = 1

Base = declarative_base()
engine = create_async_engine(DB_URL, echo=True)
SessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    files = relationship("File", back_populates="user")


class File(Base):
    __tablename__ = "files"

    id = Column(Integer, primary_key=True, index=True)
    file_id = Column(String, nullable=False)
    file_name = Column(String, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    user = relationship("User", back_populates="files")

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    user_id = message.from_user.id
    user_name = message.from_user.full_name

    async with SessionLocal() as session:
        user = await session.get(User, user_id)
        if not user:
            new_user = User(id=user_id, name=user_name)
            session.add(new_user)
            await session.commit()
            await session.refresh(new_user)
            await message.reply(f"Добро пожаловать, {user_name}! Вы добавлены в базу данных.")
        else:
            await message.reply(f"С возвращением, {user_name}!")

@dp.message_handler(content_types=types.ContentType.DOCUMENT)
async def handle_document(message: types.Message):
    document = message.document
    file_id = document.file_id
    file_name = document.file_name
    user_id = message.from_user.id

    async with SessionLocal() as session:
        user = await session.get(User, user_id)
        if not user:
            await message.reply("Ваш профиль не найден в базе данных. Пожалуйста, используйте /start.")
            return

        new_file = File(file_id=file_id, file_name=file_name, user=user)
        session.add(new_file)
        await session.commit()
        await session.refresh(new_file)
    await message.reply(f"Файл '{file_name}' сохранен в базе данных.")

@dp.message_handler(commands=['myfiles'])
async def list_files(message: types.Message):
    user_id = message.from_user.id

    async with SessionLocal() as session:
        files = await session.execute(
            File.__table__.select().where(File.user_id == user_id)
        )
        files = files.fetchall()

    if not files:
        await message.reply("У вас нет загруженных файлов.")
        return

    keyboard = types.InlineKeyboardMarkup()
    for file in files:
        keyboard.add(
            types.InlineKeyboardButton(
                text=f"{file.file_name}", callback_data=f"file_{file.id}"
            )
        )
        keyboard.add(
            types.InlineKeyboardButton(
                text=f"Удалить {file.file_name}", callback_data=f"delete_{file.id}"
            )
        )

    await message.reply("Ваши файлы:", reply_markup=keyboard)

@dp.callback_query_handler(lambda c: c.data.startswith('file_'))
async def send_file_content(callback_query: types.CallbackQuery):
    try:
        file_id = int(callback_query.data.split('_')[1])
    except ValueError:
        await callback_query.message.reply("Некорректный ID файла.")
        await callback_query.answer()
        return

    async with SessionLocal() as session:
        file = await session.get(File, file_id)

    if not file:
        await callback_query.message.reply("Файл не найден.")
        return

    telegram_file = await bot.get_file(file.file_id)
    await bot.send_document(callback_query.from_user.id, file.file_id)
    await callback_query.answer()

@dp.callback_query_handler(lambda c: c.data.startswith('delete_'))
async def delete_file(callback_query: types.CallbackQuery):
    try:
        file_id = int(callback_query.data.split('_')[1])
    except ValueError:
        await callback_query.message.reply("Некорректный ID файла.")
        await callback_query.answer()
        return

    async with SessionLocal() as session:

        file = await session.get(File, file_id)
        if not file:
            await callback_query.message.reply("Файл не найден.")
            return

        await session.delete(file)
        await session.commit()

    await callback_query.message.reply("Файл успешно удален.")
    await callback_query.answer()

async def main():
    await init_db()
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling()

if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
