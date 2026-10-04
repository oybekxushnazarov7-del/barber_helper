from __future__ import annotations

import asyncio

import aiosqlite

import config

_conn: aiosqlite.Connection | None = None
lock: asyncio.Lock | None = None  # bron yaratishni ketma-ket qilish uchun

ACTIVE = ("pending_payment", "confirmed")

SCHEMA = """
CREATE TABLE IF NOT EXISTS shops(
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    address TEXT DEFAULT '',
    phone TEXT DEFAULT '',
    card_number TEXT DEFAULT '',
    deposit_amount INTEGER DEFAULT 15000,
    free_cancel_hours INTEGER DEFAULT 24,
    slot_step INTEGER DEFAULT 30
);
CREATE TABLE IF NOT EXISTS staff(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    shop_id INTEGER NOT NULL,
    tg_id INTEGER,
    name TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('owner','barber')),
    active INTEGER DEFAULT 1,
    invite_code TEXT
);
CREATE TABLE IF NOT EXISTS services(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    shop_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    price INTEGER NOT NULL,
    duration_min INTEGER NOT NULL,
    active INTEGER DEFAULT 1
);
CREATE TABLE IF NOT EXISTS work_hours(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    staff_id INTEGER NOT NULL,
    weekday INTEGER NOT NULL,
    start_min INTEGER NOT NULL,
    end_min INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS blocked(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    staff_id INTEGER NOT NULL,
    date TEXT NOT NULL,
    start_min INTEGER NOT NULL,
    end_min INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS clients(
    shop_id INTEGER NOT NULL,
    tg_id INTEGER NOT NULL,
    name TEXT DEFAULT '',
    phone TEXT,
    deposit_credit INTEGER DEFAULT 0,
    no_show_count INTEGER DEFAULT 0,
    blocked INTEGER DEFAULT 0,
    PRIMARY KEY(shop_id, tg_id)
);
CREATE TABLE IF NOT EXISTS bookings(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    shop_id INTEGER NOT NULL,
    client_id INTEGER NOT NULL,
    staff_id INTEGER NOT NULL,
    service_id INTEGER NOT NULL,
    date TEXT NOT NULL,
    start_min INTEGER NOT NULL,
    duration_min INTEGER NOT NULL,
    price INTEGER NOT NULL,
    status TEXT NOT NULL,
    deposit_amount INTEGER DEFAULT 0,
    deposit_status TEXT DEFAULT 'none',
    receipt_file_id TEXT,
    created_at TEXT NOT NULL,
    pay_deadline TEXT,
    client_confirmed INTEGER DEFAULT 0,
    rem_day_sent INTEGER DEFAULT 0,
    rem_hour_sent INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS reviews(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    booking_id INTEGER NOT NULL UNIQUE,
    shop_id INTEGER NOT NULL,
    staff_id INTEGER NOT NULL,
    client_id INTEGER NOT NULL,
    rating INTEGER NOT NULL,
    comment TEXT,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS waitlist(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    shop_id INTEGER NOT NULL,
    client_id INTEGER NOT NULL,
    staff_id INTEGER NOT NULL,
    service_id INTEGER NOT NULL,
    date TEXT NOT NULL,
    created_at TEXT NOT NULL,
    notified_at TEXT
);
CREATE TABLE IF NOT EXISTS used_receipts(
    key TEXT PRIMARY KEY,
    booking_id INTEGER
);
CREATE INDEX IF NOT EXISTS idx_bookings_staff_date ON bookings(staff_id, date);
CREATE INDEX IF NOT EXISTS idx_bookings_client ON bookings(shop_id, client_id);
CREATE INDEX IF NOT EXISTS idx_waitlist_staff_date ON waitlist(staff_id, date);
"""

# Eski bazani yangilash: (jadval, ustun, turi)
MIGRATIONS = [
    ("shops", "lat", "REAL"),
    ("shops", "lon", "REAL"),
    ("clients", "lang", "TEXT"),
    ("clients", "is_demo", "INTEGER DEFAULT 0"),
    ("clients", "winback_for", "TEXT"),
    ("bookings", "discount_percent", "INTEGER DEFAULT 0"),
    ("bookings", "source", "TEXT DEFAULT 'bot'"),
    ("bookings", "completed_at", "TEXT"),
    ("bookings", "review_asked", "INTEGER DEFAULT 0"),
    ("bookings", "receipt_attempts", "INTEGER DEFAULT 0"),
    ("bookings", "receipt_uid", "TEXT"),
    ("bookings", "receipt_info", "TEXT"),
    ("bookings", "is_demo", "INTEGER DEFAULT 0"),
]

