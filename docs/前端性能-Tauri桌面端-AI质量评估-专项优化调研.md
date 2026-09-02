# 前端性能·Tauri桌面端·AI网文质量评估 — 专项优化调研

> 调研时间：2026-06-10 | 关联：12维度调研、500项目架构调研
> 目标：前端打包优化 + Tauri桌面端最佳实践 + AI网文质量量化体系

---

## 第一部分：前端性能优化 & Tauri 桌面端

### 1.1 昆仑前端现状诊断

| 维度 | 当前状态 | 评分 |
|------|---------|:---:|
| 构建工具 | Vite 5 + vue-tsc | 8/10 |
| UI 框架 | Naive UI 2.38（仅深色主题） | 6/10 |
| 编辑器 | Tiptap 3.26（基础安装） | 5/10 |
| 打包体积 | 主包 ~500KB（已做分包） | 7/10 |
| Tauri 集成 | Tauri 2.0 CLI + API | 6/10 |
| 主题系统 | 仅深色，无切换 | 3/10 |
| PWA | 未启用 | 0/10 |
| 离线支持 | 无 | 0/10 |
| 错误边界 | 无组件级错误处理 | 3/10 |

### 1.2 Tauri 2.0 桌面端优化

#### A. 减小安装包体积

```toml
# frontend/src-tauri/Cargo.toml — 优化建议
[dependencies]
tauri = { version = "2", features = [
    "tray-icon",         # 系统托盘（最小化到托盘）
    "protocol-asset",    # 本地资源加载（而非 http）
    "image-png",         # 仅 PNG 格式
    # 移除不需要的 features:
    # "image-ico"、"image-jpeg"、"http-request" 等
] }

# 优化编译设置
[profile.release]
panic = "abort"           # 减小二进制体积
codegen-units = 1         # 更好的 LTO 优化
lto = "fat"               # 链接时优化
opt-level = "s"           # 优化体积（s = size, 3 = speed）
strip = "symbols"         # 移除符号表
```

#### B. Tauri IPC 性能优化

```typescript
// frontend/src/api/tauri-bridge.ts（新建）
/**
 * Tauri IPC 桥接层 — 用 Rust 后端替代 HTTP 调用
 * 
 * 本地操作（文件读写、KG缓存、配置管理）走 Tauri IPC，
 * 仅 LLM API 调用保持 HTTP 模式。
 */

import { invoke } from '@tauri-apps/api/core'

export const tauriBridge = {
  // ─── 文件操作（比 HTTP 快 10-50x）───
  readFile: (path: string) => invoke<string>('read_file', { path }),
  writeFile: (path: string, content: string) => invoke('write_file', { path, content }),
  listFiles: (dir: string) => invoke<string[]>('list_files', { dir }),
  
  // ─── 本地 KG 缓存（避免每次查询走 HTTP）───
  kgQuery: (cypher: string) => invoke<any>('kg_query', { cypher }),
  kgSearch: (query: string) => invoke<any[]>('kg_search', { query }),
  
  // ─── 配置读写 ───
  getConfig: (key: string) => invoke<string>('get_config', { key }),
  setConfig: (key: string, value: string) => invoke('set_config', { key, value }),
  
  // ─── 本地导出（直接在 Rust 端生成文件）───
  exportChapter: (bookId: string, chapter: number, format: string) => 
    invoke<string>('export_chapter', { bookId, chapter, format }),
  exportBook: (bookId: string, format: string) =>
    invoke<string>('export_book', { bookId, format }),
}
```

#### C. 桌面端窗口管理优化

```rust
// frontend/src-tauri/src/main.rs — 优化建议
use tauri::Manager;

fn main() {
    tauri::Builder::default()
        .setup(|app| {
            let window = app.get_webview_window("main").unwrap();
            
            // 1. 设置最小窗口尺寸
            window.set_min_size(Some(tauri::Size::Logical(tauri::LogicalSize {
                width: 1024.0,
                height: 680.0,
            })))?;
            
            // 2. 记住窗口位置和大小
            #[cfg(desktop)]
            {
                use tauri_plugin_window_state::WindowState;
                // 需添加: tauri-plugin-window-state = "2"
            }
            
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
```

