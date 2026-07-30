# -*- coding: utf-8 -*-
"""Terminologias oficiais — porte de `backend/src/modules/terminologia`.

Catálogos em memória com índice normalizado (minúsculas, sem acento), igual ao
serviço NestJS: código casa por prefixo, descrição casa por substring.
"""
import unicodedata


def normalizar(texto):
    """Minúsculas e sem acento — busca tolerante a digitação."""
    if not texto:
        return ""
    s = unicodedata.normalize("NFD", str(texto).lower())
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


# CID-10 — 151 verbetes.
CID10 = (
    {'codigo': 'A00', 'descricao': 'Cólera'},
    {'codigo': 'A01.0', 'descricao': 'Febre tifoide'},
    {'codigo': 'A05.1', 'descricao': 'Botulismo'},
    {'codigo': 'A09', 'descricao': 'Diarreia e gastroenterite de origem infecciosa presumível'},
    {'codigo': 'A15', 'descricao': 'Tuberculose respiratória, com confirmação bacteriológica e histológica'},
    {'codigo': 'A16', 'descricao': 'Tuberculose das vias respiratórias, sem confirmação'},
    {'codigo': 'A20', 'descricao': 'Peste'},
    {'codigo': 'A27', 'descricao': 'Leptospirose'},
    {'codigo': 'A30', 'descricao': 'Hanseníase [doença de Hansen]'},
    {'codigo': 'A33', 'descricao': 'Tétano do recém-nascido'},
    {'codigo': 'A35', 'descricao': 'Outros tipos de tétano'},
    {'codigo': 'A36', 'descricao': 'Difteria'},
    {'codigo': 'A37', 'descricao': 'Coqueluche'},
    {'codigo': 'A39', 'descricao': 'Infecção meningocócica'},
    {'codigo': 'A46', 'descricao': 'Erisipela'},
    {'codigo': 'A50', 'descricao': 'Sífilis congênita'},
    {'codigo': 'A51', 'descricao': 'Sífilis precoce'},
    {'codigo': 'A53', 'descricao': 'Outras formas e as não especificadas da sífilis'},
    {'codigo': 'A80', 'descricao': 'Poliomielite aguda'},
    {'codigo': 'A82', 'descricao': 'Raiva'},
    {'codigo': 'A87', 'descricao': 'Meningite viral'},
    {'codigo': 'A90', 'descricao': 'Dengue [dengue clássico]'},
    {'codigo': 'A91', 'descricao': 'Febre hemorrágica devida ao vírus do dengue'},
    {'codigo': 'A92.0', 'descricao': 'Febre de Chikungunya'},
    {'codigo': 'A92.8', 'descricao': 'Outras febres virais especificadas transmitidas por mosquitos (Zika)'},
    {'codigo': 'A95', 'descricao': 'Febre amarela'},
    {'codigo': 'A98.5', 'descricao': 'Febre hemorrágica com síndrome renal (hantavirose)'},
    {'codigo': 'B01', 'descricao': 'Varicela [catapora]'},
    {'codigo': 'B04', 'descricao': 'Varíola dos macacos [mpox]'},
    {'codigo': 'B05', 'descricao': 'Sarampo'},
    {'codigo': 'B06', 'descricao': 'Rubéola'},
    {'codigo': 'B15', 'descricao': 'Hepatite aguda A'},
    {'codigo': 'B16', 'descricao': 'Hepatite aguda B'},
    {'codigo': 'B17.1', 'descricao': 'Hepatite aguda C'},
    {'codigo': 'B19', 'descricao': 'Hepatite viral não especificada'},
    {'codigo': 'B20', 'descricao': 'Doença pelo HIV resultando em doenças infecciosas e parasitárias'},
    {'codigo': 'B24', 'descricao': 'Doença pelo HIV não especificada'},
    {'codigo': 'B34.9', 'descricao': 'Infecção viral não especificada'},
    {'codigo': 'B50', 'descricao': 'Malária por Plasmodium falciparum'},
    {'codigo': 'B51', 'descricao': 'Malária por Plasmodium vivax'},
    {'codigo': 'B55.0', 'descricao': 'Leishmaniose visceral'},
    {'codigo': 'B57.1', 'descricao': 'Doença de Chagas aguda sem comprometimento cardíaco'},
    {'codigo': 'B58', 'descricao': 'Toxoplasmose'},
    {'codigo': 'B86', 'descricao': 'Escabiose [sarna]'},
    {'codigo': 'C16', 'descricao': 'Neoplasia maligna do estômago'},
    {'codigo': 'C18', 'descricao': 'Neoplasia maligna do cólon'},
    {'codigo': 'C34', 'descricao': 'Neoplasia maligna dos brônquios e dos pulmões'},
    {'codigo': 'C44', 'descricao': 'Outras neoplasias malignas da pele'},
    {'codigo': 'C50', 'descricao': 'Neoplasia maligna da mama'},
    {'codigo': 'C53', 'descricao': 'Neoplasia maligna do colo do útero'},
    {'codigo': 'C61', 'descricao': 'Neoplasia maligna da próstata'},
    {'codigo': 'C80', 'descricao': 'Neoplasia maligna, sem especificação de localização'},
    {'codigo': 'D50', 'descricao': 'Anemia por deficiência de ferro'},
    {'codigo': 'E03.9', 'descricao': 'Hipotireoidismo não especificado'},
    {'codigo': 'E05', 'descricao': 'Tireotoxicose [hipertireoidismo]'},
    {'codigo': 'E10', 'descricao': 'Diabetes mellitus insulino-dependente (tipo 1)'},
    {'codigo': 'E11', 'descricao': 'Diabetes mellitus não-insulino-dependente (tipo 2)'},
    {'codigo': 'E11.9', 'descricao': 'Diabetes mellitus tipo 2 sem complicações'},
    {'codigo': 'E14', 'descricao': 'Diabetes mellitus não especificado'},
    {'codigo': 'E46', 'descricao': 'Desnutrição proteico-calórica não especificada'},
    {'codigo': 'E66', 'descricao': 'Obesidade'},
    {'codigo': 'E78', 'descricao': 'Distúrbios do metabolismo de lipoproteínas (dislipidemia)'},
    {'codigo': 'E86', 'descricao': 'Depleção de volume (desidratação)'},
    {'codigo': 'F10', 'descricao': 'Transtornos mentais devidos ao uso de álcool'},
    {'codigo': 'F17', 'descricao': 'Transtornos mentais devidos ao uso de fumo'},
    {'codigo': 'F20', 'descricao': 'Esquizofrenia'},
    {'codigo': 'F29', 'descricao': 'Psicose não-orgânica não especificada'},
    {'codigo': 'F32', 'descricao': 'Episódios depressivos'},
    {'codigo': 'F33', 'descricao': 'Transtorno depressivo recorrente'},
    {'codigo': 'F41', 'descricao': 'Outros transtornos ansiosos'},
    {'codigo': 'F41.1', 'descricao': 'Ansiedade generalizada'},
    {'codigo': 'G00', 'descricao': 'Meningite bacteriana não classificada em outra parte'},
    {'codigo': 'G40', 'descricao': 'Epilepsia'},
    {'codigo': 'G43', 'descricao': 'Enxaqueca'},
    {'codigo': 'G45', 'descricao': 'Acidentes vasculares cerebrais isquêmicos transitórios'},
    {'codigo': 'H10', 'descricao': 'Conjuntivite'},
    {'codigo': 'H66', 'descricao': 'Otite média supurativa e as não especificadas'},
    {'codigo': 'I10', 'descricao': 'Hipertensão essencial (primária)'},
    {'codigo': 'I11', 'descricao': 'Doença cardíaca hipertensiva'},
    {'codigo': 'I20', 'descricao': 'Angina pectoris'},
    {'codigo': 'I20.0', 'descricao': 'Angina instável'},
    {'codigo': 'I21', 'descricao': 'Infarto agudo do miocárdio'},
    {'codigo': 'I48', 'descricao': 'Flutter e fibrilação atrial'},
    {'codigo': 'I50', 'descricao': 'Insuficiência cardíaca'},
    {'codigo': 'I63', 'descricao': 'Infarto cerebral'},
    {'codigo': 'I64', 'descricao': 'Acidente vascular cerebral não especificado'},
    {'codigo': 'I80', 'descricao': 'Flebite e tromboflebite'},
    {'codigo': 'I84', 'descricao': 'Hemorroidas'},
    {'codigo': 'J00', 'descricao': 'Nasofaringite aguda [resfriado comum]'},
    {'codigo': 'J02', 'descricao': 'Faringite aguda'},
    {'codigo': 'J03', 'descricao': 'Amigdalite aguda'},
    {'codigo': 'J06', 'descricao': 'Infecções agudas das vias aéreas superiores'},
    {'codigo': 'J11', 'descricao': 'Influenza [gripe] devida a vírus não identificado'},
    {'codigo': 'J15', 'descricao': 'Pneumonia bacteriana não classificada em outra parte'},
    {'codigo': 'J18', 'descricao': 'Pneumonia por microorganismo não especificado'},
    {'codigo': 'J20', 'descricao': 'Bronquite aguda'},
    {'codigo': 'J44', 'descricao': 'Doença pulmonar obstrutiva crônica (DPOC)'},
    {'codigo': 'J45', 'descricao': 'Asma'},
    {'codigo': 'J81', 'descricao': 'Edema pulmonar'},
    {'codigo': 'K02', 'descricao': 'Cárie dentária'},
    {'codigo': 'K29', 'descricao': 'Gastrite e duodenite'},
    {'codigo': 'K35', 'descricao': 'Apendicite aguda'},
    {'codigo': 'K40', 'descricao': 'Hérnia inguinal'},
    {'codigo': 'K80', 'descricao': 'Colelitíase [cálculo biliar]'},
    {'codigo': 'K92.2', 'descricao': 'Hemorragia gastrointestinal, sem outra especificação'},
    {'codigo': 'L03', 'descricao': 'Celulite (infecção de pele)'},
    {'codigo': 'M17', 'descricao': 'Gonartrose [artrose do joelho]'},
    {'codigo': 'M25.5', 'descricao': 'Dor articular'},
    {'codigo': 'M54', 'descricao': 'Dorsalgia'},
    {'codigo': 'M54.5', 'descricao': 'Dor lombar baixa (lombalgia)'},
    {'codigo': 'M79.1', 'descricao': 'Mialgia'},
    {'codigo': 'N18', 'descricao': 'Insuficiência renal crônica'},
    {'codigo': 'N20', 'descricao': 'Calculose do rim e do ureter'},
    {'codigo': 'N30', 'descricao': 'Cistite'},
    {'codigo': 'N39.0', 'descricao': 'Infecção do trato urinário de localização não especificada'},
    {'codigo': 'O14', 'descricao': 'Pré-eclâmpsia'},
    {'codigo': 'O20.0', 'descricao': 'Ameaça de aborto'},
    {'codigo': 'O23', 'descricao': 'Infecções do trato geniturinário na gravidez'},
    {'codigo': 'O80', 'descricao': 'Parto único espontâneo'},
    {'codigo': 'O82', 'descricao': 'Parto único por cesariana'},
    {'codigo': 'P07', 'descricao': 'Transtornos relacionados à gestação curta e peso baixo ao nascer'},
    {'codigo': 'P59', 'descricao': 'Icterícia neonatal'},
    {'codigo': 'Q21', 'descricao': 'Malformações congênitas dos septos cardíacos'},
    {'codigo': 'R05', 'descricao': 'Tosse'},
    {'codigo': 'R06.0', 'descricao': 'Dispneia'},
    {'codigo': 'R10', 'descricao': 'Dor abdominal e pélvica'},
    {'codigo': 'R10.4', 'descricao': 'Outras dores abdominais e as não especificadas'},
    {'codigo': 'R11', 'descricao': 'Náusea e vômitos'},
    {'codigo': 'R50', 'descricao': 'Febre de origem desconhecida'},
    {'codigo': 'R51', 'descricao': 'Cefaleia'},
    {'codigo': 'R55', 'descricao': 'Síncope e colapso'},
    {'codigo': 'R57.0', 'descricao': 'Choque cardiogênico'},
    {'codigo': 'R57.1', 'descricao': 'Choque hipovolêmico'},
    {'codigo': 'S06', 'descricao': 'Traumatismo intracraniano'},
    {'codigo': 'S42', 'descricao': 'Fratura do ombro e do braço'},
    {'codigo': 'S52', 'descricao': 'Fratura do antebraço'},
    {'codigo': 'S72', 'descricao': 'Fratura do fêmur'},
    {'codigo': 'S82', 'descricao': 'Fratura da perna, incluindo tornozelo'},
    {'codigo': 'T14.1', 'descricao': 'Ferimento aberto de região não especificada do corpo'},
    {'codigo': 'T63', 'descricao': 'Efeito tóxico de contato com animais venenosos'},
    {'codigo': 'T78.4', 'descricao': 'Alergia não especificada'},
    {'codigo': 'X20', 'descricao': 'Contato com serpentes e lagartos venenosos'},
    {'codigo': 'X23', 'descricao': 'Contato com abelhas, vespas e vespões'},
    {'codigo': 'X27', 'descricao': 'Contato com outros animais venenosos especificados'},
    {'codigo': 'U07.1', 'descricao': 'COVID-19, vírus identificado'},
    {'codigo': 'U07.2', 'descricao': 'COVID-19, vírus não identificado'},
    {'codigo': 'U06.9', 'descricao': 'Doença pelo vírus Zika, não especificada'},
    {'codigo': 'Z00.0', 'descricao': 'Exame médico geral'},
    {'codigo': 'Z21', 'descricao': 'Estado de infecção assintomática pelo HIV'},
    {'codigo': 'Z34', 'descricao': 'Supervisão de gravidez normal'},
    {'codigo': 'Z38', 'descricao': 'Nascidos vivos segundo o local de nascimento'},
)