BOOKING_SELECT = """
SELECT b.*, s.name AS service_name, st.name AS staff_name, st.tg_id AS staff_tg,
       c.name AS client_name, c.phone AS client_phone, sh.name AS shop_name
FROM bookings b
JOIN services s ON s.id = b.service_id
JOIN staff st ON st.id = b.staff_id
JOIN shops sh ON sh.id = b.shop_id
LEFT JOIN clients c ON c.shop_id = b.shop_id AND c.tg_id = b.client_id
"""


async def init_db() -> None:
    global _conn, lock
    lock = asyncio.Lock()
    _conn = await aiosqlite.connect(config.DB_PATH)
    _conn.row_factory = aiosqlite.Row
    await _conn.executescript(SCHEMA)
    for table, column, ddl in MIGRATIONS:
        cols = [r["name"] for r in await _all(f"PRAGMA table_info({table})")]
        if column not in cols:
            await _conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")
    await _conn.commit()


async def close_db() -> None:
    if _conn is not None:
        await _conn.close()


async def _all(sql: str, params: tuple = ()) -> list[dict]:
    async with _conn.execute(sql, params) as cur:
        rows = await cur.fetchall()
    return [dict(r) for r in rows]


async def _one(sql: str, params: tuple = ()) -> dict | None:
    async with _conn.execute(sql, params) as cur:
        row = await cur.fetchone()
    return dict(row) if row else None


async def _exec(sql: str, params: tuple = ()) -> int:
    cur = await _conn.execute(sql, params)
    await _conn.commit()
    last = cur.lastrowid
    await cur.close()
    return last


def _in(ids: list[int]) -> str:
    return ",".join("?" for _ in ids) or "NULL"


# ---------- shops ----------
async def count_shops() -> int:
    row = await _one("SELECT COUNT(*) AS n FROM shops")
    return row["n"]


async def insert_shop(shop_id, name, address, phone, card, deposit, free_cancel_hours, slot_step,
                      lat=None, lon=None) -> None:
    await _exec(
        "INSERT INTO shops(id,name,address,phone,card_number,deposit_amount,free_cancel_hours,slot_step,lat,lon) "
        "VALUES(?,?,?,?,?,?,?,?,?,?)",
        (shop_id, name, address, phone, card, deposit, free_cancel_hours, slot_step, lat, lon),
    )


async def get_shop(shop_id: int) -> dict | None:
    return await _one("SELECT * FROM shops WHERE id=?", (shop_id,))


async def list_shops() -> list[dict]:
    return await _all("SELECT * FROM shops ORDER BY id")


async def update_shop(shop_id: int, **fields) -> None:
    cols = ", ".join(f"{k}=?" for k in fields)
    await _exec(f"UPDATE shops SET {cols} WHERE id=?", (*fields.values(), shop_id))


# ---------- staff ----------
async def insert_staff(shop_id, tg_id, name, role, invite_code=None) -> int:
    return await _exec(
        "INSERT INTO staff(shop_id,tg_id,name,role,invite_code) VALUES(?,?,?,?,?)",
        (shop_id, tg_id, name, role, invite_code),
    )


async def list_staff(shop_id: int, role: str | None = None, active_only: bool = True) -> list[dict]:
    sql = "SELECT * FROM staff WHERE shop_id=?"
    params: list = [shop_id]
    if role:
        sql += " AND role=?"
        params.append(role)
    if active_only:
        sql += " AND active=1"
    sql += " ORDER BY id"
    return await _all(sql, tuple(params))


async def get_staff(staff_id: int) -> dict | None:
    return await _one("SELECT * FROM staff WHERE id=?", (staff_id,))


async def staff_by_tg(shop_id: int, tg_id: int) -> list[dict]:
    return await _all("SELECT * FROM staff WHERE shop_id=? AND tg_id=? AND active=1", (shop_id, tg_id))


async def staff_by_invite(shop_id: int, code: str) -> dict | None:
    return await _one(
        "SELECT * FROM staff WHERE shop_id=? AND invite_code=? AND role='barber' AND active=1", (shop_id, code))


