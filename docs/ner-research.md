# 中文命名实体识别（NER）方案调研

> 调研目的：为 OpenMontage（Python 视频生产工具）选择一个**准确率高、国内网络可用**的中文 NER 方案。
> 环境约束：已有 `transformers 5.x + torch (CPU) + jieba`；`huggingface.co` 不可访问（超时）；`modelscope.cn`、`GitHub`、`pypi` 可访问。
> 调研方法：逐项从 primary source（官方文档 / 模型卡 / GitHub README / ModelScope 官方 API）核实；所有链接均附在文中。本环境无法直接打开 huggingface.co（实测超时），涉及 HF 的内容已尽量用可访问的官方镜像或替代来源交叉验证，未验证到 primary 数据的地方均明确标注。

---

## 结论速览

| 方案 | 实体类别 | 模型大小 | 国内可用性 | 许可 | 官方报告 F1 |
|---|---|---|---|---|---|
| ModelScope `iic/nlp_bert_named_entity_recognition_chinese-base` | ⚠️ **模型已不可用**（ModelScope 返回 record not found） | — | — | — | — |
| ModelScope `damo/nlp_raner_named-entity-recognition_chinese-base-news`（推荐替代） | 3 类：人名/地名/机构名 | 约 409 MB | ✅ 国内直连 | Apache 2.0 | MSRA F1 **96.69** |
| HF `uer/roberta-base-finetuned-cluener2020-chinese` | 10 类细粒度（CLUENER2020） | 约 400 MB | ⚠️ 需走 hf-mirror | 未声明限制（HF 模型卡） | CLUENER2020 上约 79–80（BERT-base 级） |
| 哈工大 LTP（`ltp` 包） | 3 类：人名/机构名/地名 | 约 400 MB（base） | ✅ 国内直链 + 清华源 | ⚠️ 商业用途需付费 | OntoNotes 4.0 F1 **96.39**（Base1） |
| HanLP 2.x | PKU / MSRA(3) / OntoNotes(多) | 数十 MB～数百 MB | ✅ 模型在 hankcs 服务器 | ⚠️ 中文模型仅供研究与教学 | MSRA 96.04（多任务 base） |
| jieba posseg / spaCy zh | — | — | — | — | 不推荐（见下文） |

> 注：不同数据集（MSRA 3 类 vs CLUENER2020 10 类）的 F1 **不可直接横向比较**——类别数越多、粒度越细，F1 越低属正常现象。

---

## 1. ModelScope 达摩院模型 `iic/nlp_bert_named_entity_recognition_chinese-base`

### ⚠️ 关键发现：该模型当前在 ModelScope 上已不可用

本调研通过 ModelScope 官方 API 实测验证（2026-02）：

- `https://modelscope.cn/api/v1/models/iic/nlp_bert_named_entity_recognition_chinese-base` → `{"Code":10010205001,"Message":"获取模型信息失败，信息：record not found"}`
- `damo/` 前缀（`damo/nlp_bert_named_entity_recognition_chinese-base`）同样 `record not found`；
- 文件树接口（`/repo/files`）与 revision 接口（`/revisions`）均返回 `record not found`。

结论：**该模型 ID 已从 ModelScope 下架或迁移，模型页链接已失效**，无法从 primary source 核实其实体类别 / 基座 / F1。因此**不建议继续选用**。若项目中存在引用该模型 ID 的代码，需要一并更新。

### ✅ 推荐替代（已验证可用，同属通义实验室/达摩院）：`damo/nlp_raner_named-entity-recognition_chinese-base-news`

模型卡：https://modelscope.cn/models/damo/nlp_raner_named-entity-recognition_chinese-base-news
（ModelScope 官方 API 元数据、`config.json`、README 均已在本次调研中实测获取。）

