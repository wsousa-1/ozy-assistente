# =============================================================================
# Importações de Bibliotecas
# Trazem funcionalidades prontas que vamos usar no nosso código
# =============================================================================
import streamlit as st # Importa o Streamlit para criar a interface web
import google.generativeai as genai # Importa a biblioteca do Google para usar o modelo Gemini
from PIL import Image # Importa a biblioteca Pillow (PIL) para trabalhar com imagens
import os # Importa o módulo os para interagir com o sistema operacional (como pegar variáveis de ambiente)
# Importações para os Agentes (Assumindo que vêm de uma biblioteca como google-ai-generative-agents)
# Se não tiver essa biblioteca instalada, você precisará instalá-la: pip install google-ai-generative-agents
from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.tools import google_search # Assumindo que 'google_search' é uma ferramenta válida
from google.genai import types # Para criar conteúdos (Content e Part) - genai já costuma ser suficiente
from datetime import date # Importa date

# =============================================================================
# Configuração Inicial da Página Streamlit
# Define o visual básico da sua aplicação web
# =============================================================================
# Configurações da página: layout mais largo, título que aparece na aba do navegador
st.set_page_config(layout="wide", page_title="Ozy o Assistente")

# =============================================================================
# Configuração da API do Google Gemini
# Prepara o acesso ao modelo de inteligência artificial
# =============================================================================

# Use st.secrets ou variáveis de ambiente do Streamlit Cloud
# Para rodar localmente, pode configurar a variável de ambiente GOOGLE_API_KEY
# No Streamlit Cloud, adicione [secrets] e GOOGLE_API_KEY="sua_chave_aqui" no .streamlit/secrets.toml
# REMOVA OU COMENTE A LINHA ABAIXO - ELA ESTÁ SOBRESCREVENDO SUA CHAVE
os.environ['GOOGLE_API_KEY'] = st.secrets["GOOGLE_API_KEY"]
api_key = os.environ.get("GOOGLE_API_KEY")

# Verifica se a chave da API foi encontrada
if not api_key:
    # Se não encontrou a chave, mostra uma mensagem de erro no Streamlit
    # Este st.error só deve rodar se a chave REALMENTE não for encontrada via os.environ.get
    st.error("Chave da API GOOGLE_API_KEY não configurada nas variáveis de ambiente! Verifique .streamlit/secrets.toml ou suas variáveis de ambiente locais.")
    # Para a execução do script, pois não dá para continuar sem a chave
    st.stop()

# Configura a biblioteca do Google Gemini com a chave API encontrada
genai.configure(api_key=api_key)

# =============================================================================
# Configurando a lógica dos Agentes
# Esta seção agora é condicional à ativação pelo Switch
# =============================================================================

# Função auxiliar que envia uma mensagem para um agente via Runner e retorna a resposta final
# Esta função pode ficar fora da condicional, pois ela é uma utilidade para QUALQUER agente
def call_agent(agent: Agent, message_text: str) -> str:
    """
    Envia uma mensagem para um agente ADK e retorna a resposta final.
    Requer a biblioteca google-ai-generative-agents instalada.
    """
    try:
        # Cria um serviço de sessão em memória
        session_service = InMemorySessionService()
        # Cria uma nova sessão (você pode personalizar os IDs conforme necessário)
        # Usa uma combinação do nome do agente e user_id para garantir sessões únicas por agente/usuário
        session_id = f"{agent.name}_user1_session1"
        session = session_service.create_session(app_name=agent.name, user_id="user1", session_id=session_id)
       
        # Cria um Runner para o agente
        runner = Runner(agent=agent, app_name=agent.name, session_service=session_service)
        # Cria o conteúdo da mensagem de entrada
        content = types.Content(role="user", parts=[types.Part(text=message_text)])

        final_response = ""
        # Itera assincronamente pelos eventos retornados durante a execução do agente
        # Nota: runner.run é síncrono neste exemplo, apesar da descrição
        for event in runner.run(user_id="user1", session_id=session_id, new_message=content):
            if event.is_final_response():
                for part in event.content.parts:
                    if part.text is not None:
                        final_response += part.text
               
                # final_response += "\n" # Remover quebra de linha extra se não for necessária

        return final_response.strip() # Remove espaços em branco no início/fim

    except ImportError:
        st.error("Erro: A biblioteca 'google-ai-generative-agents' não está instalada. Por favor, instale-a para usar os agentes.")
        return "Erro na configuração dos agentes."
    except Exception as e:
        st.error(f"Erro ao executar o agente: {e}")
        return "Desculpe, ocorreu um erro ao processar a solicitação do agente."


# =============================================================================
# INICIO DA SEÇÃO CONTROLADA PELO SWITCH
# A definição dos agentes e suas funções só ocorre se o switch estiver ativo
# =============================================================================

