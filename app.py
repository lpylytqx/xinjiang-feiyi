# -*- coding: utf-8 -*-
"""
基于AIGC的新疆非遗文化互动体验平台 —— Flask 后端

结构说明：
  1. feiyi_data           : 非遗项目内容（文字 / 图片 / 语音 / 演变时间线 / 标签 / 小知识）
  2. pattern_library      : 纹样素材库（详情页图组 + 生成器共用）
  3. style_info           : 生成器三种风格的特征说明
  4. instrument_knowledge : 冬不拉知识板块
  5. costume_elements     : 民族服饰元素图鉴
  6. 首页与生成器均使用 GET 传参，刷新页面不会重复提交表单

后续接入真实 AIGC 接口时，只需替换 generator() 中的取值逻辑，
页面模板与数据结构无需改动。
"""

import base64
import glob
import hashlib
import io
import os
import uuid
from datetime import datetime

import requests
from PIL import Image, ImageFilter

from flask import Flask, render_template, request, send_from_directory, jsonify

app = Flask(__name__)


# ==========================================================
# 非遗项目内容
#
# 名录年份依据：中国非物质文化遗产网（ihchina.cn）项目页
#   维吾尔族刺绣                 项目序号 855 / 编号 Ⅶ-79   → 2008 年第二批
#   新疆维吾尔族艾德莱斯绸织染技艺  项目序号 892 / 编号 Ⅷ-109  → 2008 年第二批
#   地毯织造技艺（维吾尔族地毯织造技艺）序号 893 / 编号 Ⅷ-110  → 2008 年第二批
#   哈萨克族冬不拉艺术            编号 Ⅱ-132                → 2008 年第二批
#   《玛纳斯》                    2006 年第一批，2009 年入选联合国名录
#
# 说明：各项目的「演变时间线」为依据公开资料所做的概括性梳理，
#       陈述以工艺与风格的演变脉络为主，不虚构具体事件。
# ==========================================================
feiyi_data = {
    "embroidery": {
        "name": "维吾尔族刺绣",
        "tags": ["挑花", "刺花", "扎花", "补花", "花帽刺绣", "花卉瓜果纹"],
        "intro": "维吾尔族刺绣是维吾尔族最具代表性的传统工艺之一，历史悠久，针法多样、题材丰富，多用于服饰、壁挂、枕套等生活用品。2008 年，维吾尔族刺绣列入第二批国家级非物质文化遗产名录。",
        "history": "维吾尔族刺绣植根于古代西域绿洲居民的服饰装饰传统，经丝绸之路与中原丝绣、中亚及波斯装饰艺术长期交融，逐步形成色彩浓艳、构图饱满的独特风格。",
        "craft": "主要针法有挑花、刺花、扎花、补花等，色彩鲜艳、对比强烈，纹样多为花卉、瓜果、几何图案。",
        "value": "体现了维吾尔族妇女的审美智慧和生活情趣，是研究西域民族文化的活态载体。",
        "region": "主要分布于新疆喀什、和田、阿克苏、吐鲁番等维吾尔族聚居地区。",
        "representative": "代表作品：花帽（朵帕）刺绣、壁挂刺绣、服饰领口与袖口刺绣。",
        "tip": "维吾尔族刺绣讲究「以针代笔」，一件作品里常把多种针法混着用——花瓣用挑花、花蕊用扎花，远看像画，近看全是针脚。绣品也常是姑娘出嫁时的陪嫁，针脚细不细，是长辈评判手艺的标准。",
        "img": "/static/images/embroidery.jpg",
        "audio": "/static/audio/embroidery.mp3",
        "timeline": [
            {"period": "早期", "desc": "西域绿洲居民在毛织物、皮革上进行刺绣装饰，形成最初的装饰传统。"},
            {"period": "汉唐时期", "desc": "丝绸之路畅通，与中原丝绣、中亚装饰艺术相互影响，花卉与几何纹样逐渐定型。"},
            {"period": "明清时期", "desc": "刺绣广泛应用于服饰、壁挂、枕套等日常用品，针法体系趋于成熟。"},
            {"period": "2008 年", "desc": "维吾尔族刺绣列入第二批国家级非物质文化遗产名录。"},
        ],
    },
    "dombra": {
        "name": "哈萨克族冬不拉艺术",
        "tags": ["两根弦", "松木琴身", "阿肯", "冬不拉奎依", "即兴弹唱", "草原音乐"],
        "intro": "冬不拉是哈萨克族传统弹拨乐器，琴身多用松木或桑木制作，传统形制以两根弦为主，音色清脆悠扬。阿肯（民间歌手）怀抱冬不拉即兴弹唱，是哈萨克族草原文化的标志性符号。",
        "history": "冬不拉与哈萨克族的草原游牧生活相伴而生，其曲目以「冬不拉奎依」的形式由阿肯世代口头传承，承载着民族的历史记忆与情感表达。",
        "craft": "琴杆修长，音箱多为梨形或勺形，用钢丝或羊肠弦，弹奏时音色清脆明亮。",
        "value": "2008 年，哈萨克族冬不拉艺术列入第二批国家级非物质文化遗产名录，是哈萨克族历史记忆和情感表达的重要载体。",
        "region": "主要流传于新疆伊犁哈萨克自治州、巴里坤哈萨克自治县等哈萨克族聚居区。",
        "representative": "代表作品：冬不拉曲《黑走马》广为流传，此外还有大量以草原、骏马、思乡为题材的传统冬不拉奎依。",
        "tip": "冬不拉只有两根弦，音域听起来不宽，但阿肯们靠左手按弦、右手弹拨的配合，能奏出骏马奔驰、流水潺潺的效果。哈萨克人把冬不拉曲称作「冬不拉奎依」，同一首曲子由不同的人弹，往往各有各的味道——这正是它讲究即兴的地方。",
        "img": "/static/images/dombra.jpg",
        "audio": "/static/audio/dombra.mp3",
        "timeline": [
            {"period": "早期", "desc": "与哈萨克族草原游牧生活相伴而生，用于伴奏史诗、民歌与即兴弹唱。"},
            {"period": "世代传承", "desc": "阿肯怀抱冬不拉即兴弹唱，曲目以「冬不拉奎依」形式口耳相传。"},
            {"period": "近现代", "desc": "形制趋于多样，以两根弦为主，音色清脆明亮，成为哈萨克族文化的标志性符号。"},
            {"period": "2008 年", "desc": "哈萨克族冬不拉艺术列入第二批国家级非物质文化遗产名录。"},
        ],
    },
    "atlas": {
        "name": "艾德莱斯绸织造技艺",
        "tags": ["扎经染色", "手工丝织", "和田洛浦", "布谷鸟的翅膀", "抽象纹样"],
        "intro": "艾德莱斯绸是维吾尔族传统手工丝织品，主要产于新疆和田、洛浦一带。图案抽象奔放，色彩浓艳绚丽，被誉为「布谷鸟的翅膀」，是维吾尔族女性制作裙装的上等面料。",
        "history": "艾德莱斯绸的织造技艺沿丝绸之路传承千百年，和田、洛浦一带是著名的艾德莱斯绸之乡，至今仍保留着手工扎经染色的古老工序。",
        "craft": "采用扎经染色法，先将经线扎结染色再上机织造，因此每匹绸的图案都独一无二、无法复制。",
        "value": "2008 年，新疆维吾尔族艾德莱斯绸织染技艺列入第二批国家级非物质文化遗产名录，是西域丝绸文化的活态传承。",
        "region": "主要产于新疆和田地区洛浦县、喀什等地，是南疆绿洲特有的传统丝织品。",
        "representative": "代表纹样：波浪纹、菱形纹、花卉纹，色彩以红、黄、蓝、黑为主。",
        "tip": "艾德莱斯绸的图案不是「印」上去的，而是在织之前就染在经线上——工人按设计把经线分段扎结、浸染，再解开上机织造。因为扎结的松紧、染液的渗透都难以完全一致，所以每一匹绸的花纹都是独一份，这也正是它最迷人的地方。",
        "img": "/static/images/atlas.jpg",
        "audio": "/static/audio/atlas.mp3",
        "timeline": [
            {"period": "汉唐时期", "desc": "丝绸之路南道开通，和田一带丝织业兴起，为艾德莱斯绸的形成提供条件。"},
            {"period": "工艺定型", "desc": "扎经染色工艺逐步定型：先扎结经线染色，再上机织造，图案随机而不可复制。"},
            {"period": "明清以后", "desc": "和田、洛浦成为艾德莱斯绸的主要产地，「布谷鸟的翅膀」之名广为流传。"},
            {"period": "2008 年", "desc": "新疆维吾尔族艾德莱斯绸织染技艺列入第二批国家级非物质文化遗产名录。"},
        ],
    },
    "carpet": {
        "name": "新疆地毯编织技艺",
        "tags": ["手工打结", "羊毛", "植物染色", "和田地毯", "中心团花纹"],
        "intro": "新疆地毯编织历史悠久，图案饱满繁密，色彩庄重典雅，用料考究。和田地毯是其中最负盛名的代表，被誉为「东方地毯的明珠」。",
        "history": "新疆地毯编织距今已有两千多年历史，民丰县尼雅遗址出土的东汉地毯，是新疆现存最早的地毯实物。",
        "craft": "手工打结编织，以羊毛为原料，采用天然植物染色，每平方米多达上百万个结扣。",
        "value": "2008 年，地毯织造技艺（维吾尔族地毯织造技艺）列入第二批国家级非物质文化遗产名录，集绘画、编织艺术于一体。",
        "region": "主要分布于新疆和田、喀什、阿克苏等地，以和田地毯最为著名。",
        "representative": "代表图案：以石榴花等花卉为主题的团花纹样，配以多层连续边框，构图讲究对称饱满。",
        "tip": "手工地毯的图案主要靠织工口传与记忆传承，一般没有完整图纸。同一张纹样由不同的人织，边角处理会有些许差别；行家一眼就能看出这是手工织的还是机器织的——这些细微的不整齐，恰恰是手工地毯的印记。",
        "img": "/static/images/carpet.jpg",
        "audio": "/static/audio/carpet.mp3",
        "timeline": [
            {"period": "东汉", "desc": "民丰县尼雅遗址出土地毯，是新疆现存最早的地毯实物，证明两千多年前已有成熟织造技艺。"},
            {"period": "汉唐时期", "desc": "经丝绸之路吸收中原与中亚织造技艺，逐步形成和田地毯的工艺体系。"},
            {"period": "明清时期", "desc": "和田地毯成为重要的贡品与贸易品，图案体系趋于成熟，形成「东方地毯的明珠」之美誉。"},
            {"period": "2008 年", "desc": "地毯织造技艺（维吾尔族地毯织造技艺）列入第二批国家级非物质文化遗产名录。"},
        ],
    },
    "manas": {
        "name": "玛纳斯史诗",
        "tags": ["柯尔克孜族", "玛纳斯奇", "口传史诗", "八部唱本", "库姆孜"],
        "intro": "《玛纳斯》是柯尔克孜族英雄史诗，长达二十三万余行，讲述玛纳斯家族八代人率领柯尔克孜人民反抗侵略、追求幸福的故事，与《格萨尔》《江格尔》并称中国三大英雄史诗。",
        "history": "《玛纳斯》大约产生于 9—10 世纪，千百年来由专门的「玛纳斯奇」（说唱艺人）口耳相传，内容不断丰富，涵盖柯尔克孜族的历史、风俗与信仰。",
        "craft": "没有文字脚本，全靠玛纳斯奇记忆和演唱，篇幅浩瀚，演唱时常伴随库姆孜琴伴奏。",
        "value": "2006 年列入第一批国家级非物质文化遗产名录，2009 年入选联合国教科文组织人类非物质文化遗产代表作名录。",
        "region": "主要流传于新疆克孜勒苏柯尔克孜自治州及特克斯、昭苏等柯尔克孜族聚居区。",
        "representative": "著名玛纳斯奇：居素甫·玛玛依，能完整演唱八部《玛纳斯》，被誉为「当代荷马」。",
        "tip": "《玛纳斯》没有写定的脚本，全靠玛纳斯奇记在脑子里。一位成熟的玛纳斯奇能连续演唱多日，同一段故事在不同场次的演唱中细节也会有变化——史诗就是在这种反复演唱里被不断锤炼、丰富起来的。",
        "img": "/static/images/manas.jpg",
        "audio": "/static/audio/manas.mp3",
        "timeline": [
            {"period": "9—10 世纪", "desc": "史诗在柯尔克孜族先民中产生，以口耳相传的方式流传。"},
            {"period": "千百年传唱", "desc": "由「玛纳斯奇」记忆并演唱，在世代传唱中不断锤炼、丰富。"},
            {"period": "近现代", "desc": "经记录整理，形成八部、二十三万余行的宏大唱本，被誉为柯尔克孜族的百科全书。"},
            {"period": "2006 年", "desc": "列入第一批国家级非物质文化遗产名录。"},
            {"period": "2009 年", "desc": "入选联合国教科文组织人类非物质文化遗产代表作名录。"},
        ],
    },
}