### 1.3 前端主题系统

```typescript
// frontend/src/stores/theme.ts（新建）
/**
 * 主题状态管理 — 深色/浅色切换 + 系统跟随
 * 对标 Naive UI 内置主题 + @vueuse/core useDark
 */

import { defineStore } from 'pinia'
import { ref, watch } from 'vue'
import { darkTheme, type GlobalThemeOverrides } from 'naive-ui'

type ThemeMode = 'dark' | 'light' | 'system'

const darkOverrides: GlobalThemeOverrides = {
  common: {
    primaryColor: '#5B8FF9',
    bodyColor: '#0F1117',
    cardColor: '#161822',
    textColor1: '#E8EAED',
    // ... 现有暗色配置
  },
}

const lightOverrides: GlobalThemeOverrides = {
  common: {
    primaryColor: '#4A7DE8',
    primaryColorHover: '#5B8FF9',
    bodyColor: '#F5F7FA',
    cardColor: '#FFFFFF',
    modalColor: '#FFFFFF',
    borderColor: '#E4E7ED',
    dividerColor: '#E4E7ED',
    textColor1: '#303133',
    textColor2: '#606266',
    textColor3: '#909399',
    borderRadius: '8px',
    fontSize: '14px',
    fontFamily: "'PingFang SC','Microsoft YaHei',sans-serif",
  },
  Layout: {
    headerColor: '#FFFFFF',
    siderColor: '#F5F7FA',
    footerColor: '#FFFFFF',
    headerBorderColor: '#E4E7ED',
    siderBorderColor: '#E4E7ED',
  },
  Card: {
    color: '#FFFFFF',
    borderColor: '#E4E7ED',
    borderRadius: '10px',
  },
  Input: {
    color: '#FFFFFF',
    borderColor: '#DCDFE6',
    borderHoverColor: '#C0C4CC',
    borderFocusColor: '#4A7DE8',
  },
}

export const useThemeStore = defineStore('theme', () => {
  const mode = ref<ThemeMode>(
    (localStorage.getItem('kunlun-theme') as ThemeMode) || 'dark'
  )
  
  const isDark = ref(mode.value === 'dark')
  
  const themeOverrides = ref(
    isDark.value ? darkOverrides : lightOverrides
  )
  
  function setMode(newMode: ThemeMode) {
    mode.value = newMode
    if (newMode === 'system') {
      isDark.value = window.matchMedia('(prefers-color-scheme: dark)').matches
    } else {
      isDark.value = newMode === 'dark'
    }
    themeOverrides.value = isDark.value ? darkOverrides : lightOverrides
    localStorage.setItem('kunlun-theme', newMode)
  }
  
  function toggle() {
    setMode(isDark.value ? 'light' : 'dark')
  }
  
  // 监听系统主题变化
  if (typeof window !== 'undefined') {
    window.matchMedia('(prefers-color-scheme: dark)')
      .addEventListener('change', (e) => {
        if (mode.value === 'system') {
          isDark.value = e.matches
          themeOverrides.value = e.matches ? darkOverrides : lightOverrides
        }
      })
  }
  
  return { mode, isDark, themeOverrides, setMode, toggle }
})
```

### 1.4 构建优化

```typescript
// vite.config.ts — 优化增强
export default defineConfig({
  build: {
    // 已有分包策略（naive-ui/echarts/tiptap/vue-vendor）
    // 新增优化:
    
    // 1. 压缩选项升级
    minify: 'esbuild',  // 当前已正确配置
    
    // 2. CSS 优化
    cssMinify: 'lightningcss',  // 比 esbuild CSS minify 快 2-3x
    
    // 3. Tree-shaking 增强
    rollupOptions: {
      treeshake: {
        preset: 'recommended',
        moduleSideEffects: (id) => {
          // 标记无副作用的模块以便更激进地 tree-shake
          if (id.includes('naive-ui/lib')) return false
          return true
        },
      },
    },
    
    // 4. 资源内联阈值（小资源内联到 JS，减少 HTTP 请求）
    assetsInlineLimit: 4096,  // < 4KB 内联
  },
  
  // 5. 开发体验优化
  server: {
    warmup: {
      clientFiles: [
        './src/views/CreateCenter.vue',
        './src/views/BookManager.vue',
        './src/api/index.ts',
      ],
    },
  },
})
```

