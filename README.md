# CAMPS PDF Manager v2

Sistema web para gestão, validação e digitalização de documentos PDF com uso de metadados.

## 👨‍💻 Minha participação

Atuei na continuidade deste projeto durante meu estágio no CAMPS Santos:

- **Documentação da API REST** (`docs/API.md`): mapeei todos os endpoints dos três blueprints (auth, documents, analytics), documentando métodos HTTP, parâmetros, formatos de request/response e códigos de erro.
- **Correção de segurança no `.env.example`**: identifiquei e removi credenciais reais expostas publicamente no repositório, substituindo por placeholders documentados.

Esta versão no meu GitHub representa minha documentação pessoal e estudo prático da aplicação.

---
![Status](https://img.shields.io/badge/Status-Active-success)
![Version](https://img.shields.io/badge/Version-2.0.0-blue)
![Compliance](https://img.shields.io/badge/Compliance-Decreto%2010.278-green)

## 🎯 Visão Geral

O **CAMPS PDF Manager** é uma solução robusta para digitalização e gestão de documentos, projetada para garantir a validade jurídica e a integridade de arquivos digitais. A versão 2.0 introduz uma arquitetura modular moderna e conformidade total com os requisitos técnicos da legislação brasileira para digitalização de documentos.

### ✨ Principais Funcionalidades

*   **Gestão de Documentos**: Upload, listagem, visualização e download de PDFs.
*   **Conformidade Legal (FASE 1)**: Coleta e validação de metadados obrigatórios (Digitalizador, CPF/CNPJ, Resolução DPI, etc.).
*   **Assinatura Digital**: Integração para assinatura eletrônica de documentos.
*   **Processamento em Lote**: Atualização de metadados e exclusão de múltiplos arquivos simultaneamente.
*   **Analytics**: Dashboard interativo com estatísticas de uso e status de assinaturas.
*   **Controle de Acesso**: Sistema de autenticação JWT com níveis de permissão (Admin, User, Viewer).

---

## 🏗️ Arquitetura do Projeto

O projeto adota uma arquitetura moderna e desacoplada:

### Backend (Python/Flask)
*   **API RESTful**: Endpoints seguros e documentados.
*   **SQLAlchemy**: ORM para gestão eficiente do banco de dados.
*   **JWT Auth**: Autenticação segura e stateless.
*   **Services**: Camada de serviços para lógica de negócios complexa (PDF manipulation, Batch processing).

### Frontend (Modular JavaScript)
O frontend foi completamente reestruturado para modularidade e manutenibilidade:

```
frontend/js/
├── core/           # Núcleo (API Client, Auth Manager)
├── modules/        # Módulos funcionais independentes
│   ├── dashboard.js
│   ├── documents.js
│   ├── upload.js   # Com integração FASE 1
│   ├── batch.js
│   └── users.js
├── components/     # Componentes reutilizáveis (Charts, Modals)
├── fase1/          # Lógica de conformidade legal (Validators, Metadata)
└── utils/          # Utilitários (Formatters, Toast)
```

---

## 🚀 Instalação e Configuração

### Pré-requisitos
*   Python 3.8+
*   Pip (Gerenciador de pacotes Python)
*   Navegador moderno (Chrome, Firefox, Edge)

### Passo a Passo

1.  **Clone o repositório**
    ```bash
    git clone https://github.com/seu-org/camps-pdf-manager-v2.git
    cd camps-pdf-manager-v2
    ```

2.  **Configure o Backend**
    ```bash
    cd backend
    python -m venv venv
    source venv/bin/activate  # Windows: venv\Scripts\activate
    pip install -r requirements.txt
    ```

3.  **Variáveis de Ambiente**
    Crie um arquivo `.env` na pasta `backend` com base no `.env.example`:
    ```env
    FLASK_APP=run.py
    FLASK_ENV=development
    SECRET_KEY=sua_chave_secreta_segura
    DATABASE_URL=sqlite:///camps_manager.db
    ```

4.  **Inicialize o Banco de Dados**
    ```bash
    flask db upgrade
    ```

5.  **Execute a Aplicação**
    ```bash
    python run.py
    ```
    O servidor iniciará em `http://localhost:5000`.

---

## 📖 Guia de Uso

### 1. Upload de Documentos (FASE 1)
Ao fazer upload de um arquivo, o sistema solicitará automaticamente os metadados exigidos pelo Decreto 10.278/2020:
*   **Autor/Digitalizador**: Nome do responsável.
*   **CPF/CNPJ**: Identificação do responsável (validado automaticamente).
*   **Resolução**: DPI da digitalização (mínimo 150 DPI).

### 2. Gestão em Lote
Selecione múltiplos documentos na lista para realizar ações em massa:
*   **Atualizar Metadados**: Defina autor, assunto ou tipo para vários arquivos de uma vez.
*   **Excluir**: Remova múltiplos arquivos com segurança.

### 3. Dashboard
Acompanhe métricas em tempo real:
*   Timeline de uploads.
*   Distribuição por tipo de documento.
*   Status de assinaturas (Assinado vs. Pendente).

---

## 🤝 Contribuição

1.  Faça um Fork do projeto.
2.  Crie uma Branch para sua Feature (`git checkout -b feature/NovaFeature`).
3.  Commit suas mudanças (`git commit -m 'Add: Nova Feature'`).
4.  Push para a Branch (`git push origin feature/NovaFeature`).
5.  Abra um Pull Request.

---

## 📄 Licença

Este projeto está sob a licença [MIT](LICENSE).

---

**Desenvolvido por Equipe CAMPS Santos**