async def link_staff(staff_id: int, tg_id: int) -> None:
    await _exec("UPDATE staff SET tg_id=? WHERE id=?", (tg_id, staff_id))


async def unlink_staff(staff_id: int, new_code: str) -> None:
    await _exec("UPDATE staff SET tg_id=NULL, invite_code=? WHERE id=?", (new_code, staff_id))


async def deactivate_staff(staff_id: int) -> None:
    await _exec("UPDATE staff SET active=0 WHERE id=?", (staff_id,))
    await _exec("DELETE FROM waitlist WHERE staff_id=?", (staff_id,))


async def ensure_owner(shop_id: int, tg_id: int) -> None:
    row = await _one("SELECT id FROM staff WHERE shop_id=? AND tg_id=? AND role='owner'", (shop_id, tg_id))
    if not row:
        await insert_staff(shop_id, tg_id, "Ega", "owner")


async def sync_owners(shop_id: int, desired: set[int]) -> None:
    """Shop egalarini .env dagi ro'yxatga moslaydi: ro'yxatdagilar faol, qolganlar o'chiriladi (yashiriladi)."""
    rows = await _all("SELECT * FROM staff WHERE shop_id=? AND role='owner'", (shop_id,))
    seen: set[int] = set()
    for r in rows:
        if r["tg_id"] in desired:
            seen.add(r["tg_id"])
            if not r["active"]:
                await _exec("UPDATE staff SET active=1 WHERE id=?", (r["id"],))
        elif r["active"]:
            await _exec("UPDATE staff SET active=0 WHERE id=?", (r["id"],))
    for tg in desired - seen:
        await insert_staff(shop_id, tg, "Ega", "owner")


async def notify_ids(shop_id: int, staff_id: int | None) -> list[int]:
    """Egalar + (berilgan) usta Telegram ID lari."""
    rows = await _all(
        "SELECT DISTINCT tg_id FROM staff WHERE shop_id=? AND tg_id IS NOT NULL AND active=1 "
        "AND (role='owner' OR id=?)",
        (shop_id, staff_id or -1),
    )
    return [r["tg_id"] for r in rows]


# ---------- services ----------
async def insert_service(shop_id, name, price, duration_min) -> int:
    return await _exec(
        "INSERT INTO services(shop_id,name,price,duration_min) VALUES(?,?,?,?)",
        (shop_id, name, price, duration_min),
    )


async def list_services(shop_id: int) -> list[dict]:
    return await _all("SELECT * FROM services WHERE shop_id=? AND active=1 ORDER BY id", (shop_id,))


async def get_service(service_id: int) -> dict | None:
    return await _one("SELECT * FROM services WHERE id=?", (service_id,))


async def update_service(service_id: int, **fields) -> None:
    cols = ", ".join(f"{k}=?" for k in fields)
    await _exec(f"UPDATE services SET {cols} WHERE id=?", (*fields.values(), service_id))


async def deactivate_service(service_id: int) -> None:
    await _exec("UPDATE services SET active=0 WHERE id=?", (service_id,))
    await _exec("DELETE FROM waitlist WHERE service_id=?", (service_id,))


# ---------- work hours / blocks ----------
async def insert_work_hours(staff_id, weekday, start_min, end_min) -> None:
    await _exec(
        "INSERT INTO work_hours(staff_id,weekday,start_min,end_min) VALUES(?,?,?,?)",
        (staff_id, weekday, start_min, end_min),
    )


async def get_work_hours(staff_id: int, weekday: int) -> list[dict]:
    return await _all(
        "SELECT * FROM work_hours WHERE staff_id=? AND weekday=? ORDER BY start_min", (staff_id, weekday)
    )


async def get_week_hours(staff_id: int) -> list[dict]:
    return await _all("SELECT * FROM work_hours WHERE staff_id=? ORDER BY weekday, start_min", (staff_id,))


async def set_day_hours(staff_id: int, weekday: int, intervals: list[tuple[int, int]]) -> None:
    await _conn.execute("DELETE FROM work_hours WHERE staff_id=? AND weekday=?", (staff_id, weekday))
    for start, end in intervals:
        await _conn.execute("INSERT INTO work_hours(staff_id,weekday,start_min,end_min) VALUES(?,?,?,?)",
                            (staff_id, weekday, start, end))
    await _conn.commit()


