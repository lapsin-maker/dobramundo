# Contribuir com Dobramundo

Use uma branch própria e descreva o problema e o comportamento final. Preserve o GDD, acessibilidade, perfis existentes e fallback procedural. Combine a propriedade dos arquivos quando houver trabalho paralelo.

## Ambiente e validação

O pacote declara Python >=3.8; a matriz de CI da entrega cobre 3.8/3.12 quando executada, e o build desktop usa 3.12. Instale `requirements.txt` para teclado/mouse, `pytest`, `ruff` e `Pillow` para desenvolver/testar. Para webcam, `pip install -e ".[webcam]"`. Use um ambiente separado para o TSDK, que exige Python 3.14.

```text
python -m pytest -q
ruff check .
ruff format --check .
python -m mypy
python -m dobramundo --self-test 1200 --exigir-camera
```

O pytest isola dados em diretório temporário. Se o temporário padrão estiver inacessível, passe `--basetemp` apontando para uma **nova pasta de teste descartável**. Nunca use pasta de dados do jogador: pytest pode limpar o basetemp. Perfis e recuperação devem ser testados com diretórios temporários injetados; não leia nem altere perfis reais durante os testes.

`--exigir-camera` verifica a carga do detector; não captura vídeo. Para benchmark, use as ferramentas de `tools/` e registre condições, versão e equipamento. Não compare tempos enquanto outro build/teste pesado usa a mesma CPU.

O lint ativo exclui `tools/legado`. Não formate todo o repositório dentro de uma correção funcional; normalize os arquivos alterados e mantenha futuras mudanças globais em commit próprio. A CI deve usar comandos compatíveis com sua matriz: constraints do build 3.12 não devem ser impostas indiscriminadamente a 3.8.

## Convenções e revisão

- Código novo em inglês; textos da interface e campos persistidos em português. Não renomeie campos de save sem migração testada.
- Commits novos: `tipo: descrição em português` (`fix`, `feat`, `perf`, `docs`, `test`, `build`).
- Testes devem exercitar contratos e comportamento, incluindo falhas. Para imagens, verificar também o resultado visual.
- Fontes de tempo, aleatoriedade e câmera devem permitir testes determinísticos.
- Mudanças em recompensas precisam de idempotência; em dificuldade, de auditoria de rotas; em câmera, de testes de atraso e encerramento.
- Não gravar quadros, landmarks ou dados pessoais em evidências de desempenho. Métricas técnicas locais bastam para esse diagnóstico.

## Arte e publicação

Mantenha originais e procedência. O runtime usa PNGs locais, sem geração por IA durante o jogo. Não converter formatos sem testar o suporte no console. Pintado → papel → lógico é uma cadeia de fallback, não código duplicado para apagar automaticamente.

Confira `__version__`, self-test do executável, check/build do TSDK e hashes dos pacotes antes da release. Use `tools/runtime_assets.py` para selecionar os arquivos do jogo e `tools/package_release.py` para fechar a distribuição a partir de CI aprovada; o script verifica commits, árvores, detector e integridade. Uma mudança de número no código não confirma publicação. Preserve releases históricas e branches compartilhadas; remova branches concluídas somente após conferir seus commits e a autorização.

O mypy verifica inicialmente modelo/migração, contratos do desenho e telemetria. Amplie esse limite gradualmente; não use `Any` para esconder contratos incorretos. Referências visuais de menus ficam em `docs/visual-reference/`; atualizá-las exige abrir as imagens novas e justificar a mudança, além de rodar `tools/visual_regression.py`.
