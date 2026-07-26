# LLM Selection — Qwen3 8B Instruct

## Why Qwen3 8B Instruct?

### Model Selection Rationale

We evaluated leading open-source LLMs for this project. The key requirements are:
1. **Tool calling support** — must reliably generate function calls
2. **Reasoning quality** — must analyze building data and make optimization decisions
3. **Local inference** — must run offline on consumer hardware
4. **Acceptable latency** — responses within 2-10 seconds
5. **Open license** — no commercial restrictions

### Comparison Matrix

| Model | Parameters | VRAM | Tool Calling | Reasoning | License | Latency (RTX 3060) |
|---|---|---|---|---|---|---|
| **Qwen3 8B Instruct** | 8B | ~5 GB | ✅ Native | ⭐⭐⭐⭐⭐ | Apache 2.0 | ~3s |
| Llama 3.1 8B Instruct | 8B | ~5 GB | ✅ Native | ⭐⭐⭐⭐ | Llama 3.1 | ~3s |
| Mistral 7B Instruct v0.3 | 7B | ~4.5 GB | ⚠️ Limited | ⭐⭐⭐ | Apache 2.0 | ~2.5s |
| Gemma 2 9B | 9B | ~6 GB | ⚠️ Via prompting | ⭐⭐⭐⭐ | Gemma | ~4s |
| Qwen3 32B | 32B | ~20 GB | ✅ Native | ⭐⭐⭐⭐⭐ | Apache 2.0 | ~15s |
| Llama 3.1 70B | 70B | ~40 GB | ✅ Native | ⭐⭐⭐⭐⭐ | Llama 3.1 | Requires A100 |

### Why Qwen3 8B Wins

1. **Best-in-Class at 8B Scale**: Qwen3 8B consistently outperforms Llama 3.1 8B and Mistral 7B on MMLU, HumanEval, GSM8K, and tool-calling benchmarks
2. **Native Tool Calling**: First-class support via Ollama's `tools` parameter — no custom prompt hacking needed
3. **Thinking Mode**: Built-in chain-of-thought via `<thinking>` tags improves reasoning quality for complex optimization decisions
4. **Apache 2.0 License**: Fully permissive — no usage restrictions, no commercial limitations
5. **Reasonable Resources**: 5GB download, runs on 8GB VRAM or 16GB RAM (CPU mode)
6. **Active Ecosystem**: Strong community support, Ollama integration is mature

### Why Not Larger Models?

- **32B+ models** require 20+ GB VRAM (RTX 4090 or A100) — defeats "runs on a laptop" requirement
- **70B+ models** require enterprise GPUs — completely impractical for a hackathon PoC
- **8B is the sweet spot**: Good enough reasoning for building optimization, fast enough for interactive use

---

## Ollama Setup

### What is Ollama?

Ollama is an open-source tool for running LLMs locally. It handles model downloading, quantization, GPU acceleration, and provides an OpenAI-compatible REST API.

### Installation

#### Windows
```bash
# Download from https://ollama.com/download
# Run the installer: OllamaSetup.exe
# Ollama runs as a system service on port 11434

# Verify:
ollama --version
# Expected: ollama version 0.x.x
```

#### Linux
```bash
curl -fsSL https://ollama.ai/install.sh | sh

# Verify:
ollama --version
```

#### macOS
```bash
# Download from https://ollama.com/download
# Or via Homebrew:
brew install ollama

# Start the service:
ollama serve
```

### Download Qwen3 8B

```bash
# Pull the model (downloads ~5GB)
ollama pull qwen3:8b

# Verify model is available:
ollama list
# Expected output includes: qwen3:8b

# Test the model:
ollama run qwen3:8b "What is building energy optimization?"

# Test with tool calling (via API):
curl http://localhost:11434/api/chat -d '{
  "model": "qwen3:8b",
  "messages": [
    {"role": "user", "content": "What is the temperature in zone 1?"}
  ],
  "tools": [
    {
      "type": "function",
      "function": {
        "name": "read_building_state",
        "description": "Read building zone state",
        "parameters": {
          "type": "object",
          "properties": {
            "zone_name": {"type": "string", "description": "Zone name"}
          }
        }
      }
    }
  ]
}'
```

### Resource Requirements

| Resource | Minimum | Recommended |
|---|---|---|
| **RAM** | 8 GB (CPU mode) | 16 GB |
| **VRAM** | 5 GB (GPU mode) | 8 GB |
| **Disk** | 5 GB | 10 GB |
| **CPU** | 4 cores | 8+ cores |
| **GPU** | Optional (CUDA/Metal) | RTX 3060+ or M1+ |

### Configuration

```bash
# Set context window (for multi-turn agent conversations)
# Create a Modelfile if needed:
echo 'FROM qwen3:8b
PARAMETER num_ctx 8192' > Modelfile

ollama create qwen3-ecoloop -f Modelfile
```

### Troubleshooting

| Issue | Solution |
|---|---|
| `connection refused` | Ensure `ollama serve` is running |
| Slow responses | Check GPU is being used: `ollama ps` |
| Out of memory | Reduce `num_ctx` or use CPU mode |
| Tool calls not working | Ensure Ollama version >= 0.3.0 |
| Model not found | Run `ollama pull qwen3:8b` |

---

## LangChain Integration

### ChatOllama Wrapper

```python
from langchain_ollama import ChatOllama

llm = ChatOllama(
    model="qwen3:8b",
    temperature=0.1,       # Low temp for deterministic tool calling
    base_url="http://localhost:11434",
    num_ctx=8192,          # Context window
)

# With tool binding
llm_with_tools = llm.bind_tools(tools)
```

### Key Settings

| Setting | Value | Rationale |
|---|---|---|
| `temperature` | 0.1 | Low randomness for reliable tool calling |
| `num_ctx` | 8192 | Sufficient for building state + reasoning |
| `repeat_penalty` | 1.1 | Prevent repetitive outputs |
| `top_p` | 0.9 | Nucleus sampling for quality |

---

## Prompt Engineering Documentation

### Principles

1. **Explicit Role Assignment**: Every prompt starts with "You are the [X] Agent"
2. **Structured Output**: Prompts request JSON-formatted responses
3. **Boundary Setting**: Clearly state what the agent should NOT do
4. **Domain Knowledge**: Include ASHRAE standards, comfort ranges, energy terminology
5. **Safety First**: Every control prompt includes safety constraints
6. **Conciseness**: Keep prompts under 500 tokens to leave room for context

### Prompt Template Structure

```
ROLE: You are the {agent_name} in a building optimization system.
TASK: {specific_task_description}
CONTEXT: {relevant_domain_knowledge}
CONSTRAINTS: {safety_bounds_and_limits}
OUTPUT FORMAT: {expected_response_structure}
EXAMPLES: {1-2 few-shot_examples_if_needed}
```

### Token Budget

| Component | Tokens |
|---|---|
| System prompt | ~300-500 |
| Building state context | ~500-1000 |
| Historical data | ~500-1000 |
| Tool schemas | ~500 |
| Response | ~500-1000 |
| **Total per turn** | **~2000-4000** |
| Context window | 8192 |
| **Headroom** | **~4000 tokens** |

All prompts are documented in [docs/agents.md](agents.md) under each agent definition.
