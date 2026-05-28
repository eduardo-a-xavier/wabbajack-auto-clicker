"""
================================================================================
  AUTOMAÇÃO WABBAJACK - FrostDays 1.5
  Script para automação do instalador de modlists Wabbajack no modo gratuito
  (sem conta Nexus Premium), clicando automaticamente em "Slow Download".

  DEPENDÊNCIAS:
    pip install pyautogui opencv-python Pillow pygetwindow

  IMAGENS NECESSÁRIAS (leia as instruções abaixo):
    imgs/btn_install_from_disk.png
    imgs/btn_open.png
    imgs/btn_install.png
    imgs/btn_slow_download.png
    imgs/btn_manual_download.png   (fallback para "Slow Download")

  INSTRUÇÕES PARA CAPTURA DAS IMAGENS:
    Crie uma pasta chamada "imgs" dentro da pasta deste script.
    Tire os prints das REGIÕES EXATAS dos botões conforme abaixo:

    1. btn_install_from_disk.png
       → Abra o Wabbajack na tela de "Browse Lists"
       → Tire print (WIN+SHIFT+S) apenas do botão "Install from disk" 
         (canto superior direito, texto amarelo)

    2. btn_open.png
       → Abra qualquer janela de diálogo de arquivo do Windows
       → Tire print apenas do botão "Abrir" / "Open"

    3. btn_install.png
       → Após carregar o modlist no Wabbajack, tire print do botão 
         "Install" (canto inferior direito da tela do Wabbajack)

    4. btn_slow_download.png
       → Quando o Nexus Mods abrir pedindo download manual, tire print 
         do botão "Slow Download" (botão cinza/verde grande na página)
       → DICA: faça um download manual na mão primeiro, salve o print 
         desse botão ANTES de rodar o script.

    5. btn_manual_download.png  (opcional, fallback)
       → Mesmo botão que slow_download, mas de outra resolução/zoom.

  ATENÇÃO DE SEGURANÇA:
    - Mova o mouse para o CANTO SUPERIOR ESQUERDO da tela para abortar 
      o script a qualquer momento (pyautogui.FAILSAFE = True).
    - O script NÃO armazena nem transmite nenhuma credencial.
================================================================================
"""

import os
import sys
import time
import logging
import pyautogui
import pygetwindow as gw

# ─────────────────────────────────────────────────────────────────────────────
#  CONFIGURAÇÕES GLOBAIS
# ─────────────────────────────────────────────────────────────────────────────

# Segurança: mover o mouse para o canto superior esquerdo aborta o script
pyautogui.FAILSAFE = True

# Pasta base deste script
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Pasta com as imagens de referência dos botões
IMGS_DIR = os.path.join(BASE_DIR, "imgs")

# Caminho completo do arquivo .wabbajack do modlist
MODLIST_PATH = r"D:\FrostDays 1.5.wabbajack"

# Confiança mínima para o reconhecimento de imagem (0.0 a 1.0)
# Reduza para 0.7 se o script não encontrar os botões
CONFIANCA = 0.80

# Tempo (segundos) de espera máximo para um botão aparecer na tela
TIMEOUT_BOTAO = 60

# Tempo (segundos) entre cada verificação no loop de downloads
INTERVALO_LOOP = 2

# Tempo de espera após clicar em Slow Download (para a aba fechar)
ESPERA_APOS_DOWNLOAD = 5

# ─────────────────────────────────────────────────────────────────────────────
#  CONFIGURAÇÃO DE LOG
# ─────────────────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(os.path.join(BASE_DIR, "wabbajack_auto.log"), encoding="utf-8"),
    ],
)
log = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
#  FUNÇÕES AUXILIARES
# ─────────────────────────────────────────────────────────────────────────────

def img(nome_arquivo: str) -> str:
    """Retorna o caminho completo de uma imagem de referência."""
    return os.path.join(IMGS_DIR, nome_arquivo)


def verificar_imagens():
    """Verifica se todas as imagens de referência obrigatórias existem."""
    obrigatorias = [
        "btn_slow_download.png",
    ]
    faltando = [f for f in obrigatorias if not os.path.exists(img(f))]
    if faltando:
        log.error("As seguintes imagens de referência estão FALTANDO na pasta 'imgs':")
        for f in faltando:
            log.error(f"  → {f}")
        log.error("Leia as instruções no topo do script para saber como capturá-las.")
        sys.exit(1)
    log.info("✔ Todas as imagens de referência encontradas.")


