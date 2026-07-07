"""
本地 LLM Mock 服务器 — 模拟阿里云 DashScope OpenAI 兼容 SSE 流式响应

用途：压测时避免真实 API 调用，消除费用和限流风险，使结果可复现。
使用：uvicorn backend.tests.load.llm_mock:app --port 8001
"""

import asyncio
import json
import random
import time
import uuid
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional, List

app = FastAPI(title="LLM Mock Server", docs_url=None)

# ============ 可配置参数 ============
mock_config = {
    "first_token_delay": 0.5,       # 首 token 延迟（秒），模拟 TTFT
    "inter_token_delay": 0.03,      # token 间延迟（秒）
    "total_tokens_min": 80,         # 每个回答最少字符数
    "total_tokens_max": 300,        # 每个回答最多字符数
    "error_rate": 0.0,              # 模拟错误率（0.0-1.0）
    "slow_response_rate": 0.0,      # 模拟慢响应率（3x 延迟）
}

# ============ 电商回答模板池 ============
RESPONSE_TEMPLATES = [
    "感谢您的咨询！根据商品详情页的信息，这款产品的价格为299元，目前库存充足[来源1]。我们支持7天无理由退货，保修期为一年[来源2]。该产品采用优质材料制作，经过严格的质量检测，您可以放心购买。如果您还有其他问题，随时可以问我。",
    "关于物流配送方面，我们与多家快递公司合作（顺丰、圆通、中通等），一般下单后24小时内发货[来源1]。配送时间根据地区不同有所差异，一线城市通常1-2天到达，其他地区2-4天[来源2]。您可以登录账号实时查看物流信息。",
    "关于支付方式，我们支持支付宝、微信支付、银行卡、花呗等多种支付方式[来源1]。部分商品还支持货到付款服务。如果支付遇到问题，建议您检查网络连接或更换支付方式重试[来源2]。大额订单可能需要短信验证确认。",
    "关于退换货政策，我们提供7天无理由退货服务（需保证商品完好不影响二次销售）[来源1]。如果收到商品有质量问题，请在签收后24小时内联系客服，我们会在48小时内处理[来源2]。退货运费由责任方承担：质量问题我们承担运费，非质量问题由买家承担。",
    "这款产品上市以来好评率高达98%，用户普遍反馈品质优良、性价比高[来源1]。与同类竞品相比，我们在材质选用、生产工艺和售后服务方面都有明显优势[来源2]。近期我们还有限时优惠活动，下单立减30元，可以考虑入手。",
    "这款产品有红色、蓝色和黑色三种颜色可选，尺码从S到XXL均有库存[来源1]。产品规格在详情页有详细标注，建议您对照自己的需求选择合适的尺码[来源2]。如果不确定选哪个颜色，黑色是百搭款，红色更显活力。",
    "关于发票问题，我们支持开具增值税普通发票和专用发票[来源1]。下单时在订单备注中注明发票信息即可。电子发票会在确认收货后1-3个工作日发送到您的邮箱[来源2]。如果需要纸质发票，请在下单时勾选并填写收件地址。",
    "非常感谢您的反馈！关于保修服务，全部商品均享受国家三包政策，主机保修一年，配件保修三个月[来源1]。在保修期内出现非人为损坏的故障，我们提供免费维修服务[来源2]。过保后也可以联系官方售后，收费标准透明。您可以通过客服热线或在线客服申请售后服务。",
    "这个产品目前库存充足，下单后一般24小时内即可发货[来源1]。热销款式偶尔会出现短暂缺货情况，通常会在3-5天内补货[来源2]。如果您急需使用，建议选择预计发货时间最早的店铺下单。可以关注商品页面上的库存提示。",
    "产品包装方面，我们使用加厚纸箱和防震材料，有效保护商品在运输过程中的安全[来源1]。外部有防水包装袋，下雨天也不会受潮。如果您收到的商品包装有破损，请先拍照留存再签收，然后联系客服处理[来源2]。",
    "关于使用教程，商品详情页有详细的图文介绍和视频教程[来源1]。产品附带纸质说明书（中英文双语），内容涵盖安装步骤、使用方法和注意事项[来源2]。如果说明书遗失，您可以在官网下载电子版。",
    "关于安全性，这款产品通过了国家3C认证，所有材料符合环保标准，无毒无害[来源1]。产品出厂前都经过了严格的质量检测和安全测试，确保用户使用安全[来源2]。孕妇和儿童在正常使用条件下不会受到任何影响。",
    "节假日期间我们通常会有大型促销活动，折扣力度比平时更大[来源1]。建议您关注店铺首页或订阅活动通知，第一时间获取优惠信息。另外新用户注册还可以领取专属优惠券[来源2]。",
    "关于以旧换新服务，我们目前支持部分品类参与该活动[来源1]。您可以将旧产品的型号告知客服，我们会评估折旧价格，新订单直接抵扣[来源2]。旧产品我们会统一进行环保回收处理。",
    "会员权益方面，普通会员享受积分累计和生日优惠；VIP会员还额外享受专属折扣、优先发货和专属客服[来源1]。积分可以在下次购物时抵扣现金，100积分抵1元[来源2]。您可以通过完成订单和参与活动获取积分。",
    "如果您想取消订单，请在订单状态为'待发货'时操作[来源1]。已发货的订单无法直接取消，但可以在收到货后申请退货退款[来源2]。取消订单的款项会在1-3个工作日内原路退回您的支付账户。",
    "这款产品的材质是优质304不锈钢，具有耐腐蚀、耐高温的特点[来源1]。外壳采用食品级塑料，通过了FDA认证，确保与食物接触的安全性[来源2]。产品重量约1.2kg，尺寸为25x15x10cm，便携实用。",
    "产品续航方面，内置5000mAh大容量电池，正常使用可续航8-10小时[来源1]。充电时间约为2小时充满（支持快充），Type-C充电接口兼容市面上的主流充电器[来源2]。电池健康度经过500次充放电测试仍保持在80%以上。",
    "我们与顺丰、京东物流建立了长期合作关系，配送速度有保障[来源1]。偏远地区（如西藏、新疆、内蒙古）也能送达，但配送时间会比普通地区延长2-4天[来源2]。具体运费会在下单页面根据收货地址自动计算，满99元包邮。",
    "建议您收到商品后第一时间检查外包装是否完好，然后根据说明书进行安装和首次使用设置[来源1]。如果在安装过程中遇到问题，可以扫码包装上的二维码观看安装视频教程[来源2]。首次使用前建议充满电以获得最佳电池寿命。",
    "我们提供3年质保服务，远超行业平均水平[来源1]。第一年为全免费保修，第二、三年收取配件成本费，免人工费[来源2]。过保维修价格透明，可以在官网查询各项配件的维修费用标准。",
    "新手使用建议先从基本功能开始熟悉，逐步探索高级功能[来源1]。产品操作界面简洁直观，大部分功能都能在3步以内完成[来源2]。如果长辈使用，可以开启简易模式，字体和按钮都会变大，更容易操作。",
    "关于产品认证，我们持有ISO9001质量管理体系认证、ISO14001环境管理体系认证以及CE、RoHS国际认证[来源1]。每年还会接受第三方检测机构的抽检，检测结果在官网公示[来源2]。产品质量信誉有保障。",
    "如果您需要特定时间配送，可以在下单时备注'工作日配送'或'周末配送'[来源1]。部分城市支持夜间配送（18:00-21:00），请在结算页面选择配送时段[来源2]。重要节假日可能会有配送延迟，建议提前下单。",
    "套装商品支持单品退货，但退款的金额会按单品售价计算而非套装折扣价[来源1]。退货时请将所需保留的商品也一并寄回（我们将重新发货保留商品），运费由我们承担[来源2]。也可以选择整个套装退货后，重新下单购买需要的单品。",
]