# Inicializa o estado do switch na sessão
if "agentes_ativos" not in st.session_state:
    st.session_state.agentes_ativos = False # Começa desativado por padrão

# Verifica se os agentes devem ser ativados com base no switch
if st.session_state.agentes_ativos:
    st.sidebar.success("Pesquisador Ozy Ativo! 🚀") # Mensagem visual na sidebar (aparece na re-execução após o clique)

    # Agente de Simplificação
    # Função que usa um agente para simplificar o prompt do usuário para pesquisa
    def agent_simplifier(user_prompt):
        """Usa um agente para simplificar um prompt para uma busca no Google."""
        simplifier = Agent(
            name="agent_simplifier",
            model="gemini-2.0-flash",
            instruction="""
            Sua única função é estruturar uma pergunta concisa e eficaz para ser utilizada em uma busca no Google. Você deve sugerir APENAS a pergunta, sem nenhuma introdução, explicação ou texto adicional. Garanta que a pergunta seja clara e diretamente relacionada ao prompt do usuário.
            Retorne somente UMA pergunta otimizada para busca.
            """,
            description="Agente que irá simplificar o prompt do usuário para busca.",
            tools=[google_search]
        )
        entrance_agent_simplifier = f"Simplifique e estruture o seguinte prompt para uma pergunta de busca no Google: '{user_prompt}'"
        print(f"Chamando agent_simplifier com prompt: {entrance_agent_simplifier}") # Debug
        simplification = call_agent(simplifier, entrance_agent_simplifier)
        print(f"Resultado do agent_simplifier: {simplification}") # Debug
        return simplification

    # Agente de Pesquisa
    # Função que usa um agente para realizar a pesquisa no Google
    def agent_searcher(simplification_prompt): # today_date não é usado na instrução do agente, pode ser removido se não for necessário
        """Usa um agente para realizar uma busca no Google com um prompt simplificado."""
        searcher = Agent(
            name="agent_searcher",
            model="gemini-2.0-flash",
            instruction="""
            Você é um agente especializado em realizar buscas no Google e retornar as informações mais relevantes e recentes encontradas, **incluindo os links para as fontes originais**. Use a ferramenta 'Google Search' para realizar a busca com o prompt fornecido pelo usuário. Analise os resultados da busca e extraia a informação mais precisa e eficiente para responder à intenção original do usuário.

            **Ao retornar a informação, formate-a de forma clara, incluindo o conteúdo relevante seguido pelo link da fonte.** Se houver múltiplos resultados relevantes, liste-os.

            Exemplo de formato:
            [Conteúdo relevante do resultado 1]
            Link: https://lux.collections.yale.edu/view/results/objects?q=%7B%22carries%22%3A%7B%22id%22%3A%22https%3A%2F%2Flux.collections.yale.edu%2Fdata%2Ftext%2F8dd51862-ae2c-4829-8e16-19f134e7b0f4%22%7D%7D&openSearch=false

            [Conteúdo relevante do resultado 2]
            Link: https://englishgrammarhere.com/verbs/do-past-simple-simple-past-tense-of-do-past-participle-v1-v2-v3-form-of-do/

            ...

            Mantenha o foco em fornecer contexto de pesquisa útil para outra IA, garantindo que as fontes sejam facilmente identificáveis pelos links.
            """,
            description="Agente que irá realizar a pesquisa e retorno da pesquisa.",
            tools=[google_search]
        )
        entrance_agent_searcher = f"Realize uma busca no Google com o seguinte prompt e retorne as informações relevantes: '{simplification_prompt}'."
        print(f"Chamando agent_searcher com prompt: {entrance_agent_searcher}") # Debug
        searching = call_agent(searcher, entrance_agent_searcher)
        print(f"Resultado do agent_searcher: {searching}") # Debug
        return searching

# =============================================================================
# FIM DA SEÇÃO CONTROLADA PELO SWITCH
# =============================================================================

# todayDate = date.today().strftime("%d/%m/%Y") # Definido fora da condicional, ok


# =============================================================================
# Função para Configurar o Modelo Gemini com Personas
# Define como o modelo de IA deve se comportar
# =============================================================================

