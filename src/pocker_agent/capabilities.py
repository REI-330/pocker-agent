"""公开的玩法能力矩阵；它是产品边界的单一来源，不依赖模型描述。"""

CAPABILITIES = [
    {"id": "legacy", "title": "阶段式比大小", "status": "stable", "mechanisms": ["阶段动作", "最高牌/手牌数计分", "1-12人"]},
    {"id": "arithmetic", "title": "24点/四则算式", "status": "stable", "mechanisms": ["四张牌", "精确算式", "单人练习"]},
    {"id": "blackjack", "title": "无下注21点", "status": "stable", "mechanisms": ["玩家对庄家", "要牌/停牌", "暗牌"]},
    {"id": "shedding", "title": "接牌/疯狂八基础变体", "status": "stable", "mechanisms": ["同花色/点数", "万能牌", "2-4人"]},
    {"id": "generated_plugin", "title": "Agent代码生成玩法", "status": "experimental", "mechanisms": ["单局", "2-4人", "通用出牌/摸牌/弃牌/跳过"]},
    {"id": "multiplayer_network", "title": "多人联网房间", "status": "planned", "mechanisms": ["认证", "实时同步", "房间与并发"]},
    {"id": "betting", "title": "下注/筹码/边池", "status": "planned", "mechanisms": ["筹码", "下注轮", "边池"]},
    {"id": "combination_hands", "title": "组合牌型/叫牌/阵营", "status": "planned", "mechanisms": ["组合牌型", "叫牌", "阵营"]},
]


def capability_matrix():
    return {"version": "0.2", "capabilities": CAPABILITIES}
