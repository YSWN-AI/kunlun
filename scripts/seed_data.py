"""
种子数据脚本 — 填充 Qdrant 向量库和 SQLite FTS5 全文索引

生成 10 个测试实体（角色5个/物品3个/地点2个），每个带 name/type/description。
调用 Embedder 嵌入并写入 Qdrant，同时写入 SQLite FTS5 全文索引。

用法: python scripts/seed_data.py
"""

import sys
from pathlib import Path

# 将项目根目录加入 sys.path，支持独立运行
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from kunlun.config import settings
from kunlun.kg.client import kg_client
from kunlun.kg.embedder import embedder
from qdrant_client.models import PointStruct
from loguru import logger

# ─── 种子实体定义 ───────────────────────────────────

SEED_ENTITIES: list[dict[str, str]] = [
    # 角色 (5个)
    {
        "uid": "seed_char_001",
        "name": "林玄",
        "entity_type": "Character",
        "description": "主角，23岁，青云宗外门弟子，天生废灵根却意外获得上古传承。性格坚毅内敛，不善言辞但对朋友极度忠诚。擅长剑法和阵法推演，拥有越级战斗的能力。",
    },
    {
        "uid": "seed_char_002",
        "name": "苏晴雪",
        "entity_type": "Character",
        "description": "女主角，天灵根天才修士，云岚宗圣女。外表冷若冰霜实则内心温柔，因宗门任务与林玄相识。精通冰系法术和炼丹术，是年轻一代中的佼佼者。",
    },
    {
        "uid": "seed_char_003",
        "name": "楚狂生",
        "entity_type": "Character",
        "description": "林玄挚友，散修出身，性格豪放不羁。修炼霸体诀，肉身强悍可硬撼法宝。爱喝酒爱打架，是团队中的肉盾和气氛担当。",
    },
    {
        "uid": "seed_char_004",
        "name": "墨渊",
        "entity_type": "Character",
        "description": "反派，魔道第一天才，修炼万魔噬心诀。表面温文尔雅实则心狠手辣，为达目的不择手段。与林玄有宿命对决的命运线。",
    },
    {
        "uid": "seed_char_005",
        "name": "白鹤真人",
        "entity_type": "Character",
        "description": "青云宗太上长老，活了三千年的老怪物。修为深不可测，行事不拘一格。暗中关注林玄的成长，偶尔指点一二。",
    },
    # 物品 (3个)
    {
        "uid": "seed_item_001",
        "name": "混沌珠",
        "entity_type": "Item",
        "description": "上古至宝，内含一方小世界，可加速修炼和种植灵药。林玄在秘境中偶然获得，是他最大的机缘之一。",
    },
    {
        "uid": "seed_item_002",
        "name": "斩天剑",
        "entity_type": "Item",
        "description": "上古神兵，可斩断法则之力。原为天剑宗镇宗之宝，因缘际会落入林玄之手。剑灵沉睡中，需要特定条件才能唤醒。",
    },
    {
        "uid": "seed_item_003",
        "name": "九转还魂丹",
        "entity_type": "Item",
        "description": "极品丹药，只要还有一口气就能救活，且恢复全部伤势。苏晴雪耗费三年时间炼制，只有三颗。",
    },
    # 地点 (2个)
    {
        "uid": "seed_loc_001",
        "name": "青云宗",
        "entity_type": "Location",
        "description": "东域七大宗门之一，位于青云山脉主峰。以剑修闻名，宗门内有九层试剑塔和藏经阁。弟子数万，分为外门、内门、核心三层。",
    },
    {
        "uid": "seed_loc_002",
        "name": "万魔深渊",
        "entity_type": "Location",
        "description": "魔道圣地，位于极北之地。终年被魔气笼罩，普通修士靠近会被腐蚀心智。深渊底部据说封印着上古魔神，是墨渊的修炼之地。",
    },
]


