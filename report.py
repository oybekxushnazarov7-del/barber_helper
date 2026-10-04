"""Ega va ustalar uchun hisobot (statistika)."""
from __future__ import annotations

from collections import Counter, defaultdict

import db
import i18n
import services
from i18n import esc


def _bar(value: float, maximum: float, width: int = 10) -> str:
    if maximum <= 0:
        return "░" * width
    n = max(1 if value > 0 else 0, round(width * value / maximum))
    return "█" * n + "░" * (width - n)


def _stars(r: float) -> str:
    return "⭐" * int(round(r))


async def build_report(shop_id: int, d_from: str, d_to: str, staff_ids: list[int] | None, lang: str,
                       period_label: str) -> str:
    tr = lambda k, **kw: i18n.tr(lang, k, **kw)  # noqa: E731
    rows = await db.report_rows(shop_id, d_from, d_to, staff_ids)
    done = [r for r in rows if r["status"] == "completed"]
    noshow = [r for r in rows if r["status"] == "no_show"]
    cancelled = [r for r in rows if r["status"] in ("cancelled_by_client", "cancelled_by_barber", "expired")]
    upcoming = [r for r in rows if r["status"] in ("confirmed", "pending_payment") and r["date"] >= services.today_str()]

    if not (done or noshow or cancelled or upcoming):
        return tr("rp_empty", period=period_label)

    revenue = sum(r["price"] for r in done)
    avg = revenue // len(done) if done else 0
    visited = len(done) + len(noshow)
    noshow_rate = round(100 * len(noshow) / visited) if visited else 0
    saved = sum(r["deposit_amount"] for r in noshow if r["deposit_status"] == "forfeited")

    lines = [tr("rp_title", period=period_label), ""]
    lines.append(tr("rp_revenue", v=i18n.money(revenue, lang)))
    lines.append(tr("rp_done", n=len(done), avg=i18n.money(avg, lang)))
    lines.append(tr("rp_noshow", n=len(noshow), p=noshow_rate))
    lines.append(tr("rp_cancelled", n=len(cancelled)))
    if upcoming:
        lines.append(tr("rp_upcoming", n=len(upcoming)))
    if saved:
        lines.append(tr("rp_saved", v=i18n.money(saved, lang)))

    # ustalar bo'yicha
    reviews = await db.reviews_between(shop_id, d_from, d_to, staff_ids)
    rating_by_staff: dict[int, list[int]] = defaultdict(list)
    for rv in reviews:
        rating_by_staff[rv["staff_id"]].append(rv["rating"])
    by_staff: dict[str, dict] = {}
    for r in done:
        s = by_staff.setdefault(r["staff_name"], {"n": 0, "sum": 0, "id": r["staff_id"]})
        s["n"] += 1
        s["sum"] += r["price"]
    if len(by_staff) > 1 or (staff_ids is None and by_staff):
        lines += ["", tr("rp_by_barber")]
        mx = max(v["n"] for v in by_staff.values())
        for name, v in sorted(by_staff.items(), key=lambda kv: -kv[1]["n"]):
            rt = rating_by_staff.get(v["id"])
            rating = f" · ⭐{sum(rt) / len(rt):.1f}" if rt else ""
            lines.append(f"{_bar(v['n'], mx)} <b>{esc(name)}</b> — {v['n']} · {i18n.money(v['sum'], lang)}{rating}")

    # xizmatlar
    svc = Counter(r["service_name"] for r in done)
    if svc:
        lines += ["", tr("rp_services")]
        for name, n in svc.most_common(3):
            lines.append(f"• {esc(name)} — {n}")

    # mijozlar
    firsts = await db.first_visit_dates(shop_id)
    clients = {r["client_id"] for r in done}
    new = sum(1 for c in clients if d_from <= firsts.get(c, "") <= d_to)
    if clients:
        lines += ["", tr("rp_clients", total=len(clients), new=new, ret=len(clients) - new)]

    # eng band vaqt
    if done:
        wd = Counter(services.parse_date(r["date"]).weekday() for r in done)
        hr = Counter(r["start_min"] // 60 for r in done)
        top_wd = wd.most_common(1)[0][0]
        top_hr = hr.most_common(1)[0][0]
        lines.append(tr("rp_busy", day=i18n.WEEKDAYS_FULL[lang][top_wd], hour=f"{top_hr:02d}:00"))

    # baholar
    if reviews:
        avg_r = sum(r["rating"] for r in reviews) / len(reviews)
        lines += ["", tr("rp_rating", avg=f"{avg_r:.1f}", stars=_stars(avg_r), n=len(reviews))]
        shown = 0
        for rv in reviews:
            if rv.get("comment") and shown < 3:
                lines.append(f"💬 {'⭐' * rv['rating']} <i>{esc(rv['comment'][:90])}</i> — {esc(rv['staff_name'])}")
                shown += 1
    return "\n".join(lines)
