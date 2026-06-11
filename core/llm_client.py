from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List
import base64
import json
import mimetypes
import os
import urllib.request
import urllib.error
from pathlib import Path
import re
import uuid

SYSTEM_INSTRUCTIONS = """
你是泌尿外科科研项目中的男性尿道鳞状细胞癌（SCC）病例问答与知识库检索助手。
任务：
1. 在同一段对话内保持上下文连续，优先使用本轮会话病例信息；
2. 不把其他对话的历史自动带入当前判断；
3. 先判断医生这次到底在问什么：若是具体知识、解释、数据库查询、项目操作或追问细节，直接回答该问题；不要强行套用“相似病例/治疗转归/手术用药讨论”模板。只有 mode=initial_patient_analysis，或医生明确要求“分析当前患者/讨论治疗/比较病例/给建议”时，才使用总体病例分析结构；
4. “相似病例与治疗转归”只列出有借鉴价值的相似病例及其治疗/转归要点，不要在这一部分做总括性建议；
5. “手术/用药讨论方向”不要机械逐个分析所有病例和文献；只挑最有借鉴价值的少数材料，综合说明可讨论路径。每条之间换行；
6. 只有首次选择患者后的总体分析需要参考病例与文献；之后医生问什么就答什么，不强制引用病例或文献，也不输出相关卡片，除非医生明确要求。
7. 对上传的影像/病理图片，只做可观察内容描述和待核对要点，不编造诊断；
8. 输出中文，直接、简洁、面向医生病例讨论场景；不要为了强调而使用红色标记或特殊标签；
9. 如果 related_articles 中有与当前问题高度相关的材料，要熟读摘要/正文要点后用中文转述为临床讨论建议，不照抄原文；具体链接由前端文献卡片展示。
10. 不要在普通回答中反复插入候选患者选择；候选患者只由前端在需要确认时显示。
11. 不要无视医生的具体提问而固定套用病例分析模板。
""".strip()


@dataclass(frozen=True)
class RequestPolicy:
    connect_timeout: float
    read_timeout: float
    write_timeout: float
    pool_timeout: float
    max_retries: int
    max_output_tokens: int
    stream: bool


def build_request_policy(provider: str, mode: str) -> RequestPolicy:
    provider_name = str(provider or "openai").strip().lower()
    mode_name = str(mode or "general").strip().lower()
    if mode_name == "connection_test":
        return RequestPolicy(8.0, 20.0, 15.0, 8.0, 0, 24, False)
    slower_compatible = {"deepseek", "openrouter", "fourrouter", "custom", "siliconflow", "volcengine"}
    return RequestPolicy(
        connect_timeout=10.0,
        read_timeout=90.0 if provider_name in slower_compatible else 75.0,
        write_timeout=30.0,
        pool_timeout=10.0,
        max_retries=0,
        max_output_tokens=900 if mode_name == "initial_patient_analysis" else 600,
        stream=provider_name != "anthropic",
    )



def _clean_answer_text(text: str) -> str:
    s = str(text or "")
    s = re.sub(r'^\s*(好的|好的呀|可以|当然可以)[，,。]?\s*(医生)?[：:，,。\s]*', '', s)
    lines = []
    for line in s.splitlines():
        t = line.strip()
        t = re.sub(r'^#{1,6}\s*', '', t)
        lines.append(t)
    out = []
    blank = False
    for line in lines:
        if not line:
            if not blank:
                out.append('')
            blank = True
        else:
            out.append(line)
            blank = False
    return "\n".join(out).strip()

def _case_line(case: Dict[str, Any], row: Dict[str, Any]) -> str:
    cid = str(case.get("case_id") or "未编号病例")
    diag = str(case.get("diagnosis") or "诊断未记录")
    sim = case.get("similarity")
    surgery = str(row.get("surgery") or case.get("surgery") or "未记录")
    other = str(row.get("other_treatment") or case.get("other_treatment") or "未记录")
    recurrence = str(row.get("recurrence") or case.get("recurrence") or "未记录")
    followup = str(row.get("followup") or case.get("followup") or "未记录")
    return f"{cid}｜相似度 {format_similarity_percent(sim)}｜{diag}｜手术：{surgery}｜其他治疗：{other}｜复发/转移：{recurrence}｜随访：{followup}"