def main():
    logger.info("=" * 60)
    logger.info("种子数据脚本 — 开始填充 Qdrant + FTS5")
    logger.info("=" * 60)

    # ─── 步骤 1: 确保数据目录就绪 ────────────────
    data_dir = settings.DATA_DIR
    data_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"数据目录: {data_dir}")

    # ─── 步骤 2: 确保 Embedder 就绪 ─────────────
    logger.info(f"Embedder 状态: {embedder.stats}")

    # ─── 步骤 3: 写入 Qdrant 向量库 ─────────────
    logger.info("\n[Qdrant] 开始嵌入并索引...")
    qdrant_ok = 0
    qdrant_fail = 0

    for entity in SEED_ENTITIES:
        try:
            # 拼接用于嵌入的文本
            embed_text = f"{entity['name']} ({entity['entity_type']}): {entity['description']}"
            vector = embedder.encode(embed_text)

            # 生成安全的 point_id (使用 uid 哈希)
            point_id = hash(entity["uid"]) % (2**63 - 1)

            point = PointStruct(
                id=point_id,
                vector=vector.tolist(),
                payload={
                    "uid": entity["uid"],
                    "name": entity["name"],
                    "entity_type": entity["entity_type"],
                    "description": entity["description"],
                    "text": embed_text,
                },
            )
            kg_client.qdrant.upsert(
                collection_name=settings.qdrant_collection,
                points=[point],
            )
            qdrant_ok += 1
            logger.info(
                f"  [Qdrant] ✅ {entity['entity_type']}/{entity['name']} → point_id={point_id}"
            )
        except Exception as e:
            qdrant_fail += 1
            logger.error(f"  [Qdrant] ❌ {entity['name']}: {e}")

    # ─── 步骤 4: 写入 SQLite FTS5 ───────────────
    logger.info("\n[FTS5] 开始索引...")
    fts5_ok = 0
    fts5_fail = 0

    for entity in SEED_ENTITIES:
        try:
            kg_client.index_entity(
                uid=entity["uid"],
                name=entity["name"],
                entity_type=entity["entity_type"],
                description=entity["description"],
            )
            fts5_ok += 1
            logger.info(f"  [FTS5] ✅ {entity['entity_type']}/{entity['name']}")
        except Exception as e:
            fts5_fail += 1
            logger.error(f"  [FTS5] ❌ {entity['name']}: {e}")

    # ─── 步骤 5: 验证 ──────────────────────────
    logger.info("\n[验证] 运行查询验证...")

    # Qdrant 验证
    try:
        qdrant_count = kg_client.qdrant.count(
            collection_name=settings.qdrant_collection,
            exact=True,
        ).count
        logger.info(f"  [Qdrant] 集合内总点数: {qdrant_count}")
    except Exception as e:
        logger.warning(f"  [Qdrant] count 查询失败: {e}")
        qdrant_count = "未知"

    # FTS5 验证
    try:
        cursor = kg_client.sqlite.execute("SELECT COUNT(*) as cnt FROM entity_fts")
        fts5_count = cursor.fetchone()["cnt"]
        logger.info(f"  [FTS5] 索引内总记录数: {fts5_count}")
    except Exception as e:
        logger.warning(f"  [FTS5] count 查询失败: {e}")
        fts5_count = "未知"

    # 全文搜索验证
    try:
        results = kg_client.search_entities("林玄", limit=3)
        logger.info(f"  [FTS5] 搜索 '林玄' 返回 {len(results)} 条结果")
        for r in results:
            logger.info(
                f"    → {r.get('name', '?')} ({r.get('entity_type', '?')}): rank={r.get('rank', '?')}"
            )
    except Exception as e:
        logger.warning(f"  [FTS5] 搜索验证失败: {e}")

    # ─── 摘要 ──────────────────────────────────
    logger.info("\n" + "=" * 60)
    logger.info("种子数据填充完成!")
    logger.info(f"  Qdrant: 成功 {qdrant_ok} / 失败 {qdrant_fail} | 集合总数 {qdrant_count}")
    logger.info(f"  FTS5:   成功 {fts5_ok} / 失败 {fts5_fail} | 索引总数 {fts5_count}")
    logger.info(f"  数据目录: {data_dir}")
    logger.info(f"  Qdrant 路径: {settings.qdrant_path}")
    logger.info(f"  FTS5 路径:  {settings.sqlite_path}")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
