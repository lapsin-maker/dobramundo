"""Textos de apoio do jogo Dobramundo.

Este módulo reúne, em constantes, todos os textos exibidos fora da mecânica
de voo: abertura, aviso ao supervisor, sobre, ODS, créditos, referências,
dicas, curiosidades dos biomas e rótulos de interface. Os textos seguem o
Game Design Document (GDD) do projeto.

Uso, a partir do código do jogo:

    from dobramundo.content import texts

    titulo = texts.TITLE
    rotulo = texts.UI["decolar"]

Todas as strings estão em português do Brasil (norma culta). As falas
dirigidas à criança usam "você" e não têm marcação de gênero. Não há
dependências externas: o módulo é compatível com Python 3.8.
"""

from typing import Dict, Tuple

TITLE = "Dobramundo"

TAGLINE = "Dobre o papel, voe e transforme a cidade."

INTRO_CAPTIONS = (
    "Uma metrópole cinzenta, cheia de fumaça e poluição.",
    "Uma criança encontra um jornal esquecido na rua.",
    "Ela dobra o papel e cria um avião.",
    "Ela lança o avião ao céu.",
    "Cada voo transforma a cidade.",
)

CONSENT_TITLE = "Aviso ao supervisor e aos responsáveis"

CONSENT_LINES = (
    "O Dobramundo deve ser usado sob a supervisão de um adulto (Pereira et al., 2023).",
    "Use em área livre, sem obstáculos ao redor da criança.",
    "O vídeo da câmera é processado no próprio computador e nunca é gravado.",
    "O uso depende do consentimento dos responsáveis pela criança.",
    "Base legal: arts. 11 e 14 da Lei nº 13.709/2018 (LGPD).",
    "Se o jogador sair da área da câmera, o jogo pausa automaticamente.",
    "O supervisor pode pausar a qualquer momento com a tecla P ou ESC.",
    "Volume, silêncio e alto contraste ficam em Opções.",
)

ABOUT_SECTIONS = (
    (
        "O que é o Dobramundo",
        (
            "Dobramundo é um exergame sério de voo, com proposta terapêutica. "
            "A criança pilota, com o próprio corpo, um avião de papel reciclado.",
            "O jogo atende ao console T-TEA, mas não se restringe ao chão "
            "interativo: pode ser projetado em mesas e paredes ou exibido em "
            "monitores. O controle pode ser feito pelos pés, pelo tronco, por "
            "uma das mãos ou pela cabeça.",
            "Não há botões. A câmera, com visão computacional (MediaPipe Pose), "
            "acompanha o segmento escolhido e move o avião nos dois eixos.",
            "Destina-se a crianças neurodiversas e com deficiências motoras, "
            "visuais, sensoriais ou do neurodesenvolvimento. O nome une a "
            "dobradura de papel à transformação do mundo, como na canção "
            "Aquarela, popularizada por Toquinho.",
        ),
    ),
    (
        "Tema: duas escalas de sustentabilidade",
        (
            "Na escala ambiental, o jogo adota o paradigma solarpunk, vertente "
            "que imagina sociedades tecnológicas, movidas a energia renovável "
            "e integradas à natureza.",
            "A primeira antologia do gênero foi publicada no Brasil (Lodi-Ribeiro, "
            "2012), fechando a trilogia iniciada por vaporpunk e dieselpunk. O "
            "jogo retoma esse percurso, da cidade dieselpunk à solarpunk.",
            "O Brasil é potência energética limpa: em 2024, 88,2% de sua "
            "eletricidade e 50% de sua matriz energética vieram de fontes "
            "renováveis (EPE, 2025).",
            "Na escala pessoal, sustentabilidade significa preservar a saúde "
            "física e mental com atividade corporal regular, prazerosa e acessível.",
        ),
    ),
    (
        "Objetivo",
        (
            "O objetivo não é restaurar uma natureza intocada, mas construir uma "
            "sociedade em que a natureza integra a cidade.",
            "Na escala macro, a transformação ocorre no desenho urbano e na "
            "matriz energética. Na escala micro, ocorre na microgeração "
            "distribuída de energia, nas hortas urbanas e no reaproveitamento "
            "de resíduos.",
            "Numa metrópole poluída, uma criança dobra um jornal em avião e o "
            "lança. A cada voo, os resíduos recolhidos viram recursos que "
            "desenvolvem a vila-base e o avião, até a cidade tornar-se solarpunk.",
        ),
    ),
    (
        "Objetivo sério",
        (
            "Cada mecânica corresponde a uma demanda funcional. Ajustar a "
            "trajetória a estímulos visuais em movimento exige integração "
            "sensório-motora e visuomotora, coordenação olho-mão e olho-membros "
            "e controle postural.",
            "Esses processos dependem de circuitos cerebelares de correção e "
            "predição motora. Distinguir resíduos de obstáculos e decidir "
            "rapidamente entre coletar e desviar recruta atenção seletiva e "
            "sustentada, controle inibitório e tomada de decisão, componentes "
            "das funções executivas.",
            "A velocidade crescente gradua a carga motora e cognitiva.",
        ),
    ),
    (
        "Inovação",
        (
            "O T-TEA pressupõe projeção no chão e controle pelos pés de um "
            "jogador em pé. A demanda por adaptações nasce da experiência "
            "pessoal de integrantes da equipe, que convivem com deficiências "
            "motoras e sensoriais, e de seus familiares.",
            "O jogo responde desacoplando a superfície de exibição do segmento "
            "corporal de controle: qualquer superfície admite qualquer segmento, "
            "sem hardware extra.",
        ),
    ),
    (
        "Acessibilidade, segurança e privacidade",
        (
            "Para jogadores com baixa visão, o modo de alto contraste dessatura "
            "o fundo e destaca avião e objetos com cores intensas e contornos "
            "espessos.",
            "Há ajuste de volume e opção de silêncio, que reduzem a carga "
            "sensorial em casos de hipersensibilidade auditiva.",
            "A pausa é automática quando o jogador deixa a área de captura, e o "
            "supervisor também pode acioná-la com a tecla P ou ESC.",
            "O vídeo é processado localmente, sem gravação. O uso requer "
            "supervisão (Pereira et al., 2023) e consentimento dos responsáveis "
            "(arts. 11 e 14 da LGPD, Lei nº 13.709/2018).",
        ),
    ),
)