def _case_discussion_line(case: Dict[str, Any], row: Dict[str, Any]) -> str:
    cid = str(case.get("case_id") or "未编号病例")
    ev = "；".join((case.get("evidence_summary") or [])[:2])
    surgery = str(row.get("surgery") or case.get("surgery") or "")
    other = str(row.get("other_treatment") or case.get("other_treatment") or "")
    recurrence = str(row.get("recurrence") or case.get("recurrence") or "")
    followup = str(row.get("followup") or case.get("followup") or "")
    treatment = "；".join([x for x in [f"手术记录为{surgery}" if surgery and surgery != "未记录" else "", f"其他治疗记录为{other}" if other and other != "未记录" else ""] if x])
    outcome = "；".join([x for x in [f"转归提示{recurrence}" if recurrence and recurrence != "未记录" else "", f"随访提示{followup}" if followup and followup != "未记录" else ""] if x])
    analysis = "；".join([x for x in [ev, treatment, outcome] if x]) or "与当前病例存在若干结构化字段相似。"
    return f"病例 {cid}：分析：{analysis}。建议：将其作为治疗路径对照，重点核对肿瘤部位、分期、病理分化、淋巴结状态和既往尿道/LS病史是否真正一致。"


def _article_discussion_line(article: Dict[str, Any]) -> str:
    title = str(article.get("title") or article.get("article_id") or "未命名文献")
    points = [str(x) for x in (article.get("value_points") or []) if str(x).strip()]
    terms = "、".join([str(x) for x in (article.get("hit_terms") or [])[:4]])
    if points:
        analysis = "；".join(points[:2])
    elif terms:
        analysis = f"与当前问题在{terms}等主题上相关。"
    else:
        analysis = "与当前问题存在一定关联，但需点开原文进一步核对适用范围。"
    return f"文献《{title}》：分析：{analysis}。建议：结合当前病例的分期、病理和既往治疗信息判断是否可借鉴，详细原文可通过下方文献卡片打开。"


def _is_initial_or_analysis_question(question: str, mode: str = "") -> bool:
    return mode in {"initial_patient_analysis", "explicit_retrieval"}

def local_fallback_reply(question: str, report: Dict[str, Any], mode: str = "") -> str:
    if not _is_initial_or_analysis_question(question, mode):
        q = (question or "").strip()
        # Local mode should still give a useful answer instead of repeating a fixed failure sentence.
        # It cannot perform open-ended model reasoning, but it can answer project/database questions
        # and guide the doctor to the next operation.
        if any(k in q for k in ["API", "api", "key", "模型", "连接", "后台"]):
            return "可以在左侧“API Key 配置”中选择供应商、模型并点击“保存并测试”。若要完全停用在线模型，请点击“清除”，新版会同时清除浏览器和后端保存的配置。"
        if any(k in q for k in ["病例", "数据库", "知识库", "保存", "删除"]):
            return "本地模式已连接病例知识库。你可以在“病例知识库”中查询、添加、删除病例；对话中上传病例文件后会先弹出候选患者供确认。若需要开放式医学推理，请配置可用 API。"
        if any(k in q for k in ["文章", "文献", "投喂"]):
            return "本地模式可以保存和检索已投喂文章。投喂 DOCX/PDF 时会提取正文；若文章含图片，只有配置可用多模态 API 后才能进一步分析图片内容。"
        if q:
            return "当前为本地兜底模式，无法进行开放式 AI 推理。已收到你的问题：“" + q[:180] + "”。请配置并测试可用 API 后，系统会直接调用后台模型回答该问题；若这是病例分析问题，也可以补充病例摘要后重新发送。"
        return "当前为本地兜底模式。请输入病例或问题；如需开放式智能问答，请先配置可用 API。"

    cases = report.get("similar_cases", [])[:4]
    treatment = report.get("treatment_outcomes") or {}
    rows = {r.get("case_id"): r for r in (treatment.get("similar_case_treatment_rows") or [])}
    articles = [a for a in (report.get("related_articles") or []) if not a.get("low_confidence")][:4]
    missing = (report.get("risk") or {}).get("missing_items", [])

    lines: List[str] = []
    if cases:
        lines.append("相似病例与治疗转归：")
        for c in cases:
            lines.append(_case_line(c, rows.get(c.get("case_id"), {})))
    else:
        lines.append("暂未检索到足够有借鉴价值的本地相似病例；可补充病理、分期、影像范围和既往尿道/LS病史后再匹配。")

    discussion_lines: List[str] = []
    # 只挑少数最有参考价值的病例/文献，不把所有材料都逐条展开。
    for c in cases[:2]:
        row = rows.get(c.get("case_id"), {})
        has_treatment_value = any(str(row.get(k) or c.get(k) or "").strip() and str(row.get(k) or c.get(k) or "").strip() != "未记录" for k in ["surgery", "other_treatment", "recurrence", "followup"])
        if has_treatment_value:
            discussion_lines.append(_case_discussion_line(c, row))
    for a in articles[:2]:
        discussion_lines.append(_article_discussion_line(a))

    if discussion_lines:
        lines.extend(["", "手术/用药讨论方向："])
        lines.extend(discussion_lines[:4])

    if missing:
        lines.extend(["", "当前病例信息还可补充：" + "、".join(missing)])

    if any(word in question for word in ["图片", "病理图", "影像", "jpg", "切片"]):
        lines.extend([
            "",
            "图片分析：本地模式只保存图片文件。配置 OPENAI_API_KEY 后，系统会将当前对话上传的图片作为多模态输入，用于描述性分析和待核对要点整理。",
        ])

    return "\n".join(lines)