# ============ Pydantic Models ============


class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    model: str = "qwen-plus"
    messages: List[Message]
    stream: bool = False
    temperature: Optional[float] = 0.1
    max_tokens: Optional[int] = None


# ============ SSE 流式响应生成 ============


def _create_chunk(content: str, index: int, total: int) -> dict:
    """构造 OpenAI 兼容的 SSE chunk"""
    return {
        "id": f"chatcmpl-{uuid.uuid4().hex[:8]}",
        "object": "chat.completion.chunk",
        "created": int(time.time()),
        "model": "qwen-plus",
        "choices": [{
            "index": 0,
            "delta": {"content": content},
            "finish_reason": "stop" if index >= total - 1 else None,
        }],
    }


async def _stream_response(request: ChatRequest):
    """生成 SSE 流式响应"""
    config = mock_config

    # 1. 模拟首 token 延迟（Time To First Token）
    delay = config["first_token_delay"]
    # 慢响应模式：3x 延迟
    if random.random() < config["slow_response_rate"]:
        delay *= 3
    await asyncio.sleep(delay)

    # 2. 模拟错误率
    if random.random() < config["error_rate"]:
        error_msg = config.get("error_message", "LLM 服务暂时不可用")
        yield f"data: {json.dumps({'type': 'error', 'message': error_msg})}\n\n"
        yield "data: [DONE]\n\n"
        return

    # 3. 随机选择回答模板
    template = random.choice(RESPONSE_TEMPLATES)
    # 限制长度在 min/max 范围内
    max_chars = random.randint(config["total_tokens_min"], config["total_tokens_max"])
    text = template[:max_chars]

    # 4. 按标点分句，模拟真实的 token 粒度
    # 中文字符逐字发送，英文单词整体发送
    sentences = _split_by_sentence(text)
    total_sentences = len(sentences)

    for i, sentence in enumerate(sentences):
        # 逐句发送
        chunk = _create_chunk(sentence, i, total_sentences)
        yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
        if i < total_sentences - 1:
            await asyncio.sleep(config["inter_token_delay"])

    # 5. 发送结束标记
    yield "data: [DONE]\n\n"


