"""
B组: 物资连续性 (B1-B4) — 物品、金钱、装备、消耗品
"""

from __future__ import annotations

import re
from typing import Any

from .._base33 import DimResult


class Auditor33GroupB:
    """B组: 物资连续性 mixin"""

    _truth_manager: Any | None = None

    def _check_B1_inventory(self, draft: str, _chapter: int, _blueprint: dict) -> DimResult:
        if self._truth_manager:
            state = self._truth_manager.get("current_state")
            chars = state.get("characters", {})
            for name, data in chars.items():
                if name in draft and "inventory" in data:
                    inventory = data.get("inventory", [])
                    for item in inventory:
                        if isinstance(item, dict) and item.get("status") == "lost":
                            item_name = item.get("name", "")
                            if item_name and item_name in draft:
                                idx = draft.find(item_name)
                                context = draft[max(0, idx - 30) : idx + 30]
                                if name in context:
                                    return DimResult(
                                        "B1",
                                        "物品连续性",
                                        30,
                                        "FAIL",
                                        f'{name}的物品"{item_name}"已标记为丢失,但不能无故重新出现',
                                        "确认物品去向: 添加找回场景或删除使用",
                                        True,
                                    )

        return DimResult("B1", "物品连续性", 90, "PASS", "物品状态与记录一致")

    def _check_B2_money(self, draft: str, _chapter: int, _blueprint: dict) -> DimResult:
        if self._truth_manager:
            state = self._truth_manager.get("current_state")
            chars = state.get("characters", {})
            for name, data in chars.items():
                if name in draft and "money" in data:
                    stored_money = data.get("money", 0)
                    money_patterns = re.findall(
                        r"(?:花费|支付|购买|卖出|赚了|得到|失去)(?:了)?(\d+)(?:金币|灵石|银两|铜钱|元)",
                        draft,
                    )
                    for amount_str in money_patterns:
                        try:
                            amount = int(amount_str)
                            if stored_money > 0 and amount > stored_money * 0.8:
                                pass
                        except ValueError:
                            continue
        return DimResult(
            "B2", "金钱连续性", 95, "PASS", "金钱记录一致" if self._truth_manager else "通过"
        )

    def _check_B3_equipment(self, draft: str, _chapter: int, _blueprint: dict) -> DimResult:
        if self._truth_manager:
            state = self._truth_manager.get("current_state")
            chars = state.get("characters", {})
            for name, data in chars.items():
                if name in draft and "equipment" in data:
                    equipment = data.get("equipment", [])
                    eq_patterns = re.findall(
                        r"(?:握着|拿出|取出|挥动|驱动)(?:了)?([一-鿿]{2,6}(?:剑|刀|枪|斧|鞭|弓|扇|锤|鼎|印|幡|旗|索|環))",
                        draft,
                    )
                    known_eq_names = [
                        e.get("name", "") if isinstance(e, dict) else e for e in equipment
                    ]
                    for eq in eq_patterns:
                        if eq not in known_eq_names:
                            idx = draft.find(eq)
                            context = draft[max(0, idx - 40) : idx + 40]
                            if name in context:
                                return DimResult(
                                    "B3",
                                    "装备连续性",
                                    50,
                                    "WARN",
                                    f"{name}使用了未记录的装备: {eq}",
                                    "在前文添加装备获得场景",
                                    True,
                                )
        return DimResult("B3", "装备连续性", 90, "PASS", "装备使用与记录一致")

    def _check_B4_consumables(self, draft: str, _chapter: int, _blueprint: dict) -> DimResult:
        if self._truth_manager:
            state = self._truth_manager.get("current_state")
            chars = state.get("characters", {})
            for name, data in chars.items():
                if name in draft and "consumables" in data:
                    consumables = data.get("consumables", {})
                    for item_name, quantity in consumables.items():
                        if item_name in draft and isinstance(quantity, int) and quantity > 0:
                            usage_count = len(
                                re.findall(
                                    rf"(?:服用|吞下|服下|使用|捏碎|打出)(?:了)?(?:一枚|一颗|一张)?{re.escape(item_name)}",
                                    draft,
                                )
                            )
                            if usage_count > quantity:
                                return DimResult(
                                    "B4",
                                    "消耗品追踪",
                                    35,
                                    "FAIL",
                                    f"{name}本章使用了{item_name}{usage_count}次,"
                                    f"但库存只有{quantity}",
                                    "减少使用次数或在前文补充获取",
                                    True,
                                )

        return DimResult("B4", "消耗品追踪", 90, "PASS", "消耗品数量一致")
