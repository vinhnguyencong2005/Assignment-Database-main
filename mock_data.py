"""Mock data và helper để demo UI khi chưa kết nối CSDL."""

from __future__ import annotations

MOCK_SELLERS = [
    {"store_name": "Shop A", "TotalRevenue": 1_200_000, "TotalOrders": 150},
    {"store_name": "Shop B", "TotalRevenue": 950_000, "TotalOrders": 120},
    {"store_name": "Shop C", "TotalRevenue": 700_000, "TotalOrders": 90},
    {"store_name": "Shop D", "TotalRevenue": 550_000, "TotalOrders": 60},
]

MOCK_BUYER_HISTORIES = {
    1: "Sản phẩm A, Sản phẩm B, Sản phẩm C",
    2: "Sản phẩm D, Sản phẩm E",
    3: "Sản phẩm F",
}


def get_mock_top_sellers(top_n: int, min_revenue: int) -> list[dict[str, int | str]]:
    """Lọc dữ liệu giả theo tham số để bám sát hành vi thật."""

    filtered = [s for s in MOCK_SELLERS if s["TotalRevenue"] >= min_revenue]
    sorted_sellers = sorted(filtered, key=lambda s: s["TotalRevenue"], reverse=True)
    return sorted_sellers[: max(0, top_n)]


def get_mock_buyer_history(buyer_id: int) -> str | None:
    """Trả về chuỗi mô tả lịch sử mua hàng. None nếu không có."""

    return MOCK_BUYER_HISTORIES.get(buyer_id)