### 1.5 前端性能监控

```typescript
// frontend/src/utils/perf.ts（新建）
/**
 * 前端性能监控 — Web Vitals + 自定义指标
 * 对标 Google Web Vitals: LCP / FID / CLS / INP
 */

// 路由切换耗时
import { router } from '../router'

router.beforeEach((to, from) => {
  performance.mark(`route-${to.name as string}-start`)
})

router.afterEach((to) => {
  performance.mark(`route-${to.name as string}-end`)
  performance.measure(
    `route-${to.name}`,
    `route-${to.name as string}-start`,
    `route-${to.name as string}-end`,
  )
})

// API 调用耗时
const originalFetch = window.fetch
window.fetch = async (...args) => {
  const start = performance.now()
  const response = await originalFetch(...args)
  const duration = performance.now() - start
  if (duration > 1000) {
    console.warn(`[Perf] 慢请求: ${args[0]} (${duration.toFixed(0)}ms)`)
  }
  return response
}

// 导出性能数据到后端
export async function reportPerformance() {
  const entries = performance.getEntriesByType('measure')
  if (entries.length > 0 && import.meta.env.PROD) {
    // 生产环境上报
    await fetch('/api/v1/telemetry/frontend-perf', {
      method: 'POST',
      body: JSON.stringify({
        measures: entries.map(e => ({
          name: e.name,
          duration: Math.round(e.duration),
        })),
        memory: (performance as any).memory?.usedJSHeapSize,
      }),
    })
    performance.clearMeasures()
  }
}

// 每30秒上报一次
setInterval(reportPerformance, 30000)
```

---

## 第二部分：AI 网文质量评估体系

### 2.1 昆仑现有质量评估体系全景

昆仑已有多层质量评估，但分散且缺乏统一评分标准：

| 层级 | 系统 | 维度数 | LLM | 输出 |
|------|------|:---:|:---:|------|
| Gacha 评分 | `engine.py` 9维 | 9 | ❌ 纯统计 | 9维分数 |
| 8道门禁 | `gates.py` | 8 | ❌ 纯规则 | PASS/FAIL |
| 33维审计 | `audit33.py` | 33 | ❌ 纯规则 | 6组分数 |
| 连载ICU | `icu.py` | 7 | ✅ LLM自动修复 | 7维分数 |
| 后写验证 | `post_write_validator.py` | 11 | ❌ 纯规则 | PASS/FAIL |
| AI特征 | `ai_features.py` | 36+ | ❌ 统计 | 特征向量 |
| 质量看板 | `quality/__init__.py` | 聚合 | — | 综合评分 |

### 2.2 统一质量评分标准：昆仑创作质量指数 (KCQI)

