#!/usr/bin/env python3
"""
英文阅读材料难度分析工具

功能：
1. 自动分析词汇、句子、篇章维度的可量化指标
2. 生成初步评分和难度等级
3. 标记需要人工评估的指标
4. 生成JSON和Markdown格式的分析报告
"""

import os
import sys
import json
import argparse
import csv
from typing import Dict, List, Tuple
from pathlib import Path
from collections import Counter
import re

try:
    import spacy
    from spacy import displacy
except ImportError:
    print("错误: 需要安装 spacy")
    print("请运行: pip install spacy>=3.4.0")
    print("然后运行: python -m spacy download en_core_web_sm")
    sys.exit(1)


class VocabularyAnalyzer:
    """词汇维度分析"""
    
    def __init__(self, assets_dir: str):
        self.assets_dir = Path(assets_dir)
        self.basic_vocab = self._load_vocab('basic_vocab.txt')
        self.awl_vocab = self._load_vocab('awl.txt')
        self.coca_vocab = self._load_coca_csv()
        self.cefr_vocab = self._load_cefr_csv()
    
    def _load_vocab(self, filename: str) -> set:
        """加载词汇表"""
        filepath = self.assets_dir / filename
        if not filepath.exists():
            print(f"警告: 未找到 {filename}")
            return set()
        
        with open(filepath, 'r', encoding='utf-8') as f:
            vocab = set(line.strip().lower() for line in f if line.strip())
        print(f"已加载 {filename}: {len(vocab)} 个词汇")
        return vocab
    
    def _load_coca_csv(self) -> set:
        """从 COCA_WordFrequency.csv 加载词频词汇表"""
        filepath = self.assets_dir / 'COCA_WordFrequency.csv'
        if not filepath.exists():
            print("警告: 未找到 COCA_WordFrequency.csv")
            return set()
        vocab = set()
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                lemma = row.get('lemma', '').strip().lower()
                if lemma:
                    vocab.add(lemma)
        print(f"已加载 COCA_WordFrequency.csv: {len(vocab)} 个词汇")
        return vocab

    def _load_cefr_csv(self) -> Dict[str, str]:
        """从 cefrj-vocabulary-profile-1.5.csv 加载 CEFR 分级词汇"""
        filepath = self.assets_dir / 'cefrj-vocabulary-profile-1.5.csv'
        cefr_dict = {}
        if not filepath.exists():
            print("警告: 未找到 cefrj-vocabulary-profile-1.5.csv")
            return cefr_dict
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                level = row.get('CEFR', '').strip()
                headword = row.get('headword', '').strip()
                if not level or not headword:
                    continue
                for variant in headword.split('/'):
                    word = variant.strip().lower()
                    if word and word not in cefr_dict:
                        cefr_dict[word] = level
        print(f"已加载 cefrj-vocabulary-profile-1.5.csv: {len(cefr_dict)} 个词汇")
        return cefr_dict
    
    def analyze_vocabulary(self, tokens: List[str]) -> Dict:
        """分析词汇维度"""
        total_words = len([t for t in tokens if t.isalpha()])
        if total_words == 0:
            return {'error': '无有效词汇'}
        
        # 统计各类词汇
        basic_count = sum(1 for t in tokens if t.lower() in self.basic_vocab)
        awl_count = sum(1 for t in tokens if t.lower() in self.awl_vocab)
        coca_count = sum(1 for t in tokens if t.lower() in self.coca_vocab)
        
        # 计算比例
        basic_ratio = basic_count / total_words
        awl_ratio = awl_count / total_words
        coca_ratio = coca_count / total_words
        out_of_vocab_ratio = 1 - coca_ratio
        
        # 评分
        scores = {}
        
        # 1. 词汇量要求（基于超纲词比例）
        if out_of_vocab_ratio < 0.02:
            scores['vocab_size'] = 0
            scores['vocab_size_desc'] = '所有单词均在基础词汇表内'
        elif out_of_vocab_ratio < 0.05:
            scores['vocab_size'] = 1
            scores['vocab_size_desc'] = '少量超纲词（<2%），但不影响理解'
        elif out_of_vocab_ratio < 0.10:
            scores['vocab_size'] = 2
            scores['vocab_size_desc'] = '较多超纲词（2-5%），需根据上下文猜测'
        else:
            scores['vocab_size'] = 3
            scores['vocab_size_desc'] = '大量超纲词（>5%），严重影响理解'
        
        # 2. 低频词比例（基于COCA词频）
        low_freq_ratio = 1 - basic_ratio
        if low_freq_ratio < 0.10:
            scores['low_freq'] = 0
            scores['low_freq_desc'] = '绝大部分为高频词（前3000词）'
        elif low_freq_ratio < 0.25:
            scores['low_freq'] = 1
            scores['low_freq_desc'] = '少量低频词（4-6级词汇）'
        elif low_freq_ratio < 0.40:
            scores['low_freq'] = 2
            scores['low_freq_desc'] = '中等数量学术/低频词'
        else:
            scores['low_freq'] = 3
            scores['low_freq_desc'] = '大量专业术语或古英语/文学词汇'
        
        # 3. 学术词汇密度
        if awl_ratio < 0.01:
            scores['academic_density'] = 0
            scores['academic_density_desc'] = '几乎没有学术词汇'
        elif awl_ratio < 0.03:
            scores['academic_density'] = 1
            scores['academic_density_desc'] = '偶尔出现（<5%的实词）'
        elif awl_ratio < 0.06:
            scores['academic_density'] = 2
            scores['academic_density_desc'] = '中等密度（5-10%）'
        else:
            scores['academic_density'] = 3
            scores['academic_density_desc'] = '高密度（>10%），如学术论文'
        
        # 4. 熟词生义（需要人工评估）
        scores['familiar_word_new_meaning'] = None
        scores['familiar_word_new_meaning_desc'] = '需要人工评估：识别单词是否使用了非常见含义'
        
        return {
            'total_words': total_words,
            'basic_vocab_count': basic_count,
            'awl_vocab_count': awl_count,
            'coca_vocab_count': coca_count,
            'out_of_vocab_ratio': round(out_of_vocab_ratio, 4),
            'scores': scores
        }