project_list = [
    {"key": "embroidery", "label": "维吾尔族刺绣", "icon": "🧵"},
    {"key": "dombra", "label": "冬不拉艺术", "icon": "🎵"},
    {"key": "atlas", "label": "艾德莱斯绸", "icon": "👘"},
    {"key": "carpet", "label": "新疆地毯", "icon": "🧶"},
    {"key": "manas", "label": "玛纳斯史诗", "icon": "📜"}
]


# ==========================================================
# 纹样素材库
# 既用于首页详情页的「相关纹样」图组，也用于纹样生成器。
# 生成器按关键词的哈希稳定取图：同一个词每次得到同一张纹样，
# 不同关键词大概率得到不同纹样。接入真实文生图接口后替换此处即可。
# ==========================================================
pattern_library = {
    "embroidery": [
        "/static/images/pattern_emb1.jpg",
        "/static/images/pattern_emb2.jpg",
        "/static/images/pattern_emb3.jpg",
    ],
    "carpet": [
        "/static/images/pattern_carp1.jpg",
        "/static/images/pattern_carp2.jpg",
    ],
    "atlas": [
        "/static/images/pattern_atlas1.jpg",
        "/static/images/pattern_atlas2.jpg",
    ],
}

# 把纹样挂到对应项目的详情页上（刺绣 / 地毯 / 艾德莱斯绸）
for _key, _imgs in pattern_library.items():
    if _key in feiyi_data:
        feiyi_data[_key]["patterns"] = _imgs


