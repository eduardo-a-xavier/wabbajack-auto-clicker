"""
Testes unitários para instal.py.
Toda chamada de hardware (tela, mouse, janelas) é interceptada por mocks.
"""

import itertools
import os
import sys
import pytest
from unittest.mock import MagicMock, patch, call

# conftest.py já inseriu os mocks de pyautogui/pygetwindow antes deste import
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import instal


# ─────────────────────────────────────────────────────────────────────────────
#  img()
# ─────────────────────────────────────────────────────────────────────────────

class TestImg:
    def test_retorna_caminho_dentro_de_imgs_dir(self, tmp_path):
        with patch.object(instal, "IMGS_DIR", str(tmp_path)):
            resultado = instal.img("btn_slow_download.png")
        assert resultado == os.path.join(str(tmp_path), "btn_slow_download.png")

    def test_funciona_com_qualquer_nome_de_arquivo(self, tmp_path):
        with patch.object(instal, "IMGS_DIR", str(tmp_path)):
            resultado = instal.img("qualquer.png")
        assert resultado.endswith("qualquer.png")
        assert str(tmp_path) in resultado


# ─────────────────────────────────────────────────────────────────────────────
#  verificar_imagens()
# ─────────────────────────────────────────────────────────────────────────────

class TestVerificarImagens:
    def test_encerra_processo_quando_imagem_falta(self, tmp_path):
        with patch.object(instal, "IMGS_DIR", str(tmp_path)):
            with pytest.raises(SystemExit) as exc:
                instal.verificar_imagens()
        assert exc.value.code == 1

    def test_nao_encerra_quando_imagem_existe(self, tmp_path):
        (tmp_path / "btn_slow_download.png").write_bytes(b"fake")
        with patch.object(instal, "IMGS_DIR", str(tmp_path)):
            instal.verificar_imagens()  # não deve lançar

    def test_loga_nome_da_imagem_faltando(self, tmp_path, caplog):
        import logging
        with patch.object(instal, "IMGS_DIR", str(tmp_path)), \
             caplog.at_level(logging.ERROR, logger="__main__"):
            with pytest.raises(SystemExit):
                instal.verificar_imagens()
        assert "btn_slow_download.png" in caplog.text


# ─────────────────────────────────────────────────────────────────────────────
#  aguardar_botao()
# ─────────────────────────────────────────────────────────────────────────────

class TestAguardarBotao:
    def test_retorna_localizacao_na_primeira_tentativa(self, tmp_path):
        fake_box = MagicMock()
        with patch.object(instal, "IMGS_DIR", str(tmp_path)), \
             patch("instal.pyautogui.locateOnScreen", return_value=fake_box), \
             patch("instal.time.sleep"), \
             patch("instal.time.time", return_value=0.0):
            resultado = instal.aguardar_botao("btn.png", timeout=60, confianca=0.8)
        assert resultado is fake_box

    def test_retorna_none_quando_timeout_esgotado(self, tmp_path):
        # Usa itertools.repeat para nunca esgotar o side_effect
        # (o logger interno também chama time.time() ao criar log records)
        time_values = itertools.chain([0.0], itertools.repeat(100.0))
        with patch.object(instal, "IMGS_DIR", str(tmp_path)), \
             patch("instal.pyautogui.locateOnScreen", return_value=None), \
             patch("instal.time.sleep"), \
             patch("instal.time.time", side_effect=time_values):
            resultado = instal.aguardar_botao("btn.png", timeout=1, confianca=0.8)
        assert resultado is None

    def test_retorna_localizacao_apos_algumas_tentativas(self, tmp_path):
        fake_box = MagicMock()
        with patch.object(instal, "IMGS_DIR", str(tmp_path)), \
             patch("instal.pyautogui.locateOnScreen", side_effect=[None, None, fake_box]), \
             patch("instal.time.sleep"), \
             patch("instal.time.time", return_value=0.0):  # nunca expira
            resultado = instal.aguardar_botao("btn.png", timeout=60, confianca=0.8)
        assert resultado is fake_box

    def test_trata_image_not_found_exception_sem_propagar(self, tmp_path):
        # [0.0, 0.0] garante que o loop entra ao menos uma vez antes de expirar
        time_values = itertools.chain([0.0, 0.0], itertools.repeat(100.0))
        with patch.object(instal, "IMGS_DIR", str(tmp_path)), \
             patch("instal.pyautogui.locateOnScreen",
                   side_effect=instal.pyautogui.ImageNotFoundException), \
             patch("instal.time.sleep"), \
             patch("instal.time.time", side_effect=time_values):
            resultado = instal.aguardar_botao("btn.png", timeout=1, confianca=0.8)
        assert resultado is None

    def test_trata_excecao_generica_com_warning(self, tmp_path, caplog):
        import logging
        # [0.0, 0.0] faz o loop entrar, OSError é capturado e logado como warning
        time_values = itertools.chain([0.0, 0.0], itertools.repeat(100.0))
        with patch.object(instal, "IMGS_DIR", str(tmp_path)), \
             patch("instal.pyautogui.locateOnScreen", side_effect=OSError("sem display")), \
             patch("instal.time.sleep"), \
             patch("instal.time.time", side_effect=time_values), \
             caplog.at_level(logging.WARNING):
            resultado = instal.aguardar_botao("btn.png", timeout=1, confianca=0.8)
        assert resultado is None
        assert "Erro ao procurar" in caplog.text

    def test_usa_timeout_global_quando_nao_informado(self, tmp_path):
        time_values = itertools.chain([0.0], itertools.repeat(200.0))
        with patch.object(instal, "IMGS_DIR", str(tmp_path)), \
             patch.object(instal, "TIMEOUT_BOTAO", 99), \
             patch("instal.pyautogui.locateOnScreen", return_value=None), \
             patch("instal.time.sleep"), \
             patch("instal.time.time", side_effect=time_values) as mock_time:
            instal.aguardar_botao("btn.png")
        # Com TIMEOUT_BOTAO=99 e time pulando para 200.0 logo, sai rápido
        assert mock_time.call_count >= 2


