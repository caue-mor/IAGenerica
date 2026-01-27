# Análise Técnica: Integração de Áudio com Eleven Labs + UAZAPI

## Sumário Executivo

Esta análise detalha a implementação de mensagens de voz (áudio) no sistema IA-Generica, utilizando **Eleven Labs** para conversão de texto em fala (TTS) e **UAZAPI** para envio via WhatsApp.

---

## 1. Arquitetura da Solução

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           FLUXO DE ÁUDIO                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  1. Agente IA gera resposta em texto                                        │
│           │                                                                  │
│           ▼                                                                  │
│  2. Eleven Labs TTS API                                                      │
│     POST /v1/text-to-speech/{voice_id}                                      │
│     ├── Entrada: texto                                                       │
│     └── Saída: áudio (opus_48000_64)                                        │
│           │                                                                  │
│           ▼                                                                  │
│  3. Conversão para OGG OPUS (se necessário)                                 │
│     FFmpeg/PyDub: -c:a libopus -ar 48000 -ac 1 -b:a 32k                     │
│           │                                                                  │
│           ▼                                                                  │
│  4. Upload para Storage (S3/Supabase)                                       │
│     Gera URL pública temporária                                              │
│           │                                                                  │
│           ▼                                                                  │
│  5. UAZAPI - Envio de Áudio                                                 │
│     POST /message/sendMedia                                                  │
│     ├── media_type: "audio"                                                  │
│     ├── media_url: URL do áudio                                              │
│     └── ptt: true (para voice message)                                       │
│           │                                                                  │
│           ▼                                                                  │
│  6. Cliente recebe áudio no WhatsApp                                         │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Eleven Labs API - Detalhamento Técnico

### 2.1. Endpoint Principal

```
POST https://api.elevenlabs.io/v1/text-to-speech/{voice_id}
```

### 2.2. Headers Obrigatórios

```python
headers = {
    "xi-api-key": "YOUR_ELEVEN_LABS_API_KEY",
    "Content-Type": "application/json",
    "Accept": "audio/mpeg"  # ou audio/ogg para opus
}
```

### 2.3. Request Body

```json
{
    "text": "Olá! Como posso ajudá-lo hoje?",
    "model_id": "eleven_multilingual_v2",
    "voice_settings": {
        "stability": 0.5,
        "similarity_boost": 0.75,
        "style": 0.0,
        "speed": 1.0
    }
}
```

### 2.4. Formatos de Saída Disponíveis (Query Parameter)

| Formato | Parâmetro | Uso Recomendado |
|---------|-----------|-----------------|
| MP3 128kbps | `mp3_44100_128` | Qualidade padrão |
| MP3 192kbps | `mp3_44100_192` | Alta qualidade |
| **Opus 64kbps** | `opus_48000_64` | **WhatsApp (recomendado)** |
| Opus 128kbps | `opus_48000_128` | Alta qualidade streaming |
| PCM 16kHz | `pcm_16000` | Processamento adicional |
| WAV 44.1kHz | `wav_44100` | Edição/arquivamento |

### 2.5. Exemplo Completo em Python

```python
import httpx
from pathlib import Path

class ElevenLabsTTS:
    """Cliente para Eleven Labs Text-to-Speech API."""

    BASE_URL = "https://api.elevenlabs.io/v1"

    def __init__(self, api_key: str, voice_id: str):
        self.api_key = api_key
        self.voice_id = voice_id
        self.client = httpx.AsyncClient(timeout=30.0)

    async def text_to_speech(
        self,
        text: str,
        output_format: str = "opus_48000_64",
        model_id: str = "eleven_multilingual_v2",
        stability: float = 0.5,
        similarity_boost: float = 0.75
    ) -> bytes:
        """
        Converte texto em áudio usando Eleven Labs.

        Args:
            text: Texto para converter em fala
            output_format: Formato de saída do áudio
            model_id: Modelo de voz a usar
            stability: Estabilidade da voz (0-1)
            similarity_boost: Similaridade com voz original (0-1)

        Returns:
            bytes: Dados binários do áudio
        """
        url = f"{self.BASE_URL}/text-to-speech/{self.voice_id}"

        params = {"output_format": output_format}

        payload = {
            "text": text,
            "model_id": model_id,
            "voice_settings": {
                "stability": stability,
                "similarity_boost": similarity_boost,
                "style": 0.0,
                "use_speaker_boost": True
            }
        }

        headers = {
            "xi-api-key": self.api_key,
            "Content-Type": "application/json"
        }

        response = await self.client.post(
            url,
            json=payload,
            params=params,
            headers=headers
        )
        response.raise_for_status()

        return response.content

    async def text_to_speech_stream(
        self,
        text: str,
        output_format: str = "mp3_44100_128"
    ):
        """
        Streaming de áudio para textos longos.
        """
        url = f"{self.BASE_URL}/text-to-speech/{self.voice_id}/stream"

        async with self.client.stream(
            "POST",
            url,
            json={"text": text, "model_id": "eleven_multilingual_v2"},
            params={"output_format": output_format},
            headers={"xi-api-key": self.api_key}
        ) as response:
            async for chunk in response.aiter_bytes():
                yield chunk

    async def close(self):
        await self.client.aclose()
```