```python
# kunlun/quality/index.py（新建）
"""
昆仑创作质量指数 (Kunlun Creation Quality Index — KCQI)

对标行业标准:
- 起点中文网推荐评分 7.0+
- 番茄小说推荐流量 6.5+
- 飞卢爆款标准 7.5+

计算方式: 加权平均 (6大维度 × 对应权重)
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class KCQIReport:
    """统一质量报告"""
    book_id: str
    chapter: int
    
    # ─── 6大维度 (0-10分) ───
    readability: float = 0.0       # 可读性 (句式/节奏/段落)
    creativity: float = 0.0        # 创造性 (新颖度/反转/想象力)
    pleasure_density: float = 0.0  # 爽点密度 (频率/类型/递进)
    character_depth: float = 0.0   # 人物深度 (弧线/一致性/成长)
    coherence: float = 0.0         # 连贯性 (因果/伏笔/时空)
    anti_ai_score: float = 0.0     # 去AI味 (自然度/多样性/口语化)
    
    # ─── 综合评分 ───
    kcqi: float = 0.0              # 加权总分
    
    # ─── 元数据 ───
    weights: dict = field(default_factory=lambda: {
        "readability": 0.20,
        "creativity": 0.20,
        "pleasure_density": 0.25,   # 网文核心：爽点权重最高
        "character_depth": 0.15,
        "coherence": 0.10,
        "anti_ai_score": 0.10,
    })
    
    def compute_kcqi(self):
        """计算加权总分"""
        self.kcqi = (
            self.readability * self.weights["readability"]
            + self.creativity * self.weights["creativity"]
            + self.pleasure_density * self.weights["pleasure_density"]
            + self.character_depth * self.weights["character_depth"]
            + self.coherence * self.weights["coherence"]
            + self.anti_ai_score * self.weights["anti_ai_score"]
        )
        return round(self.kcqi, 1)
    
    def to_grade(self) -> str:
        """分数 → 等级"""
        if self.kcqi >= 8.0:
            return "S (爆款)"
        elif self.kcqi >= 7.0:
            return "A (优秀)"
        elif self.kcqi >= 6.0:
            return "B (合格)"
        elif self.kcqi >= 5.0:
            return "C (需改进)"
        else:
            return "D (不合格)"
    
    def to_radar(self) -> dict:
        """转为前端雷达图数据"""
        return {
            "可读性": self.readability,
            "创造性": self.creativity,
            "爽点密度": self.pleasure_density,
            "人物深度": self.character_depth,
            "连贯性": self.coherence,
            "去AI味": self.anti_ai_score,
        }


class KCQIEngine:
    """KCQI 计算引擎 — 聚合各审计系统的分数"""
    
    async def compute(
        self,
        book_id: str,
        chapter: int,
        draft: str = "",
        gacha_scores: Optional[dict] = None,
        audit_result: Optional[dict] = None,
        icu_result: Optional[dict] = None,
    ) -> KCQIReport:
        report = KCQIReport(book_id=book_id, chapter=chapter)
        
        # 1. 可读性 — 来自 Gacha 的 rhythm + style + dialogue 维度
        if gacha_scores:
            report.readability = (
                gacha_scores.get("rhythm", 5) * 0.4
                + gacha_scores.get("style", 5) * 0.3
                + gacha_scores.get("dialogue", 5) * 0.3
            ) / 10 * 10  # 归一化到 0-10
        
        # 2. 创造性 — 来自 Gacha 的 hook + information 维度
        if gacha_scores:
            report.creativity = (
                gacha_scores.get("hook", 5) * 0.5
                + gacha_scores.get("information", 5) * 0.5
            ) / 10 * 10
        
        # 3. 爽点密度 — 来自 pleasure 检测 + Gacha pleasure 维度
        if gacha_scores:
            report.pleasure_density = (
                gacha_scores.get("pleasure", 5) / 10 * 10
            )
        # 叠加 pleasure 检测结果
        try:
            from kunlun.pleasure import detect_pleasure_points
            pps = detect_pleasure_points(draft)
            pp_bonus = min(len(pps) / 3, 1.0)  # 每章3个爽点满分
            report.pleasure_density = min(report.pleasure_density + pp_bonus, 10)
        except Exception:
            pass
        
        # 4. 人物深度 — 来自 33维审计的 A组(角色) + Gacha character 维度
        if audit_result:
            char_score = audit_result.get("groups", {}).get("A", {}).get("score", 5)
            report.character_depth = char_score / 10 * 10
        if gacha_scores:
            report.character_depth = max(
                report.character_depth,
                gacha_scores.get("character", 5) / 10 * 10,
            )
        
        # 5. 连贯性 — 来自 8门禁 G1(弧线) + G7(对话) 通过率
        if audit_result:
            gates = audit_result.get("gates", {})
            passed = sum(1 for g in gates.values() if g.get("level") == "PASS")
            total = len(gates) or 1
            report.coherence = passed / total * 10
        
        # 6. 去AI味 — 来自 AI特征 + Gacha anti_ai + emotion 维度
        if gacha_scores:
            report.anti_ai_score = (
                gacha_scores.get("anti_ai", 5) * 0.5
                + gacha_scores.get("emotion", 5) * 0.5
            ) / 10 * 10
        
        report.compute_kcqi()
        return report


# 全局单例
kcqi_engine = KCQIEngine()
```

### 2.3 质量趋势追踪

