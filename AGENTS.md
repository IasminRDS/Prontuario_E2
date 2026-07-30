# Prontuário Eletrônico Hospitalar — Flask

Sistema de prontuário eletrônico hospitalar estilo SUS, em **Flask + Jinja2 + SQLAlchemy**.
Este repositório tem **paridade funcional e visual** com o monorepo
[prontuario-eletronico-hospitalar](https://github.com/IasminRDS/prontuario-eletronico-hospitalar)
(NestJS + Next.js), mas implementado inteiramente em Flask.

## Convenções

- **Rotas**: um blueprint por domínio em `routes/`, registrado em `app.py`. Use
  `@bp.get(...)` / `@bp.post(...)`, não `@bp.route(..., methods=[...])`.
- **Models**: um arquivo por agregado em `models/`, `db.Model` do `extensions.py`.
  Ao criar um model novo, adicione-o ao `_MODEL_IMPORTS` em `models/__init__.py`.
- **Templates**: herdam de `base.html`. Não escreva CSS inline — use as classes do
  design system em `static/css/dsgov.css`.
- **RBAC**: proteja toda rota com `@requer_permissao("recurso:acao")` de
  `utils/rbac.py`. No template, esconda o controle com `{% if pode('recurso:acao') %}`.
  O backend é a autoridade; o template só espelha.
- **Auditoria**: toda mutação clínica chama `utils/audit.registrar(...)` na mesma
  transação da escrita.

## Design system (DSGov / gov.br)

Tokens em `static/css/dsgov.css`. Azul institucional `#1351B4`, amarelo `#FFCD07`.
Tema claro/escuro via `data-theme` no `<html>`, aplicado antes da pintura para não
piscar. Cores semânticas de estado clínico (`--status-*`) e de classificação de
risco Manchester (`--risk-*`) são o ponto único de re-skin — não hardcode cor de
estado clínico em template.

Acessibilidade é requisito (eMAG/WCAG): skip-link, `:focus-visible` visível em todo
controle, VLibras.

## Como rodar

```bash
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt
# .env na raiz com SECRET_KEY e DATABASE_URL
flask db upgrade
python app.py
```
