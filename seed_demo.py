"""Hisobot bo'sh turmasligi uchun SOXTA tarixiy ma'lumotlar (demo).

Ishga tushirish: python seed_demo.py   (yoki DEMO_DATA=1 bo'lsa, baza birinchi yaratilganda avtomatik)
O'chirish: botda Admin panel -> Sozlamalar -> "Demo ma'lumotlarni o'chirish".
"""
from __future__ import annotations

import asyncio
import random
from datetime import timedelta

import db
import services

FIRST = ["Ali", "Vali", "Hasan", "Husan", "Sanjar", "Dilshod", "Jamshid", "Rustam", "Bobur", "Sherzod",
         "Akmal", "Farhod", "Nodir", "Timur", "Anvar", "Javohir", "Eldor", "Kamol", "Umid", "Zafar",
         "Otabek", "Murod", "Shaxzod", "Behzod", "Laziz", "Oybek", "Ilhom", "Sardor", "Abbos", "Doniyor"]
LAST = ["A.", "B.", "D.", "J.", "K.", "M.", "N.", "R.", "S.", "T."]
COMMENTS_GOOD = ["Zo'r usta, rahmat!", "Tez va sifatli", "Juda yoqdi, yana kelaman", "Dazmoldek bo'ldi 👌",
                 "Hammasi a'lo", "Toza va chiroyli ish"]
COMMENTS_MID = ["Yaxshi, lekin biroz kutdim", "Oddiy, yomon emas", "Narx biroz qimmat"]
COMMENTS_BAD = ["Kutib qoldim, kech boshlashdi", "Kutganimdek chiqmadi"]


def _pick_rating(rng: random.Random) -> int:
    return rng.choices([5, 4, 3, 2, 1], weights=[52, 28, 12, 5, 3])[0]


def _slots(rng: random.Random, intervals: list[tuple[int, int]], count: int, durations: list[int]):
    """Bir kun uchun bir-biriga to'qnashmaydigan vaqtlar."""
    placed: list[tuple[int, int]] = []
    tries = 0
    while len(placed) < count and tries < 80:
        tries += 1
        dur = rng.choice(durations)
        s, e = rng.choice(intervals)
        if e - s < dur:
            continue
        start = s + 30 * rng.randrange(0, (e - s - dur) // 30 + 1)
        if all(start >= pe or pstart >= start + dur for pstart, pe in placed):
            placed.append((start, start + dur))
    return sorted(placed)


async def generate(days_back: int = 45, seed: int = 7) -> bool:
    if await db.count_demo() > 0:
        return False
    rng = random.Random(seed)
    today = services.today_str()
    for shop in await db.list_shops():
        sid = shop["id"]
        barbers = await db.list_staff(sid, role="barber")
        svcs = await db.list_services(sid)
        if not barbers or not svcs:
            continue
        # demo mijozlar (virtual, manfiy ID)
        clients: list[int] = []
        for i in range(36):
            cid = await db.new_virtual_client_id()
            name = f"{rng.choice(FIRST)} {rng.choice(LAST)}"
            phone = f"+99890{rng.randint(1000000, 9999999)}"
            await db.insert_client_full(sid, cid, name, phone, is_demo=1, lang="uz")
            clients.append(cid)
        weights = [1 / (i + 1) ** 0.6 for i in range(len(clients))]  # ba'zilari tez-tez keladi
        svc_weights = [5, 3, 3, 1.5][:len(svcs)]
        no_show_count: dict[int, int] = {}

        for back in range(days_back, 0, -1):
            d = services.date_plus(today, -back)
            wd = services.parse_date(d).weekday()
            for br in barbers:
                hours = await db.get_work_hours(br["id"], wd)
                if not hours:
                    continue
                intervals = [(h["start_min"], h["end_min"]) for h in hours]
                n = rng.randint(3, 8)
                for start, _end in _slots(rng, intervals, n, [30, 30, 60]):
                    svc = rng.choices(svcs, weights=svc_weights)[0]
                    if svc["duration_min"] > _end - start:
                        continue
                    cid = rng.choices(clients, weights=weights)[0]
                    r = rng.random()
                    manual = rng.random() < 0.25
                    dep = 0 if manual else shop["deposit_amount"]
                    if r < 0.82:
                        status, dstat = "completed", ("none" if manual else "applied")
                    elif r < 0.88:
                        status, dstat = "no_show", ("none" if manual else "forfeited")
                        no_show_count[cid] = no_show_count.get(cid, 0) + 1
                    elif r < 0.96:
                        status, dstat = "cancelled_by_client", ("none" if manual else "credited")
                    else:
                        status, dstat = "cancelled_by_barber", ("none" if manual else "credited")
                    created = (services.parse_date(d) - timedelta(days=rng.randint(0, 3))).strftime("%Y-%m-%d") + " 12:00:00"
                    bid = await db.insert_booking(
                        shop_id=sid, client_id=cid, staff_id=br["id"], service_id=svc["id"], date=d,
                        start_min=start, duration_min=svc["duration_min"], price=svc["price"], status=status,
                        deposit_amount=dep, deposit_status=dstat, created_at=created,
                        completed_at=(d + " 18:00:00") if status == "completed" else None,
                        review_asked=1 if status == "completed" else 0,
                        source="manual" if manual else "bot", is_demo=1, client_confirmed=1)
                    if status == "completed" and rng.random() < 0.55:
                        rating = _pick_rating(rng)
                        comment = None
                        if rng.random() < 0.45:
                            pool = COMMENTS_GOOD if rating >= 4 else COMMENTS_MID if rating == 3 else COMMENTS_BAD
                            comment = rng.choice(pool)
                        await db.add_review(bid, sid, br["id"], cid, rating, d + " 19:00:00", comment)

        for cid, n in no_show_count.items():
            await db._exec("UPDATE clients SET no_show_count=? WHERE shop_id=? AND tg_id=?", (n, sid, cid))

        # bugun va keyingi kunlar uchun bir nechta tasdiqlangan navbat (Bugun/Ertaga ro'yxati bo'sh turmasin)
        now = services.now_local()
        for ahead in range(0, 3):
            d = services.date_plus(today, ahead)
            wd = services.parse_date(d).weekday()
            for br in barbers:
                hours = await db.get_work_hours(br["id"], wd)
                if not hours:
                    continue
                intervals = [(h["start_min"], h["end_min"]) for h in hours]
                for start, _end in _slots(rng, intervals, rng.randint(2, 4), [30, 30, 60]):
                    if ahead == 0 and start < now.hour * 60 + now.minute + 60:
                        continue
                    svc = rng.choices(svcs, weights=svc_weights)[0]
                    if svc["duration_min"] > _end - start:
                        continue
                    cid = rng.choice(clients)
                    await db.insert_booking(
                        shop_id=sid, client_id=cid, staff_id=br["id"], service_id=svc["id"], date=d,
                        start_min=start, duration_min=svc["duration_min"], price=svc["price"],
                        status="confirmed", deposit_amount=shop["deposit_amount"], deposit_status="paid",
                        created_at=(now - timedelta(days=2)).strftime(services.FMT), is_demo=1)
    return True


async def _main() -> None:
    await db.init_db()
    print("Demo ma'lumotlar qo'shildi." if await generate() else "Demo ma'lumotlar allaqachon bor.")
    await db.close_db()


if __name__ == "__main__":
    asyncio.run(_main())
