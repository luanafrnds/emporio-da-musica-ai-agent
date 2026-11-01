# 🎸 Empório da Música — Assistente de Atendimento

Protótipo de agente de atendimento por mensagens de texto para a **Empório da Música** (loja fictícia de instrumentos musicais em Campo Grande/MS), feito para o desafio técnico de AI Engineer da Artefact.

O assistente responde dúvidas sobre **catálogo, preços e estoque** (a partir dos CSVs) e sobre **políticas da loja** (a partir do manual em PDF), e recusa com educação o que foge do escopo da loja.

## Como rodar

Requisitos: Python 3.10+.

```bash
git clone https://github.com/luanafrnds/emporio-da-musica-ai-agent.git
cd emporio-da-musica-ai-agent

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

streamlit run app.py
```

O app abre em `http://localhost:8501`. **Não é necessária nenhuma chave de API**: o protótipo não chama nenhum LLM.

### Dados

Os arquivos ficam na pasta `data/` (o app também procura na raiz e em `dados/`):

| Arquivo | Uso |
|---|---|
| `desafio_tecnico_ai_eng - products.csv` | catálogo, preço, estoque e status |
| `desafio_tecnico_ai_eng - categories.csv` | nomes das categorias |
| `desafio_tecnico_ai_eng - promotions.csv` | promoções (apenas as ativas são oferecidas) |
| `desafio_tecnico_ai_eng - orders / order_items / customers.csv` | carregados e exibidos na aba *Dados*; ainda não usados nas respostas |
| `politicas_da_loja.pdf` | manual de políticas (recuperação de trechos) |

## Como funciona

```
Pergunta ─▶ normalização (minúsculas, sem acento)
          ─▶ roteador por regras, em ordem de prioridade:
               1. escopo (acessórios, conserto/usados)     → recusa educada
               2. casos de devolução/defeito/troca com prazo → aplica as regras do manual
               3. promoções                                 → lê promotions.csv
               4. políticas (pagamento, entrega, garantia…) → recuperação no PDF
               5. preço / ranking / faixa / ordinal         → consulta pandas no catálogo
               6. contato, endereço, horários               → respostas fixas conferidas no manual
               7. quantidade / estoque / marca / categoria  → consulta ao catálogo
               8. fallback                                  → admite que não sabe
```

- **Catálogo (dados estruturados):** consultas determinísticas em `pandas`. Preços, estoque e status vêm sempre do CSV, nunca de texto gerado, para não inventar valores.
- **Políticas (RAG léxico):** o PDF é extraído com PyMuPDF e dividido por seção numerada (`4.1`, `5.2`…). Cada seção recebe uma pontuação por tópico (título pesa mais que o corpo) e, dentro da seção escolhida, só os parágrafos relevantes são devolvidos.
- **Regras de negócio aplicadas ao caso:** em perguntas como *"recebi há 10 dias e me arrependi, posso devolver?"*, o prazo informado é comparado com as regras do manual (7 dias para arrependimento online, 30 dias para troca por defeito, 7 dias para troca por preferência) e a resposta diz se o cliente está dentro ou fora do prazo.
- **Contexto de conversa:** a categoria e a ordenação da última consulta ficam em `st.session_state`, permitindo *"Quais os 5 violões mais baratos?" → "E o segundo mais caro?"*.

## Decisões técnicas e justificativas

| Decisão | Escolha | Por quê |
|---|---|---|
| Abordagem | Roteamento por regras (regex e palavras-chave) + consultas determinísticas em Pandas + recuperação léxica no PDF | Respostas sobre preço, estoque e prazo precisam ser exatas e auditáveis; o manual (seção 7.1) diz que o atendente nunca deve informar preços, estoque ou prazos sem consultar o sistema. |
| Modelo / provedor | **Nenhum LLM utilizado** (nem para entender a pergunta, nem para redigir a resposta) | Escolha deliberada para o protótipo: sem custo de inferência e sem chave de API, mesma pergunta gera a mesma resposta (reprodutível), testes locais imediatos e nenhum texto de valor ou regra é gerado por um modelo, apenas lido do CSV ou do manual. Em contrapartida, o entendimento de linguagem é limitado (ver *Limitações*). |
| Interface | Streamlit | Entrega rápida de uma UI de chat com abas de catálogo e diagnóstico. |
| Persistência | Histórico e contexto na sessão (`st.session_state`) | Suficiente para o protótipo; não há dados pessoais armazenados. |
| Tratamento de dados | Leitura tolerante de CSV (encoding, separador `;`/`,`), preços em formato BR, reconhecimento de nomes de colunas | Os CSVs do desafio usam `;`; o código aceita variações. |

