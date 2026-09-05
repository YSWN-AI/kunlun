"""
昆仑创作引擎 — 题材模板库核心引擎 (Genre Template Library)

灵感来源: webnovel-writer 37题材模板 + InkOS 题材规则库
对标: 网文平台 37 种主流题材分类体系
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from loguru import logger


class GenreCategory(Enum):
    """题材大类"""

    XUANHUAN = "xuanhuan"
    XIANXIA = "xianxia"
    DUSHI = "dushi"
    LISHI = "lishi"
    WUXIA = "wuxia"
    KEHUAN = "kehuan"
    XUANYI = "xuanyi"
    YOUXI = "youxi"
    QIHUAN = "qihuan"
    JUNSHI = "junshi"
    YANQING = "yanqing"
    TONGZHI = "tongzhi"
    QITA = "qita"


class PaceType(Enum):
    """节奏类型"""

    FAST = "fast"
    MEDIUM = "medium"
    SLOW = "slow"


class AudienceLevel(Enum):
    """读者门槛"""

    MASS = "mass"
    GENERAL = "general"
    ADVANCED = "advanced"


@dataclass
class GenreConfig:
    """单题材完整配置"""

    genre_id: str
    name: str
    category: GenreCategory
    description: str

    suggested_words_per_chapter: tuple[int, int]
    suggested_total_words: tuple[int, int]
    pace: PaceType
    audience: AudienceLevel

    preferred_pleasures: list[str]
    avoid_pleasures: list[str] = field(default_factory=list)
    min_pleasure_per_1k: float = 2.0
    climax_chapter_interval: int = 30

    preferred_hooks: list[str] = field(default_factory=list)
    opening_hook_required: bool = True
    closing_hook_required: bool = True
    golden_three_intensity: float = 0.8

    dialogue_ratio: tuple[float, float] = (0.2, 0.4)
    action_ratio: tuple[float, float] = (0.25, 0.45)

    taboos: list[str] = field(default_factory=list)
    required_elements: list[str] = field(default_factory=list)
    chapter_structure: dict[str, Any] = field(default_factory=dict)

    best_platforms: list[str] = field(default_factory=list)
    avoid_platforms: list[str] = field(default_factory=list)

    style_references: list[str] = field(default_factory=list)
    style_notes: str = ""

    tags: list[str] = field(default_factory=list)
    sub_genres: list[str] = field(default_factory=list)


# ─── 37 题材完整配置 ─────────────────────────────────

GENRE_LIBRARY: dict[str, GenreConfig] = {
    "xuanhuan_dongfang": GenreConfig(
        genre_id="xuanhuan_dongfang",
        name="东方玄幻",
        category=GenreCategory.XUANHUAN,
        description="以东方文化为背景的幻想世界，修炼体系、宗门争斗、天材地宝",
        suggested_words_per_chapter=(2000, 4000),
        suggested_total_words=(2000000, 5000000),
        pace=PaceType.MEDIUM,
        audience=AudienceLevel.GENERAL,
        preferred_pleasures=["power_up", "face_slap", "treasure", "prestige", "counterattack"],
        min_pleasure_per_1k=2.5,
        climax_chapter_interval=25,
        preferred_hooks=["cliffhanger", "power_up", "confrontation"],
        dialogue_ratio=(0.2, 0.35),
        action_ratio=(0.3, 0.5),
        taboos=["现代元素过多", "感情线喧宾夺主", "修炼体系混乱"],
        required_elements=["修炼体系", "等级划分", "势力格局", "天材地宝"],
        chapter_structure={
            "normal": {"scenes": "2-4", "pleasure_min": 2, "word_range": (2000, 3000)},
            "climax": {"scenes": "1-2", "pleasure_min": 3, "word_range": (2500, 4000)},
            "transition": {"scenes": "2-3", "pleasure_min": 1, "word_range": (1500, 2500)},
        },
        best_platforms=["qidian", "fanqie", "qimao"],
        style_references=["斗破苍穹", "完美世界", "遮天"],
        style_notes="节奏紧凑，爽点密集，升级感强",
        tags=["玄幻", "修炼", "升级流", "热血"],
        sub_genres=["xitong", "chongsheng", "feisheng"],
    ),
    "xuanhuan_xifang": GenreConfig(
        genre_id="xuanhuan_xifang",
        name="西方玄幻",
        category=GenreCategory.XUANHUAN,
        description="西方中世纪/魔法世界背景，骑士、魔法、龙、精灵等元素",
        suggested_words_per_chapter=(2500, 4000),
        suggested_total_words=(1500000, 4000000),
        pace=PaceType.MEDIUM,
        audience=AudienceLevel.ADVANCED,
        preferred_pleasures=["power_up", "treasure", "prestige", "alliance", "counterattack"],
        min_pleasure_per_1k=2.0,
        climax_chapter_interval=35,
        preferred_hooks=["cliffhanger", "mystery", "confrontation"],
        dialogue_ratio=(0.25, 0.4),
        action_ratio=(0.2, 0.4),
        taboos=["东方元素混入", "世界观不一致"],
        required_elements=["魔法体系", "种族设定", "王国势力", "史诗感"],
        best_platforms=["qidian"],
        style_references=["盘龙", "诡秘之主", "放开那个女巫"],
        tags=["西幻", "魔法", "史诗", "领主"],
        sub_genres=["lingzhu", "mofa", "qihuan"],
    ),
    "xuanhuan_xiuzhen": GenreConfig(
        genre_id="xuanhuan_xiuzhen",
        name="修真/修仙",
        category=GenreCategory.XIANXIA,
        description="修仙体系，筑基→金丹→元婴→化神，飞升仙界",
        suggested_words_per_chapter=(2000, 3500),
        suggested_total_words=(2000000, 6000000),
        pace=PaceType.SLOW,
        audience=AudienceLevel.GENERAL,
        preferred_pleasures=["power_up", "treasure", "prestige", "mystery_solve"],
        min_pleasure_per_1k=2.0,
        climax_chapter_interval=30,
        preferred_hooks=["power_up", "mystery", "promise"],
        dialogue_ratio=(0.2, 0.35),
        action_ratio=(0.2, 0.4),
        taboos=["等级混乱", "战力崩坏", "修炼无瓶颈"],
        required_elements=["修仙等级体系", "丹药法宝", "宗门势力", "渡劫飞升"],
        best_platforms=["qidian", "fanqie"],
        style_references=["凡人修仙传", "仙逆", "一念永恒"],
        tags=["修仙", "凡人流", "长生", "法宝"],
        sub_genres=["chongsheng", "xitong", "fanrenliu"],
    ),
    "dushi_zhuangbi": GenreConfig(
        genre_id="dushi_zhuangbi",
        name="都市装逼打脸",
        category=GenreCategory.DUSHI,
        description="现代都市背景下，主角扮猪吃虎、装逼打脸的爽文",
        suggested_words_per_chapter=(2000, 3000),
        suggested_total_words=(1500000, 4000000),
        pace=PaceType.FAST,
        audience=AudienceLevel.MASS,
        preferred_pleasures=["face_slap", "prestige", "revenge", "counterattack"],
        avoid_pleasures=["sacrifice", "betrayal"],
        min_pleasure_per_1k=3.0,
        climax_chapter_interval=20,
        preferred_hooks=["cliffhanger", "confrontation", "reversal"],
        opening_hook_required=True,
        closing_hook_required=True,
        golden_three_intensity=0.9,
        dialogue_ratio=(0.25, 0.45),
        action_ratio=(0.2, 0.35),
        taboos=["主角太弱", "爽点间隔过长", "憋屈超过3章"],
        required_elements=["装逼场景", "打脸反转", "身份反差"],
        best_platforms=["fanqie", "qimao", "feilu"],
        avoid_platforms=["jjwxc"],
        style_references=["校花的贴身高手", "最强弃少", "超级兵王"],
        style_notes="节奏极快，每章至少一个打脸点，爽点密集",
        tags=["都市", "装逼", "打脸", "兵王", "神医"],
        sub_genres=["bingwang", "shenyi", "zongcai"],
    ),
    "dushi_shenghuo": GenreConfig(
        genre_id="dushi_shenghuo",
        name="都市生活流",
        category=GenreCategory.DUSHI,
        description="都市日常生活、职场、创业、恋爱",
        suggested_words_per_chapter=(2000, 3500),
        suggested_total_words=(1000000, 3000000),
        pace=PaceType.MEDIUM,
        audience=AudienceLevel.GENERAL,
        preferred_pleasures=["romance", "prestige", "comedy", "alliance"],
        min_pleasure_per_1k=1.5,
        climax_chapter_interval=40,
        preferred_hooks=["emotional", "promise", "revelation"],
        dialogue_ratio=(0.3, 0.5),
        action_ratio=(0.1, 0.25),
        taboos=["过度夸张", "脱离现实", "人设崩塌"],
        required_elements=["都市生活细节", "人物关系", "职场/创业线"],
        best_platforms=["qidian", "fanqie"],
        style_references=["大江大河", "都挺好", "欢乐颂"],
        tags=["都市", "生活", "职场", "现实"],
        sub_genres=["chuangye", "zongcai", "tiyu"],
    ),
    "dushi_lingyi": GenreConfig(
        genre_id="dushi_lingyi",
        name="都市灵异",
        category=GenreCategory.DUSHI,
        description="都市背景下的灵异、恐怖、悬疑故事",
        suggested_words_per_chapter=(2000, 3000),
        suggested_total_words=(800000, 2000000),
        pace=PaceType.MEDIUM,
        audience=AudienceLevel.GENERAL,
        preferred_pleasures=["mystery_solve", "counterattack", "power_up"],
        min_pleasure_per_1k=1.5,
        climax_chapter_interval=25,
        preferred_hooks=["mystery", "cliffhanger", "emotional"],
        dialogue_ratio=(0.2, 0.35),
        action_ratio=(0.2, 0.4),
        taboos=["恐怖元素过于血腥", "逻辑漏洞"],
        required_elements=["灵异体系", "恐怖氛围", "推理元素"],
        best_platforms=["qidian", "fanqie"],
        style_references=["我有一座恐怖屋", "深夜书屋", "民调局异闻录"],
        tags=["灵异", "恐怖", "悬疑", "都市"],
        sub_genres=["kongbu", "xuanyi", "tansuo"],
    ),
    "yanqing_guzhuang": GenreConfig(
        genre_id="yanqing_guzhuang",
        name="古装言情",
        category=GenreCategory.YANQING,
        description="古代背景下以爱情为主线的故事",
        suggested_words_per_chapter=(2500, 4000),
        suggested_total_words=(800000, 2500000),
        pace=PaceType.MEDIUM,
        audience=AudienceLevel.GENERAL,
        preferred_pleasures=["romance", "sacrifice", "reversal", "prestige"],
        avoid_pleasures=["face_slap"],
        min_pleasure_per_1k=1.5,
        climax_chapter_interval=35,
        preferred_hooks=["emotional", "revelation", "cliffhanger"],
        dialogue_ratio=(0.3, 0.5),
        action_ratio=(0.1, 0.25),
        taboos=["感情线过于突兀", "人设前后矛盾"],
        required_elements=["感情线主线", "古代礼仪", "家族背景"],
        best_platforms=["jjwxc", "qidian"],
        avoid_platforms=["feilu"],
        style_references=["知否知否", "步步惊心", "琅琊榜"],
        style_notes="细腻文笔，感情线层层递进，重视氛围营造",
        tags=["言情", "古装", "宫斗", "宅斗"],
        sub_genres=["gongdou", "zhaidou", "chongsheng"],
    ),
    "yanqing_xiandai": GenreConfig(
        genre_id="yanqing_xiandai",
        name="现代言情",
        category=GenreCategory.YANQING,
        description="现代都市背景下的爱情故事",
        suggested_words_per_chapter=(2500, 4000),
        suggested_total_words=(600000, 2000000),
        pace=PaceType.MEDIUM,
        audience=AudienceLevel.GENERAL,
        preferred_pleasures=["romance", "comedy", "emotional", "reversal"],
        min_pleasure_per_1k=1.5,
        climax_chapter_interval=30,
        preferred_hooks=["emotional", "revelation", "promise"],
        dialogue_ratio=(0.35, 0.55),
        action_ratio=(0.05, 0.2),
        taboos=["感情线过于狗血", "人物扁平化"],
        required_elements=["现代感情线", "职场/校园背景", "人物成长弧"],
        best_platforms=["jjwxc", "fanqie"],
        style_references=["何以笙箫默", "微微一笑很倾城", "你是我的荣耀"],
        tags=["言情", "现代", "甜宠", "职场"],
        sub_genres=["tianchong", "zongcai", "xiaoyuan"],
    ),
    "kehuan_yinghe": GenreConfig(
        genre_id="kehuan_yinghe",
        name="硬核科幻",
        category=GenreCategory.KEHUAN,
        description="基于科学理论的科幻故事，强调科学逻辑和未来推演",
        suggested_words_per_chapter=(2500, 4500),
        suggested_total_words=(1000000, 3000000),
        pace=PaceType.SLOW,
        audience=AudienceLevel.ADVANCED,
        preferred_pleasures=["mystery_solve", "revelation", "counterattack"],
        min_pleasure_per_1k=1.0,
        climax_chapter_interval=40,
        preferred_hooks=["mystery", "revelation", "cliffhanger"],
        dialogue_ratio=(0.2, 0.35),
        action_ratio=(0.15, 0.35),
        taboos=["科学逻辑漏洞", "设定不自洽"],
        required_elements=["科学理论基础", "未来世界观", "技术推演"],
        best_platforms=["qidian"],
        style_references=["三体", "流浪地球", "银河帝国"],
        style_notes="重视科学逻辑，世界观严谨，深度思考",
        tags=["科幻", "硬核", "未来", "宇宙"],
        sub_genres=["xingji", "moshi", "renengzhineng"],
    ),
    "kehuan_moshi": GenreConfig(
        genre_id="kehuan_moshi",
        name="末世科幻",
        category=GenreCategory.KEHUAN,
        description="末日/废土/丧尸背景下的生存与重建",
        suggested_words_per_chapter=(2000, 3500),
        suggested_total_words=(1000000, 3000000),
        pace=PaceType.FAST,
        audience=AudienceLevel.GENERAL,
        preferred_pleasures=["power_up", "counterattack", "alliance", "treasure"],
        min_pleasure_per_1k=2.5,
        climax_chapter_interval=20,
        preferred_hooks=["cliffhanger", "confrontation", "power_up"],
        dialogue_ratio=(0.15, 0.3),
        action_ratio=(0.3, 0.55),
        taboos=["末世设定矛盾", "资源逻辑漏洞"],
        required_elements=["末世世界观", "生存体系", "势力格局"],
        best_platforms=["qidian", "fanqie", "qimao"],
        style_references=["全球进化", "末世之黑暗召唤师", "废土"],
        tags=["末世", "丧尸", "生存", "进化"],
        sub_genres=["sangshi", "feitulu", "jineng"],
    ),
    "youxi_wangyou": GenreConfig(
        genre_id="youxi_wangyou",
        name="网游竞技",
        category=GenreCategory.YOUXI,
        description="虚拟网游/电竞竞技类故事",
        suggested_words_per_chapter=(2000, 3000),
        suggested_total_words=(1500000, 4000000),
        pace=PaceType.FAST,
        audience=AudienceLevel.MASS,
        preferred_pleasures=["power_up", "face_slap", "prestige", "treasure"],
        min_pleasure_per_1k=2.5,
        climax_chapter_interval=20,
        preferred_hooks=["cliffhanger", "power_up", "confrontation"],
        dialogue_ratio=(0.2, 0.35),
        action_ratio=(0.3, 0.5),
        taboos=["游戏设定不专业", "数据混乱"],
        required_elements=["游戏系统", "职业体系", "装备系统", "竞技元素"],
        best_platforms=["qidian", "fanqie"],
        style_references=["全职高手", "网游之近战法师", "惊悚乐园"],
        tags=["网游", "电竞", "竞技", "虚拟现实"],
        sub_genres=["dianjing", "xuniyoux", "quanxi"],
    ),
    "xuanyi_zhentan": GenreConfig(
        genre_id="xuanyi_zhentan",
        name="悬疑侦探",
        category=GenreCategory.XUANYI,
        description="侦探/推理/悬疑故事，强调逻辑推理和谜题设计",
        suggested_words_per_chapter=(2500, 4000),
        suggested_total_words=(600000, 2000000),
        pace=PaceType.MEDIUM,
        audience=AudienceLevel.ADVANCED,
        preferred_pleasures=["mystery_solve", "revelation", "reversal"],
        avoid_pleasures=["face_slap", "power_up"],
        min_pleasure_per_1k=1.0,
        climax_chapter_interval=30,
        preferred_hooks=["mystery", "cliffhanger", "revelation"],
        dialogue_ratio=(0.25, 0.45),
        action_ratio=(0.1, 0.3),
        taboos=["推理逻辑漏洞", "线索过于明显/隐晦"],
        required_elements=["谜题设计", "推理过程", "线索铺排", "反转"],
        best_platforms=["qidian", "fanqie"],
        style_references=["心理罪", "法医秦明", "白夜追凶"],
        style_notes="逻辑严密，线索层层递进，反转合理",
        tags=["悬疑", "推理", "侦探", "犯罪"],
        sub_genres=["tuili", "fanzui", "xinli"],
    ),
    "xuanyi_lingyi": GenreConfig(
        genre_id="xuanyi_lingyi",
        name="灵异悬疑",
        category=GenreCategory.XUANYI,
        description="灵异/恐怖/民俗悬疑故事",
        suggested_words_per_chapter=(2000, 3000),
        suggested_total_words=(800000, 2000000),
        pace=PaceType.FAST,
        audience=AudienceLevel.GENERAL,
        preferred_pleasures=["mystery_solve", "counterattack", "revelation"],
        min_pleasure_per_1k=1.5,
        climax_chapter_interval=20,
        preferred_hooks=["mystery", "cliffhanger", "emotional"],
        dialogue_ratio=(0.2, 0.35),
        action_ratio=(0.15, 0.35),
        taboos=["恐怖尺度过度", "逻辑不自洽"],
        required_elements=["灵异体系", "恐怖氛围", "悬疑推进"],
        best_platforms=["fanqie", "qidian"],
        style_references=["我有一座恐怖屋", "盗墓笔记", "鬼吹灯"],
        tags=["灵异", "恐怖", "民俗", "悬疑"],
        sub_genres=["kongbu", "minsu", "tanxian"],
    ),
    "lishi_jiakong": GenreConfig(
        genre_id="lishi_jiakong",
        name="架空历史",
        category=GenreCategory.LISHI,
        description="架空历史背景下争霸/种田/权谋",
        suggested_words_per_chapter=(2500, 4000),
        suggested_total_words=(1500000, 4000000),
        pace=PaceType.MEDIUM,
        audience=AudienceLevel.GENERAL,
        preferred_pleasures=["prestige", "alliance", "counterattack", "face_slap"],
        min_pleasure_per_1k=2.0,
        climax_chapter_interval=30,
        preferred_hooks=["confrontation", "cliffhanger", "revelation"],
        dialogue_ratio=(0.2, 0.35),
        action_ratio=(0.2, 0.4),
        taboos=["历史常识错误", "科技跳跃"],
        required_elements=["历史背景", "政治格局", "军事/经济体系"],
        best_platforms=["qidian"],
        style_references=["赘婿", "庆余年", "唐砖"],
        tags=["历史", "架空", "争霸", "权谋"],
        sub_genres=["zhengba", "zhongtian", "quanmou"],
    ),
    "xitong_liu": GenreConfig(
        genre_id="xitong_liu",
        name="系统流",
        category=GenreCategory.QITA,
        description="主角携带系统/面板/金手指的爽文模式（可叠加任意主类型）",
        suggested_words_per_chapter=(2000, 3000),
        suggested_total_words=(1500000, 5000000),
        pace=PaceType.FAST,
        audience=AudienceLevel.MASS,
        preferred_pleasures=["power_up", "face_slap", "treasure", "prestige"],
        min_pleasure_per_1k=3.0,
        climax_chapter_interval=15,
        preferred_hooks=["power_up", "cliffhanger", "promise"],
        dialogue_ratio=(0.2, 0.35),
        action_ratio=(0.25, 0.45),
        taboos=["系统功能混乱", "奖励不合理"],
        required_elements=["系统面板", "任务机制", "奖励体系"],
        best_platforms=["fanqie", "qimao", "feilu"],
        style_references=["超级神基因", "最强升级系统", "万界淘宝商"],
        tags=["系统流", "金手指", "面板", "升级"],
        sub_genres=[],
    ),
    "wuxia_chuantong": GenreConfig(
        genre_id="wuxia_chuantong",
        name="传统武侠",
        category=GenreCategory.WUXIA,
        description="中国传统武侠，江湖恩怨，侠义精神",
        suggested_words_per_chapter=(2500, 4000),
        suggested_total_words=(1000000, 3000000),
        pace=PaceType.MEDIUM,
        audience=AudienceLevel.ADVANCED,
        preferred_pleasures=["prestige", "counterattack", "revenge", "sacrifice"],
        min_pleasure_per_1k=1.5,
        climax_chapter_interval=35,
        preferred_hooks=["confrontation", "cliffhanger", "emotional"],
        dialogue_ratio=(0.2, 0.35),
        action_ratio=(0.25, 0.5),
        taboos=["内力体系混乱", "武侠味不足"],
        required_elements=["武功体系", "江湖门派", "侠义精神"],
        best_platforms=["qidian"],
        style_references=["天龙八部", "笑傲江湖", "雪中悍刀行"],
        tags=["武侠", "传统", "江湖", "侠义"],
        sub_genres=["gaowu", "xianxia_wuxia"],
    ),
    "qihuan_jianyuemo": GenreConfig(
        genre_id="qihuan_jianyuemo",
        name="剑与魔法",
        category=GenreCategory.QIHUAN,
        description="日式/西式奇幻，剑与魔法的冒险故事",
        suggested_words_per_chapter=(2500, 4000),
        suggested_total_words=(1000000, 3000000),
        pace=PaceType.MEDIUM,
        audience=AudienceLevel.GENERAL,
        preferred_pleasures=["power_up", "treasure", "alliance", "counterattack"],
        min_pleasure_per_1k=2.0,
        climax_chapter_interval=30,
        preferred_hooks=["cliffhanger", "confrontation", "mystery"],
        dialogue_ratio=(0.2, 0.35),
        action_ratio=(0.25, 0.45),
        taboos=["东西方元素混乱", "魔法体系不自洽"],
        required_elements=["魔法体系", "种族设定", "冒险主线"],
        best_platforms=["qidian", "fanqie"],
        style_references=["Re:从零开始", "无职转生", "哥布林杀手"],
        tags=["奇幻", "异世界", "冒险", "魔法"],
        sub_genres=["yishijie", "maoxian", "zhuansheng"],
    ),
    "dushi_fanju": GenreConfig(
        genre_id="dushi_fanju",
        name="都市反套路",
        category=GenreCategory.DUSHI,
        description="反套路/吐槽流/沙雕风格的都市文",
        suggested_words_per_chapter=(2000, 3000),
        suggested_total_words=(800000, 2000000),
        pace=PaceType.FAST,
        audience=AudienceLevel.MASS,
        preferred_pleasures=["comedy", "face_slap", "reversal"],
        min_pleasure_per_1k=3.0,
        climax_chapter_interval=20,
        preferred_hooks=["reversal", "cliffhanger", "emotional"],
        dialogue_ratio=(0.3, 0.5),
        action_ratio=(0.1, 0.25),
        taboos=["笑点重复", "吐槽过度"],
        required_elements=["反套路情节", "吐槽元素", "轻松氛围"],
        best_platforms=["fanqie", "qimao", "feilu"],
        style_references=["大王饶命", "我真没想重生啊", "亏成首富"],
        tags=["反套路", "吐槽", "搞笑", "沙雕"],
        sub_genres=["tucao", "shadiao", "fantaolu"],
    ),
    "junshi_zhanzheng": GenreConfig(
        genre_id="junshi_zhanzheng",
        name="军事战争",
        category=GenreCategory.JUNSHI,
        description="现代/近代军事战争题材",
        suggested_words_per_chapter=(2500, 4000),
        suggested_total_words=(1000000, 3000000),
        pace=PaceType.MEDIUM,
        audience=AudienceLevel.ADVANCED,
        preferred_pleasures=["counterattack", "prestige", "alliance"],
        min_pleasure_per_1k=1.5,
        climax_chapter_interval=30,
        preferred_hooks=["confrontation", "cliffhanger", "revelation"],
        dialogue_ratio=(0.15, 0.3),
        action_ratio=(0.3, 0.55),
        taboos=["军事常识错误", "政治敏感"],
        required_elements=["军事知识", "战术描写", "装备体系"],
        best_platforms=["qidian"],
        style_references=["佣兵的战争", "最强兵王", "弹痕"],
        tags=["军事", "战争", "特种兵", "佣兵"],
        sub_genres=["tezhongbing", "yongbing", "zhanzheng"],
    ),
    "tongzhi_faner": GenreConfig(
        genre_id="tongzhi_faner",
        name="同人创作",
        category=GenreCategory.TONGZHI,
        description="基于已有IP的二次创作",
        suggested_words_per_chapter=(2000, 3500),
        suggested_total_words=(500000, 2000000),
        pace=PaceType.FAST,
        audience=AudienceLevel.GENERAL,
        preferred_pleasures=["face_slap", "power_up", "prestige"],
        min_pleasure_per_1k=2.5,
        climax_chapter_interval=20,
        preferred_hooks=["cliffhanger", "confrontation", "revelation"],
        dialogue_ratio=(0.2, 0.4),
        action_ratio=(0.2, 0.4),
        taboos=["偏离原作核心设定", "OOC严重"],
        required_elements=["原作核心元素", "同人创新点"],
        best_platforms=["fanqie", "qidian", "feilu"],
        style_references=["视原作而定"],
        tags=["同人", "二次创作", "穿越"],
        sub_genres=["chuanyue_tongren", "chongsheng_tongren"],
    ),
}


# ─── 顶级10题材模板库 ─────────────────────────────────


@dataclass
class GenreTemplate:
    """题材模板 — 网文TOP10题材的完整创作蓝图

    每个模板包含: 章节结构、建议字数、爽点密度、冲突原型、开场策略
    """

    template_id: str
    name: str
    category: GenreCategory
    description: str

    # 章节结构
    recommended_chapter_structure: dict[str, Any]  # 推荐章节结构
    typical_word_count: tuple[int, int]  # 典型字数范围 (单章)
    typical_total_words: tuple[int, int]  # 典型总字数

    # 爽点配置
    pleasure_point_density: float  # 爽点密度 (每千字)
    primary_pleasure_types: list[str]  # 主要爽点类型
    secondary_pleasure_types: list[str]  # 次要爽点类型

    # 冲突原型
    conflict_archetypes: list[str]  # 推荐冲突原型

    # 开篇策略
    opening_strategy: str  # 开篇策略
    opening_pleasure_types: list[str]  # 开篇推荐爽点
    golden_three_blueprint: list[str]  # 黄金三章蓝图

    # 节奏
    pace: PaceType
    climax_interval_chapters: int  # 高潮间隔章节数

    # 其他
    suitable_platforms: list[str]
    reference_works: list[str]
    tags: list[str]
    taboo_notes: list[str] = field(default_factory=list)

    def get_prompt_context(self) -> str:
        """生成用于注入到LLM prompt的模板上下文"""
        lines = [
            f"【题材模板】{self.name}",
            f"【简介】{self.description}",
            f"【单章字数】{self.typical_word_count[0]}-{self.typical_word_count[1]}字",
            f"【总字数】{self.typical_total_words[0] // 10000}万"
            f"-{self.typical_total_words[1] // 10000}万字",
            f"【爽点密度】每千字≥{self.pleasure_point_density}个",
            f"【主要爽点】{', '.join(self.primary_pleasure_types)}",
            f"【次要爽点】{', '.join(self.secondary_pleasure_types)}",
            f"【冲突原型】{', '.join(self.conflict_archetypes)}",
            f"【开篇策略】{self.opening_strategy}",
            f"【节奏】{self.pace.value}，每{self.climax_interval_chapters}章一个高潮",
            f"【适合平台】{', '.join(self.suitable_platforms)}",
            f"【参考作品】{', '.join(self.reference_works[:3])}",
        ]
        if self.taboo_notes:
            lines.append(f"【禁忌】{', '.join(self.taboo_notes)}")
        return "\n".join(lines)

    def match_score(self, preferences: dict[str, Any]) -> float:
        """计算模板与用户偏好的匹配度 0-100"""
        score = 0.0

        pref_genre = preferences.get("genre", "")
        pref_pace = preferences.get("pace", "")
        pref_words = preferences.get("target_words", 0)
        pref_platform = preferences.get("platform", "")
        pref_pleasures = preferences.get("preferred_pleasures", [])
        pref_audience = preferences.get("audience", "general")

        if pref_genre and pref_genre in self.name:
            score += 25
        elif pref_genre and any(pref_genre in tag for tag in self.tags):
            score += 15

        if pref_pace and pref_pace == self.pace.value:
            score += 15

        if pref_words > 0:
            mid = (self.typical_total_words[0] + self.typical_total_words[1]) / 2
            if self.typical_total_words[0] <= pref_words <= self.typical_total_words[1]:
                score += 20
            elif abs(pref_words - mid) / mid < 0.5:
                score += 10

        if pref_platform and pref_platform in self.suitable_platforms:
            score += 15

        if pref_pleasures:
            matched = set(pref_pleasures) & set(
                self.primary_pleasure_types + self.secondary_pleasure_types
            )
            score += min(len(matched) * 8, 20)

        if (pref_audience == "mass" and self.pace == PaceType.FAST) or (
            pref_audience == "advanced" and self.pace in (PaceType.MEDIUM, PaceType.SLOW)
        ):
            score += 5

        return round(score, 0)


# ─── TOP10 网文题材模板 ──────────────────────────────

TOP10_TEMPLATES: dict[str, GenreTemplate] = {
    "dushi_xiuzhen": GenreTemplate(
        template_id="dushi_xiuzhen",
        name="都市修真",
        category=GenreCategory.DUSHI,
        description="现代都市背景下修真/修仙的爽文，扮猪吃虎+现代思维碰撞修仙体系",
        recommended_chapter_structure={
            "normal": {"scenes": "2-3", "pleasure_min": 2, "word_range": (2000, 3000)},
            "climax": {"scenes": "1-2", "pleasure_min": 3, "word_range": (2500, 3500)},
            "transition": {"scenes": "1-2", "pleasure_min": 1, "word_range": (1500, 2500)},
        },
        typical_word_count=(2000, 3000),
        typical_total_words=(2000000, 5000000),
        pleasure_point_density=3.0,
        primary_pleasure_types=["打脸", "装逼", "碾压", "升级"],
        secondary_pleasure_types=["奇遇", "系统奖励", "后宫"],
        conflict_archetypes=["权力压制→打脸反击", "现代认知优势→碾压", "扮猪吃虎→身份暴露"],
        opening_strategy="前3章建立金手指+首次打脸，让读者在5分钟内爽到",
        opening_pleasure_types=["打脸", "装逼", "系统奖励"],
        golden_three_blueprint=[
            "第1章: 建立主角身份+金手指获得/觉醒+首次打脸小混混",
            "第2章: 展现金手指威力+碾压第一个反派+埋下校园/职场冲突",
            "第3章: 装逼大场面+身份初露+埋下修真世界暗线",
        ],
        pace=PaceType.FAST,
        climax_interval_chapters=20,
        suitable_platforms=["fanqie", "qimao", "feilu", "qidian"],
        reference_works=["修仙高手在都市", "最强弃少", "都市极品仙帝"],
        tags=["都市", "修真", "打脸", "装逼"],
        taboo_notes=["开头超过5000字未出现打脸", "金手指展示过晚(>3章)"],
    ),
    "xuanhuan": GenreTemplate(
        template_id="xuanhuan",
        name="玄幻",
        category=GenreCategory.XUANHUAN,
        description="东方幻想世界，修炼体系完整，热血升级冒险",
        recommended_chapter_structure={
            "normal": {"scenes": "2-4", "pleasure_min": 2, "word_range": (2500, 3500)},
            "climax": {"scenes": "1-2", "pleasure_min": 4, "word_range": (3000, 5000)},
            "transition": {"scenes": "2-3", "pleasure_min": 1, "word_range": (2000, 3000)},
        },
        typical_word_count=(2500, 3500),
        typical_total_words=(2000000, 6000000),
        pleasure_point_density=2.5,
        primary_pleasure_types=["升级", "打脸", "热血", "碾压"],
        secondary_pleasure_types=["奇遇", "收获", "觉醒"],
        conflict_archetypes=["宗门大比", "秘境夺宝", "家族恩怨", "正邪对立"],
        opening_strategy="快速建立世界观+修炼体系+首次升级突破，让读者感受成长快感",
        opening_pleasure_types=["升级", "觉醒", "奇遇"],
        golden_three_blueprint=[
            "第1章: 废材/平凡出身+修炼体系初现+第一次突破",
            "第2章: 展现实力+打脸嘲讽者+获得第一份机缘",
            "第3章: 离开新手村+遭遇更强对手+埋下主线伏笔",
        ],
        pace=PaceType.MEDIUM,
        climax_interval_chapters=25,
        suitable_platforms=["qidian", "fanqie"],
        reference_works=["斗破苍穹", "完美世界", "遮天"],
        tags=["玄幻", "修炼", "升级流", "热血"],
        taboo_notes=["世界观过于复杂(前3章)", "修炼体系不清晰"],
    ),
    "xitong": GenreTemplate(
        template_id="xitong",
        name="系统流",
        category=GenreCategory.QITA,
        description="主角携带系统/面板/金手指，通过任务获得奖励的极爽模式",
        recommended_chapter_structure={
            "normal": {"scenes": "2-3", "pleasure_min": 3, "word_range": (1500, 2500)},
            "climax": {"scenes": "1-2", "pleasure_min": 4, "word_range": (2000, 3000)},
            "transition": {"scenes": "1-2", "pleasure_min": 1, "word_range": (1200, 2000)},
        },
        typical_word_count=(1500, 2500),
        typical_total_words=(1500000, 5000000),
        pleasure_point_density=3.5,
        primary_pleasure_types=["系统奖励", "打脸", "升级", "装逼"],
        secondary_pleasure_types=["碾压", "后宫", "奇遇"],
        conflict_archetypes=["系统任务→实力提升→打脸", "系统商城→资源碾压", "系统功能→信息差"],
        opening_strategy="序章即激活系统，第1章完成首次任务奖励，让读者立即进入爽点循环",
        opening_pleasure_types=["系统奖励", "打脸", "升级"],
        golden_three_blueprint=[
            "第1章: 系统激活+首次任务+首次奖励+首次打脸",
            "第2章: 系统功能扩展+新任务+碾压同龄人",
            "第3章: 第一次大任务+实力质变+征服第一个势力",
        ],
        pace=PaceType.FAST,
        climax_interval_chapters=15,
        suitable_platforms=["fanqie", "qimao", "feilu"],
        reference_works=["超级神基因", "最强升级系统", "万界淘宝商"],
        tags=["系统流", "金手指", "面板", "爽文"],
        taboo_notes=["系统设定不清晰", "奖励与升级节奏脱节"],
    ),
    "chongsheng": GenreTemplate(
        template_id="chongsheng",
        name="重生流",
        category=GenreCategory.QITA,
        description="主角重生/穿越回过去，利用前世记忆/知识逆袭",
        recommended_chapter_structure={
            "normal": {"scenes": "2-3", "pleasure_min": 2, "word_range": (2000, 3000)},
            "climax": {"scenes": "1-2", "pleasure_min": 4, "word_range": (2500, 3500)},
            "transition": {"scenes": "2-3", "pleasure_min": 1, "word_range": (1500, 2500)},
        },
        typical_word_count=(2000, 3000),
        typical_total_words=(1500000, 4000000),
        pleasure_point_density=3.0,
        primary_pleasure_types=["打脸", "复仇", "逆转", "装逼"],
        secondary_pleasure_types=["收获", "后宫", "觉醒"],
        conflict_archetypes=["信息差→降维打击", "先知→精准投资/决策", "复仇→清算前世仇人"],
        opening_strategy="重生瞬间+首个逆袭打脸场景（如考试/赌石/投资），立即展现信息差优势",
        opening_pleasure_types=["打脸", "逆转", "觉醒"],
        golden_three_blueprint=[
            "第1章: 前世悲惨/死亡+重生瞬间+首个逆袭计划",
            "第2章: 利用前世知识打脸+获得第一桶金/资源",
            "第3章: 改变关键事件+收服前世伙伴+埋下主线",
        ],
        pace=PaceType.FAST,
        climax_interval_chapters=20,
        suitable_platforms=["fanqie", "qimao", "qidian"],
        reference_works=["我真没想重生啊", "重生之都市修仙", "重返2008"],
        tags=["重生", "逆袭", "先知", "都市"],
        taboo_notes=["信息差滥用(逻辑漏洞)", "前世记忆模糊不清"],
    ),
    "chuanyue": GenreTemplate(
        template_id="chuanyue",
        name="穿越",
        category=GenreCategory.XUANHUAN,
        description="现代人穿越到异世界/古代，利用现代知识/思维降维打击",
        recommended_chapter_structure={
            "normal": {"scenes": "2-3", "pleasure_min": 2, "word_range": (2000, 3500)},
            "climax": {"scenes": "1-2", "pleasure_min": 3, "word_range": (2500, 4000)},
            "transition": {"scenes": "2-3", "pleasure_min": 1, "word_range": (1500, 2500)},
        },
        typical_word_count=(2000, 3500),
        typical_total_words=(1500000, 5000000),
        pleasure_point_density=2.5,
        primary_pleasure_types=["装逼", "碾压", "升级", "奇遇"],
        secondary_pleasure_types=["后宫", "觉醒", "收获"],
        conflict_archetypes=["现代思维→古代/异界碾压", "科技/知识优势→实力飞跃", "文化冲突→反套路"],
        opening_strategy="穿越瞬间+身份适应+首次展现现代知识优势（如发明/制度/技术）",
        opening_pleasure_types=["装逼", "奇遇", "觉醒"],
        golden_three_blueprint=[
            "第1章: 穿越+初到异界/古代+身份/处境确立",
            "第2章: 首次展现现代知识优势+获得第一批追随者",
            "第3章: 建立初步势力+对抗首个敌人+主线明朗",
        ],
        pace=PaceType.MEDIUM,
        climax_interval_chapters=25,
        suitable_platforms=["qidian", "fanqie"],
        reference_works=["赘婿", "庆余年", "诡秘之主"],
        tags=["穿越", "异世界", "种田", "争霸"],
        taboo_notes=["现代知识滥用无逻辑", "时代错位感太强"],
    ),
    "mori": GenreTemplate(
        template_id="mori",
        name="末日",
        category=GenreCategory.KEHUAN,
        description="末日/废土/丧尸背景下的生存、进化与重建",
        recommended_chapter_structure={
            "normal": {"scenes": "2-3", "pleasure_min": 2, "word_range": (2000, 3000)},
            "climax": {"scenes": "1-2", "pleasure_min": 4, "word_range": (2500, 4000)},
            "transition": {"scenes": "1-2", "pleasure_min": 1, "word_range": (1500, 2500)},
        },
        typical_word_count=(2000, 3000),
        typical_total_words=(1000000, 3000000),
        pleasure_point_density=2.5,
        primary_pleasure_types=["觉醒", "升级", "碾压", "收获"],
        secondary_pleasure_types=["热血", "守护", "后宫"],
        conflict_archetypes=["生存危机→进化突破", "资源争夺→势力扩张", "人性考验→道德抉择"],
        opening_strategy="末日降临+首次觉醒/进化+首次血腥击杀，营造紧张感+成就感",
        opening_pleasure_types=["觉醒", "升级", "碾压"],
        golden_three_blueprint=[
            "第1章: 末日降临+主角首次进化/觉醒+首次击杀丧尸",
            "第2章: 获得特殊能力/道具+救下/收服第一批伙伴",
            "第3章: 建立安全区/基地+对抗第一波威胁+主线",
        ],
        pace=PaceType.FAST,
        climax_interval_chapters=20,
        suitable_platforms=["fanqie", "qimao", "qidian"],
        reference_works=["全球进化", "末世之黑暗召唤师", "废土"],
        tags=["末日", "丧尸", "生存", "进化"],
        taboo_notes=["末世设定逻辑漏洞", "资源获取过于容易"],
    ),
    "xuanyi": GenreTemplate(
        template_id="xuanyi",
        name="悬疑",
        category=GenreCategory.XUANYI,
        description="悬疑/推理/灵异故事，强调谜题设计和逻辑推理",
        recommended_chapter_structure={
            "normal": {"scenes": "2-4", "pleasure_min": 1, "word_range": (2500, 4000)},
            "climax": {"scenes": "1-2", "pleasure_min": 2, "word_range": (3000, 5000)},
            "transition": {"scenes": "2-3", "pleasure_min": 1, "word_range": (2000, 3000)},
        },
        typical_word_count=(2500, 4000),
        typical_total_words=(600000, 2000000),
        pleasure_point_density=1.5,
        primary_pleasure_types=["揭秘", "反转", "逆转"],
        secondary_pleasure_types=["升级", "收获", "感动"],
        conflict_archetypes=[
            "谜题抛出→推理推进→真相揭示",
            "误导→反转→真相大白",
            "多线叙事→线索交织",
        ],
        opening_strategy="抛出核心悬疑+营造紧张氛围+让读者产生'必须知道答案'的好奇心",
        opening_pleasure_types=["揭秘", "反转"],
        golden_three_blueprint=[
            "第1章: 抛出核心谜案+建立悬疑氛围+主角介入",
            "第2章: 获得第一个关键线索+遭遇第一次威胁/反转",
            "第3章: 线索深化+第一个小谜题解开+更大谜团浮现",
        ],
        pace=PaceType.MEDIUM,
        climax_interval_chapters=25,
        suitable_platforms=["qidian", "fanqie"],
        reference_works=["心理罪", "白夜追凶", "盗墓笔记"],
        tags=["悬疑", "推理", "侦探", "灵异"],
        taboo_notes=["逻辑漏洞", "线索过于明显/隐晦"],
    ),
    "youxi": GenreTemplate(
        template_id="youxi",
        name="游戏",
        category=GenreCategory.YOUXI,
        description="网游/电竞/虚拟现实题材，升级打宝、PVP竞技",
        recommended_chapter_structure={
            "normal": {"scenes": "2-3", "pleasure_min": 2, "word_range": (2000, 3000)},
            "climax": {"scenes": "1-2", "pleasure_min": 4, "word_range": (2500, 4000)},
            "transition": {"scenes": "1-2", "pleasure_min": 1, "word_range": (1500, 2500)},
        },
        typical_word_count=(2000, 3000),
        typical_total_words=(1500000, 4000000),
        pleasure_point_density=3.0,
        primary_pleasure_types=["系统奖励", "升级", "打脸", "碾压"],
        secondary_pleasure_types=["装逼", "团队合作", "收获"],
        conflict_archetypes=["竞技PVP→排名攀升", "团队副本→集体协作", "隐藏任务→独特奖励"],
        opening_strategy="游戏登录/创建角色+首个隐藏任务/技能+第一次惊艳表现",
        opening_pleasure_types=["系统奖励", "升级", "打脸"],
        golden_three_blueprint=[
            "第1章: 进入游戏+创建角色+首获隐藏职业/技能",
            "第2章: 首次打怪升级+获得稀有装备+惊艳其他玩家",
            "第3章: 第一次PVP打脸+组队冒险+主线/公会",
        ],
        pace=PaceType.FAST,
        climax_interval_chapters=18,
        suitable_platforms=["fanqie", "qimao", "qidian"],
        reference_works=["全职高手", "惊悚乐园", "网游之近战法师"],
        tags=["网游", "电竞", "竞技", "虚拟现实"],
        taboo_notes=["游戏设定不专业", "数据数值混乱"],
    ),
    "kehuan": GenreTemplate(
        template_id="kehuan",
        name="科幻",
        category=GenreCategory.KEHUAN,
        description="科幻题材，强调科学逻辑和未来推演",
        recommended_chapter_structure={
            "normal": {"scenes": "2-4", "pleasure_min": 1, "word_range": (2500, 4500)},
            "climax": {"scenes": "1-2", "pleasure_min": 2, "word_range": (3000, 5000)},
            "transition": {"scenes": "2-3", "pleasure_min": 1, "word_range": (2000, 3500)},
        },
        typical_word_count=(2500, 4500),
        typical_total_words=(1000000, 3000000),
        pleasure_point_density=1.5,
        primary_pleasure_types=["揭秘", "反转", "逆袭"],
        secondary_pleasure_types=["升级", "收获", "感动"],
        conflict_archetypes=["技术突破→文明冲击", "人类vsAI/外星", "未来社会→伦理困境"],
        opening_strategy="高概念科幻设定+快速建立世界观+抛出引人思考的科学命题",
        opening_pleasure_types=["揭秘", "反转"],
        golden_three_blueprint=[
            "第1章: 科幻设定揭示+世界观背景+主角处境",
            "第2章: 核心矛盾/危机爆发+主角介入/觉醒",
            "第3章: 首次科学发现/技术突破+主线展开",
        ],
        pace=PaceType.SLOW,
        climax_interval_chapters=30,
        suitable_platforms=["qidian"],
        reference_works=["三体", "流浪地球", "银河帝国"],
        tags=["科幻", "未来", "宇宙", "硬核"],
        taboo_notes=["科学逻辑漏洞", "设定不自洽"],
    ),
    "yanqing": GenreTemplate(
        template_id="yanqing",
        name="言情",
        category=GenreCategory.YANQING,
        description="以爱情为主线的情感故事，古装/现代皆可",
        recommended_chapter_structure={
            "normal": {"scenes": "2-3", "pleasure_min": 1, "word_range": (2500, 4000)},
            "climax": {"scenes": "1-2", "pleasure_min": 2, "word_range": (3000, 5000)},
            "transition": {"scenes": "2-3", "pleasure_min": 1, "word_range": (2000, 3500)},
        },
        typical_word_count=(2500, 4000),
        typical_total_words=(600000, 2500000),
        pleasure_point_density=1.5,
        primary_pleasure_types=["暧昧", "感动", "守护", "反转"],
        secondary_pleasure_types=["后宫", "打脸", "装逼"],
        conflict_archetypes=["虐渣→翻身打脸", "误会→和解→深情", "身份对立→冲破世俗"],
        opening_strategy="抓人的相遇/重逢+情感火花+身份/背景悬念，让读者立即关心CP命运",
        opening_pleasure_types=["暧昧", "反转", "守护"],
        golden_three_blueprint=[
            "第1章: 男女主初次相遇/重逢+身份/地位悬念",
            "第2章: 情感火花/冲突+首次互动/交锋",
            "第3章: 情感升温/转折+埋下主线冲突",
        ],
        pace=PaceType.MEDIUM,
        climax_interval_chapters=30,
        suitable_platforms=["jjwxc", "fanqie", "qidian"],
        reference_works=["知否知否", "何以笙箫默", "微微一笑很倾城"],
        tags=["言情", "古装", "甜宠", "现代"],
        taboo_notes=["感情线铺垫不足", "人物扁平化"],
    ),
}


# ─── 规则引擎 ────────────────────────────────────────


class GenreRuleEngine:
    """题材规则引擎 — 题材配置查询 + 规则叠加 + 模板推荐"""

    @staticmethod
    def get_config(genre_id: str) -> GenreConfig | None:
        return GENRE_LIBRARY.get(genre_id)

    @staticmethod
    def list_all_genres() -> list[dict]:
        return [
            {
                "id": g.genre_id,
                "name": g.name,
                "category": g.category.value,
                "description": g.description,
                "tags": g.tags,
            }
            for g in GENRE_LIBRARY.values()
        ]

    @staticmethod
    def list_by_category(category: GenreCategory) -> list[GenreConfig]:
        return [g for g in GENRE_LIBRARY.values() if g.category == category]

    @staticmethod
    def list_templates() -> list[dict]:
        """列出所有TOP10模板"""
        return [
            {
                "id": t.template_id,
                "name": t.name,
                "category": t.category.value,
                "description": t.description,
                "tags": t.tags,
            }
            for t in TOP10_TEMPLATES.values()
        ]

    @staticmethod
    def get_template(template_id: str) -> GenreTemplate | None:
        """获取指定模板"""
        return TOP10_TEMPLATES.get(template_id)

    @staticmethod
    def recommend(
        genre: str = "",
        pace: str = "",
        target_words: int = 0,
        platform: str = "",
        preferred_pleasures: list[str] | None = None,
        audience: str = "general",
        top_n: int = 3,
    ) -> list[dict]:
        """根据用户偏好推荐最佳题材模板

        Args:
            genre: 用户偏好的题材关键词
            pace: 偏好节奏 (fast/medium/slow)
            target_words: 目标总字数
            platform: 目标平台 (fanqie/qidian/qimao/feilu/jjwxc)
            preferred_pleasures: 偏好爽点类型列表
            audience: 目标读者群 (mass/general/advanced)
            top_n: 返回Top N推荐

        Returns:
            排序后的推荐列表 [{template_id, name, score, reason, ...}, ...]
        """
        preferences = {
            "genre": genre,
            "pace": pace,
            "target_words": target_words,
            "platform": platform,
            "preferred_pleasures": preferred_pleasures or [],
            "audience": audience,
        }

        scored: list[tuple[GenreTemplate, float]] = []
        for t in TOP10_TEMPLATES.values():
            s = t.match_score(preferences)
            scored.append((t, s))  # 保留所有，即使分数为0也会有fallback

        scored.sort(key=lambda x: (-x[1], x[0].name))

        # 如果所有得分都为0（无偏好输入），返回前top_n个作为发现性推荐
        if all(s == 0 for _, s in scored):
            scored = [(t, 1.0) for t in TOP10_TEMPLATES.values()]
            scored.sort(key=lambda x: x[0].name)

        results: list[dict] = []
        for template, score in scored[:top_n]:
            reasons: list[str] = []
            if genre and genre in template.name:
                reasons.append(f"题材匹配: {template.name}")
            if platform and platform in template.suitable_platforms:
                reasons.append(f"适配平台: {platform}")
            if pace and pace == template.pace.value:
                reasons.append(f"节奏偏好: {template.pace.value}")
            if preferred_pleasures:
                matched = set(preferred_pleasures) & set(template.primary_pleasure_types)
                if matched:
                    reasons.append(f"爽点偏好: {', '.join(matched)}")

            results.append(
                {
                    "template_id": template.template_id,
                    "name": template.name,
                    "category": template.category.value,
                    "score": score,
                    "description": template.description,
                    "reasons": reasons if reasons else ["综合匹配"],
                    "opening_strategy": template.opening_strategy,
                    "golden_three_blueprint": template.golden_three_blueprint,
                    "primary_pleasures": template.primary_pleasure_types,
                    "pace": template.pace.value,
                    "suitable_platforms": template.suitable_platforms,
                    "reference_works": template.reference_works,
                }
            )

        logger.info(
            f"模板推荐: {len(results)}个匹配, top:{results[0]['name'] if results else 'none'}"
        )
        return results

    @staticmethod
    def merge_configs(genre_ids: list[str]) -> GenreConfig:
        configs = [GENRE_LIBRARY[gid] for gid in genre_ids if gid in GENRE_LIBRARY]
        if not configs:
            raise ValueError(f"无效的题材ID: {genre_ids}")
        if len(configs) == 1:
            return configs[0]

        primary = configs[0]
        for secondary in configs[1:]:
            p_min, p_max = primary.suggested_words_per_chapter
            s_min, s_max = secondary.suggested_words_per_chapter
            primary.suggested_words_per_chapter = (min(p_min, s_min), max(p_max, s_max))

            primary.preferred_pleasures = list(
                set(primary.preferred_pleasures) | set(secondary.preferred_pleasures)
            )
            primary.taboos = list(set(primary.taboos) | set(secondary.taboos))
            primary.required_elements = list(
                set(primary.required_elements) | set(secondary.required_elements)
            )

            if secondary.pace == PaceType.FAST:
                primary.pace = PaceType.FAST

            primary.tags = list(set(primary.tags) | set(secondary.tags))
            primary.sub_genres = list(set(primary.sub_genres) | set(secondary.sub_genres))
            primary.best_platforms = list(
                set(primary.best_platforms) | set(secondary.best_platforms)
            )
            primary.min_pleasure_per_1k = max(
                primary.min_pleasure_per_1k, secondary.min_pleasure_per_1k
            )
            primary.climax_chapter_interval = min(
                primary.climax_chapter_interval, secondary.climax_chapter_interval
            )

        return primary

    @staticmethod
    def generate_creative_brief(genre_id: str) -> dict:
        config = GENRE_LIBRARY.get(genre_id)
        if not config:
            return {}

        return {
            "genre": config.name,
            "description": config.description,
            "target_words_per_chapter": (
                f"{config.suggested_words_per_chapter[0]}-{config.suggested_words_per_chapter[1]}"
            ),
            "total_words": (
                f"{config.suggested_total_words[0] / 10000:.0f}万-"
                f"{config.suggested_total_words[1] / 10000:.0f}万"
            ),
            "pace": config.pace.value,
            "key_pleasures": config.preferred_pleasures,
            "must_include": config.required_elements,
            "must_avoid": config.taboos,
            "best_platforms": config.best_platforms,
            "reference_works": config.style_references,
            "style_notes": config.style_notes,
            "golden_three_tips": _get_golden_three_tips(config),
            "chapter_template": config.chapter_structure,
        }

    @staticmethod
    def get_genre_prompt_context(genre_id: str) -> str:
        config = GENRE_LIBRARY.get(genre_id)
        if not config:
            return ""

        lines = [
            f"【题材】{config.name}",
            f"【简介】{config.description}",
            f"【节奏】{config.pace.value}",
            f"【推荐爽点类型】{', '.join(config.preferred_pleasures)}",
            f"【每千字爽点目标】≥{config.min_pleasure_per_1k}个",
            f"【对话比例】{config.dialogue_ratio[0]:.0%}-{config.dialogue_ratio[1]:.0%}",
            f"【禁忌】{', '.join(config.taboos)}",
            f"【必须包含】{', '.join(config.required_elements)}",
        ]
        if config.style_notes:
            lines.append(f"【文风要求】{config.style_notes}")
        if config.style_references:
            lines.append(f"【参考作品】{', '.join(config.style_references[:3])}")

        return "\n".join(lines)


def _get_golden_three_tips(config: GenreConfig) -> list[str]:
    tips = [
        f"第1章: 建立世界观基础 + 引入"
        f"{config.preferred_pleasures[0] if config.preferred_pleasures else '核心'}爽点",
        f"第2章: 深化冲突 + 展现"
        f"{config.preferred_pleasures[1] if len(config.preferred_pleasures) > 1 else '次要'}爽点",
        "第3章: 第一个小高潮 + 埋下长线伏笔",
    ]
    if config.golden_three_intensity >= 0.9:
        tips.append("⚠️ 黄金三章钩子强度要求极高，每章结尾必须悬念断章")
    return tips


# ─── 工厂函数 ────────────────────────────────────────

_genre_engine: GenreRuleEngine | None = None


def get_genre_engine() -> GenreRuleEngine:
    global _genre_engine  # noqa: PLW0603
    if _genre_engine is None:
        _genre_engine = GenreRuleEngine()
    return _genre_engine