def _split_by_sentence(text: str) -> list:
    """按标点分句，保持句子完整性"""
    result = []
    current = ""
    for char in text:
        current += char
        if char in "。！？；\n！!?":
            result.append(current)
            current = ""
    if current:
        result.append(current)
    return result if result else [text]


def _create_non_stream_response(request: ChatRequest) -> dict:
    """构造非流式响应"""
    template = random.choice(RESPONSE_TEMPLATES)
    return {
        "id": f"chatcmpl-{uuid.uuid4().hex[:8]}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": request.model,
        "choices": [{
            "index": 0,
            "message": {
                "role": "assistant",
                "content": template[:200],
            },
            "finish_reason": "stop",
        }],
        "usage": {
            "prompt_tokens": 120,
            "completion_tokens": len(template[:200]),
            "total_tokens": 120 + len(template[:200]),
        },
    }


# ============ API 端点 ============


@app.get("/health")
async def health():
    return {"status": "ok", "service": "llm-mock"}


@app.get("/v1/models")
async def list_models():
    return {
        "object": "list",
        "data": [
            {"id": "qwen-plus", "object": "model", "created": 1700000000, "owned_by": "mock"},
            {"id": "qwen-turbo", "object": "model", "created": 1700000000, "owned_by": "mock"},
        ],
    }


@app.post("/v1/chat/completions")
async def chat_completions(request: ChatRequest):
    if request.stream:
        return StreamingResponse(
            _stream_response(request),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    # 非流式
    delay = mock_config["first_token_delay"]
    await asyncio.sleep(delay)
    return JSONResponse(_create_non_stream_response(request))


@app.get("/mock/config")
async def get_config():
    return mock_config


@app.post("/mock/config")
async def update_config(request: Request):
    """运行时调参：可动态调整延迟、token 数、错误率"""
    body = await request.json()
    updatable = {"first_token_delay", "inter_token_delay",
                  "total_tokens_min", "total_tokens_max",
                  "error_rate", "slow_response_rate"}
    for key in updatable:
        if key in body:
            mock_config[key] = body[key]
    return {"status": "ok", "config": mock_config}


@app.get("/mock/status")
async def status():
    return {
        "config": mock_config,
        "templates_count": len(RESPONSE_TEMPLATES),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8001, log_level="info")