```python
# 增强 quality/tracker.py
# 在现有跨章质量趋势基础上，增加 KCQI 趋势

async def get_kcqi_trend(book_id: str, last_n: int = 20) -> dict:
    """获取最近 N 章的 KCQI 趋势"""
    trend = []
    for ch in range(max(1, current_chapter - last_n), current_chapter + 1):
        report = await kcqi_engine.compute(book_id, ch)
        trend.append({
            "chapter": ch,
            "kcqi": report.kcqi,
            "grade": report.to_grade(),
        })
    
    # 趋势分析
    scores = [t["kcqi"] for t in trend]
    return {
        "trend": trend,
        "avg": sum(scores) / len(scores) if scores else 0,
        "min": min(scores) if scores else 0,
        "max": max(scores) if scores else 0,
        "improving": scores[-1] > scores[0] if len(scores) >= 2 else None,
        "volatility": max(scores) - min(scores) if scores else 0,  # 质量波动度
    }
```

### 2.4 平台适配评分

| 平台 | 核心指标 | 权重调整 | 及格线 |
|------|---------|---------|:---:|
| 番茄小说 | 爽点密度 + 可读性 | pleasure: 0.35, readability: 0.25 | 6.5 |
| 起点中文网 | 创造性 + 人物深度 | creativity: 0.30, character: 0.20 | 7.0 |
| 飞卢 | 爽点密度 + 去AI味 | pleasure: 0.35, anti_ai: 0.15 | 7.5 |
| 七猫 | 可读性 + 爽点密度 | readability: 0.30, pleasure: 0.25 | 6.0 |
| 通用 | 均衡 | 均等权重 | 6.0 |

### 2.5 质量评估 → 自动决策

```python
# kunlun/quality/auto_decision.py（新建）
"""
基于 KCQI 的自动决策引擎

决策规则:
- KCQI >= 7.5: 自动发布（跳过人工审核）
- KCQI 6.0-7.4: 标记为"建议发布"
- KCQI 5.0-5.9: 自动触发修订（增加1轮）
- KCQI < 5.0: 自动触发重写（不同模型/参数）
"""

class AutoDecisionEngine:
    
    async def decide(self, report: KCQIReport) -> dict:
        kcqi = report.kcqi
        
        if kcqi >= 7.5:
            return {
                "action": "auto_publish",
                "message": f"KCQI {kcqi} — 自动发布",
                "next_step": "publish",
            }
        elif kcqi >= 6.0:
            return {
                "action": "suggest_publish",
                "message": f"KCQI {kcqi} — 建议发布（请人工确认）",
                "next_step": "user_review",
            }
        elif kcqi >= 5.0:
            return {
                "action": "auto_revise",
                "message": f"KCQI {kcqi} — 自动修订（增加1轮）",
                "next_step": "revise",
                "revise_focus": self._identify_weakest_dimension(report),
            }
        else:
            return {
                "action": "auto_rewrite",
                "message": f"KCQI {kcqi} — 自动重写（切换模型/参数）",
                "next_step": "rewrite",
                "new_mode": "gacha_ultimate_5",  # 使用最强模式
            }
    
    def _identify_weakest_dimension(self, report: KCQIReport) -> str:
        dims = {
            "readability": report.readability,
            "creativity": report.creativity,
            "pleasure_density": report.pleasure_density,
            "character_depth": report.character_depth,
            "coherence": report.coherence,
            "anti_ai_score": report.anti_ai_score,
        }
        return min(dims, key=dims.get)
```

---

## 三、实施优先级

| 优先级 | 项目 | 工作量 | 收益 |
|:-----:|------|:---:|------|
| **P0** | Naive UI 深色/浅色主题切换 | 4h | 用户体验核心需求 |
| **P1** | KCQI 统一质量评分系统 | 6h | 质量评估标准化 |
| **P1** | Tauri 窗口管理 + 托盘 | 3h | 桌面端体验 |
| **P1** | 前端性能监控埋点 | 2h | 量化性能 |
| **P2** | Tauri IPC 桥接（本地操作加速） | 8h | 减少 HTTP 开销 |
| **P2** | 质量自动决策引擎 | 4h | 减少人工审核 |
| **P3** | PWA 离线支持 | 3h | 弱网体验 |
