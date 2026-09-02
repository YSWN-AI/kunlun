"""
昆仑创作引擎 — KG 领域知识种子数据

职责: 填充 Neo4j 领域知识图谱，构建网文题材-套路-人设-平台规则实体关系。
预设"都市修仙""赘婿""打脸"等热门题材的节点和边。

使用方式:
    from kunlun.kg.seed_data import seed_knowledge_graph
    result = seed_knowledge_graph()
"""

from __future__ import annotations

from loguru import logger

from kunlun.kg.client import kg_client

# ─── 题材实体 ────────────────────────────────────────

GENRES = [
    {
        "uid": "genre_urban_cultivation",
        "name": "都市修仙",
        "description": "现代都市背景下的修仙体系，主角在都市中修炼升级，融合现代科技与修真体系",
        "heat": 9.5,
        "market_size": "S级",
        "target_readers": "男频-都市玄幻爱好者",
        "platform_fit": {"起点": 0.95, "番茄": 0.92, "七猫": 0.88},
        "typical_elements": ["扮猪吃虎", "低调修仙", "打脸", "身份反转", "宗门秘辛"],
    },
    {
        "uid": "genre_zhui_xu",
        "name": "赘婿",
        "description": "主角入赘豪门，隐忍受辱，逐步展露真正实力完成逆袭",
        "heat": 8.8,
        "market_size": "A+级",
        "target_readers": "男频-逆袭爽文爱好者",
        "platform_fit": {"起点": 0.88, "番茄": 0.93, "七猫": 0.90},
        "typical_elements": ["隐忍", "打脸", "家族斗争", "身份暴露", "商业争霸"],
    },
    {
        "uid": "genre_slap_face",
        "name": "打脸流",
        "description": "以反复打脸为核心爽点，主角从被看不起到让所有人震惊的经典模式",
        "heat": 9.0,
        "market_size": "S级",
        "target_readers": "全频道爽文读者",
        "platform_fit": {"起点": 0.85, "番茄": 0.96, "七猫": 0.94},
        "typical_elements": ["打脸", "越级挑战", "身份反转", "装逼", "碾压"],
    },
    {
        "uid": "genre_rebirth_era",
        "name": "年代重生",
        "description": "重生回上世纪80-90年代，利用先知优势在改革开放浪潮中崛起",
        "heat": 8.5,
        "market_size": "A级",
        "target_readers": "30+怀旧读者、年代剧爱好者",
        "platform_fit": {"起点": 0.82, "番茄": 0.90, "七猫": 0.85},
        "typical_elements": ["重生", "先知", "经商", "基建", "年代感"],
    },
    {
        "uid": "genre_zongman_infinite",
        "name": "综漫无限流",
        "description": "主角穿越多个动漫/影视世界，完成任务获得能力，在各副本间穿梭",
        "heat": 8.0,
        "market_size": "B+级",
        "target_readers": "二次元爱好者、系统文读者",
        "platform_fit": {"起点": 0.78, "番茄": 0.85, "七猫": 0.80},
        "typical_elements": ["穿越", "副本", "任务系统", "能力获取", "世界观融合"],
    },
]


# ─── 套路/桥段实体 ───────────────────────────────────