# ==========================================================
# 首页速览信息
# 进入项目详情后先给出一眼可见的关键数据，避免一上来就是大段文字。
# 名录年份与项目编号依据中国非物质文化遗产网（ihchina.cn）项目页。
# 类别代号：Ⅰ 民间文学 · Ⅱ 传统音乐 · Ⅶ 传统美术 · Ⅷ 传统技艺
# ==========================================================
project_facts = {
    "embroidery": [
        {"icon": "🏛️", "label": "名录", "value": "2008 年第二批 · Ⅶ-79"},
        {"icon": "📚", "label": "类别", "value": "传统美术"},
        {"icon": "📍", "label": "分布", "value": "喀什、和田、阿克苏、吐鲁番"},
        {"icon": "🧵", "label": "代表", "value": "花帽（朵帕）、壁挂、服饰刺绣"},
    ],
    "dombra": [
        {"icon": "🏛️", "label": "名录", "value": "2008 年第二批 · Ⅱ-132"},
        {"icon": "📚", "label": "类别", "value": "传统音乐"},
        {"icon": "📍", "label": "分布", "value": "伊犁、巴里坤等哈萨克族聚居区"},
        {"icon": "🎵", "label": "代表", "value": "冬不拉曲《黑走马》等"},
    ],
    "atlas": [
        {"icon": "🏛️", "label": "名录", "value": "2008 年第二批 · Ⅷ-109"},
        {"icon": "📚", "label": "类别", "value": "传统技艺"},
        {"icon": "📍", "label": "分布", "value": "和田洛浦、喀什"},
        {"icon": "👘", "label": "代表", "value": "波浪纹、菱形纹、花卉纹"},
    ],
    "carpet": [
        {"icon": "🏛️", "label": "名录", "value": "2008 年第二批 · Ⅷ-110"},
        {"icon": "📚", "label": "类别", "value": "传统技艺"},
        {"icon": "📍", "label": "分布", "value": "和田、喀什、阿克苏"},
        {"icon": "🧶", "label": "代表", "value": "团花纹、多层连续边框"},
    ],
    "manas": [
        {"icon": "🏛️", "label": "名录", "value": "2006 年第一批 · 2009 年入选联合国名录"},
        {"icon": "📚", "label": "类别", "value": "民间文学"},
        {"icon": "📍", "label": "分布", "value": "克孜勒苏柯尔克孜自治州等"},
        {"icon": "📜", "label": "规模", "value": "八部唱本 · 二十三万余行"},
    ],
}

