# -*- coding: utf-8 -*-
"""Mede o TEXTO da fala contra o tempo que o próprio roteiro declara.

    python scripts/cronometrar_defesa.py

**Não mede a apresentação.** Mede se o texto CABE no tempo que ele mesmo anuncia
— quem fala é que sabe o resto. A distinção é a mesma dos números da monografia:
o que dá para medir, mede-se; o que não dá, declara-se como estimativa.

Existe porque o roteiro afirmava "os dezoito slides somam ~20 min" e ninguém
tinha conferido. Somavam 21:15 pelos próprios tempos declarados, e o texto
levava 23:39 num ritmo médio — três minutos e meio além do que a afirmação
prometia. Afirmação de tempo é como contagem de teste: envelhece a cada
parágrafo acrescentado, e só acusa no dia em que a banca olha o relógio.

O ritmo é **suposição declarada**, não medição: 130 palavras por minuto é uma
fala pausada, 160 é rápida para conteúdo técnico. Por isso a saída traz as três
colunas, em vez de um número só — um valor sem faixa esconderia que a resposta
depende de quem fala.
"""
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Ritmo de fala em apresentação acadêmica, em português. A faixa é larga de
# propósito: fala de defesa é mais lenta que leitura, e quem está nervoso
# acelera. 130 é um ritmo pausado; 160 é rápido para conteúdo técnico.
RITMOS = {"pausado": 130, "médio": 145, "rápido": 160}


def segundos_declarados(rotulo):
    m = re.search(r"(\d+)\s*min(?:\s*(\d+))?", rotulo)
    if m:
        return int(m.group(1)) * 60 + int(m.group(2) or 0)
    s = re.search(r"(\d+)\s*s", rotulo)
    return int(s.group(1)) if s else 0


texto = open("docs/defesa_roteiro.md", encoding="utf-8").read()

# Cada slide começa em "## Slide N — título". A fala é o bloco de citação (">")
# que segue "**Fala (...)**", até o próximo cabeçalho em negrito ou "---".
blocos = re.split(r"^## (Slide \d+[^\n]*)$", texto, flags=re.M)[1:]
linhas, total_declarado, total_medido = [], 0, {k: 0 for k in RITMOS}

for i in range(0, len(blocos), 2):
    titulo, corpo = blocos[i], blocos[i + 1]
    m = re.search(r"\*\*Fala\s*\(([^)]*)\)\*\*(.*?)(?=\n\*\*|\n---|\Z)", corpo, re.S)
    if not m:
        continue
    declarado = segundos_declarados(m.group(1))
    fala = "\n".join(l.lstrip("> ").strip() for l in m.group(2).splitlines()
                     if l.strip().startswith(">"))
    # Tira ênfase e marcação: não se fala asterisco.
    fala = re.sub(r"[*`_]", "", fala)
    palavras = len([p for p in re.split(r"\s+", fala) if p])
    total_declarado += declarado
    medidos = {}
    for nome, ppm in RITMOS.items():
        seg = palavras / ppm * 60
        medidos[nome] = seg
        total_medido[nome] += seg
    linhas.append((titulo, palavras, declarado, medidos))


def mmss(s):
    return f"{int(s) // 60}:{int(s) % 60:02d}"


print(f"{'slide':34} {'palav':>6} {'declar':>7} {'pausado':>8} {'médio':>7} {'rápido':>7}  folga(médio)")
for titulo, palavras, declarado, medidos in linhas:
    folga = declarado - medidos["médio"]
    marca = "  ESTOURA" if folga < -10 else ("  aperta" if folga < 5 else "")
    print(f"{titulo[:34]:34} {palavras:>6} {mmss(declarado):>7} "
          f"{mmss(medidos['pausado']):>8} {mmss(medidos['médio']):>7} "
          f"{mmss(medidos['rápido']):>7}  {int(folga):+4d}s{marca}")

print()
print(f"{'TOTAL':34} {sum(l[1] for l in linhas):>6} {mmss(total_declarado):>7} "
      f"{mmss(total_medido['pausado']):>8} {mmss(total_medido['médio']):>7} "
      f"{mmss(total_medido['rápido']):>7}")