TROPES = [
    {
        "uid": "trope_dismiss_marriage",
        "name": "退婚流",
        "description": "开局被退婚/被抛弃，主角立下血誓逆袭，后期让退婚方追悔莫及",
        "intensity_level": 8,
        "best_genres": ["genre_urban_cultivation", "genre_slap_face"],
        "reader_retention_boost": 0.15,
        "typical_pacing": "前3章必须完成退婚场景",
    },
    {
        "uid": "trope_sign_in_system",
        "name": "签到流",
        "description": "主角获得每日签到系统，在不同地点签到获得不同奖励，挂机变强",
        "intensity_level": 5,
        "best_genres": ["genre_urban_cultivation"],
        "reader_retention_boost": 0.10,
        "typical_pacing": "每章必须出现签到场景",
    },
    {
        "uid": "trope_identity_exposure",
        "name": "身份反转",
        "description": "隐藏真实身份的主角被小人物挑衅，最终身份暴露让所有人震惊",
        "intensity_level": 9,
        "best_genres": ["genre_urban_cultivation", "genre_zhui_xu", "genre_slap_face"],
        "reader_retention_boost": 0.25,
        "typical_pacing": "每30-50章一次大型身份反转",
    },
    {
        "uid": "trope_auction_showoff",
        "name": "拍卖会炫富",
        "description": "主角在拍卖会上展示惊人财力/实力，碾压嚣张对手",
        "intensity_level": 7,
        "best_genres": ["genre_urban_cultivation", "genre_slap_face"],
        "reader_retention_boost": 0.20,
        "typical_pacing": "每20-30章一次小拍卖，每50-80章一次大拍卖",
    },
    {
        "uid": "trope_pretend_pig_eat_tiger",
        "name": "扮猪吃虎",
        "description": "主角故意隐藏实力，被轻视后突然爆发，以碾压姿态战胜对手",
        "intensity_level": 8,
        "best_genres": ["genre_urban_cultivation", "genre_slap_face", "genre_zhui_xu"],
        "reader_retention_boost": 0.22,
        "typical_pacing": "每5-10章一次",
    },
    {
        "uid": "trope_golden_finger",
        "name": "金手指觉醒",
        "description": "主角获得/觉醒特殊能力（系统/传承/天赋），从此走上开挂之路",
        "intensity_level": 6,
        "best_genres": ["genre_urban_cultivation", "genre_rebirth_era"],
        "reader_retention_boost": 0.12,
        "typical_pacing": "前3章必须完成金手指觉醒",
    },
    {
        "uid": "trope_domineering_ceo",
        "name": "霸总护妻",
        "description": "表面冷漠的霸总暗地里默默保护/帮助主角，制造甜宠反转",
        "intensity_level": 6,
        "best_genres": ["genre_zhui_xu"],
        "reader_retention_boost": 0.18,
        "typical_pacing": "每10-15章出现一次护妻场景",
    },
    {
        "uid": "trope_tournament_arc",
        "name": "大赛/比武",
        "description": "主角参加大比/宗门试炼/全国大赛，一路越级挑战震惊全场",
        "intensity_level": 9,
        "best_genres": ["genre_urban_cultivation", "genre_slap_face"],
        "reader_retention_boost": 0.30,
        "typical_pacing": "每50-100章一次大型比武",
    },
]


# ─── 人设原型实体 ────────────────────────────────────

CHARACTER_ARCHETYPES = [
    {
        "uid": "arch_loner_keep_low",
        "name": "低调散修",
        "description": "实力强大但刻意隐藏的主角型人设，低调做人高调打脸",
        "trait_vector": [0.8, 0.6, 0.9, 0.3, 0.7, 0.2, 0.7, 0.3, 0.1, 0.8, 0.9, 0.2],
        "best_genres": ["genre_urban_cultivation"],
        "reader_appeal": 0.90,
    },
    {
        "uid": "arch_underdog_rise",
        "name": "逆袭废柴",
        "description": "开局被所有人看不起，凭借金手指/毅力一步步逆转命运",
        "trait_vector": [0.6, 0.4, 0.5, 0.8, 0.9, 0.3, 0.2, 0.6, 0.3, 0.5, 0.7, 0.4],
        "best_genres": ["genre_zhui_xu", "genre_slap_face"],
        "reader_appeal": 0.88,
    },
    {
        "uid": "arch_righteous_avenger",
        "name": "复仇者",
        "description": "身负血海深仇，修炼只为复仇，在复仇过程中收获伙伴和成长",
        "trait_vector": [0.9, 0.7, 0.4, 0.6, 0.5, 0.8, 0.3, 0.7, 0.2, 0.6, 0.9, 0.1],
        "best_genres": ["genre_urban_cultivation", "genre_slap_face"],
        "reader_appeal": 0.82,
    },
    {
        "uid": "arch_business_genius",
        "name": "商业天才",
        "description": "利用现代/未来知识在异界/古代/重生后经商崛起",
        "trait_vector": [0.4, 0.8, 0.9, 0.2, 0.6, 0.3, 0.5, 0.8, 0.7, 0.2, 0.8, 0.3],
        "best_genres": ["genre_rebirth_era", "genre_zhui_xu"],
        "reader_appeal": 0.78,
    },
    {
        "uid": "arch_cold_merciless",
        "name": "杀伐果断",
        "description": "不圣母不犹豫，杀伐果断的铁血型主角，斩草必除根",
        "trait_vector": [0.95, 0.3, 0.7, 0.4, 0.3, 0.9, 0.1, 0.4, 0.2, 0.8, 0.9, 0.1],
        "best_genres": ["genre_urban_cultivation", "genre_slap_face"],
        "reader_appeal": 0.85,
    },
]


