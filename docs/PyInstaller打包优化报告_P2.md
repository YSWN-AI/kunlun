# PyInstaller 打包优化报告 (P2)

> 日期：2026-09-05
> 目标：exe 体积从 138MB 降至 80-100MB
> 实际结果：**248.3MB → 70.2MB（降幅 71.7%）**

---

## 一、体积对比

| 指标 | 优化前 | 优化后 | 变化 |
|------|--------|--------|------|
| exe 体积 (onefile) | 248.3 MB | **70.2 MB** | -178.1 MB (-71.7%) |
| UPX 压缩 | 未启用 | 已启用 (v5.2.1) | ✅ |
| data 目录打包 | 复制整个 data/ (~2.3GB) | 仅创建空目录结构 | ✅ |
| 排除模块数 | 0 (build_app.py) | 100+ | ✅ |

> 注：任务描述中体积为 138MB，实际测量为 248.3MB（onefile 模式）。优化后 70.2MB 优于 80-100MB 目标。

---

## 二、优化措施

### 1. UPX 压缩
- 下载 UPX 5.2.1 for Windows 到 `tools/upx/upx-5.2.1-win64/`
- 在 `build_app.py` 中自动探测 UPX 路径（项目目录 → PATH）
- 配置 `upx_exclude` 列表，排除 80+ 个不能被 UPX 压缩的系统 DLL：
  - VC++ 运行时：vcruntime140.dll, msvcp140.dll 等
  - Python DLL：python311.dll, python312.dll
  - Windows API 集：api-ms-win-*.dll
  - 系统核心 DLL：kernel32.dll, user32.dll, ntdll.dll 等
  - .NET 运行时：clr.dll, mscorlib.dll, System.*.dll
  - WebView2：WebView2Loader.dll

### 2. 排除无用库（100+ 模块）

#### ML / 深度学习框架（最大体积来源）
| 模块 | 排除理由 |
|------|----------|
| torch, torchvision, torchaudio | 仅 `finetune/` 模块使用，桌面端用外部 LLM API |
| transformers, tokenizers, safetensors | 仅 `finetune/` 模块使用 |
| sentence_transformers | `kg/embedder.py` 延迟导入，有 hash 向量降级 |
| huggingface_hub, hf_xet, datasets, pyarrow | HuggingFace 生态，非运行时必需 |
| peft, trl, accelerate, bitsandbytes, triton | 微调工具，非运行时必需 |
| nvidia, cuda, cudnn | CUDA 运行时（torch 附带） |
| modelscope, modelscope_hub | 魔搭社区，非运行时必需 |

#### 数据科学
| 模块 | 排除理由 |
|------|----------|
| scipy, scikit-learn, sklearn | 运行时不使用 |
| pandas | 运行时不使用 |
| matplotlib, seaborn, plotly | 运行时不使用 |
| sympy, mpmath, joblib, threadpoolctl | 数据科学依赖 |
| numba, llvmlite, numexpr | 性能库，非运行时必需 |

#### 测试 / 开发工具
| 模块 | 排除理由 |
|------|----------|
| pytest, _pytest, pytest_asyncio, pytest_cov | 测试框架 |
| hypothesis, coverage | 测试工具 |
| ruff, mypy, mypy_extensions, bandit | 代码质量工具 |
| black, isort, flake8 | 格式化工具 |
| pre_commit, identify, cfgv, virtualenv, distlib | 开发工具 |

#### 其他
| 模块 | 排除理由 |
|------|----------|
| PIL, cv2, imageio | 仅 desktop_app.py 系统托盘使用，非主流程 |
| tkinter, PyQt5, PySide2, wx | 未使用的 GUI 框架 |
| pymysql, psycopg2, cx_Oracle, pymongo | 未使用的数据库驱动 |
| django, flask, bottle, tornado, aiohttp | 未使用的 Web 框架 |
| IPython, jupyter, notebook | Jupyter 相关 |
| sphinx, docutils | 文档工具 |
| weasyprint, pydub, edge_tts, pystray | 可选功能（PDF导出/TTS/系统托盘） |
| opentelemetry, prometheus_* | 可观测性，非必需 |
| nats, pika, celery | 消息队列，非必需 |
| boto3, botocore, azure | 云 SDK，非必需 |