class SentenceAnalyzer:
    """句子维度分析"""
    
    def __init__(self, nlp):
        self.nlp = nlp
    
    def analyze_sentences(self, doc) -> Dict:
        """分析句子维度"""
        sentences = list(doc.sents)
        if not sentences:
            return {'error': '无有效句子'}
        
        # 计算平均句长
        sentence_lengths = [len([token for token in sent if not token.is_punct]) for sent in sentences]
        avg_sentence_length = sum(sentence_lengths) / len(sentence_lengths)
        
        # 计算从句嵌套深度
        max_nesting = self._calculate_max_nesting(doc)
        
        # 评分
        scores = {}
        
        # 1. 平均句长
        if avg_sentence_length < 10:
            scores['avg_length'] = 0
            scores['avg_length_desc'] = f'<10词/句（实际: {avg_sentence_length:.1f}）'
        elif avg_sentence_length < 15:
            scores['avg_length'] = 1
            scores['avg_length_desc'] = f'10-15词/句（实际: {avg_sentence_length:.1f}）'
        elif avg_sentence_length < 20:
            scores['avg_length'] = 2
            scores['avg_length_desc'] = f'15-20词/句（实际: {avg_sentence_length:.1f}）'
        else:
            scores['avg_length'] = 3
            scores['avg_length_desc'] = f'>20词/句（实际: {avg_sentence_length:.1f}）'
        
        # 2. 从句嵌套深度
        if max_nesting == 0:
            scores['nesting_depth'] = 0
            scores['nesting_depth_desc'] = '简单句为主，无嵌套'
        elif max_nesting == 1:
            scores['nesting_depth'] = 1
            scores['nesting_depth_desc'] = '偶尔出现一层从句'
        elif max_nesting == 2:
            scores['nesting_depth'] = 2
            scores['nesting_depth_desc'] = '常见两层嵌套'
        else:
            scores['nesting_depth'] = 3
            scores['nesting_depth_desc'] = f'三层及以上嵌套（最大: {max_nesting}）'
        
        # 3. 特殊句式频率（需要人工评估）
        scores['special_structure'] = None
        scores['special_structure_desc'] = '需要人工评估：倒装、强调、虚拟、省略、独立主格等特殊句式'
        
        return {
            'total_sentences': len(sentences),
            'avg_sentence_length': round(avg_sentence_length, 1),
            'max_nesting_depth': max_nesting,
            'scores': scores
        }
    
    def _calculate_max_nesting(self, doc) -> int:
        """计算最大从句嵌套深度"""
        max_depth = 0
        
        for sent in doc.sents:
            depth = 0
            for token in sent:
                # 统计从句标记（简化版）
                if token.dep_ in ['ccomp', 'advcl', 'relcl', 'acl', 'xcomp']:
                    depth += 1
            max_depth = max(max_depth, depth)
        
        return min(max_depth, 3)  # 限制最大值为3