async def copy_week_hours(src_id: int, dst_id: int) -> None:
    await _conn.execute("DELETE FROM work_hours WHERE staff_id=?", (dst_id,))
    await _conn.execute(
        "INSERT INTO work_hours(staff_id,weekday,start_min,end_min) "
        "SELECT ?, weekday, start_min, end_min FROM work_hours WHERE staff_id=?", (dst_id, src_id))
    await _conn.commit()


async def add_block(staff_id: int, date: str, start_min: int, end_min: int) -> int:
    return await _exec(
        "INSERT INTO blocked(staff_id,date,start_min,end_min) VALUES(?,?,?,?)",
        (staff_id, date, start_min, end_min),
    )


async def get_blocks(staff_id: int, date: str) -> list[dict]:
    return await _all("SELECT * FROM blocked WHERE staff_id=? AND date=?", (staff_id, date))


# ---------- clients ----------
async def upsert_client(shop_id: int, tg_id: int, name: str) -> None:
    await _exec(
        "INSERT INTO clients(shop_id,tg_id,name) VALUES(?,?,?) "
        "ON CONFLICT(shop_id,tg_id) DO UPDATE SET name=excluded.name",
        (shop_id, tg_id, name),
    )


async def insert_client_full(shop_id: int, tg_id: int, name: str, phone: str | None, is_demo: int = 0,
                             lang: str | None = None) -> None:
    await _exec(
        "INSERT OR REPLACE INTO clients(shop_id,tg_id,name,phone,is_demo,lang) VALUES(?,?,?,?,?,?)",
        (shop_id, tg_id, name, phone, is_demo, lang),
    )


async def new_virtual_client_id() -> int:
    row = await _one("SELECT COALESCE(MIN(tg_id), 0) AS m FROM clients WHERE tg_id < 0")
    return min(-1, row["m"] - 1)


async def get_client(shop_id: int, tg_id: int) -> dict | None:
    return await _one("SELECT * FROM clients WHERE shop_id=? AND tg_id=?", (shop_id, tg_id))


async def get_lang(shop_id: int, tg_id: int) -> str | None:
    row = await _one("SELECT lang FROM clients WHERE shop_id=? AND tg_id=?", (shop_id, tg_id))
    return row["lang"] if row else None


async def set_lang(shop_id: int, tg_id: int, lang: str) -> None:
    await _exec("UPDATE clients SET lang=? WHERE shop_id=? AND tg_id=?", (lang, shop_id, tg_id))


async def set_phone(shop_id: int, tg_id: int, phone: str) -> None:
    await _exec("UPDATE clients SET phone=? WHERE shop_id=? AND tg_id=?", (phone, shop_id, tg_id))


async def find_client_by_phone(shop_id: int, phone: str, virtual_only: bool = False) -> dict | None:
    sql = "SELECT * FROM clients WHERE shop_id=? AND phone=?"
    if virtual_only:
        sql += " AND tg_id < 0 AND is_demo=0"
    sql += " ORDER BY tg_id DESC LIMIT 1"  # haqiqiy (musbat) ID birinchi
    return await _one(sql, (shop_id, phone))


async def merge_client(shop_id: int, old_id: int, new_id: int) -> None:
    """Qo'lda qo'shilgan (virtual) mijozni haqiqiy Telegram mijoz bilan birlashtiradi."""
    old = await get_client(shop_id, old_id)
    if not old or old_id == new_id:
        return
    for table in ("bookings", "reviews", "waitlist"):
        await _conn.execute(f"UPDATE {table} SET client_id=? WHERE shop_id=? AND client_id=?",
                            (new_id, shop_id, old_id))
    await _conn.execute(
        "UPDATE clients SET deposit_credit = deposit_credit + ?, no_show_count = no_show_count + ? "
        "WHERE shop_id=? AND tg_id=?",
        (old["deposit_credit"], old["no_show_count"], shop_id, new_id))
    await _conn.execute("DELETE FROM clients WHERE shop_id=? AND tg_id=?", (shop_id, old_id))
    await _conn.commit()


async def add_credit(shop_id: int, tg_id: int, delta: int) -> None:
    await _exec(
        "UPDATE clients SET deposit_credit = MAX(0, deposit_credit + ?) WHERE shop_id=? AND tg_id=?",
        (delta, shop_id, tg_id),
    )