for _k, _facts in project_facts.items():
    if _k in feiyi_data:
        feiyi_data[_k]["facts"] = _facts


# 详情页各段落的图标与标题（供模板统一渲染）
section_meta = {
    "intro": {"icon": "📖", "label": "文化简介"},
    "history": {"icon": "🕰️", "label": "历史源流"},
    "craft": {"icon": "🛠️", "label": "工艺特点"},
    "value": {"icon": "✨", "label": "文化价值"},
    "region": {"icon": "📍", "label": "分布地区"},
    "representative": {"icon": "🏆", "label": "代表作品"},
}


# ==========================================================
# 纹样生成器：三种风格的特征说明
# ==========================================================
style_options = [
    {"key": "embroidery", "label": "刺绣风格"},
    {"key": "carpet", "label": "地毯风格"},
    {"key": "atlas", "label": "艾德莱斯绸风格"},
]

style_info = {
    "embroidery": {
        "desc": "以花卉、瓜果、几何图案为主，构图饱满、色彩对比强烈，常用于花帽与服饰。",
        "traits": ["花卉瓜果纹", "对称构图", "色彩浓艳"],
    },
    "carpet": {
        "desc": "图案繁密对称，多为团花或中心徽章式构图，外围配以多层连续边框纹样。",
        "traits": ["中心团花", "多层边框", "庄重典雅"],
    },
    "atlas": {
        "desc": "扎经染色形成的抽象波浪纹与菱形纹，色块边缘自然晕散，图案不可复制。",
        "traits": ["波浪菱形纹", "边缘晕散", "色彩奔放"],
    },
}

STYLE_LABELS = {s["key"]: s["label"] for s in style_options}
DEFAULT_STYLE = "embroidery"
KEYWORD_MAX_LEN = 20

# 生成器页面的关键词示例
keyword_examples = ["石榴花", "巴旦木", "月亮", "葡萄藤", "几何菱形"]