---

## 3. Conversão de Áudio para WhatsApp

### 3.1. Requisitos do WhatsApp para Voice Messages (PTT)

| Parâmetro | Valor Obrigatório |
|-----------|-------------------|
| Codec | **libopus** |
| Container | **OGG** |
| Sample Rate | **48000 Hz** |
| Canais | **1 (Mono)** |
| Bitrate | **32k** (mínimo) |
| MIME Type | `audio/ogg; codecs=opus` |

### 3.2. Conversão com PyDub + FFmpeg

```python
import io
import subprocess
from pydub import AudioSegment

class AudioConverter:
    """Conversor de áudio para formato compatível com WhatsApp."""

    @staticmethod
    def convert_to_whatsapp_ogg(
        audio_data: bytes,
        input_format: str = "mp3"
    ) -> bytes:
        """
        Converte áudio para OGG OPUS compatível com WhatsApp PTT.

        Args:
            audio_data: Dados binários do áudio
            input_format: Formato de entrada (mp3, wav, opus)

        Returns:
            bytes: Áudio em formato OGG OPUS
        """
        # Carregar áudio
        audio = AudioSegment.from_file(
            io.BytesIO(audio_data),
            format=input_format
        )

        # Converter para mono se necessário
        if audio.channels > 1:
            audio = audio.set_channels(1)

        # Ajustar sample rate para 48kHz
        audio = audio.set_frame_rate(48000)

        # Exportar como OGG OPUS
        output = io.BytesIO()
        audio.export(
            output,
            format="ogg",
            codec="libopus",
            parameters=[
                "-ac", "1",           # Mono
                "-ar", "48000",       # 48kHz
                "-b:a", "32k",        # Bitrate
                "-application", "voip" # Otimizado para voz
            ]
        )

        return output.getvalue()

    @staticmethod
    def convert_with_ffmpeg(
        audio_data: bytes,
        input_format: str = "mp3"
    ) -> bytes:
        """
        Conversão direta usando FFmpeg (mais confiável).
        """
        process = subprocess.Popen(
            [
                "ffmpeg",
                "-f", input_format,
                "-i", "pipe:0",
                "-c:a", "libopus",
                "-b:a", "32k",
                "-ar", "48000",
                "-ac", "1",
                "-application", "voip",
                "-f", "ogg",
                "pipe:1"
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        output, error = process.communicate(input=audio_data)

        if process.returncode != 0:
            raise RuntimeError(f"FFmpeg error: {error.decode()}")

        return output
```

### 3.3. Otimização: Usar Opus Direto do Eleven Labs

Se usar `output_format=opus_48000_64` no Eleven Labs, o áudio já vem em formato Opus. Porém, ainda precisa ser encapsulado em container OGG:

```python
async def get_whatsapp_ready_audio(
    eleven_labs: ElevenLabsTTS,
    text: str
) -> bytes:
    """
    Gera áudio pronto para WhatsApp em uma única etapa.
    """
    # Obter áudio em Opus do Eleven Labs
    opus_audio = await eleven_labs.text_to_speech(
        text=text,
        output_format="opus_48000_64"  # Já vem em Opus!
    )

    # Encapsular em OGG (conversão leve)
    return AudioConverter.convert_to_whatsapp_ogg(
        opus_audio,
        input_format="opus"
    )
```

---

## 4. UAZAPI - Envio de Áudio

### 4.1. Estrutura do Endpoint (Baseado em APIs similares)

```
POST {UAZAPI_URL}/message/sendMedia
```

ou

```
POST {UAZAPI_URL}/message/sendPtt
```

### 4.2. Request Body para Áudio

```json
{
    "phone": "5511999999999",
    "media": "https://storage.example.com/audio/xyz123.ogg",
    "type": "audio",
    "ptt": true,
    "caption": ""
}
```

### 4.3. Parâmetros

