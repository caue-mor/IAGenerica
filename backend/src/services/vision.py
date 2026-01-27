"""
Vision Service - GPT-4 Vision integration
Image analysis, document extraction, and classification
"""
import logging
import json
import base64
from typing import Optional, Dict, Any, List
import httpx
from openai import OpenAI

from ..core.config import settings

logger = logging.getLogger(__name__)


class VisionService:
    """Service for image analysis using GPT-4 Vision API"""

    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o-mini"):
        """
        Initialize the vision service.

        Args:
            api_key: OpenAI API key (optional, defaults to settings)
            model: Vision model to use (default: gpt-4o-mini)
        """
        self.api_key = api_key or settings.OPENAI_API_KEY
        self.model = model
        self._client: Optional[OpenAI] = None

    @property
    def client(self) -> OpenAI:
        """Lazy initialization of OpenAI client"""
        if self._client is None:
            if not self.api_key:
                raise ValueError("OpenAI API key not configured")
            self._client = OpenAI(api_key=self.api_key)
        return self._client

    async def analyze_image(
        self,
        image_url: str,
        prompt: str = "Descreva esta imagem em detalhes.",
        max_tokens: int = 500
    ) -> Optional[str]:
        """
        Analyze an image and return a description.

        Args:
            image_url: URL of the image to analyze
            prompt: Custom prompt for analysis
            max_tokens: Maximum tokens in response

        Returns:
            Image description or None if failed
        """
        try:
            logger.info(f"Analyzing image: {image_url[:100]}...")

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {"url": image_url, "detail": "auto"}
                            }
                        ]
                    }
                ],
                max_tokens=max_tokens
            )

            result = response.choices[0].message.content
            logger.info(f"Image analyzed successfully: {result[:100]}...")
            return result

        except Exception as e:
            logger.exception(f"Error analyzing image: {e}")
            return None

    async def analyze_image_base64(
        self,
        image_base64: str,
        image_type: str = "jpeg",
        prompt: str = "Descreva esta imagem em detalhes.",
        max_tokens: int = 500
    ) -> Optional[str]:
        """
        Analyze an image from base64 data.

        Args:
            image_base64: Base64 encoded image data
            image_type: Image MIME subtype (jpeg, png, gif, webp)
            prompt: Custom prompt for analysis
            max_tokens: Maximum tokens in response

        Returns:
            Image description or None if failed
        """
        try:
            image_url = f"data:image/{image_type};base64,{image_base64}"

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {"url": image_url}
                            }
                        ]
                    }
                ],
                max_tokens=max_tokens
            )

            return response.choices[0].message.content

        except Exception as e:
            logger.exception(f"Error analyzing base64 image: {e}")
            return None

    async def extract_document_data(
        self,
        image_url: str,
        document_type: str = "generic"
    ) -> Dict[str, Any]:
        """
        Extract data from a document image.

        Args:
            image_url: URL of the document image
            document_type: Type of document (conta_luz, rg, cnh, cpf, generic)

        Returns:
            Extracted data as dictionary
        """
        # Document-specific prompts
        prompts = {
            "conta_luz": """Extraia os seguintes dados desta conta de luz:
- nome_titular: Nome do titular da conta
- endereco: Endereco completo
- consumo_kwh: Consumo em kWh
- valor_total: Valor total da fatura
- vencimento: Data de vencimento
- numero_instalacao: Numero da instalacao
- distribuidora: Nome da distribuidora

Retorne APENAS um JSON valido com esses campos.""",

            "rg": """Extraia os dados deste RG (documento de identidade):
- nome: Nome completo
- rg: Numero do RG
- data_nascimento: Data de nascimento
- filiacao_pai: Nome do pai
- filiacao_mae: Nome da mae
- naturalidade: Naturalidade
- orgao_emissor: Orgao emissor
- data_emissao: Data de emissao

Retorne APENAS um JSON valido com esses campos.""",

            "cnh": """Extraia os dados desta CNH (carteira de motorista):
- nome: Nome completo
- cpf: CPF
- data_nascimento: Data de nascimento
- registro: Numero do registro
- validade: Data de validade
- categoria: Categoria da habilitacao
- primeira_habilitacao: Data da primeira habilitacao

Retorne APENAS um JSON valido com esses campos.""",

            "cpf": """Extraia os dados deste documento de CPF:
- nome: Nome completo
- cpf: Numero do CPF
- data_nascimento: Data de nascimento

Retorne APENAS um JSON valido com esses campos.""",

            "comprovante_residencia": """Extraia os dados deste comprovante de residencia:
- nome: Nome do titular
- endereco: Endereco completo
- cep: CEP
- cidade: Cidade
- estado: Estado
- tipo_comprovante: Tipo do comprovante (conta de luz, agua, etc)

Retorne APENAS um JSON valido com esses campos.""",

            "generic": """Extraia todos os dados relevantes deste documento.
Identifique o tipo de documento e extraia as informacoes principais.
Retorne APENAS um JSON valido com os dados encontrados."""
        }

        prompt = prompts.get(document_type, prompts["generic"])

        try:
            logger.info(f"Extracting data from {document_type} document...")

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "Voce e um especialista em extracao de dados de documentos. Sempre retorne JSON valido."
                    },
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {"url": image_url, "detail": "high"}
                            }
                        ]
                    }
                ],
                max_tokens=1000,
                response_format={"type": "json_object"}
            )

            content = response.choices[0].message.content
            data = json.loads(content)
            data["_document_type"] = document_type
            data["_extraction_successful"] = True

            logger.info(f"Document data extracted: {list(data.keys())}")
            return data

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            return {"_extraction_successful": False, "error": "Invalid JSON response"}
        except Exception as e:
            logger.exception(f"Error extracting document data: {e}")
            return {"_extraction_successful": False, "error": str(e)}

    async def classify_image(
        self,
        image_url: str,
        categories: List[str],
        include_confidence: bool = False
    ) -> Optional[str]:
        """
        Classify an image into one of the given categories.

        Args:
            image_url: URL of the image
            categories: List of possible categories
            include_confidence: Whether to include confidence score

        Returns:
            Selected category or None if failed
        """
        categories_str = ", ".join(categories)

        if include_confidence:
            prompt = f"""Classifique esta imagem em uma das seguintes categorias: {categories_str}

Retorne um JSON com:
- categoria: nome da categoria escolhida
- confianca: nivel de confianca de 0 a 100
- motivo: breve explicacao da escolha"""
        else:
            prompt = f"Classifique esta imagem em uma das seguintes categorias: {categories_str}. Responda APENAS com o nome exato da categoria, sem pontuacao ou explicacao adicional."

        try:
            logger.info(f"Classifying image into categories: {categories_str[:100]}...")

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {"url": image_url}
                            }
                        ]
                    }
                ],
                max_tokens=100 if not include_confidence else 200,
                response_format={"type": "json_object"} if include_confidence else None
            )

            result = response.choices[0].message.content.strip()

            if include_confidence:
                return json.loads(result)

            # Validate result is one of the categories
            result_lower = result.lower()
            for cat in categories:
                if cat.lower() == result_lower:
                    return cat

            logger.warning(f"Classification result '{result}' not in categories")
            return result

        except Exception as e:
            logger.exception(f"Error classifying image: {e}")
            return None

    async def detect_objects(
        self,
        image_url: str,
        target_objects: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Detect objects in an image.

        Args:
            image_url: URL of the image
            target_objects: Optional list of specific objects to look for

        Returns:
            Dictionary with detected objects and their descriptions
        """
        if target_objects:
            objects_str = ", ".join(target_objects)
            prompt = f"""Analise esta imagem e identifique os seguintes objetos: {objects_str}

Para cada objeto encontrado, retorne:
- encontrado: true/false
- quantidade: numero de instancias
- descricao: breve descricao

Retorne um JSON valido."""
        else:
            prompt = """Identifique todos os objetos principais nesta imagem.

Retorne um JSON com:
- objetos: lista de objetos encontrados
- descricao_geral: descricao geral da cena"""

        try:
            logger.info("Detecting objects in image...")

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {"url": image_url, "detail": "high"}
                            }
                        ]
                    }
                ],
                max_tokens=500,
                response_format={"type": "json_object"}
            )

            return json.loads(response.choices[0].message.content)

        except Exception as e:
            logger.exception(f"Error detecting objects: {e}")
            return {"error": str(e), "objetos": []}

    async def analyze_multiple_images(
        self,
        image_urls: List[str],
        prompt: str = "Compare estas imagens e descreva as diferencas e similaridades."
    ) -> Optional[str]:
        """
        Analyze multiple images together.

        Args:
            image_urls: List of image URLs
            prompt: Custom prompt for analysis

        Returns:
            Analysis result or None if failed
        """
        if not image_urls:
            return None

        try:
            logger.info(f"Analyzing {len(image_urls)} images...")

            content = [{"type": "text", "text": prompt}]
            for url in image_urls[:4]:  # Limit to 4 images
                content.append({
                    "type": "image_url",
                    "image_url": {"url": url}
                })

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": content
                    }
                ],
                max_tokens=1000
            )

            return response.choices[0].message.content

        except Exception as e:
            logger.exception(f"Error analyzing multiple images: {e}")
            return None

    async def is_image_processable(self, image_url: str) -> bool:
        """
        Check if an image URL can be processed.

        Args:
            image_url: URL to check

        Returns:
            True if the image can be processed
        """
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.head(image_url)
                if response.status_code != 200:
                    return False

                content_type = response.headers.get("content-type", "")
                content_length = int(response.headers.get("content-length", 0))

                # Check if it's an image
                valid_types = ["image/jpeg", "image/png", "image/gif", "image/webp"]
                if not any(t in content_type.lower() for t in valid_types):
                    return False

                # Check file size (max 20MB for GPT-4 Vision)
                max_size = 20 * 1024 * 1024
                if content_length > max_size:
                    logger.warning(f"Image too large: {content_length} bytes")
                    return False

                return True

        except Exception as e:
            logger.warning(f"Could not verify image URL: {e}")
            return False


# Singleton instance
vision = VisionService()