def aguardar_botao(nome_img: str, timeout: int = TIMEOUT_BOTAO, confianca: float = CONFIANCA):
    """
    Aguarda um botão aparecer na tela por até `timeout` segundos.
    Retorna a localização (Box) ou None se não encontrado.
    """
    caminho = img(nome_img)
    inicio = time.time()
    log.info(f"Aguardando botão: {nome_img} (timeout={timeout}s) ...")

    while time.time() - inicio < timeout:
        try:
            localizacao = pyautogui.locateOnScreen(caminho, confidence=confianca)
            if localizacao:
                log.info(f"  ✔ Botão encontrado: {nome_img} em {localizacao}")
                return localizacao
        except pyautogui.ImageNotFoundException:
            pass
        except Exception as e:
            log.warning(f"  ⚠ Erro ao procurar {nome_img}: {e}")
        time.sleep(0.5)

    log.warning(f"  ✘ Botão NÃO encontrado após {timeout}s: {nome_img}")
    return None


def clicar_centro(localizacao):
    """Clica no centro de um Box retornado pelo pyautogui."""
    cx, cy = pyautogui.center(localizacao)
    pyautogui.moveTo(cx, cy, duration=0.3)
    time.sleep(0.1)
    pyautogui.click()
    log.info(f"  🖱 Clique em ({cx}, {cy})")


def focar_janela(titulo_parcial: str) -> bool:
    """Tenta trazer ao foco uma janela com título parcial informado."""
    try:
        janelas = gw.getWindowsWithTitle(titulo_parcial)
        if janelas:
            janela = janelas[0]
            janela.activate()
            time.sleep(0.5)
            log.info(f"  ✔ Janela '{janela.title}' em foco.")
            return True
    except Exception as e:
        log.warning(f"  ⚠ Não foi possível focar janela '{titulo_parcial}': {e}")
    return False


# ─────────────────────────────────────────────────────────────────────────────
#  ETAPA 1 — Clicar em "Install from disk" no Wabbajack
# ─────────────────────────────────────────────────────────────────────────────

def etapa1_install_from_disk():
    log.info("=" * 60)
    log.info("ETAPA 1: Clicando em 'Install from disk'")
    log.info("=" * 60)

    # Tenta focar a janela do Wabbajack
    if not focar_janela("Wabbajack"):
        log.warning("Janela do Wabbajack não encontrada pelo título. Continuando mesmo assim...")

    time.sleep(1)

    localizacao = aguardar_botao("btn_install_from_disk.png", timeout=30)
    if not localizacao:
        raise RuntimeError(
            "Botão 'Install from disk' não encontrado. "
            "Verifique se o Wabbajack está aberto e na tela correta."
        )

    clicar_centro(localizacao)
    log.info("  → 'Install from disk' clicado. Aguardando janela de arquivo...")
    time.sleep(2)


# ─────────────────────────────────────────────────────────────────────────────
#  ETAPA 2 — Selecionar o arquivo .wabbajack na janela de diálogo
# ─────────────────────────────────────────────────────────────────────────────

def etapa2_selecionar_modlist():
    log.info("=" * 60)
    log.info("ETAPA 2: Selecionando o arquivo do modlist")
    log.info(f"  Caminho: {MODLIST_PATH}")
    log.info("=" * 60)

    time.sleep(1.5)

    # Digita o caminho completo do arquivo na barra de endereço da janela
    # usando o atalho que funciona em qualquer janela de diálogo do Windows
    try:
        # Ativa o campo "Nome do arquivo" com Alt+N ou digita diretamente
        pyautogui.hotkey("alt", "n")  # Foca o campo Nome
        time.sleep(0.5)
        pyautogui.hotkey("ctrl", "a")  # Seleciona tudo
        time.sleep(0.2)
        pyautogui.typewrite(MODLIST_PATH, interval=0.04)
        time.sleep(0.5)
        log.info(f"  → Caminho digitado: {MODLIST_PATH}")
    except Exception as e:
        log.warning(f"  ⚠ Erro ao digitar caminho com typewrite: {e}")
        log.info("  → Tentando via clipboard...")
        import subprocess
        subprocess.run(
            f'echo {MODLIST_PATH}| clip',
            shell=True
        )
        pyautogui.hotkey("ctrl", "v")
        time.sleep(0.5)

    # Clica no botão "Abrir" / "Open"
    localizacao = aguardar_botao("btn_open.png", timeout=15)
    if localizacao:
        clicar_centro(localizacao)
    else:
        log.warning("  ⚠ Botão 'Abrir' não encontrado pela imagem. Tentando via ENTER...")
        pyautogui.press("enter")

    log.info("  → Arquivo selecionado. Aguardando Wabbajack carregar o modlist (15s)...")
    time.sleep(15)  # Wabbajack leva ~10-15s para mapear


# ─────────────────────────────────────────────────────────────────────────────
#  ETAPA 3 — Clicar no botão "Install"
# ─────────────────────────────────────────────────────────────────────────────