| Parâmetro | Tipo | Descrição |
|-----------|------|-----------|
| `phone` | string | Número com código do país (5511...) |
| `media` | string | URL pública do arquivo de áudio |
| `type` | string | "audio" |
| `ptt` | boolean | `true` = voice message, `false` = arquivo de áudio |
| `caption` | string | Legenda (opcional, geralmente vazio para PTT) |

### 4.4. Exemplo de Implementação

```python
import httpx
from typing import Optional

class UAZAPIClient:
    """Cliente para UAZAPI WhatsApp API."""

    def __init__(self, base_url: str, api_key: str, instance_id: str):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.instance_id = instance_id
        self.client = httpx.AsyncClient(timeout=30.0)

    async def send_audio(
        self,
        phone: str,
        audio_url: str,
        ptt: bool = True,
        caption: Optional[str] = None
    ) -> dict:
        """
        Envia mensagem de áudio via WhatsApp.

        Args:
            phone: Número do destinatário (ex: "5511999999999")
            audio_url: URL pública do arquivo de áudio
            ptt: Se True, envia como voice message (gravação de voz)
            caption: Legenda opcional

        Returns:
            dict: Resposta da API
        """
        url = f"{self.base_url}/message/sendMedia"

        headers = {
            "apikey": self.api_key,
            "Content-Type": "application/json"
        }

        payload = {
            "phone": phone,
            "media": audio_url,
            "type": "audio",
            "ptt": ptt
        }

        if caption:
            payload["caption"] = caption

        response = await self.client.post(
            url,
            json=payload,
            headers=headers
        )
        response.raise_for_status()

        return response.json()

    async def send_ptt(
        self,
        phone: str,
        audio_url: str
    ) -> dict:
        """
        Envia voice message (PTT - Push to Talk).
        Atalho para send_audio com ptt=True.
        """
        return await self.send_audio(
            phone=phone,
            audio_url=audio_url,
            ptt=True
        )

    async def close(self):
        await self.client.aclose()
```

---

## 5. Storage - Upload de Áudio

### 5.1. Opção 1: Supabase Storage

```python
from supabase import create_client
import uuid

class AudioStorage:
    """Gerenciador de storage para arquivos de áudio."""

    def __init__(self, supabase_url: str, supabase_key: str):
        self.client = create_client(supabase_url, supabase_key)
        self.bucket = "audio-messages"

    async def upload_audio(
        self,
        audio_data: bytes,
        filename: Optional[str] = None
    ) -> str:
        """
        Upload de áudio para Supabase Storage.

        Returns:
            str: URL pública do arquivo
        """
        if not filename:
            filename = f"{uuid.uuid4()}.ogg"

        # Upload
        self.client.storage.from_(self.bucket).upload(
            filename,
            audio_data,
            {"content-type": "audio/ogg"}
        )

        # Gerar URL pública
        url = self.client.storage.from_(self.bucket).get_public_url(filename)

        return url

    async def upload_with_expiry(
        self,
        audio_data: bytes,
        expires_in: int = 3600  # 1 hora
    ) -> str:
        """
        Upload com URL temporária (mais seguro).
        """
        filename = f"temp/{uuid.uuid4()}.ogg"

        self.client.storage.from_(self.bucket).upload(
            filename,
            audio_data,
            {"content-type": "audio/ogg"}
        )

        # URL assinada com expiração
        url = self.client.storage.from_(self.bucket).create_signed_url(
            filename,
            expires_in
        )

        return url["signedURL"]
```

### 5.2. Opção 2: AWS S3

```python
import boto3
import uuid
from botocore.config import Config

class S3AudioStorage:
    """Storage de áudio usando AWS S3."""

    def __init__(
        self,
        access_key: str,
        secret_key: str,
        bucket: str,
        region: str = "sa-east-1"
    ):
        self.s3 = boto3.client(
            "s3",
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region,
            config=Config(signature_version="s3v4")
        )
        self.bucket = bucket
        self.region = region

    async def upload_audio(
        self,
        audio_data: bytes,
        filename: Optional[str] = None,
        expires_in: int = 3600
    ) -> str:
        """
        Upload e retorna URL assinada.
        """
        if not filename:
            filename = f"audio/{uuid.uuid4()}.ogg"

        self.s3.put_object(
            Bucket=self.bucket,
            Key=filename,
            Body=audio_data,
            ContentType="audio/ogg"
        )

        # Gerar URL pré-assinada
        url = self.s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": filename},
            ExpiresIn=expires_in
        )

        return url
```

---

## 6. Integração Completa no Agente

### 6.1. Serviço de Voz

