import aiosqlite

DB_PATH = "bot.db"


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                full_name TEXT,
                university TEXT,
                role TEXT,
                stack TEXT,
                format TEXT,
                is_active INTEGER DEFAULT 1,
                socials TEXT,
                phone TEXT,
                projects TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS projects (
                project_id INTEGER PRIMARY KEY AUTOINCREMENT,
                owner_id INTEGER,
                title TEXT,
                description TEXT,
                roles TEXT,
                topic TEXT,
                stage TEXT,
                format TEXT,
                is_active INTEGER DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS responses (
                response_id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER,
                applicant_id INTEGER,
                status TEXT DEFAULT 'pending',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(project_id, applicant_id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS bookmarks (
                user_id INTEGER,
                project_id INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, project_id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS seen_projects (
                user_id INTEGER,
                project_id INTEGER,
                PRIMARY KEY (user_id, project_id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS reviews (
                review_id INTEGER PRIMARY KEY AUTOINCREMENT,
                reviewer_id INTEGER,
                target_id INTEGER,
                project_id INTEGER,
                text TEXT,
                rating INTEGER,
                tags TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.commit()
        await _migrate(db)


async def _migrate(db):
    """Добавляет колонки, появившиеся позже, в уже существующую базу."""
    expected = {
        "users": {
            "university": "TEXT",
            "projects": "TEXT",
        },
        "reviews": {
            "rating": "INTEGER",
            "tags": "TEXT",
        },
    }
    for table, columns in expected.items():
        cur = await db.execute(f"PRAGMA table_info({table})")
        existing = {row[1] for row in await cur.fetchall()}
        for name, coltype in columns.items():
            if name not in existing:
                await db.execute(f"ALTER TABLE {table} ADD COLUMN {name} {coltype}")
    await db.commit()


async def upsert_user(user_id, username, **fields):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
        exists = await cur.fetchone()
        if exists:
            if fields:
                keys = ", ".join(f"{k} = ?" for k in fields)
                values = list(fields.values()) + [user_id]
                await db.execute(f"UPDATE users SET {keys} WHERE user_id = ?", values)
        else:
            columns = ["user_id", "username"] + list(fields.keys())
            placeholders = ", ".join("?" for _ in columns)
            values = [user_id, username] + list(fields.values())
            await db.execute(
                f"INSERT INTO users ({', '.join(columns)}) VALUES ({placeholders})",
                values,
            )
        await db.commit()


async def get_user(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        return await cur.fetchone()


async def set_active(user_id, is_active: bool):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET is_active = ? WHERE user_id = ?", (int(is_active), user_id)
        )
        await db.commit()


async def create_project(owner_id, title, description, roles, topic, stage, fmt):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            """
            INSERT INTO projects (owner_id, title, description, roles, topic, stage, format, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, 1)
            """,
            (owner_id, title, description, roles, topic, stage, fmt),
        )
        await db.commit()
        return cur.lastrowid


async def get_project(project_id):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM projects WHERE project_id = ?", (project_id,))
        return await cur.fetchone()


async def get_user_projects(owner_id):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM projects WHERE owner_id = ? ORDER BY created_at DESC", (owner_id,)
        )
        return await cur.fetchall()


async def get_next_project_for_role(user_id, role):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            """
            SELECT * FROM projects
            WHERE is_active = 1
              AND owner_id != ?
              AND (',' || roles || ',') LIKE ?
              AND project_id NOT IN (
                  SELECT project_id FROM seen_projects WHERE user_id = ?
              )
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (user_id, f"%,{role},%", user_id),
        )
        return await cur.fetchone()


async def mark_project_seen(user_id, project_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO seen_projects (user_id, project_id) VALUES (?, ?)",
            (user_id, project_id),
        )
        await db.commit()


async def add_response(project_id, applicant_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO responses (project_id, applicant_id, status)
            VALUES (?, ?, 'pending')
            ON CONFLICT(project_id, applicant_id) DO NOTHING
            """,
            (project_id, applicant_id),
        )
        await db.commit()


async def set_response_status(project_id, applicant_id, status):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE responses SET status = ? WHERE project_id = ? AND applicant_id = ?",
            (status, project_id, applicant_id),
        )
        await db.commit()


async def count_pending_responses(applicant_id):
    """Сколько откликов пользователя сейчас висят без ответа (не приняты и не отклонены)."""
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT COUNT(*) FROM responses WHERE applicant_id = ? AND status = 'pending'",
            (applicant_id,),
        )
        (count,) = await cur.fetchone()
        return count


async def get_response(project_id, applicant_id):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM responses WHERE project_id = ? AND applicant_id = ?",
            (project_id, applicant_id),
        )
        return await cur.fetchone()


async def get_my_responses(applicant_id):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            """
            SELECT responses.*, projects.title AS project_title, projects.owner_id AS project_owner_id
            FROM responses
            JOIN projects ON projects.project_id = responses.project_id
            WHERE applicant_id = ?
            ORDER BY responses.created_at DESC
            """,
            (applicant_id,),
        )
        return await cur.fetchall()


async def add_bookmark(user_id, project_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO bookmarks (user_id, project_id) VALUES (?, ?)",
            (user_id, project_id),
        )
        await db.commit()


async def get_bookmarks(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            """
            SELECT projects.* FROM bookmarks
            JOIN projects ON projects.project_id = bookmarks.project_id
            WHERE bookmarks.user_id = ?
            ORDER BY bookmarks.created_at DESC
            """,
            (user_id,),
        )
        return await cur.fetchall()


async def add_review(reviewer_id, target_id, project_id, rating, tags=None):
    """tags — список ключей тегов (например ["communicative", "responsible"]) или None."""
    tags_str = ",".join(tags) if tags else None
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO reviews (reviewer_id, target_id, project_id, rating, tags) VALUES (?, ?, ?, ?, ?)",
            (reviewer_id, target_id, project_id, rating, tags_str),
        )
        await db.commit()


async def get_top_tags(target_id, limit=5):
    """Возвращает список (тег, количество) — самые частые теги в отзывах о пользователе."""
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT tags FROM reviews WHERE target_id = ? AND tags IS NOT NULL AND tags != ''",
            (target_id,),
        )
        rows = await cur.fetchall()

    counts = {}
    for (tags_str,) in rows:
        for tag in tags_str.split(","):
            tag = tag.strip()
            if tag:
                counts[tag] = counts.get(tag, 0) + 1

    return sorted(counts.items(), key=lambda kv: kv[1], reverse=True)[:limit]


async def get_average_rating(target_id):
    """Возвращает (средняя_оценка, количество_оценок) по звёздам. Если оценок нет — (None, 0)."""
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT AVG(rating), COUNT(rating) FROM reviews WHERE target_id = ? AND rating IS NOT NULL",
            (target_id,),
        )
        avg, count = await cur.fetchone()
        return (avg, count) if count else (None, 0)


async def get_reviews_for_user(target_id):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            """
            SELECT reviews.*, users.full_name AS reviewer_name
            FROM reviews
            LEFT JOIN users ON users.user_id = reviews.reviewer_id
            WHERE target_id = ?
            ORDER BY reviews.created_at DESC
            """,
            (target_id,),
        )
        return await cur.fetchall()