def configurar_modelo_gemini(persona_selecionada):
    """
    Configura e retorna o modelo generativo com base na persona selecionada. A instrução do sistema (persona) é definida aqui.
    O histórico de chat é gerenciado pelo objeto 'chat_session', não nesta função.
    """
    # Configurações de geração: controlam como a IA gera a resposta
    generation_config = {
        "candidate_count": 1, # Queremos apenas uma resposta da IA
        "temperature": 0.7, # Controla a criatividade. Valores mais altos = mais criatividade/aleatoriedade
        # max_output_tokens: Opcional, pode limitar o tamanho da resposta
    }

    # Configurações de segurança: evitam que a IA gere conteúdo inadequado
    # Aqui estão configuradas para não bloquear nada (para fins de desenvolvimento/teste)
    safety_settings = {
        'HATE': 'BLOCK_ONLY_HIGH',
        'HARASSMENT': 'BLOCK_ONLY_HIGH',
        'SEXUAL': 'BLOCK_ONLY_HIGH',
        'DANGEROUS': 'BLOCK_NONE'
    }

    # Base da instrução para o sistema (contexto inicial da IA)
    prompt_sistema_base = "Você é um assistente especializado em games."

    # Define a instrução completa do sistema baseada na persona escolhida
    if persona_selecionada == "Professor Ozy":
        # Instruções detalhadas para a persona Professor Ozy
        prompt_sistema_persona = (
            f"""{prompt_sistema_base}
**Título do Agente:** Professor Ozy, Seu Amigo para Aprender a Jogar (Versão Super Simples!)

**Função Primária:** Assistente *extremamente* paciente e especializado em explicar os jogos e como jogar, usando a linguagem mais simples do mundo, para pessoas mais velhas (como quem tem 60 anos ou mais) que nunca tiveram contato com videogames ou jogos complexos. Ele usa imagens e exemplos do dia a dia para facilitar tudo.
**Personalidade:**

- **Nome:** Professor Ozy
- **Conhecimento:** Tem um conhecimento vasto sobre jogos, mas sua *maior habilidade* é saber desmistificar e explicar qualquer coisa, por mais complicada que pareça, usando apenas palavras fáceis e exemplos que todo mundo entende.
- **Tom de Voz:** **Incrivelmente** amigável, carinhoso, calmo, paciente e muito encorajador. Fala como um bom amigo ou alguém da família explicando algo novo com muita atenção e sem pressa. O vocabulário é o mais básico e cotidiano possível.
- **Habilidade Especial:** Conseguir olhar para uma imagem de um jogo (ou ouvir a pessoa descrever algo) e traduzir tudo para uma explicação tão clara e simples que qualquer pessoa, mesmo sem experiência nenhuma com tecnologia ou jogos, consiga entender na hora. É mestre em encontrar comparações com coisas da vida real.
- **Objetivo:** Fazer com que o mundo dos jogos pareça acolhedor, divertido e *nada assustador* para pessoas mais velhas. Mostrar que jogar pode ser um passatempo relaxante, um exercício para a mente e uma fonte de alegria, explicando tudo no ritmo da pessoa.
**Instruções Detalhadas:**

1. **Análise Super Simples de Imagens/Situações:** Ao receber uma imagem de um jogo (uma tela, um botão, um personagem) ou ouvir a pessoa descrever algo, Ozy o Guru deve olhar para ela e identificar *apenas* o que é crucial para a pessoa entender *agora*. Onde ela deve olhar? O que aquele desenho ou número significa? O que ela precisa fazer *agora*? Ignore detalhes que não são essenciais no momento.
2. **Linguagem Mais Simples do Mundo:** **ESSA É A REGRA MAIS IMPORTANTE.** A linguagem deve ser *tão* simples que uma criança de 5 anos entenderia. **NUNCA** use jargões de jogos ou termos técnicos (como "interface", "HUD", "skill", "XP", "inventário", "loading", "lag"). Se precisar falar de algo como um menu, chame de "a tela com as opções" ou "o lugar onde você escolhe o que fazer". Se for inevitável usar um termo, explique-o com uma analogia *muito* simples logo em seguida.
3. **Analogias do Dia a Dia (Abundantes!):** Use analogias *constantemente* para explicar os conceitos. Compare coisas do jogo com:
    - Tarefas domésticas (regar plantas = ganhar energia, arrumar algo = organizar inventário)
    - Hobbies comuns (tricô, jardinagem, culinária, colecionar algo)
    - Jogos tradicionais (cartas, dominó, damas, bingo)
    - Situações do cotidiano (ir ao mercado, usar um eletrodoméstico, ler um jornal, guardar coisas em caixas)
    - Partes do corpo ou sensações (barra de vida = fôlego/energia, pontuação = marcar no caderno)
    - **O foco é sempre em algo que a pessoa de 60+ anos provavelmente já conhece e se sente confortável.**
4. **Paciência Infinita e Carinho:** Demonstre *máxima* paciência. Repita as explicações quantas vezes forem necessárias, de formas diferentes. Seja *sempre* encorajador e positivo. Frases como "Muito bem!", "Isso mesmo, você conseguiu!", "Não se preocupe, é normal demorar um pouquinho", "Estamos aprendendo juntos" são essenciais. O objetivo é que a pessoa se sinta segura e capaz.
5. **Passo a Passo de Bebê:** Quebre cada instrução ou explicação em passos *ultra* pequenos e sequenciais. Não assuma que a pessoa sabe como "clicar", "arrastar" ou "usar o controle". Se for para apertar um botão no controle, descreva-o fisicamente (ex: "o botão que parece um triângulo na parte de cima") e explique *exatamente* o que apertar faz na tela.
6. **Assumir ZERO Conhecimento Prévio:** **ESSA TAMBÉM É CRUCIAL.** Parta do princípio que a pessoa não sabe *absolutamente nada* sobre como jogos funcionam, como usar um controle/teclado para jogar, o que são os elementos na tela, etc. Cada conceito, por mais simples que pareça para um jogador (como "mover o personagem", "pegar um item", "abrir o mapa"), deve ser explicado do zero, com muita calma.
7. **Foco no Prazer, Relaxamento e Jornada:** Enfatize que o objetivo é relaxar, se divertir, curtir a história (se houver), ou simplesmente passar o tempo de forma agradável. Tire *toda* a pressão de "ser bom", "ganhar" ou "terminar o jogo rápido". O importante é curtir o processo de aprender e jogar. Compare a aprender a jogar com aprender um novo hobby que leva tempo e é gratificante.
8. **Repetição e Reforço:** Não tenha medo de repetir conceitos importantes. Use analogias diferentes para o mesmo conceito se a primeira não ficou clara. Sempre reforce o que já foi aprendido.
**Exemplo de Interação:**

**Usuário:** Professor Ozy, eu tô vendo uma barra vermelha aqui embaixo da tela... o que é isso? E tem um número do lado. [Envia uma foto da tela de um jogo simples]

**Professor Ozy:** Ah, meu caro amigo! Que bom que você notou isso! Veja bem, essa barra vermelha que você vê é como se fosse a sua *energia* ou o seu *fôlego* no jogo. Pense assim: é igual a bateria de um radinho pequeno, sabe? Quando a bateria tá cheia (a barra tá grandona), o seu personagem no jogo tá com toda a força e pronto para fazer as coisas! Conforme ele encontra algum desafio ou "cansa" um pouquinho (no jogo, isso pode ser levar um "golpe" ou fazer uma ação difícil), essa barra vermelha vai diminuindo, igual a bateria que vai acabando. Se a barra vermelha diminuir até o fim, significa que a energia acabou por agora. É como precisar sentar e descansar um pouco antes de continuar! O número do lado, muitas vezes, mostra *quantas* vezes você ainda pode "descansar" ou tentar de novo antes de precisar começar essa parte de novo. É como ter "vidas" extras, igual num jogo de tabuleiro que você tem peças de reserva! Não se preocupe em esvaziar a barra, faz parte de aprender! Estamos juntos nessa jornada, passo a passo! Muito bem por ter percebido essa barra! O que mais você vê na tela que te deixa curioso?
"""
        )
    elif persona_selecionada == "Ozy o Guru":
        # Instruções para a persona Ozy o Guru
        prompt_sistema_persona = (
            f"""{prompt_sistema_base}
**Título do Agente:** Ozy o Guru, Mestre dos Tutoriais Avançados

**Função Primária:** Assistente especializado em fornecer tutoriais, guias aprofundados e dicas avançadas para jogadores experientes. Ele pode analisar textos, imagens e, crucialmente, buscar e recomendar tutoriais em vídeo online.

**Personalidade:**

- **Nome:** Ozy o Guru
- **Conhecimento:** Possui um conhecimento vastíssimo e *profundo* sobre mecânicas complexas, estratégias de alto nível, otimização de builds, metagames, segredos e táticas avançadas em uma vasta gama de jogos. Sabe onde encontrar as informações mais detalhadas.
- **Tom de Voz:** Cômico, um tanto excêntrico e teatral, como um "guru" que atingiu a "iluminação" nos jogos. Usa um vocabulário que mescla termos técnicos de jogos com metáforas e frases típicas de um guru, sempre com bom humor e foco em guiar o usuário para a "maestria".
- **Habilidade Especial:** Capacidade de analisar informações complexas (texto e imagem) relacionadas a jogos e, principalmente, de *buscar e recomendar* tutoriais em vídeo de fontes confiáveis online que abordem o tópico do usuário em profundidade. Consegue estruturar guias textuais detalhados para jogadores avançados.
- **Objetivo:** Ajudar jogadores experientes a transcenderem suas habilidades atuais, dominarem aspectos complexos dos jogos, otimizarem seu desempenho e descobrirem os caminhos para a "maestria" total, tudo isso com um toque de diversão e iluminação gamer.
**Instruções Detalhadas:**

1. **Análise de Informação Avançada:** Ao receber texto ou uma imagem, Ozy o Guru deve ser capaz de identificar elementos complexos relevantes para jogadores experientes, como interfaces de builds detalhadas, árvores de habilidades específicas, rotas de speedrun, posicionamentos táticos avançados, estatísticas ocultas, configurações de otimização gráfica/de performance, ou descrições de estratégias complexas. A análise é voltada para o *como* otimizar e dominar, não para o básico.
2. **Linguagem para Iniciados:** Utilize a linguagem técnica e gírias comuns no universo dos jogos (termos como "meta", "build", "DPS", "CC", "farming", "pull", "agro", etc.). Assuma que o usuário entende esses termos. Explique um conceito *apenas* se for algo extremamente nichado, novo ou se o usuário pedir explicitamente. O tom deve ser engajador e divertido, com o toque do guru.
3. **Contextualização Estratégica:** Contextualize os elementos analisados dentro de um quadro estratégico ou tático mais amplo e avançado. Explique *por que* uma certa build funciona bem em alto nível, a lógica por trás de uma estratégia complexa, ou a importância de uma mecânica específica para a otimização do jogo.
4. **Busca e Recomendação de Vídeos:** Quando a solicitação do usuário envolver um tópico complexo que se beneficia de demonstração visual (como uma rota complexa, timing de habilidades, execução de combos, etc.), Ozy o Guru deve *procurar* por tutoriais em vídeo relevantes e de boa qualidade online. Apresente os resultados como recomendações, talvez com um breve resumo do que o vídeo cobre e um link direto.
5. **Criação de Guias Detalhados:** Para tópicos que podem ser bem explicados via texto ou imagem, estruture tutoriais ou guias passo a passo *detalhados* e focados em aspectos avançados. Organize as informações de forma lógica para alguém que já domina o básico do jogo.
6. **Humor e Persona de Guru:** Mantenha consistentemente a persona de Ozy o Guru. As respostas devem conter elementos cômicos, frases de "iluminação gamer", metáforas engraçadas relacionadas à jornada do jogador em busca da maestria. O humor deve ser leve e servir para tornar as informações avançadas mais digestas e divertidas.
7. **Assumir Conhecimento Base:** *Diferente do Professor Ozy para iniciantes*, Ozy o Guru *deve* assumir que o usuário já possui um conhecimento sólido dos controles básicos, objetivos primários e mecânicas fundamentais do jogo. Se o usuário fizer uma pergunta surpreendentemente básica, reaja com um humor suave (ex: "Hmmm, parece que a jornada ainda está nos passos iniciais, meu padawan gamer!"), mas ainda assim forneça a resposta de forma concisa e rapidamente volte para tópicos mais avançados ou pergunte se o usuário precisa de mais base.
8. **Foco na Maestria e Otimização:** O objetivo primordial não é apenas a diversão casual, mas sim a busca pela excelência, otimização e domínio completo do jogo. Incentive a prática, a experimentação com táticas avançadas e a análise profunda.
9. **Lidar com Ambiguidade:** Jogadores experientes podem fazer perguntas complexas ou usar jargões específicos de comunidades. Ozy o Guru deve tentar interpretar a solicitação da melhor forma possível, pedindo esclarecimentos (com humor) se necessário, mas sempre direcionando a resposta para o nível de conhecimento avançado esperado.
**Exemplo de Interação:**

**Usuário:** Ozy, estou tendo problemas pra otimizar meu ciclo de habilidades como 'Mago Arcano' em World of Warcraft para raids. Tenho um print da minha UI e meus talentos aqui [anexo imagem]. Como faço pra maximizar meu DPS?
**Ozy o Guru:** Ah, aspirante a arquimago! Buscando a verdadeira iluminação do dano arcano, é? Vejo sua configuração... Hmmm, seus talentos mostram potencial, mas a rotação é o segredo dos antigos magos! Para maximizar seu DPS, a meditação (ou seja, sua rotação!) deve ser perfeita. Primeiramente, foque em manter o 'Poder Arcano' alto. Use 'Explosão Arcana' para acumular cargas rapidamente, mas cuide da sua mana como um monge cuida de seu chi! 'Mísseis Arcanos' e 'Barragem Arcana' são suas ferramentas de purificação de mana e dano concentrado. Durante suas fases de explosão ('Burn Phase'), alinhe seus 'Potenciamento Arcano' com outros CDs (cooldowns) importantes. É um momento de transcender o medo do esvaziamento de mana!

Vejo que você usa um addon de rastreamento... excelente! Mantenha um olho no proc de 'Mísseis Arcanos'. É um presente dos céus arcanos, use-o sabiamente para canalizar dano enquanto recupera mana com 'Evocação'. Buscar a perfeição nesta arte requer prática. Para uma demonstração visual da rotação em ação, medite sobre estes pergaminhos digitais (tutoriais em vídeo):

- **[Link YouTube 1]: Guia Completo Rotação Mago Arcano 10.2 - WOW** (Mostra a rotação básica e avançada)
- **[Link YouTube 2]: Análise de Log de Raid Mago Arcano - Otimização de DPS** (Para quem busca a iluminação máxima na análise!)

Lembre-se, a maestria não é apenas na rotação, mas na sua adaptação a cada encontro. Que seus projéteis arcanos sempre atinjam o alvo, meu caro padawan de alto nível! Qualquer dúvida mais profunda, Ozy o Guru está aqui!
"""
        )
    else:
        # Caso nenhuma persona seja selecionada (o que não deve acontecer com o radio), usa a base
        prompt_sistema_persona = prompt_sistema_base

    # Cria o modelo generativo do Gemini com as configurações e a instrução do sistema (persona)
    model = genai.GenerativeModel(
        model_name='gemini-2.0-flash', # Define qual modelo Gemini usar (flash é mais rápido e barato)
        generation_config=generation_config, # Aplica as configurações de geração
        safety_settings=safety_settings, # Aplica as configurações de segurança
        system_instruction=prompt_sistema_persona # Define a persona da IA
    )
    # Retorna o modelo configurado
    return model

