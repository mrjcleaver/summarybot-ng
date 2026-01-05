# Enable multi-provider routing
export CLASP_MULTI_PROVIDER=true

echo ${OPENROUTER_API_KEY:+"OpenRouter API Key is set"}

# Route Opus tier to OpenAI (premium)
#export CLASP_OPUS_PROVIDER=openai
#export CLASP_OPUS_MODEL=gpt-4o
#export CLASP_OPUS_API_KEY=sk-...  # Optional, inherits from OPENAI_API_KEY

# Route Sonnet tier to OpenRouter (cost-effective)
export CLASP_SONNET_PROVIDER=openrouter
export CLASP_SONNET_MODEL=anthropic/claude-3.5-sonnet
#export CLASP_SONNET_API_KEY=sk-or-...  # Optional, inherits from OPENROUTER_API_KEY

# Route Haiku tier to local Ollama (free)
#export CLASP_HAIKU_PROVIDER=custom
#export CLASP_HAIKU_MODEL=llama3.1
#export CLASP_HAIKU_BASE_URL=http://localhost:11434/v1

export CLASP_CACHE=true 
export CLASP_CACHE_MAX_SIZE=500

# Start claude with multi-provider support 

ANTHROPIC_BASE_URL=http://localhost:8080 \
 ANTHROPIC_API_KEY=proxy-key \
 clasp  -multi-provider \
 -auth -auth-api-key "proxy-key"