ODS = (
    (
        3,
        "Saúde e Bem-Estar",
        "Atividade física e estímulo sensório-motor",
    ),
    (
        7,
        "Energia Limpa e Acessível",
        "Microgeração solar",
    ),
    (
        10,
        "Redução das Desigualdades",
        "Acessibilidade",
    ),
    (
        11,
        "Cidades e Comunidades Sustentáveis",
        "Cidade integrada à natureza",
    ),
    (
        12,
        "Consumo e Produção Responsáveis",
        "Resíduos como recursos",
    ),
    (
        15,
        "Vida Terrestre",
        "Biomas brasileiros",
    ),
)

ENERGY_FACT = (
    "Em 2024, 88,2% da eletricidade e 50% da matriz energética do Brasil vieram de fontes renováveis (EPE, 2025)."
)

CREDITS = (
    ("Equipe", "Liga de Psiquiatria e Neurociências – CENSUPEG"),
    (
        "Membros",
        "João Pedro Turnes (capitão), Isabella Cordeiro Sonza, "
        "Gerciane Larice da Silva Barros e Luiz Felipe Santana Tomio",
    ),
    ("Captura", "Adaptada do T-TEA 2.0 (LARVA/UDESC)"),
    ("Modelos 3D", "Feitos pela equipe em Blender e modelos low-poly gerados por código (tools/lowpoly)"),
    ("Programação", "IA generativa (Gemini e Claude) apoiou a programação"),
    ("Tecnologia", "Python, pygame, OpenCV e MediaPipe Pose"),
    ("Música e efeitos", "Sintetizados pelo projeto"),
    ("Evento", "3ª ExerGame JAM LARVA/UDESC 2026"),
)

REFERENCES = (
    "EPE. Balanço Energético Nacional 2025: ano base 2024. Rio de Janeiro: EPE, 2025.",
    "LODI-RIBEIRO, G. (org.). Solarpunk: histórias ecológicas e fantásticas "
    "em um mundo sustentável. São Paulo: Draco, 2012.",
    "PEREIRA, G. B. et al. Jogo sério para estímulo sensorial de crianças com "
    "transtorno do espectro autista. In: SBIE, 34., 2023, Passo Fundo. Anais "
    "[...]. Porto Alegre: SBC, 2023. DOI: 10.5753/sbie.2023.233744.",
)