| 项目 | 内容 |
|---|---|
| 实体类别 | **3 类**：地名 `LOC`、机构名 `ORG`、人名 `PER`（BIOES 标注，`num_labels=13`） |
| 模型基座 | **StructBERT-base**（`config.json` 中 `model_type="bert"`，hidden_size 768、12 层、vocab 21128），Transformer + CRF 解码 |
| 训练数据 | MSRA 中文新闻领域 NER 公开数据集，50,729 句 |
| 准确性（模型卡官方） | MSRA 测试集 **F1 = 96.69**（P 96.41 / R 96.98）；分类型：LOC 97.31 / ORG 93.48 / PER 98.26 |
| 模型大小 | `pytorch_model.bin` 约 **409 MB**（无 safetensors 文件） |
| 格式 | 标准 HuggingFace 结构：`config.json` + `tokenizer_config.json` + `vocab.txt` + `pytorch_model.bin`，可被 transformers 的 `AutoModelForTokenClassification` 加载 |
| 国内可用性 | ✅ ModelScope 国内直连，模型下载量 280 万+ |
| 许可 | Apache License 2.0（商业友好） |

**集成注意事项（重要）**：该模型权重为 `pytorch_model.bin` 而非 `safetensors`。ModelScope 官方在同类达摩院模型的 README 中明确指出：**最新版 transformers 加载 `.bin` 权重会触发安全限制**（`ValueError: ... CVE-2025-32434 ...`，要求 torch ≥ 2.6；`safetensors` 格式无此限制）。因此集成时二选一：

1. 安装 torch ≥ 2.6；或
2. 用 `transformers`/`torch` 将权重转存为 `model.safetensors` 后再加载。

调用方式（两种均可）：

```python
# 方式 A：ModelScope pipeline（最省事）
from modelscope.pipelines import pipeline
from modelscope.utils.constant import Tasks
ner = pipeline(Tasks.named_entity_recognition, 'damo/nlp_raner_named-entity-recognition_chinese-base-news')
print(ner('国正先生在我心中就是这样的一位学长。'))
# -> {'output': [{'type': 'PER', 'start': 0, 'end': 2, 'span': '国正'}]}

# 方式 B：直接用 transformers（本项目已有 transformers 5.x）
from transformers import AutoTokenizer, AutoModelForTokenClassification
tok = AutoTokenizer.from_pretrained('/path/to/model_dir')
model = AutoModelForTokenClassification.from_pretrained('/path/to/model_dir')
```

---

## 2. HuggingFace `uer/roberta-base-finetuned-cluener2020-chinese`

模型页：https://huggingface.co/uer/roberta-base-finetuned-cluener2020-chinese
（本环境实测 `huggingface.co` 超时不可达，以下信息以 CLUENER2020 官方仓库等可访问来源核实，模型卡 F1 数字未能在本环境直接打开验证。）

| 项目 | 内容 |
|---|---|
| 实体类别 | **10 类细粒度**（CLUENER2020）：地址 `address`、书名 `book`、公司 `company`、游戏 `game`、政府 `government`、电影 `movie`、姓名 `name`、组织机构 `organization`、职位 `position`、景点 `scene`（来源：CLUENER2020 官方 GitHub https://github.com/CLUEbenchmark/CLUENER2020 ） |
| 模型基座 | RoBERTa-base 中文（UER 系列 `chinese_roberta_L-12_H-768_A-12`）＋ token classification 头 |
| 格式 | 标准 HuggingFace transformers 格式，`AutoModelForTokenClassification.from_pretrained('uer/roberta-base-finetuned-cluener2020-chinese')` 一行加载 |
| 模型大小 | 约 400 MB（RoBERTa-base） |
| 准确性 | CLUENER2020 官方榜单 F1：BERT-base **78.82**，RoBERTa-wwm-large-ext **80.42**；本模型为 RoBERTa-base 微调版，预期与之同量级（具体以模型卡为准，本环境未能打开模型卡验证） |
| 国内可用性 | ⚠️ HF 主站不可达。国内一般通过 **hf-mirror.com**（`pip`/`transformers` 设 `HF_ENDPOINT=https://hf-mirror.com`）或 hugging-face.cn 获取；本调研环境对非大陆 IP 会跳转回原站，**未能在本环境实测下载成功**。国内生产环境需自行验证镜像连通性 |
| 集成成本 | 最低（标准 HF 加载流程） |

**适用性判断**：10 类细粒度类别是它最大的价值（尤其"职位/公司/游戏/景点"这些细类）；但若视频工具只需要人名/地名/机构名，3 类模型（方案 1/3）准确率明显更高、下载更省事。

---

## 3. 哈工大 LTP（pip 包 `ltp`）