```python
# backend/src/services/voice.py

import logging
from typing import Optional
from ..core.config import settings

logger = logging.getLogger(__name__)

class VoiceService:
    """
    Serviço completo de voz: TTS + Storage + Envio.
    """

    def __init__(self):
        self.tts = ElevenLabsTTS(
            api_key=settings.ELEVEN_LABS_API_KEY,
            voice_id=settings.ELEVEN_LABS_VOICE_ID
        )
        self.storage = AudioStorage(
            supabase_url=settings.SUPABASE_URL,
            supabase_key=settings.SUPABASE_SERVICE_KEY
        )
        self.whatsapp = UAZAPIClient(
            base_url=settings.UAZAPI_URL,
            api_key=settings.UAZAPI_API_KEY,
            instance_id=settings.UAZAPI_INSTANCE_ID
        )

    async def send_voice_message(
        self,
        phone: str,
        text: str,
        also_send_text: bool = False
    ) -> dict:
        """
        Pipeline completo: texto → áudio → WhatsApp.

        Args:
            phone: Número do destinatário
            text: Texto a ser convertido em voz
            also_send_text: Se True, envia também mensagem de texto

        Returns:
            dict: Resultado do envio
        """
        try:
            logger.info(f"[VOICE] Iniciando TTS para {len(text)} caracteres")

            # 1. Converter texto em áudio
            audio_data = await self.tts.text_to_speech(
                text=text,
                output_format="opus_48000_64"
            )

            logger.info(f"[VOICE] Áudio gerado: {len(audio_data)} bytes")

            # 2. Converter para OGG OPUS (WhatsApp)
            whatsapp_audio = AudioConverter.convert_to_whatsapp_ogg(
                audio_data,
                input_format="opus"
            )

            logger.info(f"[VOICE] Convertido para OGG: {len(whatsapp_audio)} bytes")

            # 3. Upload para storage
            audio_url = await self.storage.upload_with_expiry(
                whatsapp_audio,
                expires_in=3600  # 1 hora
            )

            logger.info(f"[VOICE] Upload concluído: {audio_url[:50]}...")

            # 4. Enviar áudio via WhatsApp
            result = await self.whatsapp.send_ptt(
                phone=phone,
                audio_url=audio_url
            )

            logger.info(f"[VOICE] Áudio enviado com sucesso")

            # 5. Opcionalmente enviar texto também
            if also_send_text:
                await self.whatsapp.send_text(phone=phone, message=text)

            return {
                "success": True,
                "audio_url": audio_url,
                "text_length": len(text),
                "audio_size": len(whatsapp_audio),
                "whatsapp_response": result
            }

        except Exception as e:
            logger.error(f"[VOICE] Erro: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    async def close(self):
        await self.tts.close()
        await self.whatsapp.close()


# Singleton
voice_service: Optional[VoiceService] = None

async def get_voice_service() -> VoiceService:
    global voice_service
    if voice_service is None:
        voice_service = VoiceService()
    return voice_service
```

### 6.2. Modificação no Graph do Agente

```python
# Modificação em backend/src/agent/graph.py

from ..services.voice import get_voice_service

async def send_response(state: AgentState) -> AgentState:
    """
    Node que envia a resposta ao usuário.
    Suporta texto e/ou áudio.
    """
    response_text = state.get("response", "")
    phone = state.get("phone", "")

    # Configuração da empresa
    company_config = state.get("company_config", {})
    voice_enabled = company_config.get("voice_enabled", False)
    voice_only = company_config.get("voice_only", False)

    if voice_enabled and response_text:
        voice = await get_voice_service()

        # Enviar como áudio
        await voice.send_voice_message(
            phone=phone,
            text=response_text,
            also_send_text=not voice_only  # Enviar texto também se não for voice_only
        )
    else:
        # Enviar apenas texto
        whatsapp = await get_whatsapp_service()
        await whatsapp.send_text(phone=phone, message=response_text)

    return state
```

---

## 7. Configurações Necessárias

### 7.1. Variáveis de Ambiente

```env
# Eleven Labs
ELEVEN_LABS_API_KEY=your_api_key_here
ELEVEN_LABS_VOICE_ID=JBFqnCBsd6RMkjVDRZzb  # Seu voice ID

# Supabase (Storage)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your_service_key

# UAZAPI
UAZAPI_URL=https://api.uazapi.com
UAZAPI_API_KEY=your_api_key
UAZAPI_INSTANCE_ID=your_instance
```

### 7.2. Dependências Python

```txt
# requirements.txt (adicionar)
elevenlabs>=1.0.0
pydub>=0.25.1
boto3>=1.34.0  # Se usar S3
```

### 7.3. Dependências do Sistema

