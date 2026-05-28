# Wabbajack Auto Clicker (Free Mode)

Este é um script de automação desenvolvido em Python para ajudar usuários do [Wabbajack](https://www.wabbajack.org/) a baixarem modlists gigantes no "Modo Gratuito" do Nexus Mods, sem a necessidade de uma conta Nexus Premium.

Como usuários gratuitos não têm acesso à API do Wabbajack para iniciar o download de todos os arquivos automaticamente, a tela exige que o usuário clique em "Slow Download" no site do Nexus Mods para cada um dos mods baixados. Este script resolve este problema verificando continuamente a tela usando Visão Computacional (`pyautogui` e `opencv`) e clicando nos botões de download assim que eles aparecem.

---

## 🔒 Segurança e Aviso Legal

A segurança e estabilidade foram as principais prioridades na construção desse script:

- **Failsafe Ativado**: O script possui uma trava de segurança ativada por padrão (`pyautogui.FAILSAFE = True`). **Para abortar o script instantaneamente a qualquer momento, basta mover o cursor do mouse rapidamente para o CANTO SUPERIOR ESQUERDO da sua tela.**
- **Nenhuma Credencial é Armazenada ou Lida**: Este código apenas verifica o que está visível no seu monitor no momento da execução para localizar o botão e clicar. Ele não exige senhas, não acessa seus arquivos pessoais e não se comunica via internet com nenhum servidor.
- **Transparência Total**: Todo o código-fonte está no arquivo `instal.py`, que você pode e deve revisar antes de executar.

---

## ⚙️ Pré-requisitos e Dependências

Para rodar o script você precisa do **Python** instalado na sua máquina (versão 3.8+ recomendada).

Após clonar ou baixar este repositório, instale todas as dependências rodando:

```bash
pip install -r requirements.txt
```

---

## 📸 Configuração das Imagens (Passo Obrigatório)

Como as resoluções de tela e o nível de zoom do navegador variam de computador para computador, o script precisa saber EXATAMENTE como é o botão no seu monitor.

Você deve tirar prints dos botões do Nexus e colocá-los dentro da pasta `imgs/` (que está na mesma pasta do script).

### Como fazer:
1. Comece a baixar um modlist no Wabbajack para que ele abra uma página do Nexus Mods e peça para você clicar em "Slow Download".
2. Use a ferramenta de captura do Windows apertando **`Win + Shift + S`**.
3. Recorte **apenas** o conteúdo do botão. Não deixe muita margem ou fundo aparecendo (isso facilita a vida do robô).
4. Salve essa captura com os seguintes nomes dentro da pasta `imgs/`:

- `btn_slow_download.png` (Obrigatório) — O botão clássico de "Slow Download" que aparece para os mods menores.
- `btn_standard_download.png` (Opcional, mas Recomendado) — Para mods muito grandes (+500MB), o Nexus abre um pop-up e você tem que clicar em "Standard download".

> **DICA**: Mantenha o seu navegador com o zoom padrão (100%) para que a imagem recortada e a imagem na tela combinem perfeitamente em tamanhos.

---

## 🚀 Como Executar

1. Abra o Wabbajack, inicie a instalação do seu Modlist até ele começar a abrir as abas do Nexus no navegador aguardando o seu clique.
2. No seu terminal, dentro da pasta do script, rode o comando:
   ```bash
   python instal.py
   ```
3. Você terá **5 segundos** de preparação. Mova a aba do navegador para o foco (ou clique nela).
4. Relaxe! O script agora vai rodar indefinidamente. Ele procurará o botão de "Standard Download" ou "Slow Download" na tela a cada 2 segundos.
5. Se não encontrar o botão imediatamente, ele dará um leve "scroll" (rolagem) para baixo na página após um tempo, caso a janela do navegador abra o botão escondido no rodapé da página.
6. A automação tem um limite flexível. Ela pausa sua busca e se desliga se não encontrar nada após vários minutos (o que pode significar que o Wabbajack terminou sua lista!).

---

## 📄 Licença

Este projeto é distribuído sob a licença **MIT**, o que significa que é livre, open-source e pode ser modificado como preferir. Consulte o arquivo `LICENSE` para mais detalhes.