# ==========================================================
# 冬不拉知识板块
# 依据：中国非物质文化遗产网「哈萨克族冬布拉艺术」项目页
# ==========================================================
instrument_knowledge = [
    {
        "icon": "🪕",
        "title": "形制与构造",
        "points": [
            "琴身多用松木或桑木制作，音箱呈梨形或勺形，面板较薄，利于共鸣。",
            "琴杆修长，上设品位，便于左手按弦取音。",
            "传统形制以两根弦为主，也有三弦、四弦等变体，琴弦多用钢丝。",
            "音色清脆明亮，音量不大但穿透力强，适合独奏与伴唱。",
        ],
    },
    {
        "icon": "🎼",
        "title": "乐曲与演奏",
        "points": [
            "冬不拉曲统称「冬不拉奎依」，讲究即兴与变化，同一首曲子不同的人弹各有各的味道。",
            "按演奏技法，常分为弹击乐曲与拨奏乐曲两大类。",
            "冬不拉艺术由乐曲、弹唱音乐、民间舞蹈音乐、演奏方法与技巧、乐器与制作工艺五部分组成。",
            "既可独奏自娱，也常为阿肯弹唱和民间舞蹈伴奏。",
        ],
    },
    {
        "icon": "🎤",
        "title": "阿肯与弹唱",
        "points": [
            "阿肯是哈萨克族的民间歌手与即兴诗人，怀抱冬不拉边弹边唱。",
            "弹唱形式有「安」「阿依特斯」等多种，其中阿依特斯为双人对唱，即兴接句、你来我往。",
            "阿肯弹唱既比歌喉，也比才思，是哈萨克族最重要的民间文艺活动之一。",
            "2008 年，哈萨克族冬不拉艺术列入第二批国家级非物质文化遗产名录。",
        ],
    },
]


# ==========================================================
# 民族服饰元素图鉴
# ==========================================================
costume_elements = [
    {
        "icon": "🎩",
        "name": "花帽（朵帕）",
        "desc": "维吾尔族传统头饰，四角或圆形，绣满花卉、瓜果纹样。不同地区的花帽在样式与配色上各有讲究。",
    },
    {
        "icon": "🧣",
        "name": "艾德莱斯绸",
        "desc": "采用扎经染色工艺织成的丝绸，图案抽象奔放，是维吾尔族女性连衣裙的主要面料。",
    },
    {
        "icon": "🎓",
        "name": "卡尔帕克白毡帽",
        "desc": "柯尔克孜族标志性头饰，以羊毛毡制成，帽檐镶黑绒，帽身绣有花纹。",
    },
    {
        "icon": "🧥",
        "name": "刺绣坎肩",
        "desc": "哈萨克族女性常在连衣裙外搭配刺绣坎肩，纹样多为几何纹与动物纹。",
    },
    {
        "icon": "👢",
        "name": "马靴",
        "desc": "游牧生活留下的印记，皮质靴筒便于骑马，靴面常配刺绣或压花装饰。",
    },
    {
        "icon": "🧵",
        "name": "刺绣纹样",
        "desc": "服饰上的刺绣多以花卉、瓜果、几何图案为主，色彩对比强烈，讲究对称与饱满。",
    },
]


# ==========================================================
# 路由
# ==========================================================
@app.route("/")
def index():
    """非遗浏览。使用 GET 传参，刷新不会重复提交表单。"""
    selected = request.args.get("project")
    data = feiyi_data.get(selected) if selected else None
    return render_template(
        "index.html",
        project_list=project_list,
        selected=selected if data else None,
        data=data,
        section_meta=section_meta,
    )


@app.route("/generator")
def generator():
    """纹样生成器。GET 传参，关键词经哈希稳定映射到素材图。"""
    keyword = (request.args.get("keyword") or "").strip()[:KEYWORD_MAX_LEN]
    style = request.args.get("style") or DEFAULT_STYLE
    if style not in pattern_library:
        style = DEFAULT_STYLE

    result_img = None
    if keyword:
        patterns = pattern_library[style]
        digest = hashlib.md5(keyword.encode("utf-8")).hexdigest()
        result_img = patterns[int(digest, 16) % len(patterns)]

    return render_template(
        "generator.html",
        style_options=style_options,
        style_info=style_info,
        pattern_library=pattern_library,
        keyword_examples=keyword_examples,
        keyword=keyword,
        selected_style=style,
        result_img=result_img,
        result_keyword=keyword,
        result_style=STYLE_LABELS[style],
    )


@app.route("/instrument")
def instrument():
    return render_template("instrument.html", knowledge=instrument_knowledge)


@app.route("/quiz")
def quiz():
    return render_template("quiz.html")


@app.route("/costumes")
def costumes():
    return render_template("costumes.html", elements=costume_elements)


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/fortune")
def fortune():
    return render_template("fortune.html")


@app.route("/tryon")
def tryon():
    return render_template("tryon.html")


@app.route("/map")
def map():
    return render_template("map.html")


# ==========================================================
# AI 换装：调用硅基流动文生图 API
#
# ⚠ API Key 不要写死在代码里 —— 会随代码一起泄露（提交、传阅、打包）。
# 二选一（config_local.py 已在 .gitignore 中忽略）：
#   1) 环境变量：set SILICONFLOW_API_KEY=sk-xxxx
#   2) 新建 config_local.py，内容：SILICONFLOW_API_KEY = "sk-xxxx"
# 未配置 key 时自动进入演示模式，返回本地素材图，断网也能演示。
# ==========================================================
try:
    from config_local import SILICONFLOW_API_KEY
except ImportError:
    SILICONFLOW_API_KEY = os.environ.get("SILICONFLOW_API_KEY", "")

