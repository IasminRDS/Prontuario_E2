from database.db import db

def seed_data():
    from models.user import User
    from models.unidade import Unidade
    from models.medico import Medico
    from models.regional import Regional

    # Território e catálogos não dependem de usuário e precisam existir mesmo
    # num banco já povoado — por isso vêm antes do retorno antecipado abaixo.
    #
    # Os catálogos eram carregados preguiçosamente pelo `GET` do índice de cada
    # tela. Além de um GET que escreve violar a semântica de HTTP, dois acessos
    # simultâneos com a tabela vazia colidiam no índice único de `codigo` e um
    # deles virava 500 numa requisição de leitura.
    _seed_municipios()
    _seed_catalogos()

    if User.query.first():
        return

    regional = Regional.query.filter_by(nome='Macrorregião Oeste').first()
    if not regional:
        regional = Regional(
            nome='Macrorregião Oeste',
            codigo='MO-01',
            uf='BA',
            ativo=True
        )
        db.session.add(regional)
        db.session.flush()

    # A unidade vem de `_seed_catalogos()`, que já a criou com CNES e município
    # IBGE. Criar outra aqui produziria duas "UBS Central", uma sem CNES — e o
    # RLS liga o usuário a UMA delas, deixando metade dos dados invisível.
    unidade = Unidade.query.order_by(Unidade.id.asc()).first()

    medico_user = User.query.filter_by(email='medico@sus.gov.br').first()
    if not medico_user:
        medico_user = User(
            nome='Dr. João Silva',
            email='medico@sus.gov.br',
            perfil='medico',
            unidade_id=unidade.id,
            nivel_acesso='UNIDADE',
            ativo=True
        )
        medico_user.set_password('medico123')
        db.session.add(medico_user)
        db.session.flush()

        medico = Medico(
            user_id=medico_user.id,
            crm='12345-BA',
            especialidade='Clínica Geral',
            unidade_id=unidade.id
        )
        db.session.add(medico)
        db.session.commit()
    
    _seed_vacinas()
    _seed_exames()
    _seed_hospital()


def _seed_municipios():
    """Capitais, para o sistema nascer com a tabela territorial utilizável.

    A relação completa (5.570) vem do IBGE via `flask municipios-importar`.
    """
    from database.municipios import seed_capitais

    seed_capitais()


def _seed_catalogos():
    """Exames, vacinas e estabelecimentos de demonstração."""
    from database.catalogos import seed_todos

    seed_todos()

def _seed_vacinas():
    from models.vacina import Vacina
    if Vacina.query.first():
        return
    vacinas = [
        Vacina(nome='BCG', sigla='BCG', doses_total=1),
        Vacina(nome='Hepatite B', sigla='HepB', doses_total=3, intervalo_dias=30),
        Vacina(nome='Pentavalente (DTP+Hib+HepB)', sigla='Penta', doses_total=3, intervalo_dias=60),
        Vacina(nome='VIP — Poliomielite inativada', sigla='VIP', doses_total=3, intervalo_dias=60),
        Vacina(nome='VRH — Rotavírus humano', sigla='VRH', doses_total=2, intervalo_dias=60),
        Vacina(nome='Pneumocócica 10-valente', sigla='Pneumo', doses_total=3, intervalo_dias=60),
        Vacina(nome='Meningocócica C', sigla='MenC', doses_total=2, intervalo_dias=60),
        Vacina(nome='Febre Amarela', sigla='FA', doses_total=1),
        Vacina(nome='Tríplice Viral (SCR)', sigla='SCR', doses_total=2, intervalo_dias=30),
        Vacina(nome='Varicela', sigla='VZV', doses_total=1),
        Vacina(nome='Hepatite A', sigla='HepA', doses_total=1),
        Vacina(nome='dT — Dupla adulto', sigla='dT', doses_total=3, intervalo_dias=60),
        Vacina(nome='dTpa — Tríplice bacteriana', sigla='dTpa', doses_total=1),
        Vacina(nome='Influenza', sigla='Flu', doses_total=1),
        Vacina(nome='Covid-19', sigla='COVID', doses_total=2, intervalo_dias=28),
        Vacina(nome='HPV quadrivalente', sigla='HPV', doses_total=2, intervalo_dias=180),
    ]
    for v in vacinas:
        db.session.add(v)
    db.session.commit()