# RENAME — 92 apresentações.
MEDICAMENTOS = (
    {'nome': 'Dipirona sódica', 'apresentacao': '500 mg comprimido', 'via': 'oral'},
    {'nome': 'Dipirona sódica', 'apresentacao': '500 mg/mL solução injetável', 'via': 'intravenosa'},
    {'nome': 'Paracetamol', 'apresentacao': '500 mg comprimido', 'via': 'oral'},
    {'nome': 'Paracetamol', 'apresentacao': '200 mg/mL solução oral (gotas)', 'via': 'oral'},
    {'nome': 'Ibuprofeno', 'apresentacao': '600 mg comprimido', 'via': 'oral'},
    {'nome': 'Ibuprofeno', 'apresentacao': '50 mg/mL suspensão oral', 'via': 'oral'},
    {'nome': 'Diclofenaco sódico', 'apresentacao': '50 mg comprimido', 'via': 'oral'},
    {'nome': 'Ácido acetilsalicílico', 'apresentacao': '100 mg comprimido', 'via': 'oral'},
    {'nome': 'Tramadol', 'apresentacao': '50 mg/mL solução injetável', 'via': 'intravenosa'},
    {'nome': 'Morfina', 'apresentacao': '10 mg/mL solução injetável', 'via': 'intravenosa'},
    {'nome': 'Amoxicilina', 'apresentacao': '500 mg cápsula', 'via': 'oral'},
    {'nome': 'Amoxicilina + clavulanato de potássio', 'apresentacao': '875 mg + 125 mg comprimido', 'via': 'oral'},
    {'nome': 'Azitromicina', 'apresentacao': '500 mg comprimido', 'via': 'oral'},
    {'nome': 'Cefalexina', 'apresentacao': '500 mg cápsula', 'via': 'oral'},
    {'nome': 'Ceftriaxona', 'apresentacao': '1 g pó para solução injetável', 'via': 'intravenosa'},
    {'nome': 'Ciprofloxacino', 'apresentacao': '500 mg comprimido', 'via': 'oral'},
    {'nome': 'Sulfametoxazol + trimetoprima', 'apresentacao': '400 mg + 80 mg comprimido', 'via': 'oral'},
    {'nome': 'Benzilpenicilina benzatina', 'apresentacao': '1.200.000 UI pó para suspensão injetável', 'via': 'intramuscular'},
    {'nome': 'Metronidazol', 'apresentacao': '250 mg comprimido', 'via': 'oral'},
    {'nome': 'Nitrofurantoína', 'apresentacao': '100 mg cápsula', 'via': 'oral'},
    {'nome': 'Vancomicina', 'apresentacao': '500 mg pó para solução injetável', 'via': 'intravenosa'},
    {'nome': 'Piperacilina + tazobactam', 'apresentacao': '4 g + 0,5 g pó para solução injetável', 'via': 'intravenosa'},
    {'nome': 'Losartana potássica', 'apresentacao': '50 mg comprimido', 'via': 'oral'},
    {'nome': 'Enalapril', 'apresentacao': '10 mg comprimido', 'via': 'oral'},
    {'nome': 'Captopril', 'apresentacao': '25 mg comprimido', 'via': 'oral'},
    {'nome': 'Anlodipino', 'apresentacao': '5 mg comprimido', 'via': 'oral'},
    {'nome': 'Hidroclorotiazida', 'apresentacao': '25 mg comprimido', 'via': 'oral'},
    {'nome': 'Furosemida', 'apresentacao': '40 mg comprimido', 'via': 'oral'},
    {'nome': 'Furosemida', 'apresentacao': '10 mg/mL solução injetável', 'via': 'intravenosa'},
    {'nome': 'Espironolactona', 'apresentacao': '25 mg comprimido', 'via': 'oral'},
    {'nome': 'Atenolol', 'apresentacao': '50 mg comprimido', 'via': 'oral'},
    {'nome': 'Carvedilol', 'apresentacao': '6,25 mg comprimido', 'via': 'oral'},
    {'nome': 'Sinvastatina', 'apresentacao': '20 mg comprimido', 'via': 'oral'},
    {'nome': 'Atorvastatina', 'apresentacao': '20 mg comprimido', 'via': 'oral'},
    {'nome': 'Varfarina sódica', 'apresentacao': '5 mg comprimido', 'via': 'oral'},
    {'nome': 'Enoxaparina sódica', 'apresentacao': '40 mg/0,4 mL solução injetável', 'via': 'subcutânea'},
    {'nome': 'Digoxina', 'apresentacao': '0,25 mg comprimido', 'via': 'oral'},
    {'nome': 'Amiodarona', 'apresentacao': '200 mg comprimido', 'via': 'oral'},
    {'nome': 'Nitroglicerina', 'apresentacao': '5 mg/mL solução injetável', 'via': 'intravenosa'},
    {'nome': 'Metformina', 'apresentacao': '850 mg comprimido', 'via': 'oral'},
    {'nome': 'Glibenclamida', 'apresentacao': '5 mg comprimido', 'via': 'oral'},
    {'nome': 'Gliclazida', 'apresentacao': '60 mg comprimido de liberação prolongada', 'via': 'oral'},
    {'nome': 'Insulina humana NPH', 'apresentacao': '100 UI/mL suspensão injetável', 'via': 'subcutânea'},
    {'nome': 'Insulina humana regular', 'apresentacao': '100 UI/mL solução injetável', 'via': 'subcutânea'},
    {'nome': 'Salbutamol', 'apresentacao': '100 mcg/dose aerossol', 'via': 'inalatória'},
    {'nome': 'Ipratrópio, brometo', 'apresentacao': '0,25 mg/mL solução para nebulização', 'via': 'inalatória'},
    {'nome': 'Beclometasona', 'apresentacao': '250 mcg/dose aerossol', 'via': 'inalatória'},
    {'nome': 'Prednisona', 'apresentacao': '20 mg comprimido', 'via': 'oral'},
    {'nome': 'Prednisolona', 'apresentacao': '3 mg/mL solução oral', 'via': 'oral'},
    {'nome': 'Hidrocortisona, succinato', 'apresentacao': '100 mg pó para solução injetável', 'via': 'intravenosa'},
    {'nome': 'Dexametasona', 'apresentacao': '4 mg/mL solução injetável', 'via': 'intravenosa'},
    {'nome': 'Omeprazol', 'apresentacao': '20 mg cápsula', 'via': 'oral'},
    {'nome': 'Pantoprazol', 'apresentacao': '40 mg pó para solução injetável', 'via': 'intravenosa'},
    {'nome': 'Ranitidina', 'apresentacao': '150 mg comprimido', 'via': 'oral'},
    {'nome': 'Ondansetrona', 'apresentacao': '2 mg/mL solução injetável', 'via': 'intravenosa'},
    {'nome': 'Metoclopramida', 'apresentacao': '10 mg comprimido', 'via': 'oral'},
    {'nome': 'Bromoprida', 'apresentacao': '10 mg comprimido', 'via': 'oral'},
    {'nome': 'Sais para reidratação oral', 'apresentacao': 'pó para solução oral (envelope)', 'via': 'oral'},
    {'nome': 'Fenitoína', 'apresentacao': '100 mg comprimido', 'via': 'oral'},
    {'nome': 'Fenobarbital', 'apresentacao': '100 mg comprimido', 'via': 'oral'},
    {'nome': 'Carbamazepina', 'apresentacao': '200 mg comprimido', 'via': 'oral'},
    {'nome': 'Ácido valproico', 'apresentacao': '500 mg comprimido', 'via': 'oral'},
    {'nome': 'Diazepam', 'apresentacao': '10 mg comprimido', 'via': 'oral'},
    {'nome': 'Diazepam', 'apresentacao': '5 mg/mL solução injetável', 'via': 'intravenosa'},
    {'nome': 'Clonazepam', 'apresentacao': '2 mg comprimido', 'via': 'oral'},
    {'nome': 'Haloperidol', 'apresentacao': '5 mg comprimido', 'via': 'oral'},
    {'nome': 'Risperidona', 'apresentacao': '2 mg comprimido', 'via': 'oral'},
    {'nome': 'Fluoxetina', 'apresentacao': '20 mg cápsula', 'via': 'oral'},
    {'nome': 'Sertralina', 'apresentacao': '50 mg comprimido', 'via': 'oral'},
    {'nome': 'Amitriptilina', 'apresentacao': '25 mg comprimido', 'via': 'oral'},
    {'nome': 'Loratadina', 'apresentacao': '10 mg comprimido', 'via': 'oral'},
    {'nome': 'Dexclorfeniramina', 'apresentacao': '2 mg comprimido', 'via': 'oral'},
    {'nome': 'Prometazina', 'apresentacao': '25 mg/mL solução injetável', 'via': 'intramuscular'},
    {'nome': 'Epinefrina (adrenalina)', 'apresentacao': '1 mg/mL solução injetável', 'via': 'intramuscular'},
    {'nome': 'Albendazol', 'apresentacao': '400 mg comprimido mastigável', 'via': 'oral'},
    {'nome': 'Ivermectina', 'apresentacao': '6 mg comprimido', 'via': 'oral'},
    {'nome': 'Fluconazol', 'apresentacao': '150 mg cápsula', 'via': 'oral'},
    {'nome': 'Nistatina', 'apresentacao': '100.000 UI/mL suspensão oral', 'via': 'oral'},
    {'nome': 'Aciclovir', 'apresentacao': '200 mg comprimido', 'via': 'oral'},
    {'nome': 'Oseltamivir', 'apresentacao': '75 mg cápsula', 'via': 'oral'},
    {'nome': 'Ocitocina', 'apresentacao': '5 UI/mL solução injetável', 'via': 'intravenosa'},
    {'nome': 'Sulfato de magnésio', 'apresentacao': '500 mg/mL solução injetável', 'via': 'intravenosa'},
    {'nome': 'Ácido fólico', 'apresentacao': '5 mg comprimido', 'via': 'oral'},
    {'nome': 'Sulfato ferroso', 'apresentacao': '40 mg Fe²⁺ comprimido', 'via': 'oral'},
    {'nome': 'Cloreto de sódio 0,9%', 'apresentacao': '500 mL solução para infusão', 'via': 'intravenosa'},
    {'nome': 'Glicose 5%', 'apresentacao': '500 mL solução para infusão', 'via': 'intravenosa'},
    {'nome': 'Ringer lactato', 'apresentacao': '500 mL solução para infusão', 'via': 'intravenosa'},
    {'nome': 'Atropina', 'apresentacao': '0,25 mg/mL solução injetável', 'via': 'intravenosa'},
    {'nome': 'Noradrenalina', 'apresentacao': '2 mg/mL solução injetável', 'via': 'intravenosa'},
    {'nome': 'Dopamina', 'apresentacao': '5 mg/mL solução injetável', 'via': 'intravenosa'},
    {'nome': 'Naloxona', 'apresentacao': '0,4 mg/mL solução injetável', 'via': 'intravenosa'},
    {'nome': 'Flumazenil', 'apresentacao': '0,1 mg/mL solução injetável', 'via': 'intravenosa'},
)