async def inc_no_show(shop_id: int, tg_id: int) -> int:
    await _exec("UPDATE clients SET no_show_count = no_show_count + 1 WHERE shop_id=? AND tg_id=?", (shop_id, tg_id))
    row = await get_client(shop_id, tg_id)
    return row["no_show_count"] if row else 0


async def set_client_blocked(shop_id: int, tg_id: int, blocked: bool) -> None:
    if blocked:
        await _exec("UPDATE clients SET blocked=1 WHERE shop_id=? AND tg_id=?", (shop_id, tg_id))
    else:
        await _exec("UPDATE clients SET blocked=0, no_show_count=0 WHERE shop_id=? AND tg_id=?", (shop_id, tg_id))


async def list_clients(shop_id: int, limit: int = 20) -> list[dict]:
    return await _all(
        "SELECT * FROM clients WHERE shop_id=? ORDER BY blocked DESC, no_show_count DESC, name LIMIT ?",
        (shop_id, limit),
    )


async def broadcast_targets(shop_id: int) -> list[int]:
    rows = await _all("SELECT tg_id FROM clients WHERE shop_id=? AND tg_id>0 AND is_demo=0", (shop_id,))
    return [r["tg_id"] for r in rows]


async def count_completed(shop_id: int, client_id: int) -> int:
    row = await _one(
        "SELECT COUNT(*) AS n FROM bookings WHERE shop_id=? AND client_id=? AND status='completed'",
        (shop_id, client_id))
    return row["n"]


async def has_active_discounted(shop_id: int, client_id: int) -> bool:
    row = await _one(
        "SELECT 1 AS x FROM bookings WHERE shop_id=? AND client_id=? AND discount_percent>0 "
        "AND status IN ('pending_payment','confirmed') LIMIT 1", (shop_id, client_id))
    return bool(row)


async def winback_candidates(shop_id: int, newest_date: str, oldest_date: str) -> list[dict]:
    return await _all(
        "SELECT c.tg_id, c.name, c.lang, MAX(b.date) AS last_date FROM clients c "
        "JOIN bookings b ON b.shop_id=c.shop_id AND b.client_id=c.tg_id AND b.status='completed' "
        "WHERE c.shop_id=? AND c.tg_id>0 AND c.blocked=0 AND c.is_demo=0 "
        "GROUP BY c.tg_id HAVING last_date <= ? AND last_date >= ? "
        "AND (c.winback_for IS NULL OR c.winback_for != last_date)",
        (shop_id, newest_date, oldest_date))


async def mark_winback(shop_id: int, tg_id: int, last_date: str) -> None:
    await _exec("UPDATE clients SET winback_for=? WHERE shop_id=? AND tg_id=?", (last_date, shop_id, tg_id))


async def first_visit_dates(shop_id: int) -> dict[int, str]:
    rows = await _all(
        "SELECT client_id, MIN(date) AS d FROM bookings WHERE shop_id=? AND status IN ('completed','no_show') "
        "GROUP BY client_id", (shop_id,))
    return {r["client_id"]: r["d"] for r in rows}


# ---------- bookings ----------
async def insert_booking(**f) -> int:
    cols = ", ".join(f.keys())
    marks = ", ".join("?" for _ in f)
    return await _exec(f"INSERT INTO bookings({cols}) VALUES({marks})", tuple(f.values()))


async def get_booking(booking_id: int) -> dict | None:
    return await _one(BOOKING_SELECT + " WHERE b.id=?", (booking_id,))


async def update_booking(booking_id: int, **fields) -> None:
    cols = ", ".join(f"{k}=?" for k in fields)
    await _exec(f"UPDATE bookings SET {cols} WHERE id=?", (*fields.values(), booking_id))


async def active_bookings(staff_id: int, date: str) -> list[dict]:
    return await _all(
        "SELECT * FROM bookings WHERE staff_id=? AND date=? AND status IN ('pending_payment','confirmed') "
        "ORDER BY start_min",
        (staff_id, date),
    )


async def bookings_for_day(shop_id: int, date: str, staff_ids: list[int] | None = None) -> list[dict]:
    sql = BOOKING_SELECT + (
        " WHERE b.shop_id=? AND b.date=? "
        "AND b.status IN ('pending_payment','confirmed','completed','no_show')"
    )
    params: list = [shop_id, date]
    if staff_ids is not None:
        sql += f" AND b.staff_id IN ({_in(staff_ids)})"
        params.extend(staff_ids)
    sql += " ORDER BY b.start_min, b.id"
    return await _all(sql, tuple(params))