class PassageAnalyzer:
    """篇章维度分析"""
    
    def analyze_passage(self, text: str, doc) -> Dict:
        """分析篇章维度"""
        # 计算信息密度（字符数/句子数）
        sentences = list(doc.sents)
        if not sentences:
            return {'error': '无有效内容'}
        
        text_length = len(text.replace('\n', ' ').strip())
        info_density = text_length / len(sentences)
        
        scores = {}
        
        # 1. 抽象程度（需要人工评估）
        scores['abstractness'] = None
        scores['abstractness_desc'] = '需要人工评估：内容是具体故事、科普说明、社会科学评论还是哲学思辨'
        
        # 2. 逻辑复杂度（需要人工评估）
        scores['logic_complexity'] = None
        scores['logic_complexity_desc'] = '需要人工评估：线性结构、因果对比、隐含逻辑还是多重观点交织'
        
        # 3. 文化背景依赖度（需要人工评估）
        scores['cultural_dependency'] = None
        scores['cultural_dependency_desc'] = '需要人工评估：是否需要英美文化常识、历史事件或专业背景知识'
        
        # 4. 信息密度（可自动计算）
        if info_density < 80:
            scores['info_density'] = 0
            scores['info_density_desc'] = f'信息密度低（{info_density:.0f}字符/句）'
        elif info_density < 120:
            scores['info_density'] = 1
            scores['info_density_desc'] = f'信息密度中等（{info_density:.0f}字符/句）'
        elif info_density < 160:
            scores['info_density'] = 2
            scores['info_density_desc'] = f'信息密度较高（{info_density:.0f}字符/句）'
        else:
            scores['info_density'] = 3
            scores['info_density_desc'] = f'信息密度高（{info_density:.0f}字符/句）'
        
        return {
            'text_length': text_length,
            'sentence_count': len(sentences),
            'info_density': round(info_density, 1),
            'scores': scores
        }


class QuestionAnalyzer:
    """题目维度分析（需要提供题目）"""
    
    def analyze_questions(self, questions_text: str) -> Dict:
        """分析题目维度"""
        if not questions_text:
            return {
                'note': '未提供题目文本，无法分析题目维度',
                'scores': {
                    'info_location': None,
                    'distractor_confusion': None,
                    'inference_depth': None
                }
            }
        
        # 简单统计
        question_count = len([q for q in questions_text.split('\n') if q.strip()])
        
        scores = {
            # 所有题目维度都需要人工评估
            'info_location': None,
            'info_location_desc': '需要人工评估：信息定位难度（直接对应、同义转换、跨段落整合还是全文概括）',
            'distractor_confusion': None,
            'distractor_confusion_desc': '需要人工评估：干扰项迷惑性（明显错误、轻微干扰、多个选项需辨别还是所有选项看似合理）',
            'inference_depth': None,
            'inference_depth_desc': '需要人工评估：推理深度（事实记忆、简单推理、推断言外之意还是批判性评价）'
        }
        
        return {
            'question_count': question_count,
            'scores': scores
        }