# ─── 平台规则实体 ────────────────────────────────────

PLATFORM_RULES = [
    {
        "uid": "rule_qidian_golden3",
        "name": "起点黄金三章",
        "description": (
            "起点中文网签约核心标准: 前3章必须有清晰冲突、"
            "金手指展现、世界观建立、章节钩子"
        ),
        "platform": "起点中文网",
        "requirements": [
            "第1章: 出现冲突/危机，主角身份/困境清晰",
            "第2章: 金手指觉醒或首次使用，让读者看到逆袭希望",
            "第3章: 第一次打脸/装逼，章节末尾必须有强烈钩子",
            "每章字数: 2000-3000字",
            "每3章至少一个爽点或悬念",
        ],
        "pass_rate": 0.30,
    },
    {
        "uid": "rule_fanqie_retention",
        "name": "番茄小说留存法则",
        "description": "免费阅读平台核心策略: 强钩子+快节奏+高密度爽点，确保每章读完率",
        "platform": "番茄小说",
        "requirements": [
            "每500字必须有一个小钩子",
            "每章末尾必须有强悬念或爽点",
            "前5章必须有打脸场景",
            "对话占比不低于30%",
            "平均章节长度2000-2500字",
        ],
        "pass_rate": 0.35,
    },
    {
        "uid": "rule_qimao_contract",
        "name": "七猫过签标准",
        "description": "七猫免费小说过签关键指标: 开局冲突+辨识度人设+明确金手指类型",
        "platform": "七猫",
        "requirements": [
            "前3章必须展现核心金手指",
            "主角人设必须有一定辨识度",
            "开篇冲突必须足够吸引人",
            "避免拖沓的环境描写",
            "每章至少1个情绪起伏点",
        ],
        "pass_rate": 0.28,
    },
]


# ─── 关系定义 ────────────────────────────────────────

RELATIONSHIPS = [
    # 题材 → 套路
    ("genre_urban_cultivation", "SUITABLE_TROPE", "trope_dismiss_marriage"),
    ("genre_urban_cultivation", "SUITABLE_TROPE", "trope_sign_in_system"),
    ("genre_urban_cultivation", "SUITABLE_TROPE", "trope_identity_exposure"),
    ("genre_urban_cultivation", "SUITABLE_TROPE", "trope_auction_showoff"),
    ("genre_urban_cultivation", "SUITABLE_TROPE", "trope_pretend_pig_eat_tiger"),
    ("genre_urban_cultivation", "SUITABLE_TROPE", "trope_golden_finger"),
    ("genre_urban_cultivation", "SUITABLE_TROPE", "trope_tournament_arc"),
    ("genre_zhui_xu", "SUITABLE_TROPE", "trope_identity_exposure"),
    ("genre_zhui_xu", "SUITABLE_TROPE", "trope_pretend_pig_eat_tiger"),
    ("genre_zhui_xu", "SUITABLE_TROPE", "trope_domineering_ceo"),
    ("genre_slap_face", "SUITABLE_TROPE", "trope_dismiss_marriage"),
    ("genre_slap_face", "SUITABLE_TROPE", "trope_identity_exposure"),
    ("genre_slap_face", "SUITABLE_TROPE", "trope_auction_showoff"),
    ("genre_slap_face", "SUITABLE_TROPE", "trope_pretend_pig_eat_tiger"),
    ("genre_slap_face", "SUITABLE_TROPE", "trope_tournament_arc"),
    ("genre_rebirth_era", "SUITABLE_TROPE", "trope_golden_finger"),
    # 题材 → 人设
    ("genre_urban_cultivation", "RECOMMENDED_ARCHETYPE", "arch_loner_keep_low"),
    ("genre_urban_cultivation", "RECOMMENDED_ARCHETYPE", "arch_righteous_avenger"),
    ("genre_urban_cultivation", "RECOMMENDED_ARCHETYPE", "arch_cold_merciless"),
    ("genre_zhui_xu", "RECOMMENDED_ARCHETYPE", "arch_underdog_rise"),
    ("genre_zhui_xu", "RECOMMENDED_ARCHETYPE", "arch_business_genius"),
    ("genre_slap_face", "RECOMMENDED_ARCHETYPE", "arch_underdog_rise"),
    ("genre_slap_face", "RECOMMENDED_ARCHETYPE", "arch_righteous_avenger"),
    ("genre_slap_face", "RECOMMENDED_ARCHETYPE", "arch_cold_merciless"),
    ("genre_rebirth_era", "RECOMMENDED_ARCHETYPE", "arch_business_genius"),
    # 题材 → 平台规则
    ("genre_urban_cultivation", "COMPATIBLE_PLATFORM", "rule_qidian_golden3"),
    ("genre_urban_cultivation", "COMPATIBLE_PLATFORM", "rule_fanqie_retention"),
    ("genre_urban_cultivation", "COMPATIBLE_PLATFORM", "rule_qimao_contract"),
    ("genre_zhui_xu", "COMPATIBLE_PLATFORM", "rule_qidian_golden3"),
    ("genre_zhui_xu", "COMPATIBLE_PLATFORM", "rule_fanqie_retention"),
    ("genre_zhui_xu", "COMPATIBLE_PLATFORM", "rule_qimao_contract"),
    ("genre_slap_face", "COMPATIBLE_PLATFORM", "rule_qidian_golden3"),
    ("genre_slap_face", "COMPATIBLE_PLATFORM", "rule_fanqie_retention"),
    ("genre_slap_face", "COMPATIBLE_PLATFORM", "rule_qimao_contract"),
    ("genre_rebirth_era", "COMPATIBLE_PLATFORM", "rule_qidian_golden3"),
    ("genre_rebirth_era", "COMPATIBLE_PLATFORM", "rule_fanqie_retention"),
]