# CBO — 17 ocupações.
CBO = (
    {'codigo': '225125', 'descricao': 'Médico clínico'},
    {'codigo': '225110', 'descricao': 'Médico infectologista'},
    {'codigo': '225120', 'descricao': 'Médico cardiologista'},
    {'codigo': '225103', 'descricao': 'Médico anestesiologista'},
    {'codigo': '225150', 'descricao': 'Médico pediatra'},
    {'codigo': '225170', 'descricao': 'Médico cirurgião geral'},
    {'codigo': '225124', 'descricao': 'Médico ginecologista e obstetra'},
    {'codigo': '225133', 'descricao': 'Médico psiquiatra'},
    {'codigo': '223505', 'descricao': 'Enfermeiro'},
    {'codigo': '223565', 'descricao': 'Enfermeiro da estratégia de saúde da família'},
    {'codigo': '322205', 'descricao': 'Técnico de enfermagem'},
    {'codigo': '223405', 'descricao': 'Cirurgião-dentista'},
    {'codigo': '223810', 'descricao': 'Farmacêutico'},
    {'codigo': '223605', 'descricao': 'Fisioterapeuta'},
    {'codigo': '223710', 'descricao': 'Nutricionista'},
    {'codigo': '251510', 'descricao': 'Psicólogo clínico'},
    {'codigo': '223905', 'descricao': 'Assistente social'},
)

