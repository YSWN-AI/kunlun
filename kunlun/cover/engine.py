"""
昆仑创作引擎 — 封面生成模块

基于题材/世界观/角色信息自动生成封面图的提示词。
支持对接多种文生图服务（DALL-E/Midjourney/Stable Diffusion/ComfyUI）。

核心能力:
  1. 封面提示词生成 — 根据书籍信息自动构造封面 prompt
  2. 多风格预设 — 12 种网文封面风格模板
  3. 多平台对接 — DALL-E / Midjourney / SD / ComfyUI
  4. 尺寸适配 — 番茄/起点/七猫/晋江 各平台尺寸
  5. 文字叠加方案 — 书名/作者名的排版建议
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

# ─── 枚举 ──────────────────────────────────────────


class CoverStyle(Enum):
    """封面风格"""

    EPIC_FANTASY = "epic_fantasy"  # 史诗玄幻 — 宏大场景+主角背影
    DARK_XIANXIA = "dark_xianxia"  # 暗黑仙侠 — 水墨/血月/飞剑
    MODERN_COOL = "modern_cool"  # 现代酷炫 — 都市霓虹/冷色调
    SWEET_ROMANCE = "sweet_romance"  # 甜宠言情 — 粉色/花瓣/唯美
    MYSTERY_THRILLER = "mystery_thriller"  # 悬疑惊悚 — 暗调/迷雾/眼睛
    SCI_FI_TECH = "sci_fi_tech"  # 科幻未来 — 赛博朋克/蓝光
    HISTORICAL_ELEGANT = "historical_elegant"  # 古风典雅 — 水墨/仕女/山水
    GAME_ANIME = "game_anime"  # 二次元/游戏 — 日系插画风
    APOCALYPTIC = "apocalyptic"  # 末世废土 — 废墟/昏黄/生存
    MARTIAL_ARTS = "martial_arts"  # 武侠江湖 — 刀光剑影/竹林
    COMEDY_BRIGHT = "comedy_bright"  # 搞笑轻松 — 明亮色彩/Q版
    MINIMALIST = "minimalist"  # 极简风格 — 单色/符号化


class CoverAspectRatio(Enum):
    """封面比例"""

    VERTICAL_2_3 = "2:3"  # 番茄小说推荐
    VERTICAL_3_4 = "3:4"  # 起点推荐
    VERTICAL_9_16 = "9:16"  # 手机满屏
    VERTICAL_1_2 = "1:2"  # 长图广告
    SQUARE_1_1 = "1:1"  # 方形
    HORIZONTAL_16_9 = "16:9"  # 横版横幅


class CoverComposition(Enum):
    """封面构图模板"""

    SINGLE_CHARACTER = "single_character"  # 单人 — 主角特写
    DUAL_CHARACTER = "dual_character"  # 双人 — 主角+搭档/对手/恋人
    GROUP = "group"  # 群像 — 多人全景
    SCENE = "scene"  # 场景 — 世界观场景为主
    ABSTRACT = "abstract"  # 抽象 — 符号化/概念化
    TYPOGRAPHY = "typography"  # 文字 — 书名排版为主


class ImageService(Enum):
    """文生图服务"""

    DALLE = "dalle"
    MIDJOURNEY = "midjourney"
    STABLE_DIFFUSION = "stable_diffusion"
    COMFYUI = "comfyui"
    OPENAI = "openai"  # 兼容 OpenAI Image API


# ─── 数据模型 ────────────────────────────────────────


@dataclass
class CoverConfig:
    """封面生成配置"""

    book_id: str = ""
    title: str = ""  # 书名
    author: str = ""  # 作者名
    genre: str = "xuanhuan_dongfang"  # 题材ID
    style: CoverStyle = CoverStyle.EPIC_FANTASY
    aspect_ratio: CoverAspectRatio = CoverAspectRatio.VERTICAL_2_3
    service: ImageService = ImageService.OPENAI

    # 自定义描述
    custom_scene: str = ""  # 自定义场景描述
    custom_character: str = ""  # 自定义角色描述
    custom_mood: str = ""  # 自定义氛围
    custom_color: str = ""  # 自定义色调

    # 文字叠加
    add_title_text: bool = True  # 是否叠加书名
    add_author_text: bool = False  # 是否叠加作者名


@dataclass
class CoverPrompt:
    """封面提示词"""

    service: ImageService
    prompt: str  # 主提示词
    negative_prompt: str = ""  # 负面提示词
    style_params: dict[str, Any] = field(default_factory=dict)  # 风格参数
    aspect_ratio: str = "2:3"
    title_overlay: dict[str, str] = field(default_factory=dict)  # 书名排版


# ─── 风格模板 ──────────────────────────────────────

STYLE_TEMPLATES: dict[CoverStyle, dict] = {
    CoverStyle.EPIC_FANTASY: {
        "base_prompt": "epic fantasy book cover, majestic landscape with ancient ruins, "
        "dramatic lighting, cinematic composition, Chinese fantasy aesthetic, "
        "golden and crimson color palette, swirling energy effects, "
        "detailed background, professional illustration, high quality",
        "negative": "text, watermark, signature, blurry, low quality, deformed, "
        "multiple people, modern elements, western style",
        "mood": "epic, grand, awe-inspiring",
        "colors": "gold, crimson, deep blue",
    },
    CoverStyle.DARK_XIANXIA: {
        "base_prompt": "dark xianxia book cover, ink wash painting style, "
        "floating mountains, blood moon, flying sword silhouette, "
        "mystical fog, East Asian fantasy, ethereal glow, "
        "traditional Chinese ink art meets digital painting",
        "negative": "text, watermark, bright colors, cartoon, anime style, western",
        "mood": "mysterious, dark, ethereal",
        "colors": "black, crimson, silver, ink blue",
    },
    CoverStyle.MODERN_COOL: {
        "base_prompt": "modern urban book cover, neon city lights at night, "
        "rain-slicked streets, solitary figure in trench coat, "
        "cyberpunk-adjacent aesthetic, cool blue and purple tones, "
        "professional graphic design, minimalist yet impactful",
        "negative": "text, watermark, daylight, countryside, historical",
        "mood": "cool, mysterious, sophisticated",
        "colors": "cyan, purple, dark blue, neon pink",
    },
    CoverStyle.SWEET_ROMANCE: {
        "base_prompt": "sweet romance book cover, soft pastel colors, "
        "cherry blossoms or flower petals, gentle lighting, "
        "romantic atmosphere, dreamy bokeh effect, "
        "aesthetic illustration, warm and inviting",
        "negative": "text, watermark, dark colors, horror, gothic, nsfw",
        "mood": "warm, sweet, dreamy, romantic",
        "colors": "pink, peach, lavender, cream",
    },
    CoverStyle.MYSTERY_THRILLER: {
        "base_prompt": "mystery thriller book cover, dark atmospheric scene, "
        "shadowy figure, eerie fog, dim streetlight, "
        "suspenseful composition, film noir aesthetic, "
        "high contrast, dramatic shadows",
        "negative": "text, watermark, bright, cheerful, cartoon, cute",
        "mood": "tense, mysterious, unsettling",
        "colors": "black, deep red, grey, dim yellow",
    },
    CoverStyle.SCI_FI_TECH: {
        "base_prompt": "science fiction book cover, futuristic cityscape, "
        "holographic interfaces, sleek technology, "
        "cyberpunk aesthetic, blue and cyan neon glow, "
        "professional sci-fi illustration, highly detailed",
        "negative": "text, watermark, fantasy, medieval, nature, organic",
        "mood": "futuristic, technological, sleek",
        "colors": "cyan, electric blue, dark grey, white",
    },
    CoverStyle.HISTORICAL_ELEGANT: {
        "base_prompt": "historical Chinese book cover, traditional ink painting style, "
        "elegant court lady or scholar, flowing hanfu robes, "
        "classic garden or palace background, "
        "subdued elegant colors, cultural sophistication",
        "negative": "text, watermark, modern, western, neon, technology",
        "mood": "elegant, refined, cultural",
        "colors": "vermilion, gold, celadon green, ink black, paper white",
    },
    CoverStyle.GAME_ANIME: {
        "base_prompt": "anime style book cover, dynamic pose, vibrant colors, "
        "Japanese illustration style, cel-shaded, "
        "game-inspired character design, energy effects, "
        "professional anime key visual",
        "negative": "text, watermark, realistic, photo, 3D render, western art",
        "mood": "dynamic, energetic, vibrant",
        "colors": "vibrant blue, orange, white, magenta",
    },
    CoverStyle.APOCALYPTIC: {
        "base_prompt": "post-apocalyptic book cover, ruined cityscape, "
        "dusty orange sky, survival theme, "
        "lone figure in the wasteland, desolate atmosphere, "
        "cinematic composition, gritty texture",
        "negative": "text, watermark, bright, colorful, nature, green, cheerful",
        "mood": "desolate, gritty, survival",
        "colors": "burnt orange, brown, grey, dusty yellow",
    },
    CoverStyle.MARTIAL_ARTS: {
        "base_prompt": "martial arts book cover, bamboo forest, sword duel, "
        "flowing movement, dynamic action pose, "
        "Chinese wuxia aesthetic, ink splash effects, "
        "dramatic wind, falling leaves, cinematic lighting",
        "negative": "text, watermark, modern, gun, western, cyberpunk",
        "mood": "dynamic, honorable, intense",
        "colors": "bamboo green, ink black, crimson, gold",
    },
    CoverStyle.COMEDY_BRIGHT: {
        "base_prompt": "comedy book cover, bright cheerful colors, "
        "cartoonish illustration style, humorous scene, "
        "exaggerated expressions, fun typography space, "
        "clean vector art aesthetic, energetic",
        "negative": "text, watermark, dark, horror, gothic, realistic, serious",
        "mood": "funny, bright, energetic, playful",
        "colors": "yellow, orange, sky blue, bright green",
    },
    CoverStyle.MINIMALIST: {
        "base_prompt": "minimalist book cover design, single symbolic element, "
        "clean composition, lots of negative space, "
        "modern graphic design, subtle gradient background, "
        "sophisticated and understated",
        "negative": "text, watermark, complex, busy, multiple elements, clutter",
        "mood": "calm, sophisticated, modern",
        "colors": "monochrome with one accent color",
    },
}


# ─── 题材 → 风格自动映射 ─────────────────────────

GENRE_STYLE_MAP: dict[str, CoverStyle] = {
    "xuanhuan": CoverStyle.EPIC_FANTASY,
    "xuanhuan_dongfang": CoverStyle.EPIC_FANTASY,
    "xianxia": CoverStyle.DARK_XIANXIA,
    "xianxia_xiuzhen": CoverStyle.DARK_XIANXIA,
    "dushi": CoverStyle.MODERN_COOL,
    "dushi_zhuangbi": CoverStyle.MODERN_COOL,
    "kehuan": CoverStyle.SCI_FI_TECH,
    "kehuan_moshi": CoverStyle.APOCALYPTIC,
    "yanqing": CoverStyle.SWEET_ROMANCE,
    "yanqing_guzhuang": CoverStyle.HISTORICAL_ELEGANT,
    "wuxia": CoverStyle.MARTIAL_ARTS,
    "wuxia_chuantong": CoverStyle.MARTIAL_ARTS,
    "xuanyi": CoverStyle.MYSTERY_THRILLER,
    "xuanyi_zhentan": CoverStyle.MYSTERY_THRILLER,
    "youxi": CoverStyle.GAME_ANIME,
    "youxi_wangyou": CoverStyle.GAME_ANIME,
    "lishi": CoverStyle.HISTORICAL_ELEGANT,
    "lishi_jiakong": CoverStyle.HISTORICAL_ELEGANT,
    "gaoxiao": CoverStyle.COMEDY_BRIGHT,
    "moshou": CoverStyle.APOCALYPTIC,
}

# ─── 构图模板提示词 ──────────────────────────────

COMPOSITION_TEMPLATES: dict[CoverComposition, dict] = {
    CoverComposition.SINGLE_CHARACTER: {
        "prompt": "single character focus, main protagonist in center frame, "
        "dynamic pose, detailed costume design, character art style, "
        "dramatic lighting on the character, shallow depth of field, "
        "the background should be atmospheric but secondary to the character",
        "description": "单人构图 — 主角特写，突出角色形象与气质",
    },
    CoverComposition.DUAL_CHARACTER: {
        "prompt": "two characters composition, balanced framing, "
        "interesting relationship dynamic visible in poses and expressions, "
        "one character slightly dominant in composition, "
        "complementary color contrast between the two characters, "
        "professional character illustration",
        "description": "双人构图 — 主角+搭档/对手，体现关系张力",
    },
    CoverComposition.GROUP: {
        "prompt": "group composition with 3-5 characters, triangular/pyramid arrangement, "
        "main character at center or apex, supporting characters flanking, "
        "unified color scheme with focal point on the protagonist, "
        "epic ensemble illustration, cinematic framing",
        "description": "群像构图 — 多人全景，中心角色突出",
    },
    CoverComposition.SCENE: {
        "prompt": "landscape-oriented composition, expansive world-building scenery, "
        "small figure(s) in the vast environment for scale, "
        "atmospheric and immersive, set the mood through environment, "
        "cinematic wide shot, establishing shot aesthetic",
        "description": "场景构图 — 世界观场景为主，角色点缀其间",
    },
    CoverComposition.ABSTRACT: {
        "prompt": "abstract symbolic composition, minimal recognizable elements, "
        "geometric shapes and symbolic patterns, "
        "strong color blocks and gradients, conceptual art, "
        "modern graphic design with subtle narrative hints, "
        "sophisticated and artistic",
        "description": "抽象构图 — 符号化/概念化，强调视觉冲击与艺术感",
    },
    CoverComposition.TYPOGRAPHY: {
        "prompt": "typography-forward design, the book title as the main visual element, "
        "elaborate Chinese calligraphy or stylized typography, "
        "subtle atmospheric background supporting the text, "
        "text effects: glow, emboss, gold foil appearance, "
        "professional book cover typography design",
        "description": "文字构图 — 书名排版为主，氛围背景为辅",
    },
}

# ─── 平台尺寸与比例预设 ─────────────────────────

PLATFORM_SIZES: dict[str, tuple[int, int]] = {
    "fanqie": (600, 900),  # 番茄小说 2:3
    "qidian": (600, 800),  # 起点 3:4
    "qimao": (640, 960),  # 七猫 2:3
    "jjwxc": (500, 700),  # 晋江
    "feilu": (540, 800),  # 飞卢
    "generic": (600, 900),  # 通用
}

PLATFORM_PRESETS: dict[str, dict] = {
    "fanqie": {
        "aspect_ratio": CoverAspectRatio.VERTICAL_2_3,
        "size": (600, 900),
        "recommended_styles": [
            CoverStyle.EPIC_FANTASY,
            CoverStyle.MODERN_COOL,
            CoverStyle.SWEET_ROMANCE,
        ],
        "notes": "番茄读者偏好强冲击力、高饱和色彩，避免过于抽象的构图",
    },
    "qidian": {
        "aspect_ratio": CoverAspectRatio.VERTICAL_3_4,
        "size": (600, 800),
        "recommended_styles": [
            CoverStyle.EPIC_FANTASY,
            CoverStyle.DARK_XIANXIA,
            CoverStyle.MARTIAL_ARTS,
        ],
        "notes": "起点读者偏好史诗感、传统东方美学，角色特写效果最好",
    },
    "qimao": {
        "aspect_ratio": CoverAspectRatio.VERTICAL_2_3,
        "size": (640, 960),
        "recommended_styles": [
            CoverStyle.MODERN_COOL,
            CoverStyle.SWEET_ROMANCE,
            CoverStyle.COMEDY_BRIGHT,
        ],
        "notes": "七猫偏好明快、现代感的封面，都市/言情类表现突出",
    },
    "jjwxc": {
        "aspect_ratio": CoverAspectRatio.VERTICAL_3_4,
        "size": (500, 700),
        "recommended_styles": [
            CoverStyle.SWEET_ROMANCE,
            CoverStyle.HISTORICAL_ELEGANT,
            CoverStyle.MINIMALIST,
        ],
        "notes": "晋江偏好唯美、细腻的女性向风格，古风/言情为主",
    },
    "feilu": {
        "aspect_ratio": CoverAspectRatio.VERTICAL_2_3,
        "size": (540, 800),
        "recommended_styles": [CoverStyle.EPIC_FANTASY, CoverStyle.MODERN_COOL],
        "notes": "飞卢偏好男性向爽文风格，偏重热血与冲击力",
    },
    "generic": {
        "aspect_ratio": CoverAspectRatio.VERTICAL_2_3,
        "size": (600, 900),
        "recommended_styles": [CoverStyle.EPIC_FANTASY],
        "notes": "通用预设，适配大多数平台",
    },
}


# ─── 提示词生成器 ────────────────────────────────────


class CoverPromptGenerator:
    """封面提示词生成器"""

    @classmethod
    def generate(cls, config: CoverConfig) -> CoverPrompt:
        """根据配置生成封面提示词"""
        template = STYLE_TEMPLATES.get(config.style, STYLE_TEMPLATES[CoverStyle.EPIC_FANTASY])

        parts = [template["base_prompt"]]

        genre_hint = cls._get_genre_visual_hint(config.genre)
        if genre_hint:
            parts.append(genre_hint)

        if config.custom_scene:
            parts.append(config.custom_scene)

        if config.custom_character:
            parts.append(f"featuring: {config.custom_character}")

        mood = config.custom_mood or template.get("mood", "")
        if mood:
            parts.append(f"mood: {mood}")

        color = config.custom_color or template.get("colors", "")
        if color:
            parts.append(f"color palette: {color}")

        if config.add_title_text:
            parts.append("top 30 percent area kept clear for title text overlay")

        main_prompt = ", ".join(parts)

        negative = template.get("negative", "text, watermark, signature, low quality, blurry")

        service_prompt, style_params = cls._adapt_for_service(
            main_prompt, negative, config.service, config.aspect_ratio
        )

        return CoverPrompt(
            service=config.service,
            prompt=service_prompt,
            negative_prompt=negative,
            style_params=style_params,
            aspect_ratio=config.aspect_ratio.value,
            title_overlay=cls._generate_title_overlay(config) if config.add_title_text else {},
        )

    @classmethod
    def _get_genre_visual_hint(cls, genre_id: str) -> str:
        """获取题材视觉提示"""
        hints = {
            "xuanhuan_dongfang": "Chinese fantasy world, cultivation aura, ancient sects",
            "xianxia_xiuzhen": "immortal cultivation, flying swords, celestial palaces",
            "dushi_zhuangbi": "modern city, luxury lifestyle, confident protagonist",
            "kehuan_moshi": "zombie apocalypse, survival, ruined city",
            "yanqing_guzhuang": "ancient Chinese romance, elegant costumes, palace gardens",
            "wuxia_chuantong": "martial arts world, jianghu, sword fights, bamboo forests",
            "xuanyi_zhentan": "crime scene investigation, mystery, noir atmosphere",
            "youxi_wangyou": "virtual reality game, digital world, game UI elements",
            "lishi_jiakong": "alternate history, ancient China, imperial court",
            "qihuan_jianyuemo": "fantasy world, magic circles, medieval castles",
        }
        return hints.get(genre_id, "")

    @classmethod
    def _adapt_for_service(
        cls, prompt: str, negative: str, service: ImageService, ratio: CoverAspectRatio
    ) -> tuple[str, dict]:
        """根据文生图服务调整 prompt 格式"""
        params: dict[str, Any] = {}

        if service == ImageService.DALLE:
            size_map = {
                CoverAspectRatio.VERTICAL_2_3: "1024x1536",
                CoverAspectRatio.VERTICAL_3_4: "1024x1365",
                CoverAspectRatio.SQUARE_1_1: "1024x1024",
                CoverAspectRatio.VERTICAL_9_16: "1024x1792",
            }
            params["size"] = size_map.get(ratio, "1024x1536")
            params["quality"] = "hd"
            return prompt, params

        if service == ImageService.MIDJOURNEY:
            ar_map = {
                CoverAspectRatio.VERTICAL_2_3: "--ar 2:3",
                CoverAspectRatio.VERTICAL_3_4: "--ar 3:4",
                CoverAspectRatio.SQUARE_1_1: "--ar 1:1",
                CoverAspectRatio.VERTICAL_9_16: "--ar 9:16",
            }
            mj_prompt = (
                f"{prompt} {ar_map.get(ratio, '--ar 2:3')} "
                f"--no {negative.replace(', ', ',')} --style raw"
            )
            params["aspect_ratio"] = ratio.value
            return mj_prompt, params

        if service == ImageService.STABLE_DIFFUSION:
            params["width"], params["height"] = {
                CoverAspectRatio.VERTICAL_2_3: (768, 1152),
                CoverAspectRatio.VERTICAL_3_4: (768, 1024),
                CoverAspectRatio.SQUARE_1_1: (1024, 1024),
                CoverAspectRatio.VERTICAL_9_16: (576, 1024),
            }.get(ratio, (768, 1152))
            params["negative_prompt"] = negative
            params["steps"] = 30
            params["cfg_scale"] = 7
            return prompt, params

        return prompt, params

    @classmethod
    def generate_with_composition(
        cls,
        config: CoverConfig,
        composition: CoverComposition = CoverComposition.SINGLE_CHARACTER,
    ) -> CoverPrompt:
        """根据构图模板生成封面提示词"""
        comp_template = COMPOSITION_TEMPLATES.get(
            composition, COMPOSITION_TEMPLATES[CoverComposition.SINGLE_CHARACTER]
        )
        original_scene = config.custom_scene
        config.custom_scene = (
            f"{comp_template['prompt']}, {original_scene}"
            if original_scene
            else comp_template["prompt"]
        )
        result = cls.generate(config)
        config.custom_scene = original_scene
        return result

    @classmethod
    def generate_genre_aware(
        cls,
        config: CoverConfig,
        enable_composition: bool = True,
    ) -> CoverPrompt:
        """题材感知封面生成 — 自动选择风格+构图"""
        if config.style == CoverStyle.EPIC_FANTASY and config.genre in GENRE_STYLE_MAP:
            config.style = GENRE_STYLE_MAP[config.genre]

        if enable_composition:
            genre_composition_map = {
                "xuanhuan": CoverComposition.SINGLE_CHARACTER,
                "xuanhuan_dongfang": CoverComposition.SINGLE_CHARACTER,
                "xianxia": CoverComposition.SCENE,
                "xianxia_xiuzhen": CoverComposition.SCENE,
                "dushi": CoverComposition.DUAL_CHARACTER,
                "yanqing": CoverComposition.DUAL_CHARACTER,
                "yanqing_guzhuang": CoverComposition.DUAL_CHARACTER,
                "wuxia": CoverComposition.GROUP,
                "wuxia_chuantong": CoverComposition.GROUP,
                "kehuan": CoverComposition.SCENE,
                "xuanyi": CoverComposition.ABSTRACT,
                "lishi": CoverComposition.GROUP,
                "lishi_jiakong": CoverComposition.GROUP,
                "youxi": CoverComposition.DUAL_CHARACTER,
                "gaoxiao": CoverComposition.TYPOGRAPHY,
            }
            composition = genre_composition_map.get(config.genre, CoverComposition.SINGLE_CHARACTER)
            return cls.generate_with_composition(config, composition)

        return cls.generate(config)

    @classmethod
    def generate_for_platform(
        cls,
        config: CoverConfig,
        platform: str,
        enable_genre_aware: bool = True,
    ) -> CoverPrompt:
        """平台适配封面生成 — 自动匹配比例+风格偏好"""
        preset = PLATFORM_PRESETS.get(platform, PLATFORM_PRESETS["generic"])
        config.aspect_ratio = preset["aspect_ratio"]

        if enable_genre_aware:
            return cls.generate_genre_aware(config)
        return cls.generate(config)

    @classmethod
    def get_platform_presets(cls) -> dict:
        """获取所有平台预设"""
        result = {}
        for platform, preset in PLATFORM_PRESETS.items():
            result[platform] = {
                "aspect_ratio": preset["aspect_ratio"].value,
                "size": list(preset["size"]),
                "recommended_styles": [s.value for s in preset["recommended_styles"]],
                "notes": preset["notes"],
            }
        return result

    @classmethod
    def get_composition_templates(cls) -> list[dict]:
        """获取所有构图模板"""
        return [
            {
                "id": comp.value,
                "name": comp.name,
                "description": COMPOSITION_TEMPLATES[comp]["description"],
            }
            for comp in CoverComposition
        ]

    @classmethod
    def get_genre_style_map(cls) -> dict[str, str]:
        """获取题材风格映射"""
        return {genre: style.value for genre, style in GENRE_STYLE_MAP.items()}

    @classmethod
    def _generate_title_overlay(cls, config: CoverConfig) -> dict:
        """生成书名排版建议"""
        overlay = {"title": config.title or "书名"}
        if config.add_author_text and config.author:
            overlay["author"] = config.author

        style_positions = {
            CoverStyle.EPIC_FANTASY: {
                "title_pos": "top-center",
                "font_style": "bold serif, gold gradient",
            },
            CoverStyle.DARK_XIANXIA: {
                "title_pos": "top-right",
                "font_style": "calligraphy, crimson",
            },
            CoverStyle.MODERN_COOL: {
                "title_pos": "bottom-left",
                "font_style": "sans-serif, neon cyan",
            },
            CoverStyle.SWEET_ROMANCE: {"title_pos": "center", "font_style": "script, pink"},
            CoverStyle.MINIMALIST: {"title_pos": "center", "font_style": "thin sans-serif, black"},
        }
        pos = style_positions.get(
            config.style, {"title_pos": "top-center", "font_style": "bold serif"}
        )
        overlay.update(pos)
        return overlay


# ─── 平台尺寸计算 ────────────────────────────────────


def get_platform_size(platform: str) -> tuple[int, int]:
    """获取平台推荐封面尺寸"""
    return PLATFORM_SIZES.get(platform, PLATFORM_SIZES["generic"])


def get_aspect_ratio_for_platform(platform: str) -> CoverAspectRatio:
    """获取平台推荐比例"""
    ratio_map = {
        "fanqie": CoverAspectRatio.VERTICAL_2_3,
        "qidian": CoverAspectRatio.VERTICAL_3_4,
        "qimao": CoverAspectRatio.VERTICAL_2_3,
        "jjwxc": CoverAspectRatio.VERTICAL_3_4,
        "feilu": CoverAspectRatio.VERTICAL_2_3,
    }
    return ratio_map.get(platform, CoverAspectRatio.VERTICAL_2_3)


# ─── 工厂函数 ────────────────────────────────────────

_cover_generator: CoverPromptGenerator | None = None


def get_cover_generator() -> CoverPromptGenerator:
    global _cover_generator  # noqa: PLW0603
    if _cover_generator is None:
        _cover_generator = CoverPromptGenerator()
    return _cover_generator


def get_genre_style(genre: str) -> str | None:
    """获取题材对应的推荐封面风格"""
    style = GENRE_STYLE_MAP.get(genre)
    return style.value if style else None


def get_platform_preset(platform: str) -> dict | None:
    """获取平台封面预设"""
    preset = PLATFORM_PRESETS.get(platform)
    if not preset:
        return None
    return {
        "aspect_ratio": preset["aspect_ratio"].value,
        "size": list(preset["size"]),
        "recommended_styles": [s.value for s in preset["recommended_styles"]],
        "notes": preset["notes"],
    }


def get_composition_template(composition: CoverComposition) -> dict | None:
    """获取构图模板"""
    comp = COMPOSITION_TEMPLATES.get(composition)
    if not comp:
        return None
    return {
        "id": composition.value,
        "prompt": comp["prompt"],
        "description": comp["description"],
    }


def list_platform_presets() -> dict:
    """列出所有平台预设"""
    return CoverPromptGenerator.get_platform_presets()


def list_composition_templates() -> list[dict]:
    """列出所有构图模板"""
    return CoverPromptGenerator.get_composition_templates()