# ─── 种子函数 ────────────────────────────────────────


def seed_knowledge_graph() -> dict:
    """
    填充 Neo4j 领域知识图谱种子数据。

    如果 Neo4j 不可用，降级为 SQLite 模式写入。
    返回: {created: {genres, tropes, archetypes, rules, relationships}, errors: []}
    """
    result = {
        "created": {"genres": 0, "tropes": 0, "archetypes": 0, "rules": 0, "relationships": 0},
        "errors": [],
    }

    try:
        # ── 1. 题材节点 ──
        for g in GENRES:
            try:
                kg_client.query_cypher(
                    """
                    MERGE (g:Genre {uid: $uid})
                    SET g.name = $name,
                        g.description = $description,
                        g.heat = $heat,
                        g.market_size = $market_size,
                        g.target_readers = $target_readers,
                        g.platform_fit = $platform_fit,
                        g.typical_elements = $typical_elements,
                        g.created_at = datetime()
                    """,
                    {
                        "uid": g["uid"],
                        "name": g["name"],
                        "description": g["description"],
                        "heat": g["heat"],
                        "market_size": g["market_size"],
                        "target_readers": g["target_readers"],
                        "platform_fit": g["platform_fit"],
                        "typical_elements": g["typical_elements"],
                    },
                )
                result["created"]["genres"] += 1
            except Exception as e:
                result["errors"].append(f"题材 {g['name']}: {e}")

        # ── 2. 套路节点 ──
        for t in TROPES:
            try:
                kg_client.query_cypher(
                    """
                    MERGE (t:Trope {uid: $uid})
                    SET t.name = $name,
                        t.description = $description,
                        t.intensity_level = $intensity_level,
                        t.best_genres = $best_genres,
                        t.reader_retention_boost = $reader_retention_boost,
                        t.typical_pacing = $typical_pacing,
                        t.created_at = datetime()
                    """,
                    {
                        "uid": t["uid"],
                        "name": t["name"],
                        "description": t["description"],
                        "intensity_level": t["intensity_level"],
                        "best_genres": t["best_genres"],
                        "reader_retention_boost": t["reader_retention_boost"],
                        "typical_pacing": t["typical_pacing"],
                    },
                )
                result["created"]["tropes"] += 1
            except Exception as e:
                result["errors"].append(f"套路 {t['name']}: {e}")

        # ── 3. 人设原型节点 ──
        for a in CHARACTER_ARCHETYPES:
            try:
                kg_client.query_cypher(
                    """
                    MERGE (a:CharacterArchetype {uid: $uid})
                    SET a.name = $name,
                        a.description = $description,
                        a.trait_vector = $trait_vector,
                        a.best_genres = $best_genres,
                        a.reader_appeal = $reader_appeal,
                        a.created_at = datetime()
                    """,
                    {
                        "uid": a["uid"],
                        "name": a["name"],
                        "description": a["description"],
                        "trait_vector": a["trait_vector"],
                        "best_genres": a["best_genres"],
                        "reader_appeal": a["reader_appeal"],
                    },
                )
                result["created"]["archetypes"] += 1
            except Exception as e:
                result["errors"].append(f"人设 {a['name']}: {e}")

        # ── 4. 平台规则节点 ──
        for r in PLATFORM_RULES:
            try:
                kg_client.query_cypher(
                    """
                    MERGE (r:PlatformRule {uid: $uid})
                    SET r.name = $name,
                        r.description = $description,
                        r.platform = $platform,
                        r.requirements = $requirements,
                        r.pass_rate = $pass_rate,
                        r.created_at = datetime()
                    """,
                    {
                        "uid": r["uid"],
                        "name": r["name"],
                        "description": r["description"],
                        "platform": r["platform"],
                        "requirements": r["requirements"],
                        "pass_rate": r["pass_rate"],
                    },
                )
                result["created"]["rules"] += 1
            except Exception as e:
                result["errors"].append(f"规则 {r['name']}: {e}")

        # ── 5. 关系 ──
        for from_uid, rel_type, to_uid in RELATIONSHIPS:
            try:
                kg_client.query_cypher(
                    f"""
                    MATCH (a {{uid: $from_uid}})
                    MATCH (b {{uid: $to_uid}})
                    MERGE (a)-[:{rel_type}]->(b)
                    """,
                    {"from_uid": from_uid, "to_uid": to_uid},
                )
                result["created"]["relationships"] += 1
            except Exception as e:
                result["errors"].append(f"关系 {from_uid}-[{rel_type}]->{to_uid}: {e}")

        logger.info(
            f"KG 种子数据写入完成: "
            f"{result['created']['genres']} 题材, "
            f"{result['created']['tropes']} 套路, "
            f"{result['created']['archetypes']} 人设, "
            f"{result['created']['rules']} 平台规则, "
            f"{result['created']['relationships']} 关系, "
            f"{len(result['errors'])} 错误"
        )

    except Exception as e:
        result["errors"].append(f"全局异常: {e}")
        logger.error(f"KG 种子数据填充失败: {e}")

    return result