# ─────────────────────────────────────────────────────────────────────────────
#  clicar_centro()
# ─────────────────────────────────────────────────────────────────────────────

class TestClicarCentro:
    def test_move_para_o_centro_e_clica(self):
        fake_box = MagicMock()
        with patch("instal.pyautogui.center", return_value=(100, 200)), \
             patch("instal.pyautogui.moveTo") as mock_move, \
             patch("instal.pyautogui.click") as mock_click, \
             patch("instal.time.sleep"):
            instal.clicar_centro(fake_box)
        mock_move.assert_called_once_with(100, 200, duration=0.3)
        mock_click.assert_called_once()

    def test_passa_coordenadas_corretas_ao_moveto(self):
        fake_box = MagicMock()
        with patch("instal.pyautogui.center", return_value=(42, 99)), \
             patch("instal.pyautogui.moveTo") as mock_move, \
             patch("instal.pyautogui.click"), \
             patch("instal.time.sleep"):
            instal.clicar_centro(fake_box)
        args, _ = mock_move.call_args
        assert args == (42, 99)

    def test_chama_center_com_a_localizacao_recebida(self):
        fake_box = MagicMock()
        with patch("instal.pyautogui.center", return_value=(0, 0)) as mock_center, \
             patch("instal.pyautogui.moveTo"), \
             patch("instal.pyautogui.click"), \
             patch("instal.time.sleep"):
            instal.clicar_centro(fake_box)
        mock_center.assert_called_once_with(fake_box)


# ─────────────────────────────────────────────────────────────────────────────
#  focar_janela()
# ─────────────────────────────────────────────────────────────────────────────

class TestFocarJanela:
    def test_retorna_true_e_ativa_quando_janela_encontrada(self):
        mock_janela = MagicMock()
        mock_janela.title = "Wabbajack 3.0"
        with patch("instal.gw.getWindowsWithTitle", return_value=[mock_janela]), \
             patch("instal.time.sleep"):
            resultado = instal.focar_janela("Wabbajack")
        assert resultado is True
        mock_janela.activate.assert_called_once()

    def test_retorna_false_quando_nenhuma_janela_encontrada(self):
        with patch("instal.gw.getWindowsWithTitle", return_value=[]), \
             patch("instal.time.sleep"):
            resultado = instal.focar_janela("Wabbajack")
        assert resultado is False

    def test_retorna_false_quando_activate_levanta_excecao(self):
        mock_janela = MagicMock()
        mock_janela.activate.side_effect = Exception("acesso negado")
        with patch("instal.gw.getWindowsWithTitle", return_value=[mock_janela]), \
             patch("instal.time.sleep"):
            resultado = instal.focar_janela("Wabbajack")
        assert resultado is False

    def test_usa_primeira_janela_da_lista(self):
        janela1, janela2 = MagicMock(), MagicMock()
        janela1.title = "Wabbajack"
        with patch("instal.gw.getWindowsWithTitle", return_value=[janela1, janela2]), \
             patch("instal.time.sleep"):
            instal.focar_janela("Wabbajack")
        janela1.activate.assert_called_once()
        janela2.activate.assert_not_called()