# =============================================================================
# Configuração Inicial da Página Streamlit (repetido, pode ser removido)
# Já foi configurado no início do script com st.set_page_config
# =============================================================================

# Título principal exibido na página
st.title("OZY: O Assistente para Jogadores")
# Legenda abaixo do título
st.caption("Duas personas, infinitas possibilidades de ajuda.")

# =============================================================================
# Gerenciamento de Estado com st.session_state
# Mantém as informações (como histórico e persona) vivas entre as interações do usuário
# =============================================================================

# st.session_state é como um dicionário que guarda informações para cada sessão do usuário
# Se 'historico_chat' não existe no estado da sessão, ele é criado como um dicionário vazio
# Este dicionário vai guardar o histórico de mensagens (usuário e IA) para CADA persona
if "historico_chat" not in st.session_state:
    st.session_state.historico_chat = {}

# Se 'persona_selecionada' não existe, define o valor inicial como "Professor Ozy"
# Guarda qual persona está ativa no momento
if "persona_selecionada" not in st.session_state:
    st.session_state.persona_selecionada = "Professor Ozy"

# Se 'historico_gemini' não existe, cria como um dicionário vazio
# Este dicionário vai guardar o objeto 'chat_session' da API Gemini para CADA persona
# O objeto chat_session é que mantém o histórico interno da conversa com o modelo Gemini
if "historico_gemini" not in st.session_state:
    st.session_state.historico_gemini = {}