# SIGTAP — 15 procedimentos.
SIGTAP = (
    {'codigo': '0301010013', 'descricao': 'Consulta médica em atenção básica'},
    {'codigo': '0301010072', 'descricao': 'Consulta médica em atenção especializada'},
    {'codigo': '0301060029', 'descricao': 'Atendimento de urgência com observação até 24h'},
    {'codigo': '0202010473', 'descricao': 'Hemograma completo'},
    {'codigo': '0202010295', 'descricao': 'Dosagem de glicose'},
    {'codigo': '0202010600', 'descricao': 'Dosagem de creatinina'},
    {'codigo': '0202030229', 'descricao': 'Teste rápido para dengue'},
    {'codigo': '0205020097', 'descricao': 'Ultrassonografia abdominal total'},
    {'codigo': '0204030153', 'descricao': 'Radiografia de tórax (PA e perfil)'},
    {'codigo': '0211060100', 'descricao': 'Eletrocardiograma'},
    {'codigo': '0303010037', 'descricao': 'Tratamento de pneumonia'},
    {'codigo': '0303140135', 'descricao': 'Tratamento de diabetes mellitus'},
    {'codigo': '0409060089', 'descricao': 'Parto normal'},
    {'codigo': '0411010026', 'descricao': 'Parto cesariano'},
    {'codigo': '0301100039', 'descricao': 'Aplicação de vacina (imunização)'},
)