# ─────────────────────────────────────────────────────────────────────────────
#  etapa1_install_from_disk()
# ─────────────────────────────────────────────────────────────────────────────

class TestEtapa1:
    def test_levanta_runtime_error_quando_botao_nao_encontrado(self):
        with patch("instal.focar_janela", return_value=True), \
             patch("instal.aguardar_botao", return_value=None), \
             patch("instal.time.sleep"):
            with pytest.raises(RuntimeError, match="Install from disk"):
                instal.etapa1_install_from_disk()

    def test_clica_botao_quando_encontrado(self):
        fake_box = MagicMock()
        with patch("instal.focar_janela", return_value=True), \
             patch("instal.aguardar_botao", return_value=fake_box), \
             patch("instal.clicar_centro") as mock_click, \
             patch("instal.time.sleep"):
            instal.etapa1_install_from_disk()
        mock_click.assert_called_once_with(fake_box)

    def test_continua_quando_janela_nao_encontrada(self):
        fake_box = MagicMock()
        with patch("instal.focar_janela", return_value=False), \
             patch("instal.aguardar_botao", return_value=fake_box), \
             patch("instal.clicar_centro"), \
             patch("instal.time.sleep"):
            instal.etapa1_install_from_disk()  # não deve lançar


# ─────────────────────────────────────────────────────────────────────────────
#  etapa3_iniciar_instalacao()
# ─────────────────────────────────────────────────────────────────────────────

class TestEtapa3:
    def test_levanta_runtime_error_quando_botao_nao_encontrado(self):
        with patch("instal.focar_janela", return_value=True), \
             patch("instal.aguardar_botao", return_value=None), \
             patch("instal.time.sleep"):
            with pytest.raises(RuntimeError, match="Install"):
                instal.etapa3_iniciar_instalacao()

    def test_clica_quando_botao_encontrado(self):
        fake_box = MagicMock()
        with patch("instal.focar_janela", return_value=True), \
             patch("instal.aguardar_botao", return_value=fake_box), \
             patch("instal.clicar_centro") as mock_click, \
             patch("instal.time.sleep"):
            instal.etapa3_iniciar_instalacao()
        mock_click.assert_called_once_with(fake_box)

    def test_continua_quando_janela_nao_encontrada(self):
        fake_box = MagicMock()
        with patch("instal.focar_janela", return_value=False), \
             patch("instal.aguardar_botao", return_value=fake_box), \
             patch("instal.clicar_centro"), \
             patch("instal.time.sleep"):
            instal.etapa3_iniciar_instalacao()  # não deve lançar


# ─────────────────────────────────────────────────────────────────────────────
#  etapa4_loop_slow_download()
# ─────────────────────────────────────────────────────────────────────────────

