r"""
================================================================================
  AUTOMAÇÃO WABBAJACK — Modo Gratuito (sem conta Nexus Premium)
  Clica automaticamente em "Slow Download" para qualquer modlist Wabbajack.

  USO RÁPIDO:
    python instal.py                                       # usa o caminho padrão
    python instal.py --modlist "D:\MinhaLista.wabbajack"
    python instal.py --all-steps                           # automatiza etapas 1-4
    python instal.py --help                                # mostra todas as opções

  DEPENDÊNCIAS:
    pip install pyautogui opencv-python Pillow pygetwindow

  IMAGENS NECESSÁRIAS (pasta imgs/ ao lado deste script):
    imgs/btn_slow_download.png     ← obrigatória
    imgs/btn_standard_download.png ← opcional (fallback)
    imgs/btn_manual_download.png   ← opcional (fallback)
    imgs/btn_install_from_disk.png ← só com --all-steps
    imgs/btn_open.png              ← só com --all-steps
    imgs/btn_install.png           ← só com --all-steps

  CAPTURA DAS IMAGENS:
    Use WIN+SHIFT+S (Recorte do Windows) para tirar print da região exata
    de cada botão conforme as instruções abaixo:

    1. btn_install_from_disk.png
       → Wabbajack na tela "Browse Lists" → botão "Install from disk"
    2. btn_open.png
       → Qualquer janela de diálogo do Windows → botão "Abrir" / "Open"
    3. btn_install.png
       → Wabbajack após carregar o modlist → botão "Install" (canto inferior)
    4. btn_slow_download.png  ← MAIS IMPORTANTE
       → Nexus Mods pedindo download manual → botão "Slow Download" (cinza/verde)
    5. btn_standard_download.png / btn_manual_download.png (opcionais)
       → Mesma tela, variações de resolução/zoom — aumentam robustez

  SEGURANÇA:
    Mova o mouse para o CANTO SUPERIOR ESQUERDO para abortar imediatamente.
    O script NÃO armazena nem transmite credenciais.
================================================================================
"""

import argparse
import os
import subprocess
import sys
import time
import logging
import pyautogui
import pygetwindow as gw

# ─────────────────────────────────────────────────────────────────────────────
#  CONFIGURAÇÕES PADRÃO (substituíveis via argumentos de linha de comando)
# ─────────────────────────────────────────────────────────────────────────────

pyautogui.FAILSAFE = True

BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
IMGS_DIR  = os.path.join(BASE_DIR, "imgs")

MODLIST_PATH             = r"D:\FrostDays 1.5.wabbajack"
CONFIANCA                = 0.80
TIMEOUT_BOTAO            = 60
INTERVALO_LOOP           = 2
ESPERA_APOS_DOWNLOAD     = 5
MAX_TENTATIVAS_SEM_BOTAO = 150   # ~5 min sem achar botão → encerra

IMAGENS_DOWNLOAD = [
    "btn_standard_download.png",
    "btn_slow_download.png",
    "btn_manual_download.png",
]

# ─────────────────────────────────────────────────────────────────────────────
#  LOG
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
    """Verifica se a imagem obrigatória existe; encerra com código 1 se faltar."""
    obrigatorias = ["btn_slow_download.png"]
    faltando = [f for f in obrigatorias if not os.path.exists(img(f))]
    if faltando:
        log.error("Imagens de referência FALTANDO na pasta 'imgs':")
        for f in faltando:
            log.error(f"  → {f}")
        log.error("Leia as instruções no topo do script para saber como capturá-las.")
        sys.exit(1)
    log.info("✔ Todas as imagens de referência encontradas.")


def aguardar_botao(nome_img: str, timeout: int = None, confianca: float = None):
    """
    Aguarda um botão aparecer na tela por até `timeout` segundos.
    Retorna a localização (Box) ou None se não encontrado.
    """
    if timeout is None:
        timeout = TIMEOUT_BOTAO
    if confianca is None:
        confianca = CONFIANCA

    caminho = img(nome_img)
    inicio  = time.time()
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
    """Traz ao foco a primeira janela cujo título contenha `titulo_parcial`."""
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
#  ETAPAS
# ─────────────────────────────────────────────────────────────────────────────