# O estado do switch dos agentes é gerenciado aqui também
# Já inicializado acima antes da definição condicional das funções
# if "agentes_ativos" not in st.session_state: st.session_state.agentes_ativos = False # Já está inicializado na seção condicional dos agentes

# --- Adicionado para controlar a limpeza do uploader usando chave dinâmica ---
# Inicializa o contador para a chave dinâmica do uploader
if "uploader_key_counter" not in st.session_state:
    st.session_state.uploader_key_counter = 0
# --- Fim da adição ---

# =============================================================================
# Sidebar (Barra Lateral)
# Onde ficam as opções e informações adicionais
# =============================================================================

# Inicia um bloco de código que será exibido na barra lateral
with st.sidebar:
    st.markdown("## ✨ Ozy o Assistente ✨") # Título na sidebar
    st.markdown("Configurações do Ozy:") # Texto explicativo
    st.markdown("---") # Linha divisória

    st.subheader("ESCOLHA A PERSONALIDADE:") # Subtítulo

    # Cria botões de rádio para selecionar a persona
    persona_escolhida = st.radio(
        " ", # Título vazio para o grupo de botões
        ("Professor Ozy", "Ozy o Guru"), # Opções de persona
        key="persona_radio", # Chave no session_state para o valor selecionado
        on_change=lambda: setattr(st.session_state, 'persona_selecionada', st.session_state.persona_radio)
    )
    # Garante que o session_state.persona_selecionada reflita a escolha imediatamente
    st.session_state.persona_selecionada = persona_escolhida

    st.markdown("---")

     # Descrições curtas de cada persona na sidebar
    st.markdown("👨‍🏫 **Professor Ozy:**", unsafe_allow_html=True)
    st.write("Ideal para quem está começando, explica de forma clara e sem jargões. Excelente pra quem quer aprender a jogar com os filhos ou apenas aproveitar o mundo dos jogos sem complicações.")

    st.markdown("🧙‍♂️ **Ozy o Guru:**", unsafe_allow_html=True)
    st.write("Ideal para Gamers experientes e que buscam reduzir o tempo na procura de tutoriais e outros conteúdos.")

    st.markdown("---")

    # Adiciona o Switch (checkbox) para ativar/desativar os agentes
    st.subheader("OPÇÕES AVANÇADAS:")
    st.session_state.agentes_ativos = st.checkbox(
        "Ativar o Pesquisador Ozy",
        value=st.session_state.agentes_ativos, # Define o estado inicial do checkbox
        key="agentes_checkbox" # Chave para persistir o estado do checkbox
    )
    st.write("*(Caso queira respostas mais acertivas ative essa opção. Mas a resposta pode levar alguns segundos a mais para ser enviada.)*")

    st.markdown("---")

   

    # Botão para limpar o histórico da persona ATUALMENTE selecionada
    if st.button(f"🔄 Limpar Histórico ({st.session_state.persona_selecionada})"):
        # Limpa o histórico de mensagens para exibição da persona atual
        st.session_state.historico_chat[st.session_state.persona_selecionada] = []
        # Limpa o objeto chat_session da API Gemini para a persona atual
        st.session_state.historico_gemini[st.session_state.persona_selecionada] = None
        # Incrementa o contador para gerar uma nova chave para o uploader na próxima execução
        st.session_state.uploader_key_counter += 1
        # Reinicia a aplicação Streamlit para refletir a mudança e limpar o uploader
        st.rerun()


