# Roteiro sugerido para o vídeo — 3 a 4 minutos

## 0:00–0:30 — Contexto

“Este é o projeto final da disciplina e consolida os cinco checkpoints em uma arquitetura serverless orientada a eventos com IA. A aplicação recebe e processa pedidos, garante idempotência, trata falhas e classifica o risco operacional com Amazon Bedrock.”

Na tela: título e diagrama do `README.md`.

## 0:30–1:20 — Fluxo e serviços

“A entrada ocorre em uma Lambda Function URL protegida por IAM. Ela inicia o Step Functions, responsável por coordenar as etapas que precisam ocorrer em sequência: validação, análise com IA, processamento e finalização. O DynamoDB impede que o mesmo pedido seja processado duas vezes. No final, o SNS publica o evento para consumidores independentes. Caso uma falha permaneça depois das tentativas automáticas, os dados seguem para uma SQS DLQ.”

Na tela: diagrama e `workflow/order-processing-workflow.json`.

## 1:20–2:05 — Decisões técnicas

“Usei orquestração no fluxo principal porque as tarefas possuem dependência e ordem definida. Usei coreografia com SNS na saída porque os futuros consumidores não devem ficar acoplados ao processamento. Escolhi Bedrock porque toda a solução já está na AWS e a autorização pode ser feita por IAM, sem chave de API. A IA apenas classifica e justifica o risco; ela não toma uma decisão automática de aprovação.”

Na tela: `analyze_order_ai/lambda_function.py` e seção de decisões do README.

## 2:05–2:40 — Segurança e infraestrutura

“Toda a infraestrutura está no template SAM. Removi ARNs fixos e usei referências do CloudFormation, permitindo implantar em outra conta. As permissões seguem o menor privilégio, os dados usam criptografia gerenciada e o pipeline se autentica por OIDC. Assim, não existem access keys, arquivos `.env` ou credenciais no GitHub.”

Na tela: `template.yaml` e `.github/workflows/deploy.yml`.

## 2:40–3:20 — Qualidade e observabilidade

“O pipeline executa testes, valida o template, faz o build e somente depois realiza o deploy. O CloudWatch recebe logs estruturados e métricas de pedidos iniciados, analisados, processados, duplicados e com falha. Também há dashboard, alarme da DLQ e rastreamento com X-Ray.”

Na tela: testes aprovados, GitHub Actions e dashboard/Step Functions na AWS.

## 3:20–3:40 — Encerramento

“Com isso, o projeto reúne os checkpoints em uma solução ponta a ponta, reproduzível e desacoplada, usando orquestração onde existe dependência e eventos onde é importante permitir evolução independente.”

## Resumo para colar no Canvas

O projeto consolida os checkpoints em uma arquitetura serverless orientada a eventos na AWS. Uma Function URL autenticada inicia um workflow no Step Functions, que valida o pedido, realiza classificação de risco com Amazon Bedrock, processa com idempotência no DynamoDB e publica o resultado no SNS. Falhas persistentes são preservadas em uma SQS DLQ. A solução possui logs e métricas no CloudWatch, tracing com X-Ray, infraestrutura como código com AWS SAM e pipeline CI/CD no GitHub Actions autenticado por OIDC, sem chaves permanentes.