class TestEtapa4:
    def test_clica_botao_quando_encontrado(self, tmp_path):
        (tmp_path / "btn_slow_download.png").write_bytes(b"fake")

        encontros = [0]

        def locate(path, confidence):
            if "btn_slow_download" in path:
                encontros[0] += 1
                return MagicMock() if encontros[0] == 1 else None
            return None

        cliques = []
        with patch.object(instal, "IMGS_DIR", str(tmp_path)), \
             patch.object(instal, "IMAGENS_DOWNLOAD", ["btn_slow_download.png"]), \
             patch.object(instal, "MAX_TENTATIVAS_SEM_BOTAO", 2), \
             patch("instal.pyautogui.locateOnScreen", side_effect=locate), \
             patch("instal.clicar_centro", side_effect=lambda _: cliques.append(1)), \
             patch("instal.pyautogui.scroll"), \
             patch("instal.time.sleep"):
            instal.etapa4_loop_slow_download()

        assert len(cliques) == 1

    def test_encerra_apos_max_tentativas_sem_botao(self, tmp_path):
        (tmp_path / "btn_slow_download.png").write_bytes(b"fake")
        with patch.object(instal, "IMGS_DIR", str(tmp_path)), \
             patch.object(instal, "IMAGENS_DOWNLOAD", ["btn_slow_download.png"]), \
             patch.object(instal, "MAX_TENTATIVAS_SEM_BOTAO", 3), \
             patch("instal.pyautogui.locateOnScreen", return_value=None), \
             patch("instal.pyautogui.scroll"), \
             patch("instal.time.sleep"):
            instal.etapa4_loop_slow_download()  # não deve travar

    def test_failsafe_encerra_loop_imediatamente(self, tmp_path):
        (tmp_path / "btn_slow_download.png").write_bytes(b"fake")
        with patch.object(instal, "IMGS_DIR", str(tmp_path)), \
             patch.object(instal, "IMAGENS_DOWNLOAD", ["btn_slow_download.png"]), \
             patch.object(instal, "MAX_TENTATIVAS_SEM_BOTAO", 100), \
             patch("instal.pyautogui.locateOnScreen",
                   side_effect=instal.pyautogui.FailSafeException), \
             patch("instal.time.sleep"):
            instal.etapa4_loop_slow_download()  # não deve propagar exceção

    def test_pula_imagens_ausentes_no_disco(self, tmp_path):
        # Apenas btn_slow_download existe; as outras devem ser ignoradas
        (tmp_path / "btn_slow_download.png").write_bytes(b"fake")

        chamadas_locate = []

        def locate(path, confidence):
            chamadas_locate.append(os.path.basename(path))
            return None

        with patch.object(instal, "IMGS_DIR", str(tmp_path)), \
             patch.object(instal, "IMAGENS_DOWNLOAD", [
                 "btn_standard_download.png",
                 "btn_slow_download.png",
                 "btn_manual_download.png",
             ]), \
             patch.object(instal, "MAX_TENTATIVAS_SEM_BOTAO", 1), \
             patch("instal.pyautogui.locateOnScreen", side_effect=locate), \
             patch("instal.pyautogui.scroll"), \
             patch("instal.time.sleep"):
            instal.etapa4_loop_slow_download()

        assert "btn_standard_download.png" not in chamadas_locate
        assert "btn_manual_download.png" not in chamadas_locate
        assert "btn_slow_download.png" in chamadas_locate

    def test_reseta_contador_de_tentativas_apos_clique(self, tmp_path):
        (tmp_path / "btn_slow_download.png").write_bytes(b"fake")

        chamadas = [0]

        def locate(path, confidence):
            chamadas[0] += 1
            # Falha 2x, encontra na 3ª tentativa, falha depois
            return MagicMock() if chamadas[0] == 3 else None

        cliques = []
        # MAX=3: falha(1), falha(2), clique(3-reset), falha(4), falha(5), falha(6) → encerra
        with patch.object(instal, "IMGS_DIR", str(tmp_path)), \
             patch.object(instal, "IMAGENS_DOWNLOAD", ["btn_slow_download.png"]), \
             patch.object(instal, "MAX_TENTATIVAS_SEM_BOTAO", 3), \
             patch("instal.pyautogui.locateOnScreen", side_effect=locate), \
             patch("instal.clicar_centro", side_effect=lambda _: cliques.append(1)), \
             patch("instal.pyautogui.scroll"), \
             patch("instal.time.sleep"):
            instal.etapa4_loop_slow_download()

        assert len(cliques) == 1

    def test_rola_tela_quando_botao_nao_encontrado(self, tmp_path):
        (tmp_path / "btn_slow_download.png").write_bytes(b"fake")
        with patch.object(instal, "IMGS_DIR", str(tmp_path)), \
             patch.object(instal, "IMAGENS_DOWNLOAD", ["btn_slow_download.png"]), \
             patch.object(instal, "MAX_TENTATIVAS_SEM_BOTAO", 2), \
             patch("instal.pyautogui.locateOnScreen", return_value=None), \
             patch("instal.pyautogui.scroll") as mock_scroll, \
             patch("instal.time.sleep"):
            instal.etapa4_loop_slow_download()
        assert mock_scroll.call_count == 2

    def test_excecao_generica_nao_interrompe_loop(self, tmp_path):
        (tmp_path / "btn_slow_download.png").write_bytes(b"fake")
        chamadas = [0]

        def locate(path, confidence):
            chamadas[0] += 1
            if chamadas[0] == 1:
                raise RuntimeError("erro inesperado de GPU")
            return None

        with patch.object(instal, "IMGS_DIR", str(tmp_path)), \
             patch.object(instal, "IMAGENS_DOWNLOAD", ["btn_slow_download.png"]), \
             patch.object(instal, "MAX_TENTATIVAS_SEM_BOTAO", 2), \
             patch("instal.pyautogui.locateOnScreen", side_effect=locate), \
             patch("instal.pyautogui.scroll"), \
             patch("instal.time.sleep"):
            instal.etapa4_loop_slow_download()  # não deve propagar