def _image_payloads(attachments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    base_dir = Path(__file__).resolve().parents[1]
    persistent_dir = Path(os.getenv("USCC_DATA_DIR", Path.home() / ".uscc_scc_flask_data"))
    upload_dirs = [persistent_dir / "uploads", base_dir / "uploads"]
    for item in attachments or []:
        if item.get("type") != "image":
            continue
        stored = str(item.get("stored_as") or "")
        if not stored:
            continue
        path = next((d / stored for d in upload_dirs if (d / stored).exists()), upload_dirs[0] / stored)
        if not path.exists() or path.suffix.lower() == ".dcm":
            continue
        mime = mimetypes.guess_type(path.name)[0] or "image/jpeg"
        try:
            data = base64.b64encode(path.read_bytes()).decode("ascii")
            out.append({"type": "input_image", "image_url": f"data:{mime};base64,{data}"})
        except Exception:
            continue
    return out[:4]



def _plain_text_from_chat_completion(response: Any) -> str:
    try:
        return response.choices[0].message.content if response.choices else str(response)
    except Exception:
        return str(response)


def _plain_text_from_chat_stream(stream: Any) -> str:
    parts: List[str] = []
    for chunk in stream:
        try:
            delta = chunk.choices[0].delta.content
        except Exception:
            delta = None
        if isinstance(delta, str):
            parts.append(delta)
        elif isinstance(delta, list):
            for item in delta:
                if isinstance(item, dict) and item.get("text"):
                    parts.append(str(item["text"]))
                elif getattr(item, "text", None):
                    parts.append(str(item.text))
    return "".join(parts)


def _openai_client_kwargs(api_key: str, base_url: str, policy: RequestPolicy) -> Dict[str, Any]:
    import httpx

    kwargs: Dict[str, Any] = {
        "api_key": api_key,
        "timeout": httpx.Timeout(
            connect=policy.connect_timeout,
            read=policy.read_timeout,
            write=policy.write_timeout,
            pool=policy.pool_timeout,
        ),
        "max_retries": policy.max_retries,
    }
    if base_url:
        kwargs["base_url"] = base_url
    return kwargs


def _provider_defaults(provider: str, base_url: str = "") -> Dict[str, str]:
    provider_base_urls = {
        "openai": "",
        "deepseek": "https://api.deepseek.com",
        "dashscope": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "zhipu": "https://open.bigmodel.cn/api/paas/v4",
        "siliconflow": "https://api.siliconflow.cn/v1",
        "moonshot": "https://api.moonshot.cn/v1",
        "openrouter": "https://openrouter.ai/api/v1",
        "fourrouter": base_url,
        "volcengine": "https://ark.cn-beijing.volces.com/api/v3",
        "anthropic": "https://api.anthropic.com",
        "custom": base_url,
    }
    default_models = {
        "openai": "gpt-4.1-mini",
        "deepseek": "deepseek-chat",
        "dashscope": "qwen-plus",
        "zhipu": "glm-4-flash",
        "siliconflow": "Qwen/Qwen2.5-72B-Instruct",
        "moonshot": "moonshot-v1-8k",
        "openrouter": "openai/gpt-4o-mini",
        "fourrouter": "",
        "volcengine": "doubao-1-5-pro-32k",
        "anthropic": "claude-sonnet-4-6",
        "custom": "",
    }
    return {"base_url": provider_base_urls.get(provider, base_url), "model": default_models.get(provider, "gpt-4.1-mini")}


def _anthropic_content_blocks(text: str, attachments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    blocks: List[Dict[str, Any]] = [{"type": "text", "text": text}]
    base_dir = Path(__file__).resolve().parents[1]
    persistent_dir = Path(os.getenv("USCC_DATA_DIR", Path.home() / ".uscc_scc_flask_data"))
    upload_dirs = [persistent_dir / "uploads", base_dir / "uploads"]
    for item in attachments or []:
        if item.get("type") != "image":
            continue
        stored = str(item.get("stored_as") or "")
        if not stored:
            continue
        path = next((d / stored for d in upload_dirs if (d / stored).exists()), upload_dirs[0] / stored)
        if not path.exists() or path.suffix.lower() == ".dcm":
            continue
        mime = mimetypes.guess_type(path.name)[0] or "image/jpeg"
        if mime not in {"image/jpeg", "image/png", "image/gif", "image/webp"}:
            continue
        try:
            data = base64.b64encode(path.read_bytes()).decode("ascii")
            blocks.append({"type": "image", "source": {"type": "base64", "media_type": mime, "data": data}})
        except Exception:
            continue
    return blocks[:9]




def format_similarity_percent(value: Any) -> str:
    """Display internal 0-1-ish similarity score as a readable percentage."""
    try:
        v = float(value)
        if v <= 1.5:
            pct = v * 100.0
        else:
            pct = v
        pct = max(0.0, min(100.0, pct))
        return f"{pct:.0f}%"
    except Exception:
        return str(value or "未计算")


def _looks_like_html(text: Any) -> bool:
    t = str(text or "").lstrip().lower()
    return t.startswith("<!doctype html") or t.startswith("<html") or "<div id=\"root\"" in t or "<title>" in t[:500]


def _friendly_html_backend_message(provider: str, base_url: str) -> str:
    return (
        "后台返回的是网页 HTML，而不是模型回答。\n"
        "这通常说明 API 配置里的 Base URL 填成了平台网页地址或控制台地址，而不是 API 接口地址。\n"
        f"当前供应商：{provider or '未指定'}\n"
        f"当前 Base URL：{base_url or '空'}\n\n"
        "处理方法：\n"
        "1. 如果使用 OpenRouter，请选择 OpenRouter，Base URL 使用 https://openrouter.ai/api/v1。\n"
        "2. 如果使用 4Router/其他聚合平台，请在该平台文档里找到 OpenAI-compatible API Base URL，通常不是首页地址，而是以 /v1、/api/v1 或 /openai/v1 结尾的接口地址。\n"
        "3. 不要把浏览器中打开的登录页、控制台页或平台首页填到 Base URL。\n"
        "4. 修改后点击“保存并测试”，看到“连接成功”后再对话。"
    )


def _friendly_exception_message(exc: Exception, provider: str = "", base_url: str = "") -> str:
    raw = str(exc)
    low = raw.lower()
    if "<!doctype html" in low or "<html" in low or "text/html" in low:
        return _friendly_html_backend_message(provider, base_url)
    if "invalid_api_key" in low or "incorrect api key" in low or "invalid x-api-key" in low:
        return "API Key 鉴权失败：请确认供应商选择正确、Key 没有多复制空格/换行，并且没有把其他平台的 Key 填到当前供应商。"
    if "insufficient balance" in low or "402" in low:
        return "API Key 可被识别，但账户余额或项目额度不足。请检查该供应商后台的余额、额度、项目预算或计费设置。"
    return raw


def classify_provider_error(exc: Exception, provider: str = "", request_id: str = "", base_url: str = "") -> str:
    raw = str(exc or "")
    low = raw.lower()
    error_name = type(exc).__name__.lower()
    request_note = f" 请求 ID：{request_id}。" if request_id else ""
    if "timeout" in error_name or "timed out" in low or "timeout" in low:
        return (
            f"{provider or 'API'} 请求超时。供应商可能已经接收并处理了请求，因此不要立即重复发送，以免再次计费。"
            f"{request_note}可先到供应商后台按时间或请求记录核对，再决定是否重试。"
        )
    if "invalid_api_key" in low or "incorrect api key" in low or "invalid x-api-key" in low or "401" in low:
        return f"API Key 鉴权失败，请核对供应商、Key 和项目权限。{request_note}"
    if "insufficient balance" in low or "402" in low or "quota" in low or "billing" in low:
        return f"API 账户余额、额度或项目预算不足，请到供应商后台检查计费状态。{request_note}"
    if "connection" in error_name or "connection" in low or "connect" in low:
        return f"无法连接到 {provider or 'API'} 服务，请检查网络和 Base URL。{request_note}"
    friendly = _friendly_exception_message(exc, provider, base_url)
    return f"{friendly}{request_note}".strip()

def test_llm_connection(api_key: str, provider: str = "openai", model: str = "", base_url: str = "") -> Dict[str, Any]:
    """Actively contact the selected backend with a tiny request.

    This is used by the API settings panel so the user can distinguish:
    browser-saved config vs. a real successful provider connection.
    """
    provider = (provider or "openai").strip()
    api_key = (api_key or "").strip()
    base_url = (base_url or "").strip()
    defaults = _provider_defaults(provider, base_url)
    if not base_url:
        base_url = defaults["base_url"]
    model = (model or defaults["model"]).strip()
    if not api_key:
        return {"ok": False, "error": "未填写 API Key。"}
    if not model:
        return {"ok": False, "error": "未选择或填写模型名称。"}
    request_id = uuid.uuid4().hex
    policy = build_request_policy(provider, "connection_test")
    try:
        if provider == "anthropic":
            anth_base = (base_url or "https://api.anthropic.com").rstrip("/")
            payload = {"model": model, "max_tokens": policy.max_output_tokens, "messages": [{"role": "user", "content": "请只回复：连接成功"}]}
            req = urllib.request.Request(
                anth_base + "/v1/messages",
                data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                headers={"content-type": "application/json", "x-api-key": api_key, "anthropic-version": "2023-06-01"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=policy.read_timeout) as resp:
                obj = json.loads(resp.read().decode("utf-8"))
            return {"ok": True, "provider": provider, "model": model, "base_url": anth_base, "request_id": request_id, "raw_type": obj.get("type", "message")}
        from openai import OpenAI
        client = OpenAI(**_openai_client_kwargs(api_key, base_url, policy))
        if provider == "openai":
            resp = client.responses.create(model=model, input="请只回复：连接成功", max_output_tokens=policy.max_output_tokens)
            text = getattr(resp, "output_text", "") or str(resp)[:200]
        else:
            resp = client.chat.completions.create(model=model, messages=[{"role": "user", "content": "请只回复：连接成功"}], max_tokens=policy.max_output_tokens, temperature=0)
            text = _plain_text_from_chat_completion(resp)
        if _looks_like_html(text):
            return {"ok": False, "provider": provider, "model": model, "base_url": base_url, "error": _friendly_html_backend_message(provider, base_url)}
        return {"ok": True, "provider": provider, "model": model, "base_url": base_url, "request_id": request_id, "sample": text[:120]}
    except urllib.error.HTTPError as exc:
        body = ""
        try:
            body = exc.read().decode("utf-8", errors="ignore")[:1000]
        except Exception:
            pass
        err_text = f"HTTP {exc.code}: {body or exc.reason}"
        if _looks_like_html(body):
            err_text = _friendly_html_backend_message(provider, base_url)
        return {"ok": False, "provider": provider, "model": model, "base_url": base_url, "request_id": request_id, "error": err_text}
    except Exception as exc:
        return {"ok": False, "provider": provider, "model": model, "base_url": base_url, "request_id": request_id, "error": classify_provider_error(exc, provider, request_id, base_url)}

def ask_llm(
    question: str,
    report: Dict[str, Any],
    patient: Dict[str, Any],
    history: List[Dict[str, str]] | None = None,
    attachments: List[Dict[str, Any]] | None = None,
    api_key_override: str = "",
    model_override: str = "",
    mode_override: str = "",
    provider_override: str = "",
    base_url_override: str = "",
) -> Dict[str, Any]:
    api_key = (api_key_override or os.getenv("OPENAI_API_KEY", "")).strip()
    provider = (provider_override or os.getenv("LLM_PROVIDER", "openai")).strip() or "openai"
    base_url = (base_url_override or os.getenv("LLM_BASE_URL", "")).strip()
    defaults = _provider_defaults(provider, base_url)
    if not base_url:
        base_url = defaults.get("base_url", "")
    if not api_key:
        return {"provider": "local_fallback", "answer": _clean_answer_text(local_fallback_reply(question, report, mode_override))}

    request_id = uuid.uuid4().hex
    policy = build_request_policy(provider, mode_override or "general")
    try:
        from openai import OpenAI
        client = OpenAI(**_openai_client_kwargs(api_key, base_url, policy))
        model = (model_override or os.getenv("OPENAI_MODEL", "") or defaults.get("model", "gpt-4.1-mini")).strip()
        if not model:
            raise ValueError("请在 API 配置中选择或填写模型名称。")
        context = {
            "user_question": question,
            "conversation_mode": mode_override or "normal_followup",
            "current_conversation_history": (history or [])[-8:],
            "patient_input_current_chat_only": patient,
            "similar_cases_selected": report.get("similar_cases", [])[:4],
            "related_articles_selected": report.get("related_articles", [])[:4],
            "candidate_matches": [],
            "treatment_outcomes_from_similar_cases": report.get("treatment_outcomes", {}),
            "missing_items": (report.get("risk") or {}).get("missing_items", []),
            "knowledge_base_digest_for_fast_recall": report.get("knowledge_digest", {}),
            "attachments": attachments or [],
        }
        context_text = json.dumps(context, ensure_ascii=False)
        if provider == "anthropic":
            # Native Anthropic Messages API. This supports Claude/Claude Code
            # model aliases such as claude-opus-4-7 and claude-sonnet-4-6.
            anth_base = (base_url or "https://api.anthropic.com").rstrip("/")
            payload = {
                "model": model,
                "max_tokens": policy.max_output_tokens,
                "temperature": 0.15,
                "system": SYSTEM_INSTRUCTIONS,
                "messages": [{"role": "user", "content": _anthropic_content_blocks(context_text, attachments or [])}],
            }
            req = urllib.request.Request(
                anth_base + "/v1/messages",
                data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                headers={
                    "content-type": "application/json",
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=policy.read_timeout) as resp:
                obj = json.loads(resp.read().decode("utf-8"))
            parts = []
            for block in obj.get("content", []):
                if isinstance(block, dict) and block.get("type") == "text":
                    parts.append(str(block.get("text") or ""))
            answer = "\n".join([x for x in parts if x.strip()]) or json.dumps(obj, ensure_ascii=False)
        elif provider == "openai":
            content: List[Dict[str, Any]] = [
                {"type": "input_text", "text": context_text}
            ]
            content.extend(_image_payloads(attachments or []))
            with client.responses.stream(
                model=model,
                instructions=SYSTEM_INSTRUCTIONS,
                input=[{"role": "user", "content": content}],
                temperature=0.15,
                max_output_tokens=policy.max_output_tokens,
            ) as stream:
                response = stream.get_final_response()
            answer = getattr(response, "output_text", None) or str(response)
        else:
            # Most third-party "OpenAI-compatible" services support Chat Completions
            # rather than the newer Responses API. Use Chat Completions for broad compatibility.
            img_parts = _image_payloads(attachments or [])
            if img_parts:
                user_content = [{"type": "text", "text": context_text}]
                # Chat Completions vision format used by most OpenAI-compatible providers.
                for img in img_parts:
                    user_content.append({"type": "image_url", "image_url": {"url": img.get("image_url", "")}})
            else:
                user_content = context_text
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": SYSTEM_INSTRUCTIONS},
                    {"role": "user", "content": user_content},
                ],
                temperature=0.15,
                max_tokens=policy.max_output_tokens,
                stream=policy.stream,
            )
            answer = _plain_text_from_chat_stream(response) if policy.stream else _plain_text_from_chat_completion(response)
        if _looks_like_html(answer):
            return {"provider": "api_config_error", "base_url": base_url, "model": model, "request_id": request_id, "error": "backend_returned_html", "answer": _clean_answer_text(_friendly_html_backend_message(provider, base_url))}
        return {"provider": provider, "base_url": base_url, "model": model, "request_id": request_id, "answer": _clean_answer_text(answer)}
    except Exception as exc:
        error_message = classify_provider_error(exc, provider, request_id, base_url)
        return {
            "provider": "local_fallback_after_api_error",
            "request_id": request_id,
            "error": error_message,
            "answer": _clean_answer_text(error_message + "\n\n" + local_fallback_reply(question, report, mode_override)),
        }
