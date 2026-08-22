import aiosqlite

DB_NAME = "telegram_bot.db"


async def init_db():
    """Initialize database tables for mapped users and temporary setup states."""
    async with aiosqlite.connect(DB_NAME) as db:
        # Final table mapping phone numbers to chat IDs and selected language
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS phone_chats (
                phone_number TEXT PRIMARY KEY,
                chat_id TEXT NOT NULL,
                language TEXT NOT NULL DEFAULT 'ar',
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """
        )
        # Temporary table to hold language selection during registration flow
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS user_states (
                chat_id TEXT PRIMARY KEY,
                language TEXT NOT NULL,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """
        )
        await db.commit()


async def save_user_language(chat_id: str, language: str):
    """Persist temporary language selection for a chat_id."""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            """
            INSERT INTO user_states (chat_id, language)
            VALUES (?, ?)
            ON CONFLICT(chat_id) DO UPDATE SET 
                language = excluded.language,
                updated_at = CURRENT_TIMESTAMP
        """,
            (chat_id, language),
        )
        await db.commit()


async def get_user_language(chat_id: str) -> str:
    """Retrieve temporary language choice or default to 'ar'."""
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(
            "SELECT language FROM user_states WHERE chat_id = ?",
            (chat_id,),
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else "ar"


async def save_phone_chat(phone_number: str, chat_id: str, language: str):
    """Save or update permanent phone number mapping."""
    clean_phone = phone_number.strip().replace(" ", "").replace("+", "")

    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            """
            INSERT INTO phone_chats (phone_number, chat_id, language)
            VALUES (?, ?, ?)
            ON CONFLICT(phone_number) DO UPDATE SET 
                chat_id = excluded.chat_id,
                language = excluded.language,
                updated_at = CURRENT_TIMESTAMP
        """,
            (clean_phone, chat_id, language),
        )
        await db.commit()

async def get_chat_id_by_phone(phone_number: str) -> str | None:
    """Retrieve chat_id associated with a registered phone number."""
    clean_phone = phone_number.strip().replace(" ", "").replace("+", "")
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(
            "SELECT chat_id FROM phone_chats WHERE phone_number = ?",
            (clean_phone,),
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else None