SILICONFLOW_URL = "https://api.siliconflow.cn/v1/images/generations"

# ==========================================================
# DeepSeek：文本大模型，用于为手绘纹样生成文字解读
# ⚠ 它不支持图像生成（/images/generations 返回 404），
#   纹样的「补全」由本文件的 Pillow 合成逻辑完成，不依赖网络。
# Key 同样走 config_local.py / 环境变量双通道。
# ==========================================================
try:
    from config_local import DEEPSEEK_API_KEY
except ImportError:
    DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")

DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"
DEEPSEEK_MODEL = "deepseek-flash"

# 各民族服饰的换装提示词
# 用中文描述：Qwen-Image-Edit 对中文提示词的理解更好；
# 并明确要求「保持人物面部特征不变」，避免换装后不像本人。
costume_prompts = {
    "uyghur": "把人物的服装换成新疆维吾尔族传统服饰：艾德莱斯绸连衣裙，头戴绣花小帽（朵帕），佩戴耳饰，保持人物面部特征与姿态不变，影棚人像摄影，高清",
    "kazakh": "把人物的服装换成新疆哈萨克族传统服饰：刺绣长袍配皮毛镶边帽子，佩戴首饰，保持人物面部特征与姿态不变，影棚人像摄影，高清",
    "kirgiz": "把人物的服装换成新疆柯尔克孜族传统服饰：刺绣长袍配白色毡帽（卡尔帕克），佩戴银饰，保持人物面部特征与姿态不变，影棚人像摄影，高清",
}

costume_labels = {
    "uyghur": "维吾尔族服饰",
    "kazakh": "哈萨克族服饰",
    "kirgiz": "柯尔克孜族服饰",
}

# 演示模式备用素材：断网 / 未配置 Key / 接口失败时返回本地图，保证演示不中断
costume_fallback = {
    "uyghur": "/static/images/costume_uyghur.jpg",
    "kazakh": "/static/images/costume_kazakh.jpg",
    "kirgiz": "/static/images/costume_kirgiz.jpg",
}

# 图像编辑模型：能基于用户上传的照片更换服饰，并尽量保持人物特征
TRYON_MODEL = "Qwen/Qwen-Image-Edit-2509"
GENERATED_DIR = os.path.join(app.static_folder, "generated")
GENERATED_KEEP = 60      # 结果图最多保留张数，超出则删最旧的


def _save_generated(image_bytes, suffix=".png", prefix="tryon"):
    """把生成结果落盘到 static/generated/，返回可访问的 URL。

    接口返回的图片 URL 只有 1 小时有效期，必须及时下载到本地保存，
    否则演示现场会出现图片裂开（docs.siliconflow.cn 明确提示）。
    """
    os.makedirs(GENERATED_DIR, exist_ok=True)

    name = f"{prefix}_{datetime.now():%Y%m%d_%H%M%S}_{uuid.uuid4().hex[:6]}{suffix}"
    with open(os.path.join(GENERATED_DIR, name), "wb") as fh:
        fh.write(image_bytes)

    # 清理旧结果，避免长期运行后堆积
    old_files = sorted(glob.glob(os.path.join(GENERATED_DIR, "*")), key=os.path.getmtime)
    for path in old_files[:-GENERATED_KEEP]:
        try:
            os.remove(path)
        except OSError:
            pass

    return f"/static/generated/{name}"


@app.route("/api/tryon", methods=["POST"])
def api_tryon():
    """AI 换装。

    优先调用图像编辑模型，基于用户上传的照片生成换装效果；
    未配置 Key、接口失败或超时，自动降级为演示模式返回本地素材图，
    保证断网或额度不足时演示不中断。
    """
    data = request.get_json(silent=True) or {}
    costume_type = data.get("costume", "uyghur")
    if costume_type not in costume_prompts:
        costume_type = "uyghur"

    user_image = (data.get("image") or "").strip()

    if SILICONFLOW_API_KEY and user_image:
        try:
            headers = {
                "Authorization": f"Bearer {SILICONFLOW_API_KEY}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": TRYON_MODEL,
                "prompt": costume_prompts[costume_type],
                "image": user_image,
            }
            resp = requests.post(SILICONFLOW_URL, headers=headers, json=payload, timeout=180)
            result = resp.json()

            images = result.get("images") if isinstance(result, dict) else None
            if images:
                remote_url = images[0].get("url")
                if remote_url:
                    downloaded = requests.get(remote_url, timeout=60)
                    downloaded.raise_for_status()
                    return jsonify({
                        "success": True,
                        "mode": "ai",
                        "image_url": _save_generated(downloaded.content),
                        "label": costume_labels[costume_type],
                    })

            app.logger.warning("AI 换装接口未返回图片：%s", str(result)[:300])
        except Exception as exc:                      # noqa: BLE001
            app.logger.warning("AI 换装调用失败，转入演示模式：%s", exc)

    return jsonify({
        "success": True,
        "mode": "demo",
        "image_url": costume_fallback[costume_type],
        "label": costume_labels[costume_type],
        "message": "当前为演示模式：展示该民族服饰的参考素材（未配置 API Key、网络不可用或接口调用失败）",
    })