async def client_active_bookings(shop_id: int, tg_id: int, from_date: str) -> list[dict]:
    return await _all(
        BOOKING_SELECT + " WHERE b.shop_id=? AND b.client_id=? AND b.date>=? "
        "AND b.status IN ('pending_payment','confirmed') ORDER BY b.date, b.start_min",
        (shop_id, tg_id, from_date),
    )


async def future_bookings_of_staff(staff_id: int, from_date: str) -> list[dict]:
    return await _all(
        BOOKING_SELECT + " WHERE b.staff_id=? AND b.date>=? AND b.status IN ('pending_payment','confirmed') "
        "ORDER BY b.date, b.start_min", (staff_id, from_date))


async def pending_receipt_booking(shop_id: int, tg_id: int) -> dict | None:
    return await _one(
        BOOKING_SELECT + " WHERE b.shop_id=? AND b.client_id=? AND b.status='pending_payment' "
        "AND b.deposit_status='pending' ORDER BY b.id DESC LIMIT 1",
        (shop_id, tg_id),
    )


async def receipt_sent_booking(shop_id: int, tg_id: int) -> dict | None:
    return await _one(
        BOOKING_SELECT + " WHERE b.shop_id=? AND b.client_id=? AND b.status='pending_payment' "
        "AND b.deposit_status='receipt_sent' ORDER BY b.id DESC LIMIT 1", (shop_id, tg_id))


async def expired_pending(now_str: str) -> list[dict]:
    return await _all(
        BOOKING_SELECT + " WHERE b.status='pending_payment' AND b.deposit_status='pending' "
        "AND b.pay_deadline IS NOT NULL AND b.pay_deadline < ?",
        (now_str,),
    )


async def confirmed_between(date_from: str, date_to: str) -> list[dict]:
    return await _all(
        BOOKING_SELECT + " WHERE b.status='confirmed' AND b.date BETWEEN ? AND ?",
        (date_from, date_to),
    )


async def review_requests_due(cutoff_str: str) -> list[dict]:
    return await _all(
        BOOKING_SELECT + " WHERE b.status='completed' AND b.review_asked=0 AND b.client_id>0 "
        "AND b.completed_at IS NOT NULL AND b.completed_at <= ?", (cutoff_str,))


async def report_rows(shop_id: int, d_from: str, d_to: str, staff_ids: list[int] | None = None) -> list[dict]:
    sql = ("SELECT b.*, s.name AS service_name, st.name AS staff_name FROM bookings b "
           "JOIN services s ON s.id=b.service_id JOIN staff st ON st.id=b.staff_id "
           "WHERE b.shop_id=? AND b.date BETWEEN ? AND ?")
    params: list = [shop_id, d_from, d_to]
    if staff_ids is not None:
        sql += f" AND b.staff_id IN ({_in(staff_ids)})"
        params.extend(staff_ids)
    return await _all(sql, tuple(params))


# ---------- reviews ----------
async def add_review(booking_id, shop_id, staff_id, client_id, rating, created_at, comment=None) -> int:
    return await _exec(
        "INSERT OR REPLACE INTO reviews(booking_id,shop_id,staff_id,client_id,rating,comment,created_at) "
        "VALUES(?,?,?,?,?,?,?)", (booking_id, shop_id, staff_id, client_id, rating, comment, created_at))


async def set_review_comment(booking_id: int, comment: str) -> None:
    await _exec("UPDATE reviews SET comment=? WHERE booking_id=?", (comment, booking_id))


async def get_review(booking_id: int) -> dict | None:
    return await _one("SELECT * FROM reviews WHERE booking_id=?", (booking_id,))


async def reviews_between(shop_id: int, d_from: str, d_to: str, staff_ids: list[int] | None = None) -> list[dict]:
    sql = ("SELECT r.*, b.date, st.name AS staff_name, c.name AS client_name FROM reviews r "
           "JOIN bookings b ON b.id=r.booking_id JOIN staff st ON st.id=r.staff_id "
           "LEFT JOIN clients c ON c.shop_id=r.shop_id AND c.tg_id=r.client_id "
           "WHERE r.shop_id=? AND b.date BETWEEN ? AND ?")
    params: list = [shop_id, d_from, d_to]
    if staff_ids is not None:
        sql += f" AND r.staff_id IN ({_in(staff_ids)})"
        params.extend(staff_ids)
    sql += " ORDER BY r.id DESC"
    return await _all(sql, tuple(params))