# ─────────────────────────────────────────────────────────────────────────────
#  parse_args()
# ─────────────────────────────────────────────────────────────────────────────

class TestParseArgs:
    def test_valores_padrao(self):
        args = instal.parse_args([])
        assert args.confidence == instal.CONFIANCA
        assert args.timeout == instal.TIMEOUT_BOTAO
        assert args.all_steps is False
        assert args.imgs_dir is None

    def test_modlist_personalizado(self):
        args = instal.parse_args(["--modlist", r"E:\MeuMod.wabbajack"])
        assert args.modlist == r"E:\MeuMod.wabbajack"

    def test_atalho_m_para_modlist(self):
        args = instal.parse_args(["-m", r"C:\Lista.wabbajack"])
        assert args.modlist == r"C:\Lista.wabbajack"

    def test_confidence_personalizada(self):
        args = instal.parse_args(["--confidence", "0.70"])
        assert abs(args.confidence - 0.70) < 1e-9

    def test_all_steps_ativa_flag(self):
        args = instal.parse_args(["--all-steps"])
        assert args.all_steps is True

    def test_max_attempts_personalizado(self):
        args = instal.parse_args(["--max-attempts", "50"])
        assert args.max_attempts == 50

    def test_imgs_dir_personalizado(self):
        args = instal.parse_args(["--imgs-dir", r"C:\meus_prints"])
        assert args.imgs_dir == r"C:\meus_prints"


# ─────────────────────────────────────────────────────────────────────────────
#  main()
# ─────────────────────────────────────────────────────────────────────────────

class TestMain:
    def test_chama_verificar_imagens_antes_de_comecar(self):
        with patch("instal.verificar_imagens") as mock_verif, \
             patch("instal.etapa4_loop_slow_download"), \
             patch("instal.time.sleep"):
            instal.main([])
        mock_verif.assert_called_once()

    def test_chama_etapa4_por_padrao(self):
        with patch("instal.verificar_imagens"), \
             patch("instal.etapa4_loop_slow_download") as mock_etapa4, \
             patch("instal.time.sleep"):
            instal.main([])
        mock_etapa4.assert_called_once()

    def test_all_steps_chama_etapas_1_2_3_e_4(self):
        with patch("instal.verificar_imagens"), \
             patch("instal.etapa1_install_from_disk") as m1, \
             patch("instal.etapa2_selecionar_modlist") as m2, \
             patch("instal.etapa3_iniciar_instalacao") as m3, \
             patch("instal.etapa4_loop_slow_download") as m4, \
             patch("instal.time.sleep"):
            instal.main(["--all-steps"])
        m1.assert_called_once()
        m2.assert_called_once()
        m3.assert_called_once()
        m4.assert_called_once()

    def test_trata_failsafe_sem_propagar(self):
        with patch("instal.verificar_imagens"), \
             patch("instal.etapa4_loop_slow_download",
                   side_effect=instal.pyautogui.FailSafeException), \
             patch("instal.time.sleep"):
            instal.main([])  # não deve propagar

    def test_trata_keyboard_interrupt_sem_propagar(self):
        with patch("instal.verificar_imagens"), \
             patch("instal.etapa4_loop_slow_download", side_effect=KeyboardInterrupt), \
             patch("instal.time.sleep"):
            instal.main([])

    def test_trata_excecao_generica_sem_propagar(self):
        with patch("instal.verificar_imagens"), \
             patch("instal.etapa4_loop_slow_download",
                   side_effect=RuntimeError("falha inesperada")), \
             patch("instal.time.sleep"):
            instal.main([])

    def test_args_personalizado_atualiza_globals(self):
        with patch("instal.verificar_imagens"), \
             patch("instal.etapa4_loop_slow_download"), \
             patch("instal.time.sleep"):
            instal.main(["--confidence", "0.60", "--max-attempts", "10"])
        assert abs(instal.CONFIANCA - 0.60) < 1e-9
        assert instal.MAX_TENTATIVAS_SEM_BOTAO == 10