# ==========================================================
# 手绘纹样补全：用户画几笔 → 合成完整纹样
#
# 对应申报书第一条创新点：
#   「用户手绘线条，AI 补全为完整非遗纹样，从『观看』变成『参与创作』」
#
# 合成过程不依赖任何外部接口（断网也能演示）：
#   1. 从线稿中提取笔画作为蒙版
#   2. 取一张纹样素材作为底图，整体淡化
#   3. 在笔画附近露出清晰的纹样，模拟「沿笔触补全」
#   4. 叠回用户原线条，保留手绘痕迹
# 以后若要接入真实图像接口，只需替换 _compose_sketch_pattern。
# ==========================================================
SKETCH_SIZE = 720
SKETCH_MAX_BYTES = 6 * 1024 * 1024


def _parse_data_url(data_url):
    """把 data:image/...;base64,xxx 解析为 PIL Image；失败返回 None。"""
    if not data_url or "," not in data_url:
        return None
    try:
        _, encoded = data_url.split(",", 1)
        raw = base64.b64decode(encoded)
    except Exception:                                     # noqa: BLE001
        return None
    if not raw or len(raw) > SKETCH_MAX_BYTES:
        return None
    try:
        return Image.open(io.BytesIO(raw))
    except Exception:                                     # noqa: BLE001
        return None


def _compose_sketch_pattern(sketch_img, pattern_path, size=SKETCH_SIZE):
    """把线稿与纹样素材合成成一张「补全」结果，返回 (图片, 错误信息)。"""
    sketch = sketch_img.convert("RGBA").resize((size, size), Image.LANCZOS)

    # 笔画 = 深色区域（画布为白底深色笔迹）
    stroke = sketch.convert("L").point(lambda p: 255 if p < 150 else 0)
    if stroke.getbbox() is None:
        return None, "画布还是空的，先用画笔勾几笔再来生成。"

    # 底图：纹样素材淡化，作为「待补全」的底色
    pattern = Image.open(pattern_path).convert("RGB").resize((size, size), Image.LANCZOS)
    faded = Image.blend(pattern, Image.new("RGB", (size, size), (255, 252, 246)), 0.74)

    # 笔画附近露出清晰纹样，边缘柔化让衔接自然
    wide = stroke.filter(ImageFilter.MaxFilter(13)).filter(ImageFilter.GaussianBlur(5))
    composed = Image.composite(pattern, faded, wide)

    # 叠回用户原线条，保留手绘痕迹
    ink = Image.new("RGB", (size, size), (78, 46, 30))
    composed.paste(ink, mask=stroke.filter(ImageFilter.GaussianBlur(1)))

    return composed, None


# 三种风格对应的图像提示词（用于图像编辑模型）
pattern_prompts = {
    "embroidery": "新疆维吾尔族刺绣纹样，以石榴花、花卉与藤蔓为主题，构图饱满对称，"
                  "色彩浓艳，红、金、绿、蓝对比强烈，针脚细腻",
    "carpet": "新疆和田地毯纹样，中心团花搭配多层连续边框，构图严谨对称，"
              "色彩庄重典雅，以深红、靛蓝、赭金为主",
    "atlas": "新疆艾德莱斯绸纹样，扎经染色形成的抽象波浪纹与菱形纹，"
             "色块边缘自然晕散，色彩奔放，红黄蓝黑对比强烈",
}


def _ai_compose_sketch(sketch_img, style, keyword):
    """调用图像编辑模型，沿用户笔触真正「AI 补全」纹样。

    成功返回图片字节，失败返回 None（由调用方降级到本地合成）。
    """
    if not SILICONFLOW_API_KEY:
        return None

    buf = io.BytesIO()
    sketch_img.convert("RGB").save(buf, "JPEG", quality=92)
    data_url = "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()

    prompt = (
        "这是一张手绘线稿。请沿着线稿的笔触与构图，把它补全成一幅完整的"
        + pattern_prompts.get(style, pattern_prompts["embroidery"])
        + ("。主题元素：" + keyword + "。" if keyword else "。")
        + "保持线稿的整体布局与线条走向，填充饱满的民族图案与配色；"
          "画面为纯装饰纹样，不要出现文字、人物、签名或水印。"
    )

    try:
        resp = requests.post(
            SILICONFLOW_URL,
            headers={
                "Authorization": f"Bearer {SILICONFLOW_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": TRYON_MODEL,
                "prompt": prompt,
                "image": data_url,
            },
            timeout=180,
        )
        data = resp.json()
        images = data.get("images") if isinstance(data, dict) else None
        if images:
            remote = images[0].get("url")
            if remote:
                got = requests.get(remote, timeout=60)
                got.raise_for_status()
                return got.content
        app.logger.warning("纹样补全接口未返回图片：%s", str(data)[:300])
    except Exception as exc:                              # noqa: BLE001
        app.logger.warning("纹样补全调用失败，转入本地合成：%s", exc)
    return None


