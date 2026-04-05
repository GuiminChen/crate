# 模型与嵌入：多平台配置（OpenAI 兼容）

CRATE 的 **`compile` / `ask` / `wiki-check`** 使用 **`openai` Python 包** 的 **`OpenAI(base_url=…, api_key=…)`**，只要服务商提供 **OpenAI 兼容的 HTTPS Chat Completions**（路径与请求体与 OpenAI 一致），即可接入。

**`crate index`** / **`search --semantic`** 使用同一库调用 **`embeddings.create`**，同样需要 **OpenAI 兼容的嵌入端点**。

以下默认 **base URL** 与 **模型名** 可在各云控制台变更；若与默认不符，请用环境变量覆盖（见下表）。

---

## 1. 聊天（LLM）

### 1.1 选择服务商

设置 **`CRATE_LLM_PROVIDER`**（可选）。若不设置，则按环境中**已出现的密钥**自动推断，优先级大致为：

DeepSeek → 阿里云 DashScope → 火山 Ark → 腾讯混元 → OpenRouter → OpenAI → Azure →（仅 **`CRATE_CHAT_API_KEY`** 时）custom。

| `CRATE_LLM_PROVIDER` | 默认 `base_url`（可用专属变量覆盖） | 默认模型（可覆盖） | 常见密钥环境变量 |
|---------------------|-------------------------------------|-------------------|------------------|
| `deepseek` | `https://api.deepseek.com` | `deepseek-chat` | `CRATE_DEEPSEEK_API_KEY` / `DEEPSEEK_API_KEY` |
| `openai` | `https://api.openai.com/v1` | `gpt-4o-mini` | `CRATE_OPENAI_API_KEY` / `OPENAI_API_KEY` |
| `aliyun` | `https://dashscope.aliyuncs.com/compatible-mode/v1` | `qwen-turbo` | `CRATE_DASHSCOPE_API_KEY` / `DASHSCOPE_API_KEY` |
| `volcengine` / `bytedance` | `https://ark.cn-beijing.volces.com/api/v3` | `doubao-pro-32k` | `CRATE_ARK_API_KEY` / `ARK_API_KEY` |
| `tencent` | `https://api.hunyuan.cloud.tencent.com/v1` | `hunyuan-turbo` | `CRATE_HUNYUAN_API_KEY` / `HUNYUAN_API_KEY` |
| `openrouter` | `https://openrouter.ai/api/v1` | `openai/gpt-4o-mini` | `CRATE_OPENROUTER_API_KEY` / `OPENROUTER_API_KEY` |
| `azure_openai` | 见下文 | `AZURE_OPENAI_DEPLOYMENT` 或 `CRATE_CHAT_MODEL` | `AZURE_OPENAI_API_KEY` / `CRATE_AZURE_OPENAI_API_KEY` |
| `custom` | **必填** `CRATE_CHAT_BASE_URL` | `CRATE_CHAT_MODEL` 或 `gpt-4o-mini` | `CRATE_CHAT_API_KEY` |

### 1.2 通用覆盖（任意服务商）

| 变量 | 含义 |
|------|------|
| `CRATE_CHAT_API_KEY` | 统一覆盖「当前 provider」解析出的密钥（最高优先级）。 |
| `CRATE_CHAT_BASE_URL` | 统一覆盖 `base_url`（用于自建网关、代理或与默认不同的区域端点）。 |
| `CRATE_CHAT_MODEL` | 在 **未** 设置 `CRATE_MODEL_COMPILE` / `CRATE_MODEL_QA` / `CRATE_MODEL_LINT` 时，作为默认模型名；仍可与 `CRATE_DEEPSEEK_MODEL` 链式配合（兼容旧名）。 |

Purpose 专用模型：**`CRATE_MODEL_COMPILE`**、**`CRATE_MODEL_QA`**、**`CRATE_MODEL_LINT`** 含义不变，见 [usage.md](usage.md) §3.1。

### 1.3 Anthropic Claude（原生 API）

Anthropic **不是** OpenAI 兼容协议。可选方式：

- 使用 **[OpenRouter](https://openrouter.ai/)** 等聚合服务：`CRATE_LLM_PROVIDER=openrouter`，模型填 `anthropic/claude-3.5-sonnet` 等（以 OpenRouter 模型列表为准）。
- 使用自建 **LiteLLM / 兼容网关**，对外暴露 OpenAI 兼容接口，再设 **`CRATE_CHAT_BASE_URL`** 指向网关。

### 1.4 Azure OpenAI

推荐直接设置 **`CRATE_CHAT_BASE_URL`** 为 Azure 门户中给出的 **OpenAI 兼容** 部署 URL（通常含 `api-version` 查询参数），并设置 **`AZURE_OPENAI_API_KEY`**。

或设置 **`AZURE_OPENAI_ENDPOINT`**（资源根 URL，无尾斜杠）+ **`AZURE_OPENAI_DEPLOYMENT`**（部署名），CRATE 会拼接为  
`{ENDPOINT}/openai/deployments/{DEPLOYMENT}`。若调用失败，请核对 Azure 要求的 **`api-version`** 并优先改用完整 **`CRATE_CHAT_BASE_URL`**。

---

## 2. 嵌入（Embedding）

设置 **`CRATE_EMBEDDING_PROVIDER`** 为 **`openai`** | **`aliyun`** | **`volcengine`** | **`tencent`** 之一；不设置时，根据 **`CRATE_EMBEDDING_BASE_URL`** 子串或密钥推断。

| Provider | 默认 `base_url` | 默认模型 |
|----------|-----------------|----------|
| `openai` | `https://api.openai.com/v1` | `text-embedding-3-small` |
| `aliyun` | `https://dashscope.aliyuncs.com/compatible-mode/v1` | `text-embedding-v3` |
| `volcengine` | `https://ark.cn-beijing.volces.com/api/v3` | `doubao-embedding` |
| `tencent` | `https://api.hunyuan.cloud.tencent.com/v1` | `hunyuan-embedding` |

密钥：优先 **`CRATE_EMBEDDING_API_KEY`**（专用于嵌入）；否则各 preset 会回退到 **`OPENAI_API_KEY`**、**`DASHSCOPE_API_KEY`**、**`ARK_API_KEY`** 等（与聊天密钥可分开配置）。

**`CRATE_EMBEDDING_BASE_URL`** / **`CRATE_EMBEDDING_MODEL`** 仍可覆盖默认值。**`CRATE_EMBEDDING_BATCH_SIZE`** 默认 **10**（阿里云等限制较严时保持较小；纯 OpenAI 可调大以加快索引）。

---

## 3. 与聊天共用同一密钥时

若聊天与嵌入均使用 **OpenAI** 且共用 **`OPENAI_API_KEY`**：不设 **`CRATE_EMBEDDING_API_KEY`** 亦可建立语义索引；**`CRATE_LLM_PROVIDER=openai`** 与 **`CRATE_EMBEDDING_PROVIDER=openai`** 时行为一致。

若聊天用 DeepSeek、嵌入用阿里云：请分别为两套 **`base_url` + key + model** 配置，**勿**混用密钥与错误域名（`crate index` 报错信息中会提示）。
