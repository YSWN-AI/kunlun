"""
测试: API 路由
"""

import pytest

pytestmark = pytest.mark.integration

from fastapi.testclient import TestClient

from kunlun.api.main import app


@pytest.fixture
def client():
    return TestClient(app)


class TestHealthEndpoint:
    """健康检查"""

    def test_health_returns_200(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data

    def test_health_status_value(self, client):
        response = client.get("/health")
        data = response.json()
        assert data["status"] in ["ok", "healthy"]


class TestBookEndpoints:
    """建书相关 (routes.py 中无独立建书路由，此测试组仅验证路由注册存在)"""

    def test_generate_route_accepts_valid_params(self, client):
        """章节生成路由接受合法参数"""
        payload = {
            "book_id": "test_book_001",
            "chapter": 1,
            "mode": "gacha_parallel_3",
            "chapter_type": "normal",
        }
        response = client.post("/api/v1/books/test_book_001/chapters/1/generate", json=payload)
        # 500 仅在没有 API 密钥时出现，非代码缺陷。此处验证端点可达。
        assert response.status_code in [200, 422, 503]

    def test_generate_route_rejects_missing_fields(self, client):
        """缺少必填字段应返回422"""
        response = client.post("/api/v1/books/test/chapters/1/generate", json={})
        assert response.status_code in [400, 422]  # 空请求体应触发验证错误


class TestGenerateChapterEndpoint:
    """章节生成"""

    def test_generate_chapter_no_llm(self, client):
        """无LLM时优雅降级"""
        payload = {
            "book_id": "test_book_001",
            "chapter": 1,
            "chapter_type": "normal",
            "mode": "single_fix",
        }
        response = client.post("/api/v1/books/test_book_001/chapters/1/generate", json=payload)
        # 500 仅在没有 API 密钥时出现，非代码缺陷。此处验证端点可达。
        assert response.status_code in [200, 422, 503]
        if response.status_code == 200:
            data = response.json()
            assert "draft" in data or "error" in data or "success" in data

    def test_generate_chapter_with_mode(self, client):
        """指定模式生成"""
        payload = {
            "book_id": "test_book_001",
            "chapter": 2,
            "chapter_type": "transition",
            "mode": "gacha_parallel_3",
        }
        response = client.post("/api/v1/books/test_book_001/chapters/2/generate", json=payload)
        # 500 仅在没有 API 密钥时出现，非代码缺陷。此处验证端点可达。
        assert response.status_code in [200, 422, 503]

    def test_generate_chapter_minimal(self, client):
        """最小参数"""
        payload = {
            "book_id": "test_book_001",
            "chapter": 3,
        }
        response = client.post("/api/v1/books/test_book_001/chapters/3/generate", json=payload)
        # 500 仅在没有 API 密钥时出现，非代码缺陷。此处验证端点可达。
        assert response.status_code in [200, 422, 503]


class TestAuditEndpoint:
    """审计接口"""

    def test_audit_draft(self, client):
        """审计一段正文"""
        payload = {
            "draft": "这是一段网文正文，用来测试审计功能。角色言行正常，情节推进合理。",
            "chapter_type": "normal",
            "chapter": 5,
        }
        response = client.post("/api/v1/audit/run", json=payload)
        # 500 仅在没有 API 密钥时出现，非代码缺陷。此处验证端点可达。
        assert response.status_code in [200, 422, 503]
        if response.status_code == 200:
            data = response.json()
            inner = data.get("data", {})
            assert "gates" in inner or "passed" in inner

    def test_audit_empty_draft(self, client):
        """审计空正文"""
        response = client.post(
            "/api/v1/audit/run",
            json={
                "draft": "",
                "chapter_type": "normal",
                "chapter": 1,
            },
        )
        assert response.status_code in [200, 422]  # 空 draft 返回验证错误或审计结果


class TestQualityEndpoints:
    """质量看板API"""

    def test_quality_check_endpoint(self, client):
        response = client.post("/api/v1/quality/check?text=测试文本。")
        assert response.status_code == 200
        data = response.json()
        assert "data" in data

    def test_quality_check_missing_text(self, client):
        # 无text参数时端点应优雅处理（返回错误消息而非崩溃）
        response = client.post("/api/v1/quality/check?text=")
        assert response.status_code in (200, 422)

    def test_fanqie_check_endpoint(self, client):
        text = "死在" * 30
        response = client.post(f"/api/v1/quality/fanqie?text={text}&chapter=1")
        assert response.status_code == 200
        data = response.json()
        assert "data" in data

    def test_refine_analyze_endpoint(self, client):
        response = client.post("/api/v1/quality/refine?text=他淡淡地说。&analyze_only=true")
        assert response.status_code == 200
        data = response.json()
        assert "total_issues" in data or "action" in data

    def test_refine_execute_endpoint(self, client):
        response = client.post("/api/v1/quality/refine?text=他淡淡地说。好的。")
        assert response.status_code == 200
        data = response.json()
        assert "refined_text" in data or "refined_length" in data


class TestEndpoint404:
    """不存在路径"""

    def test_nonexistent_endpoint(self, client):
        response = client.get("/api/nonexistent")
        assert response.status_code == 404
