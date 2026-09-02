"""
33维审计 — 分组子模块

6个审计组:
  A: 角色一致性 (group_a_character.Auditor33GroupA)
  B: 物资连续性 (group_b_plot.Auditor33GroupB)
  C: 伏笔管理   (group_c_structure.Auditor33GroupC)
  D: 叙事质量   (group_d_style.Auditor33GroupD)
  E: 情感弧线   (group_e_reader.Auditor33GroupE)
  F: AI痕迹检测 (group_f_ai.Auditor33GroupF)

每个 mixin 类提供对应组的 _check_* 方法,由主类 Auditor33 通过多重继承组合。
"""

from .group_a_character import Auditor33GroupA
from .group_b_plot import Auditor33GroupB
from .group_c_structure import Auditor33GroupC
from .group_d_style import Auditor33GroupD
from .group_e_reader import Auditor33GroupE
from .group_f_ai import Auditor33GroupF

__all__ = [
    "Auditor33GroupA",
    "Auditor33GroupB",
    "Auditor33GroupC",
    "Auditor33GroupD",
    "Auditor33GroupE",
    "Auditor33GroupF",
]