### Suposições documentadas

- Só produtos com `status = active` **e** estoque > 0 são oferecidos. Produtos `discontinued` e `coming_soon` são informados como indisponíveis.
- A categoria oficial vem de `categories.csv`; a marca é buscada **só no nome** do produto, porque as descrições do CSV às vezes citam outra marca (ex.: *Music Man Bass 1X* descrito como Jazz Bass da Fender).
- Promoções com `is_active = 0` não são oferecidas ("nunca prometer um desconto que não está mais vigente", manual seção 7.3).
- O manual **não** trata de retirada na loja: o assistente diz que não encontrou a informação e encaminha para o WhatsApp, em vez de responder com regras de frete.
- O manual traz dois telefones (capa: (67) 3341-4444; seção 7: (67) 3321-4500). O assistente usa o da capa/dados da empresa.
- Os prazos de devolução contam a partir do **recebimento**; quando o cliente diz "comprei há X dias", assume-se a mesma contagem.

## Limitações conhecidas

- **Ausência de LLM:** o assistente opera apenas com regras e palavras-chave predefinidas. Perguntas formuladas de maneira atípica caem no *fallback*, e frases que misturam vários tópicos podem ser respondidas só em parte. Por ser baseado em regras, o roteamento também pode errar: um erro de classificação da pergunta gera uma resposta correta para o assunto errado (já corrigi vários casos assim durante os testes). Não ter LLM elimina respostas inventadas pelo modelo, mas não elimina erros de lógica.
- **Respostas de política citam o manual:** o assistente devolve o trecho relevante, mas não reescreve em linguagem natural (isso exigiria um LLM).
- **Status de pedido não implementado:** `orders.csv` está carregado, mas ainda não há consulta por número de pedido ou rastreamento.
- **Prazos de devolução no código:** os prazos (7 e 30 dias) estão escritos nas regras; se o manual mudar, é preciso atualizar o código.
- **Datas:** entende "há 10 dias", "ontem" e "uma semana", mas não datas como "dia 20/10".
- **Persona:** o tom é acolhedor e informal, mas fixo (sem variação gerada).

## O que eu faria com mais tempo

1. Usar as funções de catálogo e política como **ferramentas (function calling)** de um LLM, mantendo os dados determinísticos e deixando o modelo responsável por entender a pergunta e redigir a resposta no tom da loja.
2. Trocar a recuperação léxica por **embeddings** (com fallback para "não encontrei") e avaliar com um conjunto fixo de perguntas.
3. Implementar **consulta de pedido** (status, rastreamento, previsão de entrega) com verificação do cliente.
4. Criar uma **suíte de testes automatizados** com as perguntas de exemplo e as respostas esperadas.
5. Persistir conversas e adicionar logs de perguntas não respondidas para melhorar a cobertura.

## Uso de assistentes de código

Usei o **Claude** (Anthropic) como assistente de código e revisão. O fluxo foi:

1. Escrevi a primeira versão do app e pedi uma revisão crítica do código.
2. Apliquei as melhorias sugeridas (categorias, busca por marca, recuperação de políticas, quantidade de unidades e contexto de conversa) com o apoio do Claude.
3. Testei o assistente com os CSVs e o PDF reais, com perguntas de exemplo, e usei os resultados (ex.: retirada na loja, produto danificado, prazo de devolução) para ajustar as regras.
4. Revisei cada mudança antes de aceitar e mantive o roteamento o mais simples possível.

> Ajuste esta seção para refletir exatamente como você usou as ferramentas (e outras, se houver).

## Exemplos de interação

Conversas de exemplo (texto) na pasta [`exemplos/`](exemplos/).

### Prints da interface funcionando

**Tela inicial, com as fontes de dados carregadas**
<img width="2914" height="1652" alt="image" src="https://github.com/user-attachments/assets/0d743c6f-16b8-4b4e-82ef-4304cf115705" />


**Consulta ao catálogo e resposta fora do escopo (acessórios)**
<img width="2916" height="1666" alt="image" src="https://github.com/user-attachments/assets/4508b329-c6c8-4e4e-8c4c-4274731281bb" />


**Política de garantia recuperada do manual em PDF**
<img width="2940" height="1650" alt="image" src="https://github.com/user-attachments/assets/e3653743-4d29-4be3-bf56-22177e87b88f" />

## Estrutura

```
.
├── app.py               # interface Streamlit + motor de respostas
├── requirements.txt
├── data/                # CSVs e PDF de políticas
├── exemplos/            # conversas de exemplo
└── README.md
```
