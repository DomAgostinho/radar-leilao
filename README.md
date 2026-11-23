# Radar de Leilão

Busca carros de leilão no Sul e Sudeste (PR, SC, RS, SP, MG, RJ, ES) e mostra tudo num site só.

- **Robôs** (`coletor/`): um arquivo por leiloeiro. Rodam sozinhos no GitHub Actions a cada 3 horas e salvam os carros em `docs/dados/lotes.json`.
- **Site** (`docs/index.html`): publicado pelo GitHub Pages. Abas Semana (financeira + pequena monta), Buscar, Favoritos e Leiloeiros.

## Leiloeiros
| Fonte | Como lê |
|---|---|
| Favareto Leilões (Curitiba) | páginas de edital |
| Claudio Kuss Leilões (Curitiba) | `json_edital.php` |
| Copart | busca pública, só pátios do Sul/Sudeste |
| Superbid | API pública; cobre Kron/Kronberg, Sold, Monzon, Marangoni, Eckert e outros |
| Palácio dos Leilões (MG/SP) | lista de lotes do site |

Para rodar na mão: aba **Actions → Coletar lotes → Run workflow**.

Os robôs fazem poucas visitas, com pausa entre pedidos. Valores e condições valem o que está no edital de cada leilão.
