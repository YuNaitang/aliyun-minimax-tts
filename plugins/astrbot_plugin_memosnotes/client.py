"""
MemosNotes - Memos REST API 异步 HTTP 客户端

封装 Memos (https://usememos.com/) v1 REST API 的 5 个核心端点：
  - create_memo    POST /api/v1/memos
  - list_memos     GET  /api/v1/memos
  - get_memo       GET  /api/v1/memos/{id}
  - update_memo    PATCH /api/v1/memos/{id}
  - delete_memo    DELETE /api/v1/memos/{id}
"""
from typing import Optional
import httpx
from astrbot.api import logger


class MemosClient:
    """Memos REST API 客户端"""

    def __init__(self, base_url: str, token: str, timeout: int = 30):
        self._api_base = base_url.rstrip("/") + "/api/v1"
        self._headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        self._timeout = timeout
        self._client = httpx.AsyncClient(
            headers=self._headers, timeout=self._timeout
        )
        logger.info(f"MemosClient initialized: {self._api_base}")

    async def close(self):
        """关闭 HTTP 客户端（在 terminate 中调用）"""
        await self._client.aclose()

    # ------------------------------------------------------------------
    # 内部辅助
    # ------------------------------------------------------------------
    def _log_error(self, endpoint: str, e: Exception):
        logger.error(f"Memos API [{endpoint}] failed: {type(e).__name__}: {e}")

    # ------------------------------------------------------------------
    # API 方法
    # ------------------------------------------------------------------

    async def create_memo(
        self, content: str, visibility: str = "PRIVATE"
    ) -> Optional[dict]:
        """创建备忘录

        Args:
            content: 备忘录内容
            visibility: 可见性 PRIVATE | PROTECTED | PUBLIC

        Returns:
            memo dict 或 None（失败时）
        """
        endpoint = "POST /api/v1/memos"
        try:
            resp = await self._client.post(
                f"{self._api_base}/memos",
                json={"content": content, "visibility": visibility},
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            self._log_error(endpoint, e)
            return None

    async def list_memos(
        self,
        page_size: int = 10,
        page_token: str = "",
        filter_str: str = "",
    ) -> Optional[dict]:
        """列出备忘录

        Args:
            page_size: 每页数量（最大 1000）
            page_token: 分页令牌（从上次响应获取）
            filter_str: AIP-160 过滤语法，例如 `row_status == "NORMAL"`

        Returns:
            {"memos": [...], "nextPageToken": "..."} 或 None
        """
        endpoint = "GET /api/v1/memos"
        try:
            params = {"pageSize": min(max(page_size, 1), 1000)}
            if page_token:
                params["pageToken"] = page_token
            if filter_str:
                params["filter"] = filter_str
            resp = await self._client.get(
                f"{self._api_base}/memos", params=params
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            self._log_error(endpoint, e)
            return None

    async def get_memo(self, memo_id: int) -> Optional[dict]:
        """获取单条备忘录

        Args:
            memo_id: 备忘录 ID

        Returns:
            memo dict 或 None
        """
        endpoint = f"GET /api/v1/memos/{memo_id}"
        try:
            resp = await self._client.get(
                f"{self._api_base}/memos/{memo_id}"
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            self._log_error(endpoint, e)
            return None

    async def update_memo(
        self, memo_id: int, **fields
    ) -> Optional[dict]:
        """更新备忘录（PATCH，仅传需要更新的字段）

        支持字段: content, visibility, pinned, rowStatus, createdTs, resourceIdList
        不传的字段不会被修改。

        Args:
            memo_id: 备忘录 ID
            **fields: 要更新的字段

        Returns:
            更新后的 memo dict 或 None
        """
        endpoint = f"PATCH /api/v1/memos/{memo_id}"
        if not fields:
            logger.warning(f"Memos update_memo({memo_id}) called with no fields.")
            return None
        try:
            # updateMask 是逗号分隔的字段名列表
            update_mask = ",".join(fields.keys())
            resp = await self._client.patch(
                f"{self._api_base}/memos/{memo_id}",
                params={"updateMask": update_mask},
                json=fields,
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            self._log_error(endpoint, e)
            return None

    async def delete_memo(self, memo_id: int) -> bool:
        """删除（软删除）备忘录

        Args:
            memo_id: 备忘录 ID

        Returns:
            bool 是否成功
        """
        endpoint = f"DELETE /api/v1/memos/{memo_id}"
        try:
            resp = await self._client.delete(
                f"{self._api_base}/memos/{memo_id}"
            )
            resp.raise_for_status()
            return True
        except Exception as e:
            self._log_error(endpoint, e)
            return False
