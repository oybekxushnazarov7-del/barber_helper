"""Demo ma'lumotlar: 2 ta shop, har birida 3 ta usta, xizmatlar va ish vaqti."""
from __future__ import annotations

import asyncio
import secrets

import config
import db

BARBERS = {
    1: ["Jasur", "Aziz", "Sardor"],
    2: ["Bekzod", "Otabek", "Doston"],
}

# (nomi, narxi, davomiyligi daqiqada) — davomiylik 30 ning karrali bo'lishi qulay
SERVICES = [
    ("Soch olish", 60000, 30),
    ("Soqol", 30000, 30),
    ("Soch + soqol", 80000, 60),
    ("Bolalar sochi", 40000, 30),
]

# Dushanba-Shanba: 09:00-13:00 va 14:00-21:00 (13:00-14:00 tushlik). Yakshanba dam.
WORK_DAYS = range(0, 6)
WORK_INTERVALS = [(9 * 60, 13 * 60), (14 * 60, 21 * 60)]


async def create_barber(shop_id: int, name: str) -> dict:
    """Yangi usta + standart ish vaqti + shaxsiy havola kodi."""
    staff_id = await db.insert_staff(shop_id, None, name, "barber", secrets.token_hex(4))
    for wd in WORK_DAYS:
        for s, e in WORK_INTERVALS:
            await db.insert_work_hours(staff_id, wd, s, e)
    return await db.get_staff(staff_id)


async def seed_if_empty() -> bool:
    if await db.count_shops() > 0:
        await ensure_location_defaults()
        return False
    for shop_id, cfg in config.SHOPS.items():
        await db.insert_shop(
            shop_id, cfg["name"], "Toshkent, manzilni Sozlamalardan kiriting", "+998 90 000 00 00",
            config.CARD_NUMBER, config.DEPOSIT_AMOUNT, config.FREE_CANCEL_HOURS, config.SLOT_STEP,
            cfg["lat"], cfg["lon"],
        )
        for name in BARBERS[shop_id]:
            await create_barber(shop_id, name)
        for name, price, dur in SERVICES:
            await db.insert_service(shop_id, name, price, dur)
    return True


async def ensure_location_defaults() -> None:
    """Eski bazada lokatsiya bo'sh bo'lsa, demo koordinatalarni qo'yadi."""
    for shop in await db.list_shops():
        cfg = config.SHOPS.get(shop["id"])
        if cfg and shop.get("lat") is None:
            await db.update_shop(shop["id"], lat=cfg["lat"], lon=cfg["lon"])


async def _main() -> None:
    await db.init_db()
    created = await seed_if_empty()
    print("Demo ma'lumotlar kiritildi." if created else "Baza allaqachon to'ldirilgan.")
    await db.close_db()


if __name__ == "__main__":
    asyncio.run(_main())