def _describe_pattern(keyword, style_label):
    """调用 DeepSeek 生成一段纹样解读；失败或未配置 Key 时返回 None。"""
    if not DEEPSEEK_API_KEY:
        return None

    prompt = (
        f"这是「新疆非遗纹样生成器」的辅助说明。用户选择的是「{style_label}」风格，"
        f"输入的关键词是「{keyword or '自由手绘'}」。\n"
        "请用不超过 80 个字写一段纹样解读，包含这类纹样常见的母题、配色特点，"
        "以及它在传统生活中的常见用途。\n"
        "要求：只写工艺与风格层面的描述；不要提及具体历史年代，不要编造文献或人物；"
        "不要使用夸张宣传语；直接输出正文，不要任何前缀。"
    )

    try:
        resp = requests.post(
            DEEPSEEK_URL,
            headers={
                "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": DEEPSEEK_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                # deepseek-flash 是推理模型：先输出思考过程再写正文。
                # 上限给小了会只拿到思考、content 为空（finish_reason=length）。
                "max_tokens": 1200,
                "temperature": 0.7,
            },
            timeout=60,
        )
        data = resp.json()
        choice = (data.get("choices") or [{}])[0]
        text = ((choice.get("message") or {}).get("content") or "").strip()
        if not text:
            app.logger.warning("DeepSeek 未返回正文（finish_reason=%s）", choice.get("finish_reason"))
            return None
        return text.replace("\n", " ")[:200]
    except Exception as exc:                              # noqa: BLE001
        app.logger.warning("DeepSeek 解读生成失败：%s", exc)
        return None


@app.route("/api/pattern", methods=["POST"])
def api_pattern():
    """手绘纹样补全。

    优先调用图像编辑模型，沿用户笔触真正「AI 补全」；
    未配置 Key、网络不可用或接口失败时，降级为本地 Pillow 合成，
    保证断网也能演示。
    """
    payload = request.get_json(silent=True) or {}
    style = payload.get("style") or DEFAULT_STYLE
    if style not in pattern_library:
        style = DEFAULT_STYLE
    keyword = (payload.get("keyword") or "").strip()[:KEYWORD_MAX_LEN]

    sketch_img = _parse_data_url(payload.get("sketch") or "")
    if sketch_img is None:
        return jsonify({"success": False, "error": "没有收到有效的画布内容，请重画一次。"})

    # 先判断画布是否为空，避免白跑一次接口
    if sketch_img.convert("L").point(lambda p: 255 if p < 150 else 0).getbbox() is None:
        return jsonify({"success": False, "error": "画布还是空的，先用画笔勾几笔再来生成。"})

    result_img = None
    mode = "local"

    # 1) 优先：图像编辑模型，真正的 AI 补全
    ai_bytes = _ai_compose_sketch(sketch_img, style, keyword)
    if ai_bytes:
        try:
            result_img = Image.open(io.BytesIO(ai_bytes)).convert("RGB")
            mode = "ai"
        except Exception as exc:                          # noqa: BLE001
            app.logger.warning("AI 返回的图片无法解析，转入本地合成：%s", exc)

    # 2) 降级：本地合成（不依赖网络）
    if result_img is None:
        patterns = pattern_library[style]
        seed = keyword or datetime.now().strftime("%Y%m%d%H%M%S")
        digest = hashlib.md5(seed.encode("utf-8")).hexdigest()
        relative = patterns[int(digest, 16) % len(patterns)].replace("/static/", "")
        result_img, err = _compose_sketch_pattern(
            sketch_img, os.path.join(app.static_folder, relative)
        )
        if result_img is None:
            return jsonify({"success": False, "error": err})

    buf = io.BytesIO()
    result_img.save(buf, "JPEG", quality=90, optimize=True, progressive=True)

    return jsonify({
        "success": True,
        "mode": mode,
        "image_url": _save_generated(buf.getvalue(), suffix=".jpg", prefix="pattern"),
        "style": STYLE_LABELS[style],
        "keyword": keyword,
        "commentary": _describe_pattern(keyword, STYLE_LABELS[style]),
    })


@app.route("/favicon.ico")
def favicon():
    """浏览器默认会请求 /favicon.ico，指向 SVG 图标，避免 404。"""
    return send_from_directory(app.static_folder, "favicon.svg", mimetype="image/svg+xml")


@app.errorhandler(404)
def page_not_found(error):
    return render_template("404.html"), 404


@app.errorhandler(500)
def server_error(error):
    return render_template("500.html"), 500


if __name__ == "__main__":
    # 演示时可用环境变量关闭调试模式：FLASK_DEBUG=0
    debug = os.environ.get("FLASK_DEBUG", "1") != "0"
    host = os.environ.get("FLASK_HOST", "0.0.0.0")
    port = int(os.environ.get("FLASK_PORT", "5000"))
    app.run(debug=debug, host=host, port=port)






