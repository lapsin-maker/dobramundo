# Entrega da sprint 2 — aquarela em movimento

A [prévia de 25/10/2026](https://github.com/lapsin-maker/dobramundo/releases/tag/sprint2-aquarela-2026-10-25) reúne os arquivos testáveis da sprint. Código, arte e documentação são integrados pelo [PR #9](https://github.com/lapsin-maker/dobramundo/pull/9). A tag `sprint2-aquarela-2026-10-25` identifica esta entrega; a versão interna do aplicativo continua 1.4.0.

## Arquivos e instalação

| Arquivo da release | Uso |
|---|---|
| `Dobramundo-Aquarela-Sprint2-Windows.zip` | Extraia a pasta inteira e execute `Jogar-Sprint2.bat`. Mantenha a subpasta `Dobramundo` junto do lançador. |
| `Dobramundo-Aquarela-Sprint2-Galeria.zip` | Extraia a pasta inteira e abra `galeria.html`. Os botões reproduzem gravações reais do Pygame, com 12 segundos por cidade em 20 quadros/s. |
| `SHA256SUMS.txt` | Hashes para conferir a integridade dos dois pacotes. |
| Source code (zip/tar.gz) | Código-fonte, documentação e assets versionados da tag, fornecidos pelo GitHub. |

O lançador Windows usa `%LOCALAPPDATA%\Dobramundo-Aquarela-Sprint2` para manter um perfil separado. Executar diretamente `Dobramundo.exe` usa o perfil padrão do aplicativo. Não execute de dentro do ZIP: extraia todos os arquivos primeiro.

No teclado, use as setas; `P` pausa o voo. Em Opções estão os controles corporais, a superfície de projeção e o movimento reduzido. A primeira jornada começa pelo boneco neutro, segue para a vila e oferece treino opcional antes do primeiro voo. A vila permite voltar ao piloto, personalizar o avião no hangar e decolar pelo mapa.

Os arquivos estão em um repositório privado; o download no GitHub exige acesso ao projeto. Nenhuma geração de imagem ou chamada de rede é necessária durante a partida.

## Rastreabilidade e validação

O executável foi construído com o código de `b08bcac82a2ffc883f515debcb25afcf8b340861`, Python 3.12.10, Pygame 2.6.1 e PyInstaller 6.22.3. A revisão seguinte acrescenta documentação de publicação, sem alterar o código executável ou a arte.

SHA-256 do ZIP Windows:

```text
17b49b4cd4a325d0871a96e8386814baafcfbac423d0c4bef68ee1d7f5782c20
```

Para conferir um download no PowerShell:

```powershell
Get-FileHash -Algorithm SHA256 .\Dobramundo-Aquarela-Sprint2-Windows.zip
```

Passaram 365 testes locais, lint, self-tests de 1.200 quadros por cidade na fonte e no executável e o CI em Python 3.8/3.12. Os 28 PNGs aquarelados do bundle conferem com a fonte por SHA-256. Resultados e condições das medições: [direção e validação](DIRECAO_AQUARELA.md) e [dados estruturados](validacao-sprint2.json).

O self-test carrega o detector de pose, mas não abre uma câmera física. Projeção a 2–3 m, rastreamento contínuo e experiência com crianças ainda precisam de avaliação presencial. A release não inclui um novo cartucho `.ttea`; a auditoria automatizada não equivale à execução no console físico.

Licença e atribuição: [CC BY 4.0 do projeto](../LICENSE), com [créditos da arte aquarelada](../assets/watercolor/CREDITOS.txt) e licenças próprias das dependências descritas no [README](../README.md#licenças).
