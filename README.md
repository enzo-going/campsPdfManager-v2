# CAMPS PDF Manager v2

![Python](https://img.shields.io/badge/Python-3776AB?style=flat&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-000000?style=flat&logo=flask&logoColor=white)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-D71F00?style=flat&logo=sqlalchemy&logoColor=white)
![JWT](https://img.shields.io/badge/JWT-000000?style=flat&logo=jsonwebtokens&logoColor=white)
![JavaScript](https://img.shields.io/badge/JavaScript-F7DF1E?style=flat&logo=javascript&logoColor=black)

Sistema web para gestão, validação e digitalização de documentos PDF com conformidade ao **Decreto 10.278/2020** (padrões de digitalização do governo federal brasileiro).

---

## Funcionalidades

- Upload de documentos PDF com coleta de metadados obrigatórios
- Autenticação via JWT com controle de acesso por roles (Admin, User, Viewer)
- Dashboard analítico com filtros e métricas de uso
- Processamento em lote de documentos
- Integração com assinatura digital
- API REST documentada com três blueprints principais: auth, documents, analytics

---

## Stack

| Camada | Tecnologia |
|---|---|
| Backend | Python 3.8+ · Flask · SQLAlchemy ORM |
| Banco de dados | SQLite com suporte a migrations |
| Autenticação | JWT (PyJWT) |
| Frontend | JavaScript modular (core / modules / components / utils) |

---

## Como executar

```bash
git clone https://github.com/enzo-going/campsPdfManager-v2.git
cd campsPdfManager-v2
pip install -r requirements.txt
python app.py
```

Acesse em `http://localhost:5000`.

---

## Estrutura da API

```
POST   /auth/login          # Autenticação e geração de token JWT
POST   /documents/upload    # Upload de documento com metadados
GET    /documents/          # Listagem com filtros
DELETE /documents/<id>      # Remoção (Admin only)
GET    /analytics/summary   # Métricas e relatórios
```

---

## Conformidade

O sistema implementa os requisitos de metadados definidos pelo **Decreto 10.278/2020**, que estabelece padrões técnicos para digitalização de documentos em órgãos públicos e empresas conveniadas.