def etapa1_install_from_disk():
    log.info("=" * 60)
    log.info("ETAPA 1: Clicando em 'Install from disk'")
    log.info("=" * 60)

    if not focar_janela("Wabbajack"):
        log.warning("Janela do Wabbajack não encontrada. Continuando mesmo assim...")

    time.sleep(1)
    localizacao = aguardar_botao("btn_install_from_disk.png", timeout=30)
    if not localizacao:
        raise RuntimeError(
            "Botão 'Install from disk' não encontrado. "
            "Verifique se o Wabbajack está aberto na tela correta."
        )

    clicar_centro(localizacao)
    log.info("  → 'Install from disk' clicado. Aguardando janela de arquivo...")
    time.sleep(2)


def etapa2_selecionar_modlist():
    log.info("=" * 60)
    log.info("ETAPA 2: Selecionando o arquivo do modlist")
    log.info(f"  Caminho: {MODLIST_PATH}")
    log.info("=" * 60)

    time.sleep(1.5)

    try:
        pyautogui.hotkey("alt", "n")
        time.sleep(0.5)
        pyautogui.hotkey("ctrl", "a")
        time.sleep(0.2)
        pyautogui.typewrite(MODLIST_PATH, interval=0.04)
        time.sleep(0.5)
        log.info(f"  → Caminho digitado: {MODLIST_PATH}")
    except Exception as e:
        log.warning(f"  ⚠ Erro ao digitar caminho: {e}")
        log.info("  → Tentando via clipboard...")
        # Sem shell=True para evitar injeção de comandos
        subprocess.run(["clip"], input=MODLIST_PATH.encode("utf-8"), check=False)
        pyautogui.hotkey("ctrl", "v")
        time.sleep(0.5)

    localizacao = aguardar_botao("btn_open.png", timeout=15)
    if localizacao:
        clicar_centro(localizacao)
    else:
        log.warning("  ⚠ Botão 'Abrir' não encontrado. Tentando via ENTER...")
        pyautogui.press("enter")

    log.info("  → Arquivo selecionado. Aguardando Wabbajack carregar o modlist (15s)...")
    time.sleep(15)


def etapa3_iniciar_instalacao():
    log.info("=" * 60)
    log.info("ETAPA 3: Iniciando a instalação")
    log.info("=" * 60)

    if not focar_janela("Wabbajack"):
        log.warning("  ⚠ Janela do Wabbajack não encontrada. Continuando mesmo assim...")

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


def etapa4_loop_slow_download():
    log.info("=" * 60)
    log.info("ETAPA 4: Loop automático de 'Slow Download'")
    log.info("  (Mova o mouse para o canto superior ESQUERDO para abortar)")
    log.info("=" * 60)

    clicks_realizados    = 0
    tentativas_sem_botao = 0

    while tentativas_sem_botao < MAX_TENTATIVAS_SEM_BOTAO:
        botao_encontrado = False

        for nome_img in IMAGENS_DOWNLOAD:
            caminho = img(nome_img)
            if not os.path.exists(caminho):
                continue

            try:
                localizacao = pyautogui.locateOnScreen(caminho, confidence=CONFIANCA)
                if localizacao:
                    log.info(f"  🟢 Download #{clicks_realizados + 1} — Botão: {nome_img}")
                    clicar_centro(localizacao)
                    clicks_realizados    += 1
                    tentativas_sem_botao  = 0
                    botao_encontrado      = True
                    log.info(f"  ⏳ Aguardando {ESPERA_APOS_DOWNLOAD}s...")
                    time.sleep(ESPERA_APOS_DOWNLOAD)
                    break

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
                f"  ⏸ Botão não encontrado "
                f"({tentativas_sem_botao}/{MAX_TENTATIVAS_SEM_BOTAO}). "
                f"Rolando e aguardando {INTERVALO_LOOP}s..."
            )
            pyautogui.scroll(-500)
            time.sleep(INTERVALO_LOOP)

    log.info("=" * 60)
    log.info(f"✅ Loop encerrado. Total de cliques: {clicks_realizados}")
    log.info("=" * 60)


# ─────────────────────────────────────────────────────────────────────────────
#  CLI
# ─────────────────────────────────────────────────────────────────────────────

