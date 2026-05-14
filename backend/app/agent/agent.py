"""Agent factory — builds LangChain agent graph for legal consultation.

Uses LangChain's new ``create_agent`` (LangGraph-based) which handles the
tool-calling loop natively.  Supports both DeepSeek (OpenAI-compatible) and
Ollama providers.
"""

from typing import Any

from langchain.agents import create_agent
from langchain_core.language_models import BaseLanguageModel
from langchain_core.tools import BaseTool
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
from langchain_core.messages import AIMessageChunk
from langchain_core.outputs import ChatGenerationChunk

from app.agent.config import get_llm_config


class _DeepSeekChatOpenAI(ChatOpenAI):
    """Subclass of ChatOpenAI that captures ``reasoning_content`` from
    DeepSeek R1 streaming responses and passes it through ``additional_kwargs``."""

    def _convert_chunk_to_generation_chunk(
        self,
        chunk: dict,
        default_chunk_class: type,
        base_generation_info: dict | None,
    ) -> ChatGenerationChunk | None:
        gen = super()._convert_chunk_to_generation_chunk(chunk, default_chunk_class, base_generation_info)
        if gen is not None and isinstance(gen.message, AIMessageChunk):
            choices = chunk.get("choices", [])
            if choices:
                delta = choices[0].get("delta", {})
                reasoning = delta.get("reasoning_content") or ""
                if reasoning:
                    gen.message.additional_kwargs["reasoning_content"] = reasoning
        return gen

DEFAULT_SYSTEM_PROMPT = (
    "## 角色\n"
    "你是一位严谨的中国法律咨询助手。你的唯一知识来源是 search_knowledge_base 工具的检索结果。\n\n"
    "## 核心规则\n"
    "1. 接到用户问题后，**必须首先调用 search_knowledge_base 检索相关法律法规**，绝不能跳过检索直接回答。\n"
    "2. 严格依据检索结果回答，**严禁使用自身知识编造法条、案例或解释**。\n"
    "3. 若检索结果为空，如实告知用户「知识库中未找到相关内容，建议咨询执业律师」，不得自行发挥。\n"
    "4. 若检索结果不足以完整回答，仅回答有依据的部分，对无依据的部分明确说明「此部分暂无相关法律依据」。\n\n"
    "## 回答格式\n"
    "1. 引用法律时注明全称和具体条款，如《中华人民共和国劳动合同法》第四十七条。\n"
    "2. 先给出结论，再引用法条，最后结合用户具体情况分析。\n"
    "3. 使用清晰的分段结构，避免大段文字堆砌。\n\n"
    "## 工具调用规则\n"
    "1. 知识库检索完成、获得足够信息后，**必须立即给出最终答案**，不得重复调用工具。\n"
    "2. 如果某工具返回了结果，基于这些结果直接回答，不要再尝试换参数换 URL 重新调用。\n"
    "3. 如果某工具返回错误或超时，告知用户该信息来源不可用，用已有知识回答，不要反复重试。\n"
    "4. 全轮回答中最多调用3次工具。\n\n"
    "## 行为边界\n"
    "1. 不提供诉讼策略或具体维权方案，仅解释法律规定。\n"
    "2. 不预测案件结果，不承诺赔偿金额。\n"
    "3. 涉及程序性事项（如管辖法院、诉讼时效等）以检索结果为准。\n"
    "4. 遇到明显超出法律范围的请求（如要求起草合同等），礼貌引导用户提出法律咨询类问题。\n\n"
    "## 免责声明\n"
    "每次回答末尾必须附带：以上内容仅供参考，不构成法律意见。如有具体法律问题，请咨询执业律师。"
)


def _build_llm() -> BaseLanguageModel:
    """Construct the LLM based on current config."""
    cfg = get_llm_config()
    provider = cfg.get("provider", "ollama")

    if provider == "deepseek":
        api_key = cfg.get("deepseek_api_key", "")
        if not api_key:
            raise RuntimeError("DeepSeek API key not configured. Set it in Settings → Model Provider.")
        return _DeepSeekChatOpenAI(
            model=cfg.get("deepseek_model", "deepseek-chat"),
            api_key=api_key,
            base_url=cfg.get("deepseek_api_base", "https://api.deepseek.com"),
            temperature=0.1,
        )

    if provider == "llamacpp":
        return ChatOpenAI(
            model=cfg.get("llamacpp_model", "qwen2.5-3b-instruct-q4_k_m.gguf"),
            api_key="not-needed",
            base_url=cfg.get("llamacpp_base_url", "http://127.0.0.1:11435") + "/v1",
            temperature=0.1,
        )

    return ChatOllama(
        model=cfg.get("ollama_model", "qwen2:7b-instruct"),
        base_url=cfg.get("ollama_base_url", "http://localhost:11434"),
        temperature=0.1,
    )


def build_agent(
    tools: list[BaseTool],
    system_prompt: str | None = None,
) -> "CompiledStateGraph":
    """Build a LangChain agent graph with the given tools and prompt.

    The returned ``CompiledStateGraph`` handles the full tool-calling loop
    natively.  Input / output format::

        inputs = {"messages": [HumanMessage(content="..."), ...]}
        result = await agent.ainvoke(inputs)
        answer = result["messages"][-1].content

    For token-level streaming::

        async for event in agent.astream_events(inputs, version="v2"):
            ...

    Args:
        tools: Full tool list the agent can use.
        system_prompt: Override the default system prompt.

    Returns:
        A compiled ``StateGraph`` (LangGraph-based agent executor).
    """
    llm = _build_llm()
    agent = create_agent(
        llm,
        tools=tools,
        system_prompt=system_prompt or DEFAULT_SYSTEM_PROMPT,
    )
    # Limit tool-calling loop: 9999 (default) causes repeated tool calls
    # without producing a final answer. 25 allows ~8-10 tool invocations.
    config = {"recursion_limit": 25}
    return agent.with_config(config)
