/* ============================================================================
   Comportamento do shell — porte de Sidebar.tsx / ThemeToggle.tsx /
   LgpdConsentBanner.tsx do frontend Next.

   Sem framework: só delegação de eventos e localStorage.
   ========================================================================= */
(function () {
  'use strict';

  var CHAVE_TEMA = 'snpe-tema';
  var CHAVE_NAV = 'snpe-nav-abertas';
  var CHAVE_LGPD = 'snpe-lgpd-ok';

  function ler(chave, padrao) {
    try {
      var v = localStorage.getItem(chave);
      return v === null ? padrao : JSON.parse(v);
    } catch (e) {
      return padrao;
    }
  }

  function gravar(chave, valor) {
    try {
      localStorage.setItem(chave, JSON.stringify(valor));
    } catch (e) {
      /* modo privado / storage cheio — o estado fica só em memória */
    }
  }

  /* ---------------- Tema claro/escuro ---------------- */
  function alternarTema() {
    var atual = document.documentElement.dataset.theme === 'dark' ? 'dark' : 'light';
    var proximo = atual === 'dark' ? 'light' : 'dark';
    document.documentElement.dataset.theme = proximo;
    try {
      localStorage.setItem(CHAVE_TEMA, proximo);
    } catch (e) {}
  }

  /* ---------------- Grupos da navegação ---------------- */
  function restaurarNav() {
    var abertas = ler(CHAVE_NAV, {});
    var grupos = document.querySelectorAll('[data-navgroup]');

    for (var i = 0; i < grupos.length; i++) {
      var grupo = grupos[i];
      var titulo = grupo.getAttribute('data-navgroup');

      // O grupo da rota ativa fica SEMPRE aberto: nunca esconder onde o
      // operador está. Fora disso, vale a preferência salva; sem preferência,
      // tudo aberto — descoberta importa mais que densidade.
      var temAtivo = !!grupo.querySelector('[aria-current="page"]');
      var aberto = temAtivo || (titulo in abertas ? !!abertas[titulo] : true);

      aplicarEstado(grupo, aberto);
    }
  }

  function aplicarEstado(grupo, aberto) {
    grupo.setAttribute('data-open', aberto ? 'true' : 'false');
    var btn = grupo.querySelector('[data-navgroup-toggle]');
    if (btn) btn.setAttribute('aria-expanded', aberto ? 'true' : 'false');
  }

  function alternarGrupo(grupo) {
    var aberto = grupo.getAttribute('data-open') !== 'true';
    aplicarEstado(grupo, aberto);

    var abertas = ler(CHAVE_NAV, {});
    abertas[grupo.getAttribute('data-navgroup')] = aberto;
    gravar(CHAVE_NAV, abertas);
  }

  /* ---------------- Menu (mobile) ---------------- */
  function alternarMenu() {
    var aberto = document.body.getAttribute('data-menu') === 'open';
    document.body.setAttribute('data-menu', aberto ? 'closed' : 'open');
  }

  function fecharMenu() {
    document.body.setAttribute('data-menu', 'closed');
  }

  /* ---------------- Banner de consentimento LGPD ---------------- */
  function iniciarLgpd() {
    var banner = document.querySelector('[data-lgpd-banner]');
    if (!banner) return;
    if (ler(CHAVE_LGPD, false)) return;
    banner.classList.remove('hidden');
  }

  function aceitarLgpd(banner) {
    gravar(CHAVE_LGPD, true);
    banner.classList.add('hidden');
  }

  /* ---------------- Confirmação de ação destrutiva ---------------- */
  // Qualquer form/botão com data-confirm="mensagem" pede confirmação.
  function interceptarConfirmacao(evento) {
    var alvo = evento.target.closest('[data-confirm]');
    if (!alvo) return;
    if (!window.confirm(alvo.getAttribute('data-confirm'))) {
      evento.preventDefault();
      evento.stopPropagation();
    }
  }

  /* ---------------- Bootstrap ---------------- */
  document.addEventListener('DOMContentLoaded', function () {
    restaurarNav();
    iniciarLgpd();

    document.addEventListener('click', function (evento) {
      if (evento.target.closest('[data-theme-toggle]')) {
        alternarTema();
        return;
      }

      var toggleGrupo = evento.target.closest('[data-navgroup-toggle]');
      if (toggleGrupo) {
        alternarGrupo(toggleGrupo.closest('[data-navgroup]'));
        return;
      }

      if (evento.target.closest('[data-menu-toggle]')) {
        alternarMenu();
        return;
      }

      var okLgpd = evento.target.closest('[data-lgpd-ok]');
      if (okLgpd) {
        aceitarLgpd(okLgpd.closest('[data-lgpd-banner]'));
        return;
      }

      // Clique no backdrop (o ::after do body) fecha o menu no mobile.
      if (
        document.body.getAttribute('data-menu') === 'open' &&
        !evento.target.closest('#sidebar') &&
        !evento.target.closest('[data-menu-toggle]')
      ) {
        fecharMenu();
      }
    });

    document.addEventListener('submit', interceptarConfirmacao, true);
    document.addEventListener('click', interceptarConfirmacao, true);

    document.addEventListener('keydown', function (evento) {
      if (evento.key === 'Escape') fecharMenu();
    });
  });
})();