def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Automação Wabbajack — clica em Slow Download automaticamente",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Exemplos:\n"
            "  python instal.py\n"
            "  python instal.py --modlist \"D:\\MinhaLista.wabbajack\"\n"
            "  python instal.py --all-steps --confidence 0.75\n"
            "  python instal.py --imgs-dir C:\\meus-prints\n"
        ),
    )
    parser.add_argument(
        "--modlist", "-m",
        default=MODLIST_PATH,
        metavar="CAMINHO",
        help=f"Arquivo .wabbajack a instalar (padrão: {MODLIST_PATH})",
    )
    parser.add_argument(
        "--confidence", "-c",
        type=float, default=CONFIANCA,
        metavar="0.0-1.0",
        help=f"Confiança mínima para reconhecimento de imagem (padrão: {CONFIANCA})",
    )
    parser.add_argument(
        "--timeout", "-t",
        type=int, default=TIMEOUT_BOTAO,
        metavar="SEGS",
        help=f"Espera máxima por botão em segundos (padrão: {TIMEOUT_BOTAO})",
    )
    parser.add_argument(
        "--interval", "-i",
        type=float, default=INTERVALO_LOOP,
        metavar="SEGS",
        help=f"Intervalo entre verificações no loop (padrão: {INTERVALO_LOOP})",
    )
    parser.add_argument(
        "--wait", "-w",
        type=float, default=ESPERA_APOS_DOWNLOAD,
        metavar="SEGS",
        help=f"Espera após clicar no botão (padrão: {ESPERA_APOS_DOWNLOAD})",
    )
    parser.add_argument(
        "--max-attempts", "-a",
        type=int, default=MAX_TENTATIVAS_SEM_BOTAO,
        metavar="N",
        help=f"Tentativas sem botão antes de encerrar (padrão: {MAX_TENTATIVAS_SEM_BOTAO} ≈ 5 min)",
    )
    parser.add_argument(
        "--imgs-dir",
        default=None,
        metavar="PASTA",
        help="Pasta com as imagens de referência (padrão: imgs/ ao lado do script)",
    )
    parser.add_argument(
        "--all-steps",
        action="store_true",
        help="Executar todas as etapas 1-4 (inclui seleção automática do modlist)",
    )
    return parser.parse_args(argv)


# ─────────────────────────────────────────────────────────────────────────────
#  PONTO DE ENTRADA
# ─────────────────────────────────────────────────────────────────────────────

def main(argv=None):
    global MODLIST_PATH, CONFIANCA, TIMEOUT_BOTAO, INTERVALO_LOOP
    global ESPERA_APOS_DOWNLOAD, MAX_TENTATIVAS_SEM_BOTAO, IMGS_DIR

    args = parse_args(argv)
    MODLIST_PATH             = args.modlist
    CONFIANCA                = args.confidence
    TIMEOUT_BOTAO            = args.timeout
    INTERVALO_LOOP           = args.interval
    ESPERA_APOS_DOWNLOAD     = args.wait
    MAX_TENTATIVAS_SEM_BOTAO = args.max_attempts
    if args.imgs_dir:
        IMGS_DIR = args.imgs_dir

    log.info("╔══════════════════════════════════════════════════════════╗")
    log.info("║   AUTOMAÇÃO WABBAJACK — Modo Gratuito                   ║")
    log.info("║   Iniciando em 5 segundos... (Ctrl+C para cancelar)     ║")
    log.info("╚══════════════════════════════════════════════════════════╝")
    log.info(f"  Modlist  : {MODLIST_PATH}")
    log.info(f"  Imagens  : {IMGS_DIR}")
    log.info(f"  Confiança: {CONFIANCA}  |  Timeout: {TIMEOUT_BOTAO}s")

    verificar_imagens()

    for i in range(5, 0, -1):
        log.info(f"  Iniciando em {i}s...")
        time.sleep(1)

    try:
        if args.all_steps:
            etapa1_install_from_disk()
            etapa2_selecionar_modlist()
            etapa3_iniciar_instalacao()

        etapa4_loop_slow_download()

    except pyautogui.FailSafeException:
        log.info("\n🛑 FAILSAFE ativado! Script encerrado com segurança.")

    except KeyboardInterrupt:
        log.info("\n⚠ Script interrompido pelo usuário (Ctrl+C).")

    except Exception as e:
        log.error(f"\n❌ Erro inesperado: {e}", exc_info=True)
        log.error("Verifique 'wabbajack_auto.log' para detalhes.")

    finally:
        log.info("Script finalizado.")


if __name__ == "__main__":
    main()
