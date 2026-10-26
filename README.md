# Dobramundo

![Dobramundo](docs/logo.jpg)

**Dobre o papel, voe e transforme o mundo.** Um jogo em papel e aquarela para crianças de 6 a 10 anos: pilote com o corpo um avião reciclado, cuide dos biomas brasileiros e ajude sua vila a florescer.

[![Testes](https://github.com/lapsin-maker/dobramundo/actions/workflows/testes.yml/badge.svg)](https://github.com/lapsin-maker/dobramundo/actions/workflows/testes.yml)
[![Versão](https://img.shields.io/github/v/release/lapsin-maker/dobramundo)](https://github.com/lapsin-maker/dobramundo/releases/latest)
[![Licença CC BY 4.0](https://img.shields.io/badge/licença-CC_BY_4.0-blue)](LICENSE)

## Baixar e jogar

1. Na [página de downloads](https://github.com/lapsin-maker/dobramundo/releases/latest), escolha **Windows** ou **Linux**.
2. Extraia toda a pasta. Mantenha o jogo junto da pasta `_internal`, que contém os arquivos necessários.
3. No Windows, abra **Jogar-Dobramundo.bat**. No Linux, instale `libegl1` e `libgles2` pelo gerenciador de pacotes e abra `Dobramundo`. Não precisa instalar Python.

Para o console T-TEA, baixe o arquivo **.ttea** e instale pelo console. Os arquivos com verificações de integridade são opcionais para quem só quer jogar.

Já jogou a versão 1.5 pelo lançador? O atalho **Continuar-perfil-1.5.bat** abre aquela pasta de progresso. Os outros pilotos ficam em **Trocar piloto**, com até oito perfis locais, sem pedir nomes reais.

## Uma aventura que continua

Crie seu piloto, acompanhe a história do jornal e entre na vila. A história pode ser pulada e vista novamente. A aparência começa neutra, pronta para escolher pele, cabelos, olhos, roupa, óculos, aparelho auditivo, cadeira de rodas ou andador.

Na vila, você pode **voar**, entrar no **hangar**, mudar o **piloto** e **cuidar da comunidade**. Ela começa colorida, industrial e poluída; as obras trazem água limpa, natureza, energia e alimentos. Manaus e Petrolina estão disponíveis desde o começo, para visitar a Amazônia e a Caatinga na ordem que preferir.

A transformação avança durante o voo ativo; coletar resíduos acelera a recuperação e traz recursos para construir. O avanço fica guardado entre os voos. Uma cidade recuperada continua solarpunk — um lugar em que pessoas, construções e natureza convivem. Voar de novo começa outra viagem, sem apagar essa transformação nem duplicar recompensas.

Nos primeiros voos, o apoio oferece mais vidas e proteção. Você pode mudar essa escolha. Também há **Explorar**, sem eliminação por batidas, e voos com duração combinada.

## Jogar com o corpo

- Escolha **pés, tronco em pé, tronco sentado, mão direita, mão esquerda ou cabeça**.
- Calibre uma posição confortável e os alcances do movimento.
- Nos menus, mire um botão, espere a confirmação e retire o cursor. A espera pode ser ajustada.
- O adulto pode ajudar com mouse e teclado; **Esc/P** pausa o voo.
- Jogue no monitor ou projete na parede, na mesa ou no chão. Para pés na projeção, calibre os quatro cantos.

As opções separam controles, imagem, conforto e som. Alto contraste, tamanho dos elementos, movimento reduzido e volumes podem ser ajustados desde o início. Não é preciso comprar melhorias para acessar esses recursos.

## Câmera e privacidade

A câmera funciona no próprio computador. O jogo não grava vídeo nem envia imagens para serviços de IA. As ilustrações já vêm incluídas no download.

A experiência deve ser acompanhada e ajustada à pessoa. Testes no computador não substituem observar conforto, alcance e leitura da projeção a 2–3 metros. [Orientações de uso](docs/GUIA_DO_JOGO.md) · [Roteiro de verificação presencial](docs/VALIDACAO_PRESENCIAL.md).

## Para desenvolver

O jogo usa Python e pygame; a webcam usa MediaPipe e OpenCV. O console fornece seu próprio rastreamento. [Instalação e contribuição](CONTRIBUTING.md) · [Arquitetura](docs/arquitetura.md) · [Ferramentas e testes](tools/README.md).

```powershell
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt
.venv/Scripts/python -m dobramundo
```

As instruções de webcam, geração de pacotes e TSDK estão na documentação técnica. Os testes automáticos do jogo não abrem a webcam; as ferramentas que a utilizam são explícitas.

[Novidades e verificação da versão 1.7](docs/ENTREGA_1_7.md) · [Documentação](docs/README.md) · [Histórico de versões](CHANGELOG.md) · [GDD](docs/GDD_Dobramundo_v10.pdf).

## Equipe e licença

**Liga de Psiquiatria e Neurociências — CENSUPEG**, 3ª ExerGame JAM LARVA/UDESC, 2026. João Pedro Turnes (capitão), Isabella Cordeiro Sonza, Gerciane Larice da Silva Barros e Luiz Felipe Santana Tomio.

Programação com apoio de IA generativa e arte aquarelada gerada por IA. [Créditos das imagens](assets/watercolor/CREDITOS.txt). Fontes, modelo de pose e bibliotecas mantêm suas próprias licenças. Código e conteúdo autoral do jogo: **[CC BY 4.0](LICENSE)**.