#### 保留的关键库
- **numpy**：`kg/embedder.py` 运行时使用 `np.zeros`/`np.random`/`np.linalg`
- **fastapi, uvicorn, starlette**：Web 框架核心
- **pydantic, pydantic_settings, pydantic_core**：数据校验
- **loguru**：日志
- **httpx, openai, anthropic**：LLM API 调用
- **jieba**：中文分词
- **sqlalchemy, alembic**：数据库
- **neo4j, redis, qdrant_client**：知识图谱/缓存/向量检索
- **pywebview, pythonnet, clr_loader**：桌面窗口
- **ebooklib, lxml, docx, Jinja2**：导出功能
- **slowapi, limits**：限流

### 3. 修复 data 目录打包问题（关键发现）
- **问题**：`build_app.py` 原逻辑复制整个 `data/` 目录（含 adapters 1.5GB + models 457MB + lora 307MB，共 ~2.3GB）
- **修复**：改为仅创建空的 data 子目录结构（40+ 目录），运行时由应用自动填充
- **影响**：这是体积从 248MB 降至 70MB 的最大单一因素

### 4. 前端构建优化
- `build_app.py` 新增：`frontend/dist` 已存在时跳过 `vite build`
- 避免因 npx/npm 不在 PATH 导致构建失败

---

## 三、更新的文件

| 文件 | 变更内容 |
|------|----------|
| `build_app.py` | 新增 UPX 探测、100+ 排除模块、upx_exclude DLL 列表、data 目录不复制、前端构建跳过逻辑 |
| `kunlun_desktop.spec` | upx=False→True、扩展排除列表、新增 upx_exclude、UPX 路径自动探测、补充 hidden_imports |
| `昆仑引擎.spec` | excludes=[]→全面排除列表、新增 upx_exclude、补充 hidden_imports、data 目录不打包、UPX 路径探测 |
| `tools/upx/upx-5.2.1-win64/upx.exe` | 新增 UPX 5.2.1 可执行文件 |

---

## 四、构建测试结果

### 构建过程
- PyInstaller 6.22.2 + Python 3.13.14 + Windows 11
- 构建时间：约 2 分钟（含 UPX 压缩）
- 构建状态：✅ 成功

### 运行时验证
| 测试项 | 结果 |
|--------|------|
| exe 启动 | ✅ 成功（进程正常运行） |
| HTTP 服务器 | ✅ 正常响应（GET / → 200 OK） |
| 模块导入 | ✅ 无 ImportError |
| uvicorn 启动 | ✅ 正常 |
| /health 端点 | ⚠️ 500（slowapi 已知 bug，非打包问题） |

> `/health` 的 500 错误源于 `slowapi` 中间件的 `AttributeError: 'AttributeError' object has no attribute 'detail'`，这是源代码中的预存 bug（`desktop.py` 通过设置 `RATE_LIMIT_PER_MINUTE=0` 规避，`launcher.py` 未设置）。与打包优化无关。

### UPX 压缩警告
- 部分 `.pyd` 和 `.dll` 文件 UPX 无法压缩（如 `_ssl.pyd`, `python313.dll`, `numpy.libs/*`），自动跳过，不影响功能
- 所有警告均为良性

---

## 五、注意事项

1. **杀毒软件误报**：UPX 压缩的 exe 可能被某些杀毒软件误报为病毒，这是 UPX 的已知问题。如遇误报，可将 exe 添加白名单或禁用 UPX。
2. **微调功能不可用**：排除 torch/transformers 后，`finetune/` 模块的本地微调功能不可用。桌面端使用外部 LLM API，不受影响。
3. **本地嵌入模型**：排除 sentence_transformers 后，`kg/embedder.py` 会自动降级为 hash 向量（确定性伪随机），语义搜索精度下降。如需精确语义搜索，需移除该排除项并安装模型。
4. **可选功能缺失**：PDF 导出(weasyprint)、TTS(edge_tts/pydub)、系统托盘(pystray/PIL) 等功能因依赖被排除而不可用。主流程不受影响。
5. **重新构建**：运行 `python build_app.py` 即可重新构建。如需强制重建前端，删除 `frontend/dist/` 目录。

---

## 六、后续优化建议

1. **onefile → onedir**：当前为 onefile 模式（启动时需解压到临时目录）。改用 onedir 模式（spec 文件已支持）可加快启动速度，但分发时需打包整个文件夹。
2. **移除冗余 kunlun 数据复制**：`build_app.py` 同时将 kunlun/ 作为 `--add-data` 复制，又通过 hidden_imports 编译进 PYZ。可移除 `--add-data kunlun` 以进一步减小体积。
3. **修复 slowapi bug**：在 launcher.py 中设置 `RATE_LIMIT_PER_MINUTE=0` 或修复 slowapi 中间件。
4. **UPX 启动时间**：UPX 压缩会增加约 0.5-1 秒启动时间（解压），如对启动速度敏感可权衡。