def query_genre_recommendations(genre_uid: str) -> dict:
    """查询指定题材的推荐套路和人设"""
    try:
        tropes = kg_client.query_cypher(
            """
            MATCH (g:Genre {uid: $genre_uid})-[:SUITABLE_TROPE]->(t:Trope)
            RETURN t.name AS name, t.description AS description,
                   t.intensity_level AS intensity, t.reader_retention_boost AS retention_boost
            ORDER BY t.intensity_level DESC
            """,
            {"genre_uid": genre_uid},
        )

        archetypes = kg_client.query_cypher(
            """
            MATCH (g:Genre {uid: $genre_uid})-[:RECOMMENDED_ARCHETYPE]->(a:CharacterArchetype)
            RETURN a.name AS name, a.description AS description,
                   a.reader_appeal AS appeal
            ORDER BY a.reader_appeal DESC
            """,
            {"genre_uid": genre_uid},
        )

        rules = kg_client.query_cypher(
            """
            MATCH (g:Genre {uid: $genre_uid})-[:COMPATIBLE_PLATFORM]->(r:PlatformRule)
            RETURN r.name AS name, r.platform AS platform,
                   r.pass_rate AS pass_rate, r.requirements AS requirements
            ORDER BY r.pass_rate DESC
            """,
            {"genre_uid": genre_uid},
        )

        return {
            "success": True,
            "genre": genre_uid,
            "recommended_tropes": tropes,
            "recommended_archetypes": archetypes,
            "platform_rules": rules,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# ─── 初始化钩子 ──────────────────────────────────────


def init_seed_data_if_empty() -> dict:
    """
    启动时检查 KG 是否已有种子数据，如无则自动填充。
    可在 main.py 的 lifespan 中调用。
    """
    try:
        existing = kg_client.query_cypher("MATCH (g:Genre) RETURN count(g) AS genre_count")
        # 使用明确的别名确保Neo4j/SQLite两种模式键名一致
        if existing and existing[0].get("genre_count", 0) > 0:
            logger.info(f"KG 已有 {existing[0]['genre_count']} 个题材节点，跳过种子数据填充")
            return {"seeded": False, "reason": "已有数据"}

        logger.info("KG 无种子数据，开始填充...")
        return {"seeded": True, **seed_knowledge_graph()}
    except Exception as e:
        logger.warning(f"检查/填充种子数据失败: {e}")
        return {"seeded": False, "error": str(e)}