def etapa3_iniciar_instalacao():
    log.info("=" * 60)
    log.info("ETAPA 3: Iniciando a instalação")
    log.info("=" * 60)

    # Volta o foco para o Wabbajack
    focar_janela("Wabbajack")
    time.sleep(1)

    localizacao = aguardar_botao("btn_install.png", timeout=30)
    if not localizacao:
        raise RuntimeError(
            "Botão 'Install' não encontrado. "
            "Verifique se o modlist foi carregado corretamente."
        )

    clicar_centro(localizacao)
    log.info("  → Instalação iniciada! O Wabbajack começará a abrir páginas do Nexus.")
    time.sleep(3)


# ─────────────────────────────────────────────────────────────────────────────
#  ETAPA 4 — Loop: clicar em "Slow Download" repetidamente
# ─────────────────────────────────────────────────────────────────────────────

def etapa4_loop_slow_download():
    log.info("=" * 60)
    log.info("ETAPA 4: Loop automático de 'Slow Download'")
    log.info("  (Mova o mouse para o canto superior ESQUERDO para abortar)")
    log.info("=" * 60)

    # Nomes das imagens a tentar (fallback entre elas)
    imagens_download = [
        "btn_standard_download.png",
        "btn_slow_download.png",
        "btn_manual_download.png",
    ]

    clicks_realizados = 0
    tentativas_sem_botao = 0
    MAX_TENTATIVAS_SEM_BOTAO = 150  # ~5 minutos sem achar (esperando downloads grandes)

    while tentativas_sem_botao < MAX_TENTATIVAS_SEM_BOTAO:
        botao_encontrado = False

        for nome_img in imagens_download:
            caminho = img(nome_img)
            if not os.path.exists(caminho):
                continue  # Pula imagens que não existem (ex: fallback opcional)

            try:
                localizacao = pyautogui.locateOnScreen(caminho, confidence=CONFIANCA)
                if localizacao:
                    log.info(f"  🟢 Download #{clicks_realizados + 1} — Botão encontrado: {nome_img}")
                    clicar_centro(localizacao)
                    clicks_realizados += 1
                    tentativas_sem_botao = 0  # Reset do contador de espera
                    botao_encontrado = True

                    log.info(f"  ⏳ Aguardando {ESPERA_APOS_DOWNLOAD}s para o download iniciar...")
                    time.sleep(ESPERA_APOS_DOWNLOAD)
                    break  # Sai do for e volta para o while

            except pyautogui.ImageNotFoundException:
                pass
            except pyautogui.FailSafeException:
                log.info("\n🛑 FAILSAFE ativado! Script encerrado pelo usuário.")
                return
            except Exception as e:
                log.warning(f"  ⚠ Erro ao buscar {nome_img}: {e}")

        if not botao_encontrado:
            tentativas_sem_botao += 1
            log.info(
                f"  ⏸ Botão de download não encontrado "
                f"({tentativas_sem_botao}/{MAX_TENTATIVAS_SEM_BOTAO}). "
                f"Rolando a tela e aguardando {INTERVALO_LOOP}s..."
            )
            pyautogui.scroll(-500)  # Rola a tela para baixo
            time.sleep(INTERVALO_LOOP)

    log.info("=" * 60)
    log.info(f"✅ Loop encerrado. Total de downloads clicados: {clicks_realizados}")
    log.info(
        "   Se ainda houver mods pendentes, o Wabbajack pode ter pausado ou "
        "todos os downloads foram concluídos."
    )
    log.info("=" * 60)


# ─────────────────────────────────────────────────────────────────────────────
#  PONTO DE ENTRADA PRINCIPAL
# ─────────────────────────────────────────────────────────────────────────────

def main():
    log.info("╔══════════════════════════════════════════════════════════╗")
    log.info("║   AUTOMAÇÃO WABBAJACK — FrostDays 1.5                   ║")
    log.info("║   Iniciando em 5 segundos... (Alt+F4 para cancelar)     ║")
    log.info("╚══════════════════════════════════════════════════════════╝")

    # Verifica imagens antes de começar
    verificar_imagens()

    # Pausa para o usuário posicionar as janelas
    for i in range(5, 0, -1):
        log.info(f"  Iniciando em {i}s...")
        time.sleep(1)

    try:
        etapa4_loop_slow_download()

    except pyautogui.FailSafeException:
        log.info("\n🛑 FAILSAFE ativado! Script encerrado com segurança.")

    except KeyboardInterrupt:
        log.info("\n⚠ Script interrompido pelo usuário (Ctrl+C).")

    except Exception as e:
        log.error(f"\n❌ Erro inesperado: {e}", exc_info=True)
        log.error("Verifique o arquivo 'wabbajack_auto.log' para detalhes.")

    finally:
        log.info("Script finalizado.")


if __name__ == "__main__":
    main()
