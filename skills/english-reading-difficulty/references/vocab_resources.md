# 词汇资源说明

## 目录
- [一、权威数据源（优先使用）](#一权威数据源优先使用)
- [二、当前脚本使用的衍生资源](#二当前脚本使用的衍生资源)
- [三、词汇表格式](#三词汇表格式)
- [四、自定义词汇表](#四自定义词汇表)

## 一、权威数据源（优先使用）

以下 CSV 文件为词汇分析的主要依据，应优先参考：

| 文件名 | 用途 | 关键列 | 来源 |
|--------|------|--------|------|
| `COCA_WordFrequency.csv` | 词频统计、低频词判断 | `lemma`, `rank`, `freq` | Corpus of Contemporary American English (COCA) |
| `cefrj-vocabulary-profile-1.5.csv` | 词汇难度分级、CEFR 等级 | `headword`, `pos`, `CEFR` | CEFR-J Vocabulary Profile |

### 1. COCA 词频 (COCA_WordFrequency.csv)

**用途**：词频分析、低频词比例、词汇量要求推断

**来源**：Corpus of Contemporary American English
- 开发者：Mark Davies (Brigham Young University)
- 规模：超过 10 亿词

**关键列**：`lemma`（词元）、`rank`（频次排名）、`freq`（总频次）及各类语域频次列

### 2. CEFR 分级 (cefrj-vocabulary-profile-1.5.csv)

**用途**：词汇难度分级、CEFR 等级判断

**来源**：CEFR-J Vocabulary Profile（基于 Common European Framework of Reference）

**分级标准**：A1–A2（基础）、B1–B2（中级）、C1–C2（高级）

**关键列**：`headword`（词条）、`pos`（词性）、`CEFR`（等级）

## 二、当前脚本使用的其他资源

`scripts/analyze_difficulty.py` 从 CSV 加载 COCA 与 CEFR 数据；另使用以下 `.txt` 文件：

| 文件名 | 说明 | 备注 |
|--------|------|------|
| `awl.txt` | 学术词汇列表 | Academic Word List（独立 curated 资源） |
| `basic_vocab.txt` | 基础词汇列表 | 常见教材/课程标准（非 CSV 衍生） |

**注意**：`awl.txt` 与 `basic_vocab.txt` 为独立 curated 资源，可靠性依赖具体来源。

## 三、词汇表格式

### 基础格式（每行一个词）

```
apple
banana
computer
...
```

### 带频率的格式（词 + 频率）

```
the 1
be 2
and 3
...
```

### 带等级的格式（等级 + 词）

```
A1 apple
A1 book
B1 comfortable
C2 sophisticated
...
```

## 四、自定义词汇表

如需使用自定义词汇表，请按照以下步骤：

### 1. 准备词汇表文件

创建文本文件，每行一个词汇，使用小写形式：

```
custom_word1
custom_word2
custom_word3
...
```

### 2. 将文件放入 assets 目录

将词汇表文件放置在 `assets/` 目录中。

### 3. 修改脚本引用

编辑 `scripts/analyze_difficulty.py` 中的 `VocabularyAnalyzer` 类：

```python
def __init__(self, assets_dir: str):
    self.assets_dir = Path(assets_dir)
    self.basic_vocab = self._load_vocab('basic_vocab.txt')
    self.custom_vocab = self._load_vocab('your_custom_file.txt')  # 添加自定义词汇表
    # ...
```

### 4. 在分析逻辑中使用

在 `analyze_vocabulary` 方法中添加自定义词汇的统计逻辑。

## 扩展词汇表资源

### 建议的词汇表

如需更全面的词汇资源，可考虑以下来源：

1. **Oxford 3000/5000**
   - 网址：https://www.oxfordlearnersdictionaries.com/
   - 说明：牛津学习词典核心词汇

2. **Longman Communication 3000**
   - 网址：https://www.ldoceonline.com/
   - 说明：朗文通信词汇表

3. **British National Corpus (BNC)**
   - 网址：https://www.english-corpora.org/bnc/
   - 说明：英国国家语料库

4. **New General Service List (NGSL)**
   - 开发者：Dr. Charles Browne
   - 说明：新一代通用服务词汇表（2800词）

5. **New Academic Word List (NAWL)**
   - 开发者：Dr. Charles Browne
   - 说明：新一代学术词汇表（963词）

### 下载和使用建议

1. **优先级**：
   - 词频与分级：使用 `COCA_WordFrequency.csv` 与 `cefrj-vocabulary-profile-1.5.csv`（脚本已直接加载）
   - 学术词汇：`awl.txt`（独立 curated）
   - 基础词汇：`basic_vocab.txt`（脚本使用）

2. **更新频率**：
   - 基础词汇表：每2-3年更新一次
   - 词频表：每1-2年更新一次（语言变化较快）
   - 学术词汇表：每3-5年更新一次（相对稳定）

3. **格式转换**：
   - 下载后转换为统一格式（小写、每行一词）
   - 去除重复项
   - 确保文件编码为UTF-8

## 词汇表质量检查

使用以下Python脚本检查词汇表质量：

```python
def check_vocab_quality(filepath):
    """检查词汇表质量"""
    with open(filepath, 'r', encoding='utf-8') as f:
        words = [line.strip().lower() for line in f if line.strip()]
    
    # 统计
    total = len(words)
    unique = len(set(words))
    duplicates = total - unique
    avg_length = sum(len(w) for w in words) / total
    
    print(f"总词数: {total}")
    print(f"唯一词数: {unique}")
    print(f"重复词数: {duplicates}")
    print(f"平均长度: {avg_length:.1f}")
    
    if duplicates > 0:
        print("⚠️  存在重复词汇，建议去重")
    
    if avg_length < 3:
        print("⚠️  平均词长过短，可能包含缩写或错误")
```

## 参考资料

- **权威数据**：`assets/COCA_WordFrequency.csv`、`assets/cefrj-vocabulary-profile-1.5.csv`
- COCA Corpus: https://www.english-corpora.org/coca/
- Academic Word List: https://www.academicvocabulary.info/
- CEFR: https://www.coe.int/en/web/common-european-framework-of-reference-for-languages
- Oxford 3000: https://www.oxfordlearnersdictionaries.com/about/oxford3000