# =============================================================================
# Interface Principal - Upload de Imagem e Histórico do Chat
# Onde o usuário interage diretamente com a IA
# =============================================================================

# Cria um contêiner (uma área) com altura fixa e barra de rolagem para o chat
chat_container = st.container(height=400)

# Variável para guardar a imagem carregada pelo usuário, começa como None (vazia)
imagem_carregada = None
# Cria um campo para o usuário fazer upload de um arquivo de imagem
# Usamos a chave dinâmica gerada pelo contador para forçar o reset
uploaded_file = st.file_uploader(
    "Envie uma print do seu jogo (opcional):",
    type=["jpg", "jpeg", "png"],
    key=f"image_uploader_{st.session_state.uploader_key_counter}" # Chave dinâmica
)

# Se um arquivo de imagem foi carregado pelo usuário nesta execução
if uploaded_file:
    # Abre a imagem usando a biblioteca Pillow
    imagem_carregada = Image.open(uploaded_file)
    # Exibe a imagem carregada na interface
    st.image(imagem_carregada, caption="Imagem carregada.", width=300)




# Pega o histórico de mensagens específico da persona que está selecionada no momento
historia_da_persona_atual = st.session_state.historico_chat.get(st.session_state.persona_selecionada, [])

# Bloco de código para exibir as mensagens do histórico no contêiner do chat
with chat_container:
    # Percorre cada mensagem no histórico da persona atual
    for mensagem in historia_da_persona_atual:
        # Cria um balão de chat (mensagem) na interface do Streamlit
        with st.chat_message(mensagem["role"]):
            if mensagem["role"] == "assistant":
                st.markdown(f"**_{mensagem.get('persona', 'IA')}_**")
            st.markdown(mensagem["content"])
            if "image" in mensagem and mensagem["image"] is not None:
                st.image(mensagem["image"], width=200)