官方仓库：https://github.com/HIT-SCIR/ltp ｜ 文档：ltp.ai

| 项目 | 内容 |
|---|---|
| 实体类别 | **3 类**：`Nh` 人名 / `Ni` 机构名 / `Ns` 地名（官方附录文档 https://github.com/HIT-SCIR/ltp/blob/main/python/interface/docs/appendix.rst ） |
| 模型下载源 | HuggingFace（`LTP/base` 等）或 **hf-mirror**；另有**国内直链** `http://39.96.43.154/ltp/v4/base.tgz`（阿里云 IP，README 提供，国内可直接 wget） |
| 准确性（官方模型表） | NER F1（OntoNotes 4.0 中文）：Base1 **96.39** / Base **95.4** / Small 94.3 / Tiny 91.6 / Legacy（感知机）94.28 |
| 模型大小 | base 约 400 MB（small/tiny 更小） |
| 国内可用性 | ✅ 官方文档明确推荐用清华 TUNA 源安装：`pip install -i https://pypi.tuna.tsinghua.edu.cn/simple ltp ltp-core ltp-extension` |
| 集成成本 | 中等：`pip install ltp`；依赖 **torch + transformers**（本项目已具备）；Pipeline API（`tasks=["cws","pos","ner"]`）；NER 依赖分词+词性结果 |
| 许可 | ⚠️ **商业用途需付费**（README 声明：面向高校/中科院/个人研究者免费，企业合作等商业目的需付费） |

**适用性判断**：准确率高、国内获取零障碍，是很好的"模型库"级选择；但对商业闭源产品有许可风险，需要确认 OpenMontage 的发布方式。

---

## 4. HanLP 2.x

官方仓库：https://github.com/hankcs/HanLP ｜ 文档：https://hanlp.hankcs.com/docs/

| 项目 | 内容 |
|---|---|
| 实体类别 | 支持多种标注体系：PKU、**MSRA（3 类）**、**OntoNotes（多类，如人名/地名/机构/日期等）**、电商细分类等 |
| 模型下载源 | **`https://file.hankcs.com/hanlp/...`**（hankcs 官方服务器，国内可访问）；例如 `MSRA_NER_BERT_BASE_ZH = https://file.hankcs.com/hanlp/ner/ner_bert_base_msra_20211227_114712.zip` |
| 准确性（官方性能表） | 中文多任务模型 zh open base（MSRA）NER F1 **96.04**；单任务 BERT-base 在 MSRA 上更高（README 明确"单任务学习性能往往优于多任务"，建议在乎精度用单任务模型） |
| 模型大小 | 数十 MB（Electra-small）～数百 MB（BERT-base） |
| 集成成本 | 中等：`pip install hanlp`；PyTorch 引擎；首次使用自动下载模型 zip 并解压缓存；RESTful / native API 均支持 |
| 许可 | ⚠️ 源代码 Apache 2.0，但 **中文预训练模型授权为"仅供研究与教学使用"**（README 声明），商业产品存在授权风险 |
| 国内可用性 | ✅ 模型在 hankcs 服务器，国内可直接下载 |

**适用性判断**：功能最全（分词/词性/NER/句法/SRL 全家桶），但**中文模型的研究用途授权**限制了商业使用，与 LTP 一样需要先确认 OpenMontage 的发布/授权模式。

---

## 5. 其他候选的评估

### jieba posseg（已有依赖，但不适合当 NER）
- `jieba.posseg` 是**分词 + 词性标注**，不是真正的命名实体识别：它对已切分好的词打粗词性标签（`nr` 人名、`ns` 地名、`nt` 机构名等），**没有实体边界识别、没有统一实体类别体系**。
- 词典 + 规则 + HMM 的准确率有限：多字人名/机构名常被切碎（如"深圳华强北科技"），未登录词基本漏检。
- **结论**：只能作为零依赖兜底/粗筛，不能作为主 NER 方案。

### spaCy 中文（`zh_core_web_sm/md/lg`）
- spaCy 官方中文模型的 NER 质量差：中文模型分词依赖 jieba，NER 主要靠规则，实体类型少且识别率低，社区普遍不推荐用于中文生产。
- Transformer 版 `zh_core_web_trf` 质量尚可，但需从 huggingface.co 下载（国内不可直达）且体积大。
- **结论**：不推荐，除非项目已重度使用 spaCy 且只做英文/混合文本。

