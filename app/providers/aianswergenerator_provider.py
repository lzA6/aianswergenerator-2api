# aianswergenerator-2api/app/providers/aianswergenerator_provider.py
import httpx
import json
import time
import uuid
import asyncio
import urllib.parse
from typing import Dict, Any, AsyncGenerator

from fastapi import HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from loguru import logger

from app.core.config import settings
from app.providers.base_provider import BaseProvider
from app.utils.sse_utils import create_sse_data, create_chat_completion_chunk, DONE_CHUNK

class AIAnswerGeneratorProvider(BaseProvider):
    BASE_URL = "https://text.pollinations.ai"

    def __init__(self):
        self.client = httpx.AsyncClient(timeout=settings.API_REQUEST_TIMEOUT)

    async def chat_completion(self, request_data: Dict[str, Any]) -> StreamingResponse:
        
        async def stream_generator() -> AsyncGenerator[bytes, None]:
            request_id = f"chatcmpl-{uuid.uuid4()}"
            model_name = request_data.get("model", settings.DEFAULT_MODEL)
            
            try:
                messages = request_data.get("messages", [])
                last_user_message = next((m['content'] for m in reversed(messages) if m.get('role') == 'user'), None)

                if not last_user_message:
                    raise HTTPException(status_code=400, detail="未找到用户消息。")

                encoded_prompt = urllib.parse.quote(last_user_message)
                upstream_url = f"{self.BASE_URL}/{encoded_prompt}"
                
                headers = self._prepare_headers()
                params = {"model": settings.UPSTREAM_MODEL_PARAM}

                logger.info(f"请求上游 URL: GET {upstream_url}")
                response = await self.client.get(upstream_url, headers=headers, params=params)
                response.raise_for_status()
                
                full_text = response.text
                logger.info(f"收到上游完整响应，长度: {len(full_text)} characters.")

                # --- 执行【模式：伪流式生成】 ---
                logger.info("开始执行伪流式生成...")
                for char in full_text:
                    chunk = create_chat_completion_chunk(request_id, model_name, char)
                    yield create_sse_data(chunk)
                    await asyncio.sleep(settings.PSEUDO_STREAM_DELAY)
                
                final_chunk = create_chat_completion_chunk(request_id, model_name, "", "stop")
                yield create_sse_data(final_chunk)
                yield DONE_CHUNK
                logger.success("伪流式生成完成。")

            except httpx.HTTPStatusError as e:
                logger.error(f"请求上游失败: {e.response.status_code} - {e.response.text}")
                error_message = f"上游服务错误: {e.response.status_code}"
                error_chunk = create_chat_completion_chunk(request_id, model_name, error_message, "stop")
                yield create_sse_data(error_chunk)
                yield DONE_CHUNK
            except Exception as e:
                logger.error(f"处理流时发生未知错误: {e}", exc_info=True)
                error_message = f"内部服务器错误: {str(e)}"
                error_chunk = create_chat_completion_chunk(request_id, model_name, error_message, "stop")
                yield create_sse_data(error_chunk)
                yield DONE_CHUNK

        return StreamingResponse(stream_generator(), media_type="text/event-stream")

    def _prepare_headers(self) -> Dict[str, str]:
        return {
            "Accept": "*/*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Origin": "https://aianswergenerator.pro",
            "Referer": "https://aianswergenerator.pro/",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        }

    async def get_models(self) -> JSONResponse:
        model_data = {
            "object": "list",
            "data": [
                {"id": name, "object": "model", "created": int(time.time()), "owned_by": "lzA6"}
                for name in settings.KNOWN_MODELS
            ]
        }
        return JSONResponse(content=model_data)