# CNES — 6 estabelecimentos.
CNES = (
    {'cnes': '2077485', 'nome': 'Hospital Geral de Fortaleza', 'municipio': 'Fortaleza', 'uf': 'CE'},
    {'cnes': '2295415', 'nome': 'Hospital das Clínicas da UFBA', 'municipio': 'Salvador', 'uf': 'BA'},
    {'cnes': '2269481', 'nome': 'UPA 24h Centro', 'municipio': 'Salvador', 'uf': 'BA'},
    {'cnes': '5717256', 'nome': 'UBS Vila Nova', 'municipio': 'Feira de Santana', 'uf': 'BA'},
    {'cnes': '0011800', 'nome': 'Hospital das Clínicas FMUSP', 'municipio': 'São Paulo', 'uf': 'SP'},
    {'cnes': '2237601', 'nome': 'Hospital Municipal Souza Aguiar', 'municipio': 'Rio de Janeiro', 'uf': 'RJ'},
)

def _indexar(rows, campos):
    return [
        dict(r, _busca=normalizar(" ".join(str(r.get(c, "")) for c in campos)))
        for r in rows
    ]


_IDX = {
    "cid10": _indexar(CID10, ("codigo", "descricao")),
    "medicamentos": _indexar(MEDICAMENTOS, ("nome", "apresentacao")),
    "cbo": _indexar(CBO, tuple(CBO[0]) if CBO else ()),
    "sigtap": _indexar(SIGTAP, tuple(SIGTAP[0]) if SIGTAP else ()),
    "cnes": _indexar(CNES, tuple(CNES[0]) if CNES else ()),
}

