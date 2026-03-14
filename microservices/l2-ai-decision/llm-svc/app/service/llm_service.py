"""
大模型统一调用服务
支持: OpenAI / Claude / 文心一言
提供统一接口，屏蔽底层差异
"""
import json
from typing import AsyncGenerator, Optional
from enum import Enum

from app.core.config import settings


class LLMProvider(str, Enum):
    OPENAI = "openai"
    CLAUDE = "claude"
    ERNIE = "ernie"


class LLMRequest:
    def __init__(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        provider: Optional[LLMProvider] = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
        stream: bool = False,
    ):
        self.prompt = prompt
        self.system_prompt = system_prompt or settings.SYSTEM_PROMPT
        self.provider = provider or LLMProvider(settings.DEFAULT_PROVIDER)
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.stream = stream


class LLMService:

    async def complete(self, request: LLMRequest) -> str:
        """同步调用大模型，返回完整响应"""
        if request.provider == LLMProvider.OPENAI:
            return await self._call_openai(request)
        elif request.provider == LLMProvider.CLAUDE:
            return await self._call_claude(request)
        elif request.provider == LLMProvider.ERNIE:
            return await self._call_ernie(request)
        raise ValueError(f"不支持的模型提供商: {request.provider}")

    async def stream_complete(self, request: LLMRequest) -> AsyncGenerator[str, None]:
        """流式调用大模型"""
        request.stream = True
        if request.provider == LLMProvider.OPENAI:
            async for chunk in self._stream_openai(request):
                yield chunk
        elif request.provider == LLMProvider.CLAUDE:
            async for chunk in self._stream_claude(request):
                yield chunk

    async def generate_purchase_report(
        self,
        user_type: str,
        brand_status: str,
        product_category: str,
        products_data: list,
        user_requirements: dict,
    ) -> str:
        """
        采购决策报告生成专用接口
        根据评分结果生成结构化分析报告
        """
        report_prompt = self._build_report_prompt(
            user_type, brand_status, product_category,
            products_data, user_requirements
        )
        req = LLMRequest(prompt=report_prompt, temperature=0.2, max_tokens=8192)
        return await self.complete(req)

    def _build_report_prompt(
        self, user_type, brand_status, category, products, requirements
    ) -> str:
        """构建采购报告生成提示词"""
        return f"""
请为以下采购需求生成专业的采购决策报告：

用户类型: {user_type}
品牌状态: {brand_status}
商品类别: {category}
采购需求: {json.dumps(requirements, ensure_ascii=False, indent=2)}

候选商品数据（已评分排序）:
{json.dumps(products[:5], ensure_ascii=False, indent=2)}

请按以下结构生成报告：
1. 需求摘要
2. 推荐商品（品质款 + 性价比款各一）
3. 详细对比分析
4. 风险提示
5. 采购建议
"""

    async def _call_openai(self, request: LLMRequest) -> str:
        """调用 OpenAI GPT"""
        try:
            import openai
            client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
            response = await client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": request.system_prompt},
                    {"role": "user", "content": request.prompt},
                ],
                temperature=request.temperature,
                max_tokens=request.max_tokens,
            )
            return response.choices[0].message.content
        except Exception as e:
            raise RuntimeError(f"OpenAI调用失败: {e}")

    async def _call_claude(self, request: LLMRequest) -> str:
        """调用 Anthropic Claude"""
        try:
            import anthropic
            client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
            response = await client.messages.create(
                model=settings.CLAUDE_MODEL,
                max_tokens=request.max_tokens,
                system=request.system_prompt,
                messages=[{"role": "user", "content": request.prompt}],
            )
            return response.content[0].text
        except Exception as e:
            raise RuntimeError(f"Claude调用失败: {e}")

    async def _call_ernie(self, request: LLMRequest) -> str:
        """调用 文心一言"""
        # 文心一言API对接（需先获取access_token）
        raise NotImplementedError("文心一言接口待实现")

    async def _stream_openai(self, request: LLMRequest) -> AsyncGenerator[str, None]:
        """OpenAI 流式输出"""
        import openai
        client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        stream = await client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": request.system_prompt},
                {"role": "user", "content": request.prompt},
            ],
            stream=True,
        )
        async for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    async def _stream_claude(self, request: LLMRequest) -> AsyncGenerator[str, None]:
        """Claude 流式输出"""
        import anthropic
        client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        async with client.messages.stream(
            model=settings.CLAUDE_MODEL,
            max_tokens=request.max_tokens,
            system=request.system_prompt,
            messages=[{"role": "user", "content": request.prompt}],
        ) as stream:
            async for text in stream.text_stream:
                yield text


llm_service = LLMService()
