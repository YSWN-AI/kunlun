# 02 Agent 与管线

> 更新条件：新增/删除 Agent、管线步数变化、Agent 行数变动

## 11 个 Agent

| Agent | 文件 | 行数 | 角色 | 核心能力 |
|-------|------|:----:|------|---------|
| **VibeOrchestrator** ★ | `vibe_writer/orchestrator.py` | ~300 | 总调度 | Vibe Writing入口，一句话完成开书→创作→导出全流程 |
| **Makefile** | `agents/makefile.py` | 909 | 管线调度员 | 17步编排，sync/async双模式，自适应章节类型跳过 |
| **EditorInChief** | `agents/editor.py` | 682 | 主编 | 对话式交互，LLM意图分类(8类)，控制文档联动 |
| **Scheduler** | `agents/scheduler.py` | 362 | 集群调度 | 任务分解→并行编排→结果聚合，依赖解析+重试 |
| **Architect** | `agents/architect.py` | 322 | 架构师 | LLM生成蓝图+ContextBudget分配，含冲突/氛围/爽点排布 |
| **Writer** | `agents/writer.py` | 310 | 写手 | Gacha多模型正文生成+Token预算控制+Vibe prompt注入，修订模式 |
| **Auditor** | `agents/auditor.py` | 191 | 审计员 | 委托层，调用33维审计或8门禁 |
| **Sociologist** | `agents/sociologist.py` | 474 | 社会学家 | 44维社会推演，4维+降维+蝴蝶效应 |
| **StyleEngineer** | `agents/style_engineer.py` | 13 | 风格师 | 包装层，委托 `style/engineer.py` + `style/vibe.py` |
| **ConflictEngine** ★ | `conflict/__init__.py` | ~300 | 冲突追踪 | 6冲突类型+6状态+10级张力+热力图+升级建议 |
| **Publisher** | `agents/publisher.py` | 312 | 发布员 | 多平台发布，定时发布，自动Git commit |

消息总线：`agents/message_bus.py` — NATS(首选) → MockNATS(降级) → InProcessBus

## 创作管线 (17步，六大驱动力全覆盖)

```
 0. KG 快照拍摄             ~0.1s   snapshot_manager.create_snapshot()
 1. Architect 蓝图(含冲突/氛围) ~10s  LLM+ContextBudget+冲突/爽点排布
 1.5 社会推演(可选)          ~30s    Sociologist.deduce_all() → 44维
 2. Writer Gacha 抽卡+Vibe  ~15s    Gacha+VibePrompt+TokenBudget
 3. 🔥 冲突追踪(新)           ~0.1s   ConflictManager张力更新+热力图
 4. 🎯 Vibe氛围追踪(新)       ~0.1s   VibeEngine氛围注册+过渡建议
 5. 后写验证(零LLM)          ~0.2s   PostWriteValidator 11条规则
 6. Auditor 审计             ~0.5s   auditor33.run_audit() / gates G1-G8
 7. 修订循环(×3)             ~45s    Writer._revise() + Auditor 重审
 8. 连载ICU检查               ~10s    icu_system.run_full_check()
 9. 质量看板(可执行结果)       ~0.2s   QualityDashboard + get_action()
10. StyleEngineer 润色       ~0.3s   连词替换+句首多样+段落节奏+精炼304规则
11. KG 更新                  ~0.5s   _run_kg_update() + PleasurePoint
12. 爽点追踪                  ~0.1s   PleasureEngine 12种检测
13. 真相文件同步              ~0.1s   TruthFileManager+Schema校验
14. 反射学习                  ~0.3s   Reflector.reflect()
```

用户也可通过 **Vibe Writing 总调度** 一句话完成全流程：
```
你: "我想写一本玄幻小说"
AI: 自动创建项目→构建世界观→设计角色→规划大纲→逐章创作→质量检查→导出
```