```bash
# Ubuntu/Debian
apt-get install ffmpeg

# macOS
brew install ffmpeg

# Docker
RUN apt-get update && apt-get install -y ffmpeg
```

---

## 8. Schema do Banco de Dados (Atualização)

```sql
-- Adicionar configurações de voz na tabela companies
ALTER TABLE companies ADD COLUMN IF NOT EXISTS voice_config JSONB DEFAULT '{
    "enabled": false,
    "voice_only": false,
    "eleven_labs_voice_id": null,
    "voice_settings": {
        "stability": 0.5,
        "similarity_boost": 0.75
    }
}';

-- Tabela para cache de áudios (evitar regenerar)
CREATE TABLE IF NOT EXISTS audio_cache (
    id SERIAL PRIMARY KEY,
    company_id INTEGER REFERENCES companies(id) ON DELETE CASCADE,
    text_hash VARCHAR(64) NOT NULL,  -- SHA256 do texto
    audio_url TEXT NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(company_id, text_hash)
);

CREATE INDEX idx_audio_cache_hash ON audio_cache(text_hash);
CREATE INDEX idx_audio_cache_expires ON audio_cache(expires_at);
```

---

## 9. Custos e Limites

### 9.1. Eleven Labs

| Plano | Caracteres/mês | Preço |
|-------|----------------|-------|
| Free | 10,000 | $0 |
| Starter | 30,000 | $5/mês |
| Creator | 100,000 | $22/mês |
| Pro | 500,000 | $99/mês |

**Estimativa**: Mensagem média de 200 caracteres = ~50 mensagens/mês no plano free.

### 9.2. Latência Esperada

| Etapa | Tempo Médio |
|-------|-------------|
| Eleven Labs TTS | 500ms - 2s |
| Conversão FFmpeg | 100ms - 300ms |
| Upload Storage | 200ms - 500ms |
| Envio UAZAPI | 300ms - 800ms |
| **Total** | **1.1s - 3.6s** |

---

## 10. Considerações e Boas Práticas

### 10.1. Cache de Áudios

Implementar cache para mensagens frequentes (saudações, despedidas):

```python
async def get_or_create_audio(text: str) -> str:
    """Verifica cache antes de gerar novo áudio."""
    text_hash = hashlib.sha256(text.encode()).hexdigest()

    # Buscar no cache
    cached = await db.get_audio_cache(text_hash)
    if cached and cached.expires_at > datetime.utcnow():
        return cached.audio_url

    # Gerar novo
    audio_url = await generate_audio(text)

    # Salvar no cache
    await db.save_audio_cache(text_hash, audio_url)

    return audio_url
```

### 10.2. Limite de Caracteres

Eleven Labs tem melhor qualidade com textos de até **5.000 caracteres**. Para textos maiores, dividir em partes.

### 10.3. Fallback para Texto

Sempre ter fallback para texto em caso de erro no áudio:

```python
try:
    await send_voice_message(phone, text)
except Exception:
    logger.error("Fallback para texto")
    await send_text_message(phone, text)
```

### 10.4. Voz Personalizada

O Eleven Labs permite clonar vozes. O usuário pode criar uma voz personalizada e usar o `voice_id` gerado.

---

## 11. Referências

- [Eleven Labs Python SDK](https://github.com/elevenlabs/elevenlabs-python)
- [Eleven Labs API Documentation](https://elevenlabs.io/docs/api-reference/text-to-speech/convert)
- [PyDub Documentation](https://github.com/jiaaro/pydub)
- [UAZAPI Documentation](https://docs.uazapi.com/)
- [UAZAPI Postman Collection](https://www.postman.com/augustofcs/uazapi/documentation/j48ko4t/uazapi-whatsapp-api-v1-0)
- [WhatsApp Audio Format Requirements](https://blog.ultramsg.com/how-to-send-ogg-file-using-whatsapp-api/)
- [Evolution API Send Audio](https://docs.evoapicloud.com/api-reference/message-controller/send-audio)

---

## 12. Próximos Passos

1. **Confirmar endpoint exato da UAZAPI** - Verificar documentação ou testar endpoints `/message/sendMedia` ou `/message/sendPtt`
2. **Obter Voice ID** - Usar voice ID existente ou criar voz personalizada no Eleven Labs
3. **Configurar Storage** - Criar bucket no Supabase ou S3
4. **Implementar VoiceService** - Usar código desta análise como base
5. **Testar end-to-end** - Enviar áudio de teste via WhatsApp
6. **Adicionar configuração no frontend** - Toggle para ativar/desativar voz por empresa