class DifficultyCalculator:
    """难度计算器"""
    
    def calculate_total_score(self, vocab_analysis: Dict, sentence_analysis: Dict, 
                             passage_analysis: Dict, question_analysis: Dict) -> Dict:
        """计算总分和难度等级"""
        # 提取各维度得分
        vocab_scores = vocab_analysis.get('scores', {})
        sentence_scores = sentence_analysis.get('scores', {})
        passage_scores = passage_analysis.get('scores', {})
        question_scores = question_analysis.get('scores', {})
        
        # 计算各维度总分（归一化）
        vocab_total = 0
        vocab_max = 0
        for key in ['vocab_size', 'low_freq', 'academic_density']:
            if vocab_scores.get(key) is not None:
                vocab_total += vocab_scores[key]
                vocab_max += 1
        
        sentence_total = 0
        sentence_max = 0
        for key in ['avg_length', 'nesting_depth']:
            if sentence_scores.get(key) is not None:
                sentence_total += sentence_scores[key]
                sentence_max += 1
        
        passage_total = 0
        passage_max = 0
        for key in ['info_density']:
            if passage_scores.get(key) is not None:
                passage_total += passage_scores[key]
                passage_max += 1
        
        # 计算加权得分
        vocab_weighted = (vocab_total / 4) * 25 if vocab_max > 0 else 0
        sentence_weighted = (sentence_total / 3) * 30 if sentence_max > 0 else 0
        passage_weighted = (passage_total / 3) * 25 if passage_max > 0 else 0
        question_weighted = 0  # 题目需要人工评估
        
        # 计算总分（仅自动评估部分）
        auto_total = vocab_weighted + sentence_weighted + passage_weighted + question_weighted
        
        # 确定难度等级
        if auto_total < 30:
            level = 'E'
            level_desc = '简单'
        elif auto_total < 50:
            level = 'M'
            level_desc = '中等'
        elif auto_total < 70:
            level = 'H'
            level_desc = '较难'
        else:
            level = 'VH'
            level_desc = '困难'
        
        return {
            'vocab_score': round(vocab_weighted, 2),
            'sentence_score': round(sentence_weighted, 2),
            'passage_score': round(passage_weighted, 2),
            'question_score': round(question_weighted, 2),
            'auto_total': round(auto_total, 2),
            'difficulty_level': level,
            'difficulty_description': level_desc,
            'needs_human_assessment': self._identify_needs_human(vocab_scores, sentence_scores, passage_scores, question_scores)
        }
    
    def _identify_needs_human(self, vocab_scores, sentence_scores, passage_scores, question_scores) -> List[str]:
        """识别需要人工评估的指标"""
        needs = []
        
        if vocab_scores.get('familiar_word_new_meaning') is None:
            needs.append('词汇维度 - 熟词生义')
        if sentence_scores.get('special_structure') is None:
            needs.append('句子维度 - 特殊句式频率')
        if passage_scores.get('abstractness') is None:
            needs.append('篇章维度 - 抽象程度')
        if passage_scores.get('logic_complexity') is None:
            needs.append('篇章维度 - 逻辑复杂度')
        if passage_scores.get('cultural_dependency') is None:
            needs.append('篇章维度 - 文化背景依赖度')
        if question_scores.get('info_location') is None:
            needs.append('题目维度 - 信息定位难度')
        if question_scores.get('distractor_confusion') is None:
            needs.append('题目维度 - 干扰项迷惑性')
        if question_scores.get('inference_depth') is None:
            needs.append('题目维度 - 推理深度')
        
        return needs