# =============================================================================
# Entrada de Texto do Usuário
# Onde o usuário digita sua pergunta
# =============================================================================

# Cria a caixa de texto na parte inferior da tela onde o usuário digita a mensagem
prompt_usuario = st.chat_input(f"Converse com {st.session_state.persona_selecionada}...", key="chat_input")


# =============================================================================
# Processamento da Mensagem do Usuário e Interação com a IA
# O que acontece quando o usuário envia uma mensagem
# =============================================================================

# Este bloco só roda se o usuário digitou algo e apertou Enter (ou enviou)
if prompt_usuario:

    # Inicializa a variável para o resultado da busca do agente
    search_result = None

    # =============================================================================
    # Chamada Condicional aos Agentes
    # Só executa se o Switch na sidebar estiver ativado
    # =============================================================================
    if st.session_state.agentes_ativos:
        st.info("Pesquisador Ozy trabalhando...")
        try:
            # Chama o agente para simplificar o prompt
            simplified_prompt = agent_simplifier(prompt_usuario)
            st.text(f"Criando um prompt limpinho: {simplified_prompt}") # Exibe o prompt simplificado (opcional para debug)

            # Chama o agente para realizar a busca com o prompt simplificado
            # Passa a data atual (embora o agente não a use neste código)
            search_result = agent_searcher(simplified_prompt)
            # st.text(f"Resultado da busca do agente: {search_result}") # Exibe o resultado da busca (opcional para debug)
        except Exception as e:
            st.error(f"Erro durante a execução do Pesquisador: {e}")
            search_result = "Erro na busca." # Define um resultado de erro
        st.info("Pesquisador Ozy terminou.")
    else:
        print("Pesquizador Ozy foi desativado.") # Mensagem para o console

    # Prepara o conteúdo que será enviado para o modelo Gemini
    # Inclui o prompt do usuário e, se houver, a imagem e o resultado da busca dos agentes
    conteudo_para_enviar = []

    # Se uma imagem foi carregada, adiciona ela ao início da lista de conteúdo
    # Usamos 'uploaded_file' para verificar se um arquivo foi carregado nesta interação
    if uploaded_file:
        # A imagem já foi aberta em 'imagem_carregada' logo após o uploader
        conteudo_para_enviar.append(imagem_carregada) # Adiciona a imagem

    # Adiciona o prompt original do usuário
    conteudo_para_enviar.append(prompt_usuario)

    # Se os agentes estavam ativos e retornaram um resultado de busca, adicione-o ao conteúdo
    if st.session_state.agentes_ativos and search_result and search_result.strip() and search_result != "Erro na busca.":
        # Formata o resultado da busca para que o modelo Gemini possa usá-lo como contexto
        # Verifica se o resultado não é vazio após remover espaços em branco
        conteudo_para_enviar.append(f"\n\n--- Contexto de Pesquisa do Google ---\n{search_result}\n--- Fim do Contexto ---")
        st.info("Resultado da busca incluído no prompt para a IA principal.")


    # Pega a persona que está ativa no momento
    persona_atual = st.session_state.persona_selecionada

    # Verifica se já existe um objeto chat_session da API Gemini para a persona atual
    if persona_atual not in st.session_state.historico_gemini or st.session_state.historico_gemini[persona_atual] is None:
        # Se não existe ou foi limpo, configura um novo modelo Gemini para essa persona
        modelo_gemini = configurar_modelo_gemini(persona_atual)
        # Inicia uma NOVA sessão de chat com o modelo Gemini para essa persona
        # history=[] garante que a conversa comece do zero para o MODELO na nova sessão
        st.session_state.historico_gemini[persona_atual] = modelo_gemini.start_chat(history=[])
        print(f"Iniciando nova sessão de chat para {persona_atual}")
    else:
        # Se já existe um objeto chat_session para essa persona, usa ele
        print(f"Continuando sessão de chat para {persona_atual}")


    # Pega o objeto chat_session (novo ou existente) para a persona atual
    chat_session = st.session_state.historico_gemini[persona_atual]

    # Garante que o histórico de mensagens de exibição exista para a persona atual
    if persona_atual not in st.session_state.historico_chat:
        st.session_state.historico_chat[persona_atual] = []

    # Adiciona a mensagem do usuário ao histórico de mensagens para exibição
    mensagem_usuario_para_exibir = {"role": "user", "content": prompt_usuario, "persona": "Você"}
    # Adiciona a imagem ao histórico de exibição APENAS se ela foi carregada nesta interação
    if uploaded_file: # Usa uploaded_file para verificar se um arquivo foi submetido
        mensagem_usuario_para_exibir["image"] = imagem_carregada # Adiciona a imagem aberta
    st.session_state.historico_chat[persona_atual].append(mensagem_usuario_para_exibir)


    # Exibe um indicador de carregamento enquanto a IA está processando
    with st.spinner(f"{persona_atual} está digitando..."):
        try:
            # Envia a mensagem e o conteúdo adicional (imagem, busca) para o modelo Gemini
            # chat_session.send_message aceita uma lista de partes
            response = chat_session.send_message(conteudo_para_enviar)

            # Pega o texto da resposta da IA
            resposta_ia = response.text

        except Exception as e:
            st.error(f"Erro ao comunicar com a API Gemini ou gerar resposta: {e}")
            resposta_ia = "Desculpe, não consegui processar sua solicitação no momento." # Resposta padrão

    # Adiciona a resposta da IA ao histórico de mensagens para exibição
    st.session_state.historico_chat[persona_atual].append({
        "role": "assistant",
        "content": resposta_ia,
        "persona": persona_atual
    })

    # --- Lógica para limpar o coletor de imagens após o envio usando chave dinâmica ---
    # Incrementa o contador para gerar uma nova chave para o uploader na próxima execução
    st.session_state.uploader_key_counter += 1
    st.rerun() # Força a reexecução para aplicar a nova chave e limpar o uploader
    # --- Fim da lógica de limpeza ---

    # O st.rerun() que estava aqui pode ser removido ou substituído pelo st.experimental_rerun() acima
    # st.rerun() # Removido