TABELAS = {
    "cid10": ("CID-10", "Classificação Internacional de Doenças"),
    "medicamentos": ("RENAME", "Relação Nacional de Medicamentos Essenciais"),
    "cbo": ("CBO", "Classificação Brasileira de Ocupações"),
    "sigtap": ("SIGTAP", "Tabela de Procedimentos, Medicamentos e OPM do SUS"),
    "cnes": ("CNES", "Cadastro Nacional de Estabelecimentos de Saúde"),
}


def colunas(tabela):
    """Colunas de uma terminologia, na ordem de exibição."""
    linhas = _IDX.get(tabela) or []
    return [k for k in linhas[0] if k != "_busca"] if linhas else []


def buscar(tabela, termo, limite=25):
    """Busca numa terminologia. Termo vazio devolve o início do catálogo."""
    linhas = _IDX.get(tabela)
    if linhas is None:
        return []

    alvo = normalizar((termo or "").strip())
    if not alvo:
        return [{k: v for k, v in r.items() if k != "_busca"} for r in linhas[:limite]]

    sem_ponto = alvo.replace(".", "")
    achados = []
    for r in linhas:
        codigo = normalizar(r.get("codigo", "")).replace(".", "")
        if (codigo and codigo.startswith(sem_ponto)) or alvo in r["_busca"]:
            achados.append({k: v for k, v in r.items() if k != "_busca"})
            if len(achados) >= limite:
                break
    return achados


def descricao_cid(codigo):
    """Descrição de um CID exato, ou None."""
    alvo = normalizar(codigo).replace(".", "")
    for r in _IDX["cid10"]:
        if normalizar(r["codigo"]).replace(".", "") == alvo:
            return r["descricao"]
    return None