class ReportGenerator:
    """报告生成器"""
    
    def generate_json_report(self, analysis_result: Dict, output_path: str):
        """生成JSON格式报告"""
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(analysis_result, f, ensure_ascii=False, indent=2)
        print(f"JSON报告已生成: {output_path}")
    
    def generate_markdown_report(self, analysis_result: Dict, output_path: str):
        """生成Markdown格式报告"""
        lines = []
        
        # 标题
        lines.append("# 英文阅读材料难度分析报告")
        lines.append("")
        
        # 总览
        lines.append("## 📊 总体评估")
        lines.append("")
        difficulty = analysis_result['difficulty_calculation']
        lines.append(f"**难度等级**: {difficulty['difficulty_level']} ({difficulty['difficulty_description']})")
        lines.append(f"**自动评估得分**: {difficulty['auto_total']}/100")
        lines.append("")
        
        # 各维度得分
        lines.append("### 各维度得分")
        lines.append("")
        lines.append(f"- 词汇维度: {difficulty['vocab_score']}/25")
        lines.append(f"- 句子维度: {difficulty['sentence_score']}/30")
        lines.append(f"- 篇章维度: {difficulty['passage_score']}/25")
        lines.append(f"- 题目维度: {difficulty['question_score']}/20")
        lines.append("")
        
        # 词汇维度详细分析
        lines.append("## 📚 词汇维度分析")
        lines.append("")
        vocab = analysis_result['vocabulary_analysis']
        lines.append(f"**总词数**: {vocab['total_words']}")
        lines.append(f"**基础词汇占比**: {vocab['basic_vocab_count']}/{vocab['total_words']} ({vocab['basic_vocab_count']/vocab['total_words']*100:.1f}%)")
        lines.append(f"**学术词汇占比**: {vocab['awl_vocab_count']}/{vocab['total_words']} ({vocab['awl_vocab_count']/vocab['total_words']*100:.1f}%)")
        lines.append(f"**超纲词比例**: {vocab['out_of_vocab_ratio']*100:.1f}%")
        lines.append("")
        lines.append("### 评分详情")
        lines.append("")
        for key, value in vocab['scores'].items():
            if key.endswith('_desc'):
                score_key = key.replace('_desc', '')
                score = vocab['scores'].get(score_key, 'N/A')
                lines.append(f"- **{score_key}**: {score} - {value}")
        lines.append("")
        
        # 句子维度详细分析
        lines.append("## 📝 句子维度分析")
        lines.append("")
        sentence = analysis_result['sentence_analysis']
        lines.append(f"**句子总数**: {sentence['total_sentences']}")
        lines.append(f"**平均句长**: {sentence['avg_sentence_length']} 词/句")
        lines.append(f"**最大嵌套深度**: {sentence['max_nesting_depth']} 层")
        lines.append("")
        lines.append("### 评分详情")
        lines.append("")
        for key, value in sentence['scores'].items():
            if key.endswith('_desc'):
                score_key = key.replace('_desc', '')
                score = sentence['scores'].get(score_key, 'N/A')
                lines.append(f"- **{score_key}**: {score} - {value}")
        lines.append("")
        
        # 篇章维度详细分析
        lines.append("## 📖 篇章维度分析")
        lines.append("")
        passage = analysis_result['passage_analysis']
        lines.append(f"**文本长度**: {passage['text_length']} 字符")
        lines.append(f"**句子数量**: {passage['sentence_count']}")
        lines.append(f"**信息密度**: {passage['info_density']} 字符/句")
        lines.append("")
        lines.append("### 评分详情")
        lines.append("")
        for key, value in passage['scores'].items():
            if key.endswith('_desc'):
                score_key = key.replace('_desc', '')
                score = passage['scores'].get(score_key, 'N/A')
                lines.append(f"- **{score_key}**: {score} - {value}")
        lines.append("")
        
        # 题目维度分析
        lines.append("## ❓ 题目维度分析")
        lines.append("")
        question = analysis_result['question_analysis']
        if 'note' in question:
            lines.append(f"**注意**: {question['note']}")
        else:
            lines.append(f"**题目数量**: {question['question_count']}")
            lines.append("")
            lines.append("### 评分详情")
            lines.append("")
            for key, value in question['scores'].items():
                if key.endswith('_desc'):
                    score_key = key.replace('_desc', '')
                    score = question['scores'].get(score_key, 'N/A')
                    lines.append(f"- **{score_key}**: {score} - {value}")
        lines.append("")
        
        # 需要人工评估的指标
        lines.append("## ⚠️ 需要人工评估的指标")
        lines.append("")
        needs_human = difficulty['needs_human_assessment']
        if needs_human:
            lines.append("以下指标需要人工补充评估：")
            lines.append("")
            for i, item in enumerate(needs_human, 1):
                lines.append(f"{i}. {item}")
            lines.append("")
            lines.append("**评估方法**: 请参考 `references/human_assessment.md` 进行评分，然后将评分结果添加到分析结果中。")
        else:
            lines.append("✅ 所有指标已完成评估")
        lines.append("")
        
        # 建议
        lines.append("## 💡 建议")
        lines.append("")
        level = difficulty['difficulty_level']
        if level == 'E':
            lines.append("- 适合英语初学者练习")
            lines.append("- 建议用于基础阅读训练")
        elif level == 'M':
            lines.append("- 适合英语中级学习者")
            lines.append("- 可用于日常阅读练习")
        elif level == 'H':
            lines.append("- 适合英语高级学习者")
            lines.append("- 建议配备词汇表和注释")
        else:
            lines.append("- 适合英语母语者或专业学习者")
            lines.append("- 建议提供详细讲解和背景知识")
        lines.append("")
        
        # 写入文件
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        
        print(f"Markdown报告已生成: {output_path}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='英文阅读材料难度分析工具')
    parser.add_argument('--text', type=str, help='输入文本文件路径')
    parser.add_argument('--text-content', type=str, help='直接输入文本内容')
    parser.add_argument('--questions', type=str, help='题目文本文件路径（可选）')
    parser.add_argument('--output', type=str, default='difficulty_report', help='输出文件前缀')
    
    args = parser.parse_args()
    
    # 获取文本
    if args.text:
        with open(args.text, 'r', encoding='utf-8') as f:
            text = f.read()
    elif args.text_content:
        text = args.text_content
    else:
        print("错误: 必须提供 --text 或 --text-content 参数")
        sys.exit(1)
    
    # 获取题目
    questions_text = None
    if args.questions:
        with open(args.questions, 'r', encoding='utf-8') as f:
            questions_text = f.read()
    
    # 获取assets目录
    script_dir = Path(__file__).parent
    assets_dir = script_dir.parent / 'assets'
    
    # 加载spacy模型
    print("正在加载spaCy模型...")
    try:
        nlp = spacy.load('en_core_web_sm')
    except OSError:
        print("错误: 未找到 en_core_web_sm 模型")
        print("请运行: python -m spacy download en_core_web_sm")
        sys.exit(1)
    
    # 初始化分析器
    print("正在初始化分析器...")
    vocab_analyzer = VocabularyAnalyzer(assets_dir)
    sentence_analyzer = SentenceAnalyzer(nlp)
    passage_analyzer = PassageAnalyzer()
    question_analyzer = QuestionAnalyzer()
    difficulty_calculator = DifficultyCalculator()
    report_generator = ReportGenerator()
    
    # 处理文本
    print("正在分析文本...")
    doc = nlp(text)
    tokens = [token.text for token in doc if not token.is_punct and not token.is_space]
    
    # 执行分析
    vocab_analysis = vocab_analyzer.analyze_vocabulary(tokens)
    sentence_analysis = sentence_analyzer.analyze_sentences(doc)
    passage_analysis = passage_analyzer.analyze_passage(text, doc)
    question_analysis = question_analyzer.analyze_questions(questions_text)
    
    # 计算难度
    difficulty_calculation = difficulty_calculator.calculate_total_score(
        vocab_analysis, sentence_analysis, passage_analysis, question_analysis
    )
    
    # 组装结果
    analysis_result = {
        'vocabulary_analysis': vocab_analysis,
        'sentence_analysis': sentence_analysis,
        'passage_analysis': passage_analysis,
        'question_analysis': question_analysis,
        'difficulty_calculation': difficulty_calculation
    }
    
    # 生成报告
    report_generator.generate_json_report(analysis_result, f"{args.output}.json")
    report_generator.generate_markdown_report(analysis_result, f"{args.output}.md")
    
    print("\n分析完成！")
    print(f"难度等级: {difficulty_calculation['difficulty_level']} ({difficulty_calculation['difficulty_description']})")
    print(f"自动评估得分: {difficulty_calculation['auto_total']}/100")
    
    if difficulty_calculation['needs_human_assessment']:
        print(f"\n⚠️  还有 {len(difficulty_calculation['needs_human_assessment'])} 个指标需要人工评估")


if __name__ == '__main__':
    main()
