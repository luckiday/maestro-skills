---
name: english-reading-difficulty
description: 英文阅读材料多维度难度自动化分析工具；当用户需要评估英文试卷、文章或阅读材料的难度等级，或需要量化对比不同文本的难易程度时使用
dependency:
  python:
    - spacy>=3.4.0
    - nltk>=3.8.0
  system:
    - python -m spacy download en_core_web_sm
---

# 英文阅读材料难度分析工具

## 任务目标
- 本 Skill 用于:自动化评估英文阅读材料的难度等级
- 能力包含:多维度指标分析（词汇、句子、篇章、题目）、量化评分、难度分级、生成分析报告
- 触发条件:用户需要分析英文试卷、文章或阅读材料的难度，或量化对比不同文本的难易程度

## 前置准备
- 依赖说明:核心NLP库
  ```
  spacy>=3.4.0
  nltk>=3.8.0
  ```
- ⚠️ 注意: 需要 Python 3.12（Python 3.14 与 spacy 不兼容）
- 环境初始化:
  ```bash
  # 方法1: 使用 uv (推荐)
  cd ~/.agents/skills/english-reading-difficulty
  uv venv .venv --python 3.12
  source .venv/bin/activate
  uv pip install spacy nltk
  curl -sS https://bootstrap.pypa.io/get-pip.py | python
  python -m spacy download en_core_web_sm

  # 方法2: 使用系统Python 3.12
  python3.12 -m venv .venv
  source .venv/bin/activate
  pip install spacy nltk
  python -m spacy download en_core_web_sm
  ```

## 操作步骤
- 标准流程:
  1. **输入准备**
     - 准备需要分析的英文阅读文本
     - 如果有题目，准备题目文本（可选）
     - 调用 `scripts/analyze_difficulty.py` 执行分析
  2. **自动化分析**
     - 脚本自动计算以下指标:
       - 词汇维度:词汇量要求、低频词比例、学术词汇密度
       - 句子维度:平均句长、从句嵌套深度
       - 篇章维度:信息密度
     - 生成初步评分和报告
  3. **人工评估补充**
     - 根据脚本输出的待评估项，参考 [references/human_assessment.md](references/human_assessment.md) 进行人工评分
     - 主要包括:熟词生义、抽象程度、逻辑复杂度、文化背景依赖度、题目相关指标
  4. **生成最终报告**
     - 结合自动分析和人工评估，生成完整的难度分析报告
     - 报告包含:各维度得分、总分、难度等级、详细建议
  5. **文件归档**
     - 将原始PDF和报告保存到 workspace 的 `teaching-docs/reading/` 目录
     - 命名格式: `[年][月][日]-[考试名称].[pdf/md]`, `[年][月][日]-[考试名称]-analyze.[md]`

## 资源索引
- 核心脚本:见 [scripts/analyze_difficulty.py](scripts/analyze_difficulty.py)(用途:执行自动化分析，参数:`--text`文本路径或`--text-content`文本内容，`--questions`题目路径可选)
- 评分标准:见 [references/scoring_guide.md](references/scoring_guide.md)(何时读取:需要理解评分规则和标准时)
- 人工评估指导:见 [references/human_assessment.md](references/human_assessment.md)(何时读取:需要补充人工评估指标时)
- 词汇资源:见 [references/vocab_resources.md](references/vocab_resources.md)(何时读取:了解词汇表来源与数据结构时)

### 权威词汇数据
- **COCA 词频**：[assets/COCA_WordFrequency.csv](assets/COCA_WordFrequency.csv) — 词频数据，用于超纲词判断；关键列：`lemma`
- **CEFR 分级**：[assets/cefrj-vocabulary-profile-1.5.csv](assets/cefrj-vocabulary-profile-1.5.csv) — CEFR 分级，用于难度判断；关键列：`headword`, `pos`, `CEFR`

`scripts/analyze_difficulty.py` 直接从上述两个 CSV 加载词汇数据。

## 注意事项
- 本工具提供半自动化分析:可量化指标自动计算，语义理解类指标需要人工评估
- 分析结果仅供参考，建议结合实际教学场景调整权重
- 首次使用需要下载spacy语言模型（约10MB）
- 题目分析需要提供题目文本，否则仅分析文章本身难度
- 分析完成后务必更新 memory 工作日志，记录分析过程和结果

## Workspace 文件结构
```
workspace/
├── skills/
│   └── english-reading-difficulty/    # 技能所在目录
├── teaching-docs/
│   └── reading/                       # 分析文档存放目录
│       ├── 2026-0312-taichung-edu-vocab.pdf
│       └── 2026-0312-taichung-edu-vocab-analyze.md
└── memory/
    └── YYYY-MM-DD.md                  # 工作日志
```

## 使用示例

### 示例1:分析英文文章（无题目）
```bash
cd ~/.agents/skills/english-reading-difficulty
source .venv/bin/activate
python scripts/analyze_difficulty.py --text content.txt --output report.md
```

### 示例2:分析带题目的完整试卷
```bash
python scripts/analyze_difficulty.py --text reading.txt --questions questions.txt --output full_report.md
```

### 示例3:直接输入文本内容
```bash
python scripts/analyze_difficulty.py --text-content "The quick brown fox..." --output result.json
```

## 输出说明
- **JSON格式**:包含所有指标得分的结构化数据，便于程序处理
- **Markdown格式**:可读性强的分析报告，包含详细解读和建议
- **难度等级**:E(简单)、M(中等)、H(较难)、VH(困难)