def _seed_exames():
    from models.exame import TipoExame
    if TipoExame.query.first():
        return
    exames = [
        TipoExame(codigo='HMG', nome='Hemograma completo', categoria='laboratorial', instrucoes='Não requer jejum'),
        TipoExame(codigo='GLI', nome='Glicemia em jejum', categoria='laboratorial', instrucoes='Jejum de 8 horas'),
        TipoExame(codigo='URE', nome='Ureia', categoria='laboratorial', instrucoes='Jejum de 4 horas'),
        TipoExame(codigo='CRE', nome='Creatinina', categoria='laboratorial', instrucoes='Jejum de 4 horas'),
        TipoExame(codigo='PCR', nome='Proteína C-reativa (PCR)', categoria='laboratorial', instrucoes='Jejum de 4 horas'),
        TipoExame(codigo='VHS', nome='Velocidade de hemossedimentação', categoria='laboratorial'),
        TipoExame(codigo='TGO', nome='TGO (AST)', categoria='laboratorial', instrucoes='Jejum de 4 horas'),
        TipoExame(codigo='TGP', nome='TGP (ALT)', categoria='laboratorial', instrucoes='Jejum de 4 horas'),
        TipoExame(codigo='COL', nome='Colesterol total e frações', categoria='laboratorial', instrucoes='Jejum de 12 horas'),
        TipoExame(codigo='TRI', nome='Triglicerídeos', categoria='laboratorial', instrucoes='Jejum de 12 horas'),
        TipoExame(codigo='TSH', nome='TSH', categoria='laboratorial', instrucoes='Não requer jejum'),
        TipoExame(codigo='T4L', nome='T4 livre', categoria='laboratorial', instrucoes='Não requer jejum'),
        TipoExame(codigo='URO', nome='Urina tipo I (EAS)', categoria='laboratorial', instrucoes='Primeira urina da manhã'),
        TipoExame(codigo='URC', nome='Urocultura', categoria='laboratorial', instrucoes='Primeira urina da manhã'),
        TipoExame(codigo='HBA1', nome='Hemoglobina glicada (HbA1c)', categoria='laboratorial', instrucoes='Não requer jejum'),
        TipoExame(codigo='RXTO', nome='Raio-X de tórax', categoria='imagem'),
        TipoExame(codigo='RXAB', nome='Raio-X de abdome', categoria='imagem'),
        TipoExame(codigo='USAB', nome='Ultrassom abdominal', categoria='imagem', instrucoes='Jejum de 6 horas'),
        TipoExame(codigo='USPV', nome='Ultrassom pélvico', categoria='imagem', instrucoes='Bexiga cheia'),
        TipoExame(codigo='ECG', nome='Eletrocardiograma', categoria='funcional'),
        TipoExame(codigo='PICO', nome='Peak flow / espirometria', categoria='funcional'),
    ]
    for e in exames:
        db.session.add(e)
    db.session.commit()

def _seed_hospital():
    from models.internacao import Setor, Leito
    from models.cirurgia import SalaCirurgica
    from models.unidade import Unidade
    
    if Setor.query.first():
        return
        
    unidade = Unidade.query.first()
    unidade_id = unidade.id if unidade else 1

    setores_data = [
        ('Clínica Médica', 'CM', 'enfermaria', '2º andar', 10),
        ('Pronto-Socorro', 'PS', 'ps', 'Térreo', 8),
        ('UTI Adulto', 'UTI', 'uti', '3º andar', 6),
        ('Pediatria', 'PED', 'enfermaria', '2º andar', 8),
        ('Maternidade', 'MAT', 'obstetricia', '1º andar', 6),
        ('Cirurgia Geral', 'CG', 'enfermaria', '2º andar', 8),
    ]
    for nome, sigla, tipo, andar, qtd in setores_data:
        s = Setor(nome=nome, sigla=sigla, tipo=tipo, andar=andar)
        db.session.add(s)
        db.session.flush()
        for i in range(1, qtd + 1):
            l = Leito(setor_id=s.id, unidade_id=unidade_id, numero=f'{sigla}-{i:02d}',
                      tipo='uti' if tipo=='uti' else 'comum')
            db.session.add(l)

    for nome, tipo in [('CC-01','geral'),('CC-02','geral'),
                       ('CC-Ortopedia','ortopedia'),('CC-Urgência','urgencia')]:
        db.session.add(SalaCirurgica(nome=nome, tipo=tipo))

    db.session.commit()