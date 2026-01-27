# Configuração do Serviço de Voz

Guia rápido para configurar o envio de mensagens de voz usando Eleven Labs + UAZAPI.

## Código do SDK Eleven Labs

```python
from elevenlabs.client import ElevenLabs

client = ElevenLabs(api_key="YOUR_API_KEY")

audio = client.text_to_speech.convert(
    text="Olá! Como posso ajudá-lo hoje?",
    voice_id="xPnmQf6Ow3GGYWWURFPi",
    model_id="eleven_multilingual_v2",
    output_format="mp3_44100_128",
)

# audio é um generator - coletar bytes
audio_bytes = b"".join(chunk for chunk in audio)
```

## 1. Requisitos

### 1.1. Conta Eleven Labs

1. Crie uma conta em [elevenlabs.io](https://elevenlabs.io)
2. Obtenha sua **API Key** em Profile → API Keys (formato: `sk_xxx`)
3. Escolha ou clone uma voz e copie o **Voice ID**

### 1.2. FFmpeg

O serviço de voz requer FFmpeg para conversão de áudio.

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install ffmpeg

# macOS
brew install ffmpeg

# Verificar instalação
ffmpeg -version
```

### 1.3. Supabase Storage

Crie um bucket para armazenar os arquivos de áudio:

1. Acesse o Supabase Dashboard
2. Vá em Storage → New Bucket
3. Nome: `audio-messages`
4. Marque como **Public** (para URLs públicas)
5. Clique em Create Bucket

Ou via SQL:

```sql
-- No Supabase SQL Editor
INSERT INTO storage.buckets (id, name, public)
VALUES ('audio-messages', 'audio-messages', true);

-- Política para upload (service key)
CREATE POLICY "Service can upload audio" ON storage.objects
FOR INSERT WITH CHECK (bucket_id = 'audio-messages');

-- Política para leitura pública
CREATE POLICY "Public can read audio" ON storage.objects
FOR SELECT USING (bucket_id = 'audio-messages');
```

## 2. Variáveis de Ambiente

Adicione ao seu `.env`:

```env
# Eleven Labs
ELEVEN_LABS_API_KEY=sk-your-eleven-labs-key
ELEVEN_LABS_VOICE_ID=JBFqnCBsd6RMkjVDRZzb
ELEVEN_LABS_MODEL_ID=eleven_multilingual_v2

# Voice Config
VOICE_ENABLED=true
VOICE_OUTPUT_FORMAT=opus_48000_64
```

## 3. Testando

### 3.1. Health Check

```bash
curl http://localhost:8000/api/voice/health
```

Resposta esperada:
```json
{
  "tts_configured": true,
  "ffmpeg_available": true,
  "storage_configured": true,
  "voice_enabled": true,
  "overall": true
}
```

### 3.2. Listar Vozes

```bash
curl http://localhost:8000/api/voice/voices
```

### 3.3. Verificar Uso

```bash
curl http://localhost:8000/api/voice/usage
```

### 3.4. Testar Síntese (sem enviar)

```bash
curl -X POST http://localhost:8000/api/voice/synthesize \
  -H "Content-Type: application/json" \
  -d '{"text": "Olá! Este é um teste de voz."}'
```

### 3.5. Enviar Mensagem de Voz

```bash
curl -X POST http://localhost:8000/api/voice/test \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Olá! Esta é uma mensagem de voz automática.",
    "phone": "5511999999999",
    "also_send_text": false
  }'
```

## 4. Uso no Código

### 4.1. Envio Básico

```python
from src.services.voice import get_voice_service

voice = get_voice_service()

# Enviar mensagem de voz
result = await voice.send_voice_message(
    phone="5511999999999",
    text="Olá! Como posso ajudá-lo hoje?"
)

if result["success"]:
    print(f"Audio URL: {result['audio_url']}")
```

### 4.2. Com Fallback para Texto

```python
# Se voz falhar, envia texto automaticamente
result = await voice.send_voice_with_fallback(
    phone="5511999999999",
    text="Mensagem que será enviada como voz ou texto"
)

print(f"Método de entrega: {result['delivery_method']}")  # 'voice' ou 'text_fallback'
```

### 4.3. Usar Voz Específica

```python
result = await voice.send_voice_message(
    phone="5511999999999",
    text="Esta mensagem usa uma voz específica",
    voice_id="outra-voice-id-aqui"
)
```

## 5. Integração com Agente

Para que o agente envie mensagens de voz automaticamente, atualize a configuração da empresa:

```sql
UPDATE companies
SET voice_config = '{
    "enabled": true,
    "voice_only": false,
    "eleven_labs_voice_id": "seu-voice-id",
    "voice_settings": {
        "stability": 0.5,
        "similarity_boost": 0.75
    }
}'::jsonb
WHERE id = 1;
```

## 6. Custos

| Plano Eleven Labs | Caracteres/mês | Preço |
|-------------------|----------------|-------|
| Free | 10,000 | $0 |
| Starter | 30,000 | $5/mês |
| Creator | 100,000 | $22/mês |
| Pro | 500,000 | $99/mês |

**Dica**: Use cache para mensagens repetitivas (o serviço já implementa cache automático).

## 7. Troubleshooting

### Erro: "FFmpeg not found"

```bash
# Verificar instalação
which ffmpeg
ffmpeg -version

# Reinstalar se necessário
sudo apt-get install --reinstall ffmpeg
```

### Erro: "Voice ID not configured"

Verifique se `ELEVEN_LABS_VOICE_ID` está configurado no `.env`.

### Erro: "Failed to upload audio"

1. Verifique se o bucket `audio-messages` existe no Supabase
2. Verifique se o bucket é público
3. Verifique as políticas de storage

### Áudio não reproduz como voice message

O WhatsApp requer formato OGG OPUS com parâmetros específicos:
- Codec: libopus
- Sample rate: 48000 Hz
- Canais: 1 (mono)
- Bitrate: 32k mínimo

O serviço já converte automaticamente, mas verifique se FFmpeg suporta libopus:

```bash
ffmpeg -codecs | grep opus
```