# ---------- waitlist ----------
async def add_waitlist(shop_id, client_id, staff_id, service_id, date, created_at) -> int:
    row = await _one("SELECT id FROM waitlist WHERE client_id=? AND staff_id=? AND date=? AND shop_id=?",
                     (client_id, staff_id, date, shop_id))
    if row:
        return row["id"]
    return await _exec(
        "INSERT INTO waitlist(shop_id,client_id,staff_id,service_id,date,created_at) VALUES(?,?,?,?,?,?)",
        (shop_id, client_id, staff_id, service_id, date, created_at))


async def get_waitlist(entry_id: int) -> dict | None:
    return await _one(
        "SELECT w.*, s.name AS service_name, s.duration_min, st.name AS staff_name FROM waitlist w "
        "JOIN services s ON s.id=w.service_id JOIN staff st ON st.id=w.staff_id WHERE w.id=?", (entry_id,))


async def waitlist_for(staff_id: int, date: str) -> list[dict]:
    return await _all(
        "SELECT w.*, s.name AS service_name, s.duration_min, st.name AS staff_name FROM waitlist w "
        "JOIN services s ON s.id=w.service_id JOIN staff st ON st.id=w.staff_id "
        "WHERE w.staff_id=? AND w.date=? ORDER BY w.id", (staff_id, date))


async def client_waitlist(shop_id: int, client_id: int, from_date: str) -> list[dict]:
    return await _all(
        "SELECT w.*, s.name AS service_name, s.duration_min, st.name AS staff_name FROM waitlist w "
        "JOIN services s ON s.id=w.service_id JOIN staff st ON st.id=w.staff_id "
        "WHERE w.shop_id=? AND w.client_id=? AND w.date>=? ORDER BY w.date", (shop_id, client_id, from_date))


async def delete_waitlist(entry_id: int) -> None:
    await _exec("DELETE FROM waitlist WHERE id=?", (entry_id,))


async def delete_waitlist_for(client_id: int, staff_id: int, date: str) -> None:
    await _exec("DELETE FROM waitlist WHERE client_id=? AND staff_id=? AND date=?", (client_id, staff_id, date))


async def mark_waitlist_notified(entry_id: int, ts: str) -> None:
    await _exec("UPDATE waitlist SET notified_at=? WHERE id=?", (ts, entry_id))


async def purge_waitlist(before_date: str) -> None:
    await _exec("DELETE FROM waitlist WHERE date < ?", (before_date,))


# ---------- cheklar (takror ishlatishdan himoya) ----------
async def receipt_key_used(key: str) -> bool:
    return bool(await _one("SELECT 1 AS x FROM used_receipts WHERE key=?", (key,)))


async def mark_receipt_used(key: str, booking_id: int) -> None:
    await _exec("INSERT OR IGNORE INTO used_receipts(key,booking_id) VALUES(?,?)", (key, booking_id))


async def unmark_receipts(booking_id: int) -> None:
    await _exec("DELETE FROM used_receipts WHERE booking_id=?", (booking_id,))


# ---------- demo ma'lumotlar ----------
async def count_demo(shop_id: int | None = None) -> int:
    if shop_id is None:
        row = await _one("SELECT COUNT(*) AS n FROM bookings WHERE is_demo=1")
    else:
        row = await _one("SELECT COUNT(*) AS n FROM bookings WHERE is_demo=1 AND shop_id=?", (shop_id,))
    return row["n"]


async def clear_demo(shop_id: int) -> None:
    await _conn.execute("DELETE FROM reviews WHERE booking_id IN (SELECT id FROM bookings WHERE shop_id=? AND is_demo=1)",
                        (shop_id,))
    await _conn.execute("DELETE FROM waitlist WHERE client_id IN (SELECT tg_id FROM clients WHERE shop_id=? AND is_demo=1) "
                        "AND shop_id=?", (shop_id, shop_id))
    await _conn.execute("DELETE FROM bookings WHERE shop_id=? AND is_demo=1", (shop_id,))
    await _conn.execute("DELETE FROM clients WHERE shop_id=? AND is_demo=1", (shop_id,))
    await _conn.commit()
