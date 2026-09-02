# 昆仑引擎 API 参考文档

## 基础信息

- **Base URL**: `http://localhost:8000`
- **API版本**: v1
- **认证**: 无需认证（本地部署）

## 健康检查

### GET /health

检查服务状态。

**响应示例**：
```json
{
  "status": "healthy",
  "version": "0.1.0-alpha",
  "components": {
    "database": "connected",
    "llm": "available",
    "kg": "connected"
  }
}
```

## 书籍管理

### POST /api/v1/books/{book_id}/chapters/{chapter}/generate

生成章节内容。

**路径参数**：
| 参数 | 类型 | 说明 |
|------|------|------|
| book_id | string | 书籍ID |
| chapter | integer | 章节号 |

**请求体**：
```json
{
  "intent": "主角在昆仑山巅觉醒异能",
  "genre": "玄幻",
  "target_words": 3000,
  "temperature": 0.7
}
```

**响应示例**：
```json
{
  "success": true,
  "chapter": 1,
  "title": "第一章：觉醒",
  "content": "暮色笼罩下的昆仑山巅...",
  "word_count": 3280,
  "audit_result": {
    "passed": true,
    "score": 92,
    "issues": []
  }
}
```

## 审计系统

### POST /api/v1/audit/run

执行章节审计。

**请求体**：
```json
{
  "chapter_content": "章节正文内容..."
}
```

**响应示例**：
```json
{
  "passed": true,
  "gates": {
    "G1_arc": true,
    "G2_info": true,
    "G3_deai": true,
    "G4_pleasure": true,
    "G5_diversity": true,
    "G6_emotion": true,
    "G7_dialogue": true,
    "G8_battle": true
  },
  "dimensions": {
    "character": [6, 6],
    "plot": [6, 5],
    "logic": [6, 5],
    "emotion": [5, 4],
    "ai_marker": [5, 5]
  },
  "issues": [
    {
      "type": "warning",
      "dimension": "G3_deai",
      "message": "建议替换第3段的AI常用句式"
    }
  ]
}
```

## 知识图谱

### GET /api/v1/kg/query

查询知识图谱。

**查询参数**：
| 参数 | 说明 |
|------|------|
| cypher | Cypher查询语句 |
| type | 实体类型（人物/地点/物品等） |

**响应示例**：
```json
{
  "entities": [
    {
      "id": "entity_001",
      "type": "人物",
      "name": "叶青云",
      "properties": {
        "身份": "主角",
        "状态": "觉醒前期"
      }
    }
  ],
  "relationships": [
    {
      "source": "叶青云",
      "target": "昆仑派",
      "type": "弟子"
    }
  ]
}
```

### GET /api/v1/kg/foreshadowing/overdue

查询超期伏笔。

**响应示例**：
```json
{
  "overdue_items": [
    {
      "foreshadow": "玉佩发光",
      "first_mention": "第1章",
      "expected_resolution": "第5章",
      "days_overdue": 3
    }
  ]
}
```

## 全文搜索

### GET /api/v1/search

全文搜索。

**查询参数**：
| 参数 | 说明 |
|------|------|
| q | 搜索关键词 |
| book_id | 书籍ID（可选） |
| limit | 返回数量（默认10） |

**响应示例**：
```json
{
  "results": [
    {
      "chapter": 1,
      "snippet": "...暮色笼罩下的昆仑<em>山巅</em>...",
      "relevance": 0.95
    }
  ],
  "total": 1
}
```

## 统计信息

### GET /api/v1/books/{book_id}/stats

获取书籍统计。

**响应示例**：
```json
{
  "book_id": "昆仑变",
  "total_words": 128592,
  "total_chapters": 42,
  "completed_chapters": 38,
  "audit_pass_rate": 0.89,
  "writing_days": 15,
  "avg_words_per_day": 8573
}
```

## WebSocket 实时推送

### WS /api/v1/ws/{book_id}/{chapter}

实时获取写作进度。

**消息格式**：
```json
{
  "type": "progress",
  "stage": "writing",
  "progress": 0.68,
  "message": "正在生成第3段..."
}
```

## 错误码

| 错误码 | 说明 |
|--------|------|
| 1001 | 后端未连接 |
| 1002 | API Key未配置 |
| 2001 | 书籍不存在 |
| 2002 | 章节生成失败 |
| 3001 | 审计超时 |
| 4001 | 知识图谱查询失败 |
| 5001 | LLM API调用失败 |

## 速率限制

- 无速率限制（本地部署）
- 建议单次生成间隔5秒以上
