#!/bin/bash

# Script de instalação do Frontend IA-Generica
# Uso: bash INSTALL.sh

echo "=================================================="
echo "  Frontend IA-Generica - Instalação Automática"
echo "=================================================="
echo ""

# Cores para output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Verificar se está no diretório correto
if [ ! -f "package.json" ]; then
    echo -e "${RED}❌ Erro: package.json não encontrado${NC}"
    echo "Execute este script na pasta do frontend"
    exit 1
fi

echo -e "${YELLOW}📦 Instalando dependências...${NC}"
echo ""

# Instalar dependências principais
npm install

# Verificar se a instalação foi bem sucedida
if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Erro ao instalar dependências principais${NC}"
    exit 1
fi

echo ""
echo -e "${YELLOW}📦 Instalando dependências adicionais...${NC}"
echo ""

# Instalar dependências adicionais
npm install @hello-pangea/dnd date-fns

# Verificar se a instalação foi bem sucedida
if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Erro ao instalar dependências adicionais${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}✅ Dependências instaladas com sucesso!${NC}"
echo ""

# Verificar se .env.local existe
if [ ! -f ".env.local" ]; then
    echo -e "${YELLOW}⚠️  Arquivo .env.local não encontrado${NC}"
    echo ""
    echo "Criando .env.local de exemplo..."

    cat > .env.local << EOL
# Supabase
NEXT_PUBLIC_SUPABASE_URL=https://seu-projeto.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=sua-chave-anonima-aqui

# API Backend
NEXT_PUBLIC_API_URL=http://localhost:8000
EOL

    echo -e "${GREEN}✅ Arquivo .env.local criado${NC}"
    echo -e "${YELLOW}⚠️  IMPORTANTE: Edite o arquivo .env.local com suas credenciais reais${NC}"
else
    echo -e "${GREEN}✅ Arquivo .env.local já existe${NC}"
fi

echo ""
echo "=================================================="
echo -e "${GREEN}  Instalação Concluída!${NC}"
echo "=================================================="
echo ""
echo "Próximos passos:"
echo ""
echo "1. Configure suas credenciais no arquivo .env.local"
echo "2. Execute: npm run dev"
echo "3. Acesse: http://localhost:3000"
echo ""
echo "Documentação:"
echo "- QUICK_START.md - Guia rápido"
echo "- FRONTEND_IMPLEMENTATION.md - Documentação completa"
echo "- VERIFICATION_CHECKLIST.md - Checklist de testes"
echo ""
echo "=================================================="
