from collections import defaultdict
from datetime import datetime, timedelta

from odoo import fields, http
from odoo.http import request

from ....util.portal_auth import get_portal_admin_from_request
from ....util.request import json_response

GRANULARITIES = {
    "day": "day",
    "week": "week",
    "month": "month",
}


class PortalDashboardController(http.Controller):
    @http.route("/api/portal/dashboard", type="http", auth="public", methods=["GET"], csrf=False, cors="*")
    def get_dashboard(self, **kwargs):
        user, auth_error = get_portal_admin_from_request()
        if auth_error:
            return auth_error

        partner = user.crm_partner_id
        date_range, error = self._parse_date_range(kwargs)
        if error:
            return error

        granularity = self._parse_granularity(kwargs.get("granularity"))
        date_from = date_range["date_from"]
        date_to = date_range["date_to"]

        return json_response({
            "date_from": fields.Datetime.to_string(date_from),
            "date_to": fields.Datetime.to_string(date_to),
            "granularity": granularity,
            "members_by_tier": self._get_members_by_tier(partner),
            "user_registrations": self._get_user_registrations(partner, date_from, date_to, granularity),
            "user_registrations_by_hour": self._get_user_registrations_by_hour(partner, date_from, date_to),
            "receipt_amounts": self._get_receipt_amounts(partner, date_from, date_to, granularity),
            "coupons_by_name": self._get_coupons_by_name(partner, date_from, date_to),
            "points": self._get_points_summary(partner, date_from, date_to, granularity),
        })

    def _parse_date_range(self, kwargs):
        now = fields.Datetime.now()
        default_from = now - timedelta(days=30)

        date_from = self._parse_datetime(kwargs.get("date_from"), end_of_day=False) or default_from
        date_to = self._parse_datetime(kwargs.get("date_to"), end_of_day=True) or now

        if date_from > date_to:
            return None, json_response(
                {
                    "error": "invalid_date_range",
                    "message": "date_from must be earlier than or equal to date_to.",
                },
                status=400,
            )

        return {"date_from": date_from, "date_to": date_to}, None

    def _parse_datetime(self, value, end_of_day=False):
        if not value:
            return None

        text = str(value).strip()
        if not text:
            return None

        parsed = fields.Datetime.to_datetime(text)
        if end_of_day and len(text) <= 10:
            parsed = parsed.replace(hour=23, minute=59, second=59)
        return parsed

    def _parse_granularity(self, value):
        granularity = (value or "day").strip().lower()
        return GRANULARITIES.get(granularity, "day")

    def _get_members_by_tier(self, partner):
        user_model = request.env["crm.user"].sudo()
        tier_model = request.env["partner.tier"].sudo()

        groups = user_model.read_group(
            [("partner_id", "=", partner.id), ("active", "=", True)],
            ["__count"],
            ["tier_id"],
            lazy=False,
        )
        counts_by_tier_id = {}
        unassigned_count = 0
        for group in groups:
            if group.get("tier_id"):
                counts_by_tier_id[group["tier_id"][0]] = group["__count"]
            else:
                unassigned_count = group["__count"]

        tiers = tier_model.search([("partner_id", "=", partner.id)], order="min_spending asc, id asc")
        results = []
        for tier in tiers:
            results.append({
                "tier_id": tier.id,
                "tier_code": tier.code,
                "tier_name": tier.name,
                "count": counts_by_tier_id.get(tier.id, 0),
            })

        if unassigned_count:
            results.append({
                "tier_id": False,
                "tier_code": False,
                "tier_name": "Unassigned",
                "count": unassigned_count,
            })

        return results

    def _get_user_registrations(self, partner, date_from, date_to, granularity):
        user_model = request.env["crm.user"].sudo()
        domain = [
            ("partner_id", "=", partner.id),
            ("create_date", ">=", date_from),
            ("create_date", "<=", date_to),
        ]
        groups = user_model.read_group(
            domain,
            ["__count"],
            [f"create_date:{granularity}"],
            lazy=False,
        )
        return self._serialize_time_series(
            groups,
            f"create_date:{granularity}",
            date_from,
            date_to,
            granularity,
            value_key="count",
            value_getter=lambda group: group["__count"],
        )

    def _get_user_registrations_by_hour(self, partner, date_from, date_to):
        user_model = request.env["crm.user"].sudo()
        users = user_model.search([
            ("partner_id", "=", partner.id),
            ("create_date", ">=", date_from),
            ("create_date", "<=", date_to),
        ])

        hour_counts = {hour: 0 for hour in range(24)}
        for user in users:
            if not user.create_date:
                continue
            hour_counts[user.create_date.hour] += 1

        return [
            {"hour": hour, "count": hour_counts[hour]}
            for hour in range(24)
        ]

    def _get_receipt_amounts(self, partner, date_from, date_to, granularity):
        receipt_model = request.env["crm.partner.receipt.redeem"].sudo()
        domain = [
            ("partner_id", "=", partner.id),
            ("state", "=", "approved"),
            ("reviewed_date", ">=", date_from),
            ("reviewed_date", "<=", date_to),
        ]
        groups = receipt_model.read_group(
            domain,
            ["amount:sum", "__count"],
            [f"reviewed_date:{granularity}"],
            lazy=False,
        )
        return self._serialize_time_series(
            groups,
            f"reviewed_date:{granularity}",
            date_from,
            date_to,
            granularity,
            value_key="amount",
            value_getter=lambda group: group["amount"] or 0.0,
            extra_getter=lambda group: {"count": group["__count"]},
        )

    def _get_coupons_by_name(self, partner, date_from, date_to):
        coupon_model = request.env["crm.user.coupon"].sudo()
        user_coupons = coupon_model.search([
            ("partner_id", "=", partner.id),
            ("acquired_date", ">=", date_from),
            ("acquired_date", "<=", date_to),
        ])

        now = fields.Datetime.now()
        stats = defaultdict(lambda: {
            "coupon_id": False,
            "coupon_name": "",
            "redeemed_count": 0,
            "used_count": 0,
            "expired_count": 0,
        })

        for user_coupon in user_coupons:
            coupon = user_coupon.coupon_id
            key = coupon.id
            entry = stats[key]
            entry["coupon_id"] = coupon.id
            entry["coupon_name"] = coupon.name

            if user_coupon.is_used:
                entry["used_count"] += 1
            elif user_coupon.expiration_date and user_coupon.expiration_date < now:
                entry["expired_count"] += 1
            else:
                entry["redeemed_count"] += 1

        return sorted(
            [
                {
                    **item,
                    "total_count": item["redeemed_count"] + item["used_count"] + item["expired_count"],
                }
                for item in stats.values()
            ],
            key=lambda item: (-item["total_count"], item["coupon_name"]),
        )

    def _get_points_summary(self, partner, date_from, date_to, granularity):
        point_model = request.env["crm.user.point"].sudo()
        default_currency = partner.currency_ids.filtered("is_default")[:1]
        domain = [
            ("user_id.partner_id", "=", partner.id),
            ("given_date", ">=", date_from),
            ("given_date", "<=", date_to),
        ]
        if default_currency:
            domain.append(("currency_id", "=", default_currency.id))

        earned_groups = point_model.read_group(
            domain + [("type", "=", "earn")],
            ["value:sum"],
            [f"given_date:{granularity}"],
            lazy=False,
        )
        used_groups = point_model.read_group(
            domain + [("type", "=", "burn")],
            ["value:sum"],
            [f"given_date:{granularity}"],
            lazy=False,
        )

        earned_by_period = {
            self._normalize_period(group[f"given_date:{granularity}"], granularity): group["value"] or 0.0
            for group in earned_groups
        }
        used_by_period = {
            self._normalize_period(group[f"given_date:{granularity}"], granularity): group["value"] or 0.0
            for group in used_groups
        }

        periods = self._iter_periods(date_from, date_to, granularity)
        series = [
            {
                "period": period,
                "earned": earned_by_period.get(period, 0.0),
                "used": used_by_period.get(period, 0.0),
            }
            for period in periods
        ]
        return {
            "currency": {
                "id": default_currency.id,
                "name": default_currency.name,
            } if default_currency else False,
            "series": series,
        }

    def _serialize_time_series(
        self,
        groups,
        group_field,
        date_from,
        date_to,
        granularity,
        value_key,
        value_getter,
        extra_getter=None,
    ):
        values_by_period = {}
        for group in groups:
            period = self._normalize_period(group.get(group_field), granularity)
            if not period:
                continue
            item = {value_key: value_getter(group)}
            if extra_getter:
                item.update(extra_getter(group))
            values_by_period[period] = item

        results = []
        for period in self._iter_periods(date_from, date_to, granularity):
            item = values_by_period.get(period, {value_key: 0 if value_key == "count" else 0.0})
            results.append({"period": period, **item})

        return results

    def _format_week_period(self, value):
        if isinstance(value, str):
            parsed = fields.Date.to_date(value)
        elif isinstance(value, datetime):
            parsed = value.date()
        elif hasattr(value, "year") and hasattr(value, "month"):
            parsed = value
        else:
            return str(value)

        iso_year, iso_week, _ = parsed.isocalendar()
        return f"{iso_year}-W{iso_week:02d}"

    def _normalize_period(self, value, granularity):
        if not value:
            return False

        if granularity == "week":
            return self._format_week_period(value)

        if isinstance(value, str):
            if granularity == "month":
                return value[:7]
            return value[:10]

        if isinstance(value, datetime):
            if granularity == "month":
                return value.strftime("%Y-%m")
            return value.strftime("%Y-%m-%d")

        if hasattr(value, "year") and hasattr(value, "month"):
            if granularity == "month":
                return value.strftime("%Y-%m")
            return value.strftime("%Y-%m-%d")

        return str(value)

    def _iter_periods(self, date_from, date_to, granularity):
        if granularity == "month":
            current = date_from.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            end = date_to.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            periods = []
            while current <= end:
                periods.append(current.strftime("%Y-%m"))
                if current.month == 12:
                    current = current.replace(year=current.year + 1, month=1)
                else:
                    current = current.replace(month=current.month + 1)
            return periods

        if granularity == "week":
            current = date_from.date()
            end = date_to.date()
            current -= timedelta(days=current.weekday())
            periods = []
            seen = set()
            while current <= end:
                period = self._format_week_period(current)
                if period not in seen:
                    seen.add(period)
                    periods.append(period)
                current += timedelta(days=7)
            return periods

        current = date_from.replace(hour=0, minute=0, second=0, microsecond=0)
        end = date_to.replace(hour=0, minute=0, second=0, microsecond=0)
        periods = []
        while current <= end:
            periods.append(current.strftime("%Y-%m-%d"))
            current += timedelta(days=1)
        return periods