### 其他可选方向（供参考）
- **自行微调**：在 CLUENER2020 上微调 RoBERTa/BERT，可获得 10 类细粒度 NER（约 79–80 F1），且权重可托管到 ModelScope 国内分发；代价是需要标注数据 + GPU 训练。
- **开放域/零样本抽取大模型**：如 ModelScope 的 `damo/nlp_seqgpt-560m`（README 声明无需训练即可完成实体识别等任务），适合实体类型动态变化的场景，但 CPU 推理慢、工程依赖重。

---

## 6. 推荐

### 首选：ModelScope `damo/nlp_raner_named-entity-recognition_chinese-base-news`（3 类，MSRA）

理由：

1. **国内网络零障碍**：ModelScope 国内直连下载（下载量 280 万+），完全避开 huggingface.co 不可达的问题。
2. **准确率高**：MSRA 官方 F1 **96.69**（PER 98.26 / LOC 97.31 / ORG 93.48），与视频生产工具"提取人名/地名/机构名"的核心诉求高度匹配。
3. **许可友好**：Apache 2.0，可放心用于商业产品。
4. **集成成本低且与现有依赖兼容**：标准 HF BERT 格式，`AutoModelForTokenClassification` 直接加载（本项目已有 transformers 5.x）；只需注意 `.bin` 权重与新版 transformers 的 CVE 限制——升级 torch ≥ 2.6 或转 `safetensors` 即可。
5. 训练数据（MSRA 新闻）与视频字幕/文稿类文本的分布相近，泛化预期良好。

### 备选 / 何时换方案

- **需要 10 类细粒度实体**（职位、公司、景点等）→ 评估/微调 CLUENER2020 类模型（方案 2 的类别体系），但 F1 会降到约 80 且需解决 HF 镜像下载问题。
- **需要"全家桶"且能接受 3 类、确认许可** → 哈工大 LTP（F1 96.39，国内直链 + 清华源，但商业需付费）。
- **HanLP / spaCy zh / jieba posseg** → 不建议作为主 NER（分别受中文模型研究授权、NER 质量、能力缺失限制）。

### 行动项

- [ ] 若代码中引用了 `iic/nlp_bert_named_entity_recognition_chinese-base`，替换为 `damo/nlp_raner_named-entity-recognition_chinese-base-news`。
- [ ] 集成时处理 `.bin` 权重与 transformers 5.x 的兼容（升级 torch 或转 safetensors）。
- [ ] 国内机器上实测一次 ModelScope 下载与 CPU 推理速度（MSRA base 在 CPU 上单句约数百毫秒量级，建议压测后再定模型）。

---

## 来源链接

- ModelScope RaNER 中文模型卡：https://modelscope.cn/models/damo/nlp_raner_named-entity-recognition_chinese-base-news
- CLUENER2020 官方仓库（10 类定义与 F1 榜单）：https://github.com/CLUEbenchmark/CLUENER2020
- LTP 官方仓库（模型性能表、国内直链、安装方式、许可）：https://github.com/HIT-SCIR/ltp
- LTP NER 标注集附录：https://github.com/HIT-SCIR/ltp/blob/main/python/interface/docs/appendix.rst
- HanLP 官方仓库（性能表、许可声明）：https://github.com/hankcs/HanLP
- HanLP 预训练 NER 模型与下载地址：https://hanlp.hankcs.com/docs/api/hanlp/pretrained/ner.html
- ModelScope 分词模型 README（`.bin` 权重与 transformers 5.x 兼容性说明）：https://modelscope.cn/models/damo/nlp_structbert_word-segmentation_chinese-base
- AdaSeq（达摩院序列标注框架，含全部 RaNER 模型卡列表）：https://github.com/modelscope/AdaSeq/blob/master/docs/modelcards.md

> 调研记录（2026-02，本环境实测）：`huggingface.co`、`hf-mirror.com`（非大陆 IP 跳转）、`web.archive.org` 均不可达，故 uer CLUENER 模型卡原始数字未能直接核对，已在文中标注。