# Chave -> (nome, cor da lixeira segundo a Resolução CONAMA nº 275/2001, dica).
WASTE_INFO: Dict[str, Tuple[str, str, str]] = {
    "papel": (
        "Papel",
        "azul",
        "Papel limpo e seco pode ser reciclado e virar papel novo.",
    ),
    "plastico": (
        "Plástico",
        "vermelho",
        "Embalagens plásticas limpas podem ser recicladas em novos produtos.",
    ),
    "metal": (
        "Metal",
        "amarelo",
        "Latas de alumínio e aço podem ser derretidas e reutilizadas.",
    ),
    "vidro": (
        "Vidro",
        "verde",
        "O vidro pode ser reciclado muitas vezes sem perder qualidade.",
    ),
}

BIOME_FACTS: Dict[str, Tuple[str, ...]] = {
    "amazonia": (
        "A Amazônia é a maior floresta tropical do mundo.",
        "Em Manaus, os rios Negro e Solimões formam o encontro das águas: correm lado a lado por um bom trecho.",
        "O Teatro Amazonas, em Manaus, foi inaugurado em 1896.",
        "A samaúma é uma das maiores árvores da floresta e tem raízes grandes que ajudam a firmar o tronco.",
        "O açaí é um fruto roxo da Amazônia, muito usado em polpas e sucos.",
        "Os rios voadores levam umidade pelo ar e ajudam a trazer chuva para outras regiões.",
    ),
    "caatinga": (
        "A Caatinga é um bioma exclusivamente brasileiro.",
        "O mandacaru é um cacto que guarda água no caule e ajuda a enfrentar a seca.",
        "O Rio São Francisco, o 'Velho Chico', corta a região e liga Petrolina (PE) a Juazeiro (BA) por uma ponte.",
        "Na região, a fruticultura irrigada produz uvas e mangas, muitas delas vendidas para outros países.",
        "Sol forte e vento favorecem a energia solar e a eólica no Nordeste.",
        "As cisternas de placas guardam água da chuva para usar na época seca.",
    ),
}

STAGE_NAMES = (
    "Cidade industrial",
    "Despertar ecológico",
    "Cidade solarpunk",
)

STAGE_MESSAGES = (
    "Fumaça, concreto e ferrugem. Cada coleta ajuda a mudar isso.",
    "A natureza volta a aparecer entre os prédios.",
    "Energia limpa e natureza integradas à vida da cidade.",
)

TIPS = (
    "Colete os resíduos coloridos e desvie dos obstáculos.",
    "Os obstáculos podem ser evitados por cima, por baixo ou ao lado.",
    "Escudo, ímã e reparo ajudam você no voo. Pegue-os quando puder.",
    "Peças do avião ajudam a conquistar as três estrelas da fase.",
    "Na vila, troque recursos por melhorias para a cidade e para o avião.",
    "Quer uma pausa? Saia da área da câmera ou peça ao supervisor.",
    "Se a visão ajudar, ative o alto contraste nas opções.",
    "Ajuste o volume ou desligue o som nas opções, se preferir.",
)

UI: Dict[str, str] = {
    "decolar": "Decolar",
    "vila": "Vila",
    "mapa": "Mapa",
    "hangar": "Hangar",
    "piloto": "Piloto",
    "opcoes": "Opções",
    "sobre": "Sobre",
    "creditos": "Créditos",
    "voltar": "Voltar",
    "sair": "Sair",
    "pausado": "Pausado",
    "continuar": "Continuar",
    "fim_de_fase": "Fim de fase",
    "tentar_de_novo": "Tentar de novo",
    "estrelas": "Estrelas",
    "recursos": "Recursos",
    "bloqueado": "Em breve",
    "calibrar": "Calibrar",
    "entendi": "Entendi",
    "alto_contraste": "Alto contraste",
    "volume": "Volume",
    "silencio": "Silêncio",
    "fase": "Fase",
    "estagio": "Estágio",
    "iniciar": "Iniciar",
    "normal": "Normal",
    "dificil": "Difícil",
    "combo": "Combo",
    "vidas": "Vidas",
    "pecas": "Peças",
    "melhorias": "Melhorias",
    "residuos": "Resíduos",
    "pontos": "Pontos",
}
