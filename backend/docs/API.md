# API Reference — CAMPS PDF Manager v2

Documentação completa dos endpoints da API REST do sistema de gestão e digitalização de documentos PDF.

---

## Índice

- [Autenticação](#autenticação)
- [Roles e Permissões](#roles-e-permissões)
- [Rotas de Autenticação](#rotas-de-autenticação-apiauthroute)
- [Rotas de Documentos](#rotas-de-documentos-apidocumentosroute)
- [Rotas de Analytics](#rotas-de-analytics-apianalyticsroute)
- [Códigos de Erro](#códigos-de-erro)

---

## Autenticação

A API utiliza **JWT (JSON Web Token)** stateless com dois tokens:

| Token | Duração | Uso |
|---|---|---|
| `access_token` | Curta (ex: 15 min) | Enviado no header de cada requisição |
| `refresh_token` | Longa (ex: 30 dias) | Usado apenas para renovar o access token |

**Header obrigatório em rotas protegidas:**
```
Authorization: Bearer {access_token}
```

---

## Roles e Permissões

| Role | Nível | Permissões |
|---|---|---|
| `admin` | 3 | Acesso total — gerencia usuários, documentos e analytics |
| `user` | 2 | Upload, edição de metadados, download e deleção de documentos |
| `viewer` | 1 | Leitura e download apenas |

---

## Rotas de Autenticação `/api/auth`

### `POST /api/auth/login`
Autentica um usuário e retorna par de tokens JWT.

**Autenticação:** Não requerida

**Request body:**
```json
{
  "email": "admin@camps.com",
  "password": "senha123"
}
```

**Response 200:**
```json
{
  "message": "Login realizado com sucesso",
  "user": { "id": 1, "name": "Admin", "email": "admin@camps.com", "role": "admin" },
  "access_token": "eyJ...",
  "refresh_token": "eyJ..."
}
```

**Erros:** `400` campos ausentes · `401` credenciais inválidas · `403` usuário desativado

---

### `POST /api/auth/refresh`
Gera novo access token a partir de um refresh token válido.

**Autenticação:** `Authorization: Bearer {refresh_token}`

**Response 200:**
```json
{
  "access_token": "eyJ..."
}
```

**Erros:** `403` usuário inativo ou inválido · `422` token inválido/expirado

---

### `GET /api/auth/me`
Retorna os dados do usuário autenticado.

**Autenticação:** JWT (access token)

**Response 200:**
```json
{
  "id": 1,
  "name": "Enzo",
  "email": "enzo@camps.com",
  "role": "user",
  "is_active": true,
  "last_login": "2025-06-01T14:30:00"
}
```

**Erros:** `404` usuário não encontrado · `500` erro interno

---

### `POST /api/auth/logout`
Encerra a sessão. Como JWT é stateless, o token deve ser removido pelo cliente.

**Autenticação:** JWT (access token)

**Response 200:**
```json
{ "message": "Logout realizado com sucesso" }
```

---

### `POST /api/auth/change-password`
Permite que o próprio usuário altere sua senha.

**Autenticação:** JWT (access token)

**Request body:**
```json
{
  "current_password": "senhaAtual",
  "new_password": "novaSenha"
}
```

**Response 200:**
```json
{ "message": "Senha alterada com sucesso" }
```

**Erros:** `400` campos ausentes · `401` senha atual incorreta · `404` usuário não encontrado

---

### `GET /api/auth/users`
Lista todos os usuários do sistema.

**Autenticação:** JWT · Role: `admin`

**Response 200:**
```json
{
  "users": [
    { "id": 1, "name": "Admin", "email": "admin@camps.com", "role": "admin", "is_active": true }
  ],
  "total": 1
}
```

**Erros:** `403` acesso negado (não admin)

---

### `POST /api/auth/users`
Cria um novo usuário no sistema.

**Autenticação:** JWT · Role: `admin`

**Request body:**
```json
{
  "email": "novo@camps.com",
  "name": "Nome Completo",
  "password": "senha123",
  "role": "user"
}
```
> Valores válidos para `role`: `admin`, `user`, `viewer`

**Response 201:**
```json
{
  "message": "Usuário criado com sucesso",
  "user": { "id": 2, "name": "Nome Completo", "email": "novo@camps.com", "role": "user" }
}
```

**Erros:** `400` campos inválidos · `403` acesso negado · `409` email já cadastrado

---

### `PUT /api/auth/users/{user_id}`
Atualiza dados de um usuário existente.

**Autenticação:** JWT · Role: `admin`

**Request body (todos opcionais):**
```json
{
  "name": "Novo Nome",
  "email": "novo@email.com",
  "role": "admin",
  "is_active": false,
  "password": "novaSenha"
}
```

**Response 200:**
```json
{
  "message": "Usuário atualizado com sucesso",
  "user": { ... }
}
```

**Erros:** `400` role inválida · `403` acesso negado · `404` usuário não encontrado · `409` email já em uso

---

### `DELETE /api/auth/users/{user_id}`
Remove um usuário do sistema. Não é possível deletar o próprio usuário.

**Autenticação:** JWT · Role: `admin`

**Response 200:**
```json
{ "message": "Usuário deletado com sucesso" }
```

**Erros:** `400` auto-deleção · `403` acesso negado · `404` usuário não encontrado

---

## Rotas de Documentos `/api/documents`

> Os metadados obrigatórios marcados com **[Decreto 10.278/2020]** são exigidos para conformidade legal na digitalização de documentos.

---

### `POST /api/documents/upload`
Faz upload de um ou mais arquivos PDF com metadados de digitalização.

**Autenticação:** JWT · Role: `user` ou `admin`

**Content-Type:** `multipart/form-data`

**Campos do formulário:**

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `files[]` | File | Sim | Um ou mais arquivos PDF |
| `digitizer_name` | string | Não | Nome do digitalizador (padrão: nome do usuário) |
| `digitizer_cpf_cnpj` | string | Não | CPF (11 dígitos) ou CNPJ (14 dígitos) — validado |
| `resolution_dpi` | int | Não | DPI da digitalização — mínimo 150 (padrão: 300) |
| `equipment_info` | string | Não | Equipamento utilizado |
| `company_name` | string | Não | Nome da empresa |
| `company_cnpj` | string | Não | CNPJ da empresa |
| `document_type` | string | Não | Tipo do documento |
| `document_category` | string | Não | Categoria do documento |
| `author` | string | Não | Autor do documento |
| `subject` | string | Não | Assunto |
| `production_date` | string | Não | Data de produção (`YYYY-MM-DD`) **[Decreto 10.278/2020]** |
| `digitization_location` | string | Não | Local de digitalização **[Decreto 10.278/2020]** |
| `destination` | string | Não | Destinação do documento **[Decreto 10.278/2020]** |
| `retention_period` | string | Não | Prazo de guarda **[Decreto 10.278/2020]** |

**Response 200:**
```json
{
  "success": true,
  "message": "2 de 2 arquivos processados",
  "data": [
    {
      "filename": "contrato.pdf",
      "success": true,
      "document_id": 42,
      "title": "Prontuário de contrato",
      "hash": "sha256...",
      "size": 204800,
      "pages": 3,
      "uploaded_at": "2025-06-01T14:30:00-03:00",
      "digitizer_name": "Enzo Going",
      "resolution_dpi": 300,
      "document_type": "Contrato de Aprendizagem"
    }
  ]
}
```

**Erros:** `400` CPF/CNPJ ou DPI inválido · `413` arquivo muito grande

---

### `GET /api/documents/`
Lista documentos com suporte a filtros e paginação.

**Autenticação:** JWT

**Query parameters:**

| Parâmetro | Tipo | Padrão | Descrição |
|---|---|---|---|
| `search` | string | — | Busca por título, autor, nome do arquivo ou digitalizador |
| `document_type` | string | — | Filtra por tipo de documento |
| `document_category` | string | — | Filtra por categoria |
| `sort_by` | string | `uploaded_at` | Campo de ordenação |
| `order` | string | `desc` | Direção: `asc` ou `desc` |
| `page` | int | `1` | Página atual |
| `per_page` | int | `20` | Itens por página (máximo: 100) |

**Response 200:**
```json
{
  "success": true,
  "data": {
    "documents": [ { ... } ],
    "pagination": {
      "total": 50,
      "pages": 3,
      "current_page": 1,
      "per_page": 20
    }
  }
}
```

---

### `GET /api/documents/{doc_id}`
Retorna detalhes completos de um documento, incluindo os últimos 10 registros de auditoria.

**Autenticação:** JWT

**Response 200:**
```json
{
  "success": true,
  "data": {
    "id": 42,
    "title": "Prontuário de contrato",
    "original_filename": "contrato.pdf",
    "is_signed": false,
    "uploaded_at": "2025-06-01T14:30:00-03:00",
    "audit_logs": [
      { "action": "upload", "timestamp": "...", "user_id": 1 }
    ]
  }
}
```

**Erros:** `404` documento não encontrado

---

### `POST /api/documents/{doc_id}/metadata`
Adiciona ou atualiza metadados de um documento existente.

**Autenticação:** JWT · Role: `user` ou `admin`

**Request body (todos opcionais):**
```json
{
  "title": "Novo Título",
  "subject": "Assunto",
  "author": "Nome",
  "digitizer_name": "Digitalizador",
  "digitizer_cpf_cnpj": "12345678901",
  "resolution_dpi": 300,
  "equipment_info": "Scanner HP",
  "company_name": "CAMPS Santos",
  "document_type": "Contrato",
  "document_category": "Trabalhista"
}
```

**Response 200:**
```json
{
  "success": true,
  "message": "Metadados adicionados com sucesso",
  "data": { ... }
}
```

**Erros:** `400` CPF/CNPJ ou DPI inválido · `404` documento não encontrado · `500` erro interno

---

### `GET /api/documents/{doc_id}/download`
Faz download do PDF. Se o documento estiver assinado, retorna a versão assinada.

**Autenticação:** JWT

**Response 200:** Arquivo PDF (binary)

**Erros:** `404` documento ou arquivo não encontrado

---

### `DELETE /api/documents/{doc_id}`
Remove um documento e seu arquivo físico do servidor.

**Autenticação:** JWT · Role: `user` ou `admin`

**Response 200:**
```json
{ "success": true, "message": "Documento deletado com sucesso" }
```

**Erros:** `404` documento não encontrado · `500` erro ao deletar

---

### `POST /api/documents/delete-many`
Remove múltiplos documentos em uma única requisição. Limite: 100 documentos por vez.

**Autenticação:** JWT · Role: `user` ou `admin`

**Request body:**
```json
{ "document_ids": [1, 2, 3] }
```

**Response 200:**
```json
{
  "success": true,
  "message": "3 de 3 documentos deletados",
  "deleted": 3,
  "errors": []
}
```

**Erros:** `400` lista inválida ou acima de 100 itens

---

### `POST /api/documents/batch/metadata`
Aplica metadados em lote para múltiplos documentos de forma assíncrona. Limite: 50 documentos.

**Autenticação:** JWT · Role: `user` ou `admin`

**Request body:**
```json
{
  "document_ids": [1, 2, 3],
  "metadata": {
    "author": "Enzo Going",
    "document_type": "Contrato",
    "resolution_dpi": 300
  }
}
```

**Response 202:**
```json
{
  "success": true,
  "message": "Processamento iniciado para 3 documentos",
  "task_id": "uuid-da-tarefa",
  "total_documents": 3
}
```

> Use `GET /api/documents/batch/status/{task_id}` para acompanhar o progresso.

**Erros:** `400` lista inválida, acima de 50 itens ou metadados inválidos · `404` documento não encontrado

---

### `POST /api/documents/batch/sign`
Assina digitalmente múltiplos documentos com certificado ICP-Brasil A1. Documentos já assinados são ignorados.

**Autenticação:** JWT · Role: `user` ou `admin`

**Request body:**
```json
{
  "document_ids": [1, 2, 3],
  "reason": "Documento digitalizado conforme Decreto 10.278/2020",
  "location": "Santos, SP"
}
```

**Response 202:**
```json
{
  "success": true,
  "message": "Assinatura iniciada para 2 documentos",
  "task_id": "uuid-da-tarefa",
  "total_documents": 2,
  "already_signed": 1
}
```

**Erros:** `400` todos já assinados · `500` certificado não configurado ou não encontrado

---

### `GET /api/documents/batch/status/{task_id}`
Retorna o status atual de uma tarefa de processamento em lote.

**Autenticação:** JWT

**Response 200:**
```json
{
  "success": true,
  "task_id": "uuid-da-tarefa",
  "status": "completed",
  "submitted_at": "2025-06-01T14:30:00",
  "updated_at": "2025-06-01T14:30:05",
  "result": { ... }
}
```

**Erros:** `404` tarefa não encontrada

---

### `GET /api/documents/stats`
Retorna estatísticas rápidas sobre os documentos do sistema.

**Autenticação:** JWT

**Response 200:**
```json
{
  "success": true,
  "data": {
    "total_documents": 120,
    "signed_documents": 98,
    "documents_today": 5,
    "signing_rate": "81.7%"
  }
}
```

---

### `POST /api/documents/{doc_id}/sign`
Assina digitalmente um documento individual com certificado ICP-Brasil A1.

O processo segue a ordem exigida pelo Decreto 10.278/2020:
1. Embed de metadados no PDF
2. Adição de página de assinatura
3. Adição de rodapé CAMPS em todas as páginas
4. Conversão para PDF/A
5. Assinatura digital (último passo — nada pode modificar o PDF após isso)

**Autenticação:** JWT · Role: `user` ou `admin`

**Request body (opcional):**
```json
{
  "reason": "Documento digitalizado conforme Decreto 10.278/2020",
  "location": "Santos, SP"
}
```

**Response 200:**
```json
{
  "success": true,
  "message": "Documento assinado com sucesso",
  "data": {
    "signed_at": "2025-06-01T14:30:00-03:00",
    "certificate": {
      "name": "CAMPS Santos",
      "organization": "CAMPS",
      "valid_until": "2026-01-01"
    },
    "document_hash": "sha256..."
  }
}
```

**Erros:** `400` documento já assinado · `404` arquivo não encontrado · `500` certificado não configurado

---

### `GET /api/documents/signature/status`
Verifica disponibilidade e validade do serviço de assinatura digital.

**Autenticação:** JWT

**Response 200:**
```json
{
  "success": true,
  "data": {
    "configured": true,
    "valid": true,
    "message": "Certificado válido",
    "certificate": {
      "common_name": "CAMPS Santos",
      "organization": "CAMPS",
      "valid_until": "2026-01-01"
    }
  }
}
```

---

## Rotas de Analytics `/api/analytics`

### `GET /api/analytics/dashboard/summary`
Retorna métricas consolidadas para o dashboard principal.

**Autenticação:** JWT

> Admins visualizam dados de todos os usuários. Usuários comuns visualizam apenas seus próprios dados.

**Response 200:**
```json
{
  "success": true,
  "data": {
    "totals": {
      "documents": 120,
      "signed_documents": 98,
      "documents_today": 5,
      "documents_week": 23,
      "documents_month": 67,
      "active_users": 8,
      "total_users": 10
    },
    "recent_documents": [
      { "id": 42, "title": "Prontuário de X", "is_signed": true, "uploaded_at": "..." }
    ],
    "signing_rate": 81.7
  }
}
```

---

### `GET /api/analytics/charts/documents-timeline`
Retorna série temporal de uploads para exibição em gráfico.

**Autenticação:** JWT

**Query parameters:**

| Parâmetro | Tipo | Padrão | Descrição |
|---|---|---|---|
| `days` | int | `30` | Período em dias (máximo: 365) |

**Response 200:**
```json
{
  "success": true,
  "data": {
    "basic": [
      { "date": "2025-05-01", "count": 12, "day_name": "Thu" }
    ],
    "period_days": 30,
    "total_points": 30
  }
}
```

---

### `GET /api/analytics/charts/documents-by-type`
Retorna contagem de documentos agrupados por tipo.

**Autenticação:** JWT

**Response 200:**
```json
{
  "success": true,
  "data": {
    "basic": [
      { "type": "Contrato de Aprendizagem", "count": 80 },
      { "type": "Termo de Compromisso", "count": 40 }
    ]
  }
}
```

---

### `GET /api/analytics/charts/signature-status`
Retorna proporção de documentos assinados vs. não assinados.

**Autenticação:** JWT

**Response 200:**
```json
{
  "success": true,
  "data": {
    "basic": [
      { "status": "Assinados", "count": 98 },
      { "status": "Não Assinados", "count": 22 }
    ]
  }
}
```

---

### `GET /api/analytics/reports/export`
Exporta dados do sistema em formato JSON para relatórios.

**Autenticação:** JWT

**Query parameters:**

| Parâmetro | Tipo | Padrão | Opções |
|---|---|---|---|
| `type` | string | `documents` | `documents`, `audit_log` |
| `format` | string | `json` | `json` |

**Response 200:**
```json
{
  "success": true,
  "data": {
    "report_type": "documents",
    "format": "json",
    "generated_at": "2025-06-01T14:30:00-03:00",
    "records_count": 120,
    "exported_by": "admin@camps.com",
    "data": [ { ... } ]
  }
}
```

**Erros:** `400` tipo de relatório inválido

---

## Códigos de Erro

| Código | Significado |
|---|---|
| `400` | Bad Request — dados inválidos ou campos ausentes |
| `401` | Unauthorized — credenciais inválidas ou token ausente |
| `403` | Forbidden — sem permissão para o recurso |
| `404` | Not Found — recurso não encontrado |
| `409` | Conflict — recurso já existe (ex: email duplicado) |
| `413` | Payload Too Large — arquivo acima do limite permitido |
| `422` | Unprocessable Entity — token JWT malformado ou expirado |
| `500` | Internal Server Error — erro inesperado no servidor |
