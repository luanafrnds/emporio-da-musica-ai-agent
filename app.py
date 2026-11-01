import re
import unicodedata
from pathlib import Path

import pandas as pd
import streamlit as st
import fitz  # PyMuPDF

# ============================================================
# CONFIGURAÇÃO DA PÁGINA E ESTILO VISUAL
# ============================================================

st.set_page_config(
    page_title="Empório da Música | Assistente",
    page_icon="🎸",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Playfair+Display:wght@600;700&display=swap');
.stApp { background: radial-gradient(circle at 85% 0%, #263321 0, #101310 35%); color:#f4f4ec; }
html, body, [class*="css"] { font-family:'DM Sans',sans-serif; }
h1 { font-family:'Playfair Display',serif !important; letter-spacing:-.7px; }
[data-testid="stSidebar"] { background:#151a15; border-right:1px solid #30382d; }
.hero { padding:1.5rem; border:1px solid #30382d; border-radius:20px; background:linear-gradient(125deg,rgba(199,243,107,.13),rgba(255,255,255,.025)); margin-bottom:1rem; }
.eyebrow { color:#c7f36b; text-transform:uppercase; letter-spacing:2px; font-size:.7rem; font-weight:700; }
.sub { color:#a8b0a3; font-size:.95rem; }
.pill { display:inline-block; background:#263321; color:#c7f36b; border:1px solid #465638; border-radius:999px; padding:.2rem .6rem; font-size:.7rem; margin-right:.3rem; }
.stButton>button { border-radius:10px; border:1px solid #c7f36b66; background:#c7f36b; color:#17200d; font-weight:700; }
.stButton>button:hover { background:#a9d652; color:#11170b; }
.stChatMessage { background:#ffffff05; border:1px solid #ffffff12; border-radius:14px; }
div[data-testid="stExpander"] { border:1px solid #ffffff18; border-radius:12px; }
</style>
""", unsafe_allow_html=True)

BASE_DIR = Path(__file__).resolve().parent
DATA_DIRS = [BASE_DIR, BASE_DIR / "data", BASE_DIR / "dados"]

PRODUCT_FILE_NAMES = ["products.csv", "produtos.csv", "product.csv", "produto.csv", "desafio_tecnico_ai_eng - products.csv"]
CATEGORY_FILE_NAMES = ["categories.csv", "categorias.csv", "category.csv", "categoria.csv", "desafio_tecnico_ai_eng - categories.csv"]
PROMOTION_FILE_NAMES = ["promotions.csv", "desafio_tecnico_ai_eng - promotions.csv"]
ORDER_FILE_NAMES = ["orders.csv", "desafio_tecnico_ai_eng - orders.csv"]
ORDER_ITEM_FILE_NAMES = ["order_items.csv", "desafio_tecnico_ai_eng - order_items.csv"]
CUSTOMER_FILE_NAMES = ["customers.csv", "desafio_tecnico_ai_eng - customers.csv"]
PDF_FILE_NAMES = ["politicas_da_loja.pdf", "políticas_da_loja.pdf", "faq.pdf", "perguntas_frequentes.pdf", "politicas.pdf", "policies.pdf"]

KNOWN_BRANDS = ["fender", "yamaha", "crafter", "giannini", "pearl", "shelby", "tagima", "gibson", "ibanez",
                "takamine", "roland", "casio", "korg", "nord", "taylor", "martin", "kala", "kalani", "ohana",
                "rozini", "prs", "music man"]

# Padrões ESTRITOS (palavras inteiras) — nada de "nylon", "aco" ou "folk" soltos.
CATEGORY_PATTERNS = {
    "violao": r"\bviol(?:ao|oes)\b",
    "guitarra": r"\bguitarras?\b",
    "teclado": r"\bteclados?\b|\bsintetizad(?:or|ores)\b|\bpianos?\b",
    "bateria": r"\bbaterias?\b",
    "baixo": r"\bbaixos?\b|\bcontrabaixos?\b",
    "microfone": r"\bmicrofones?\b",
    "ukulele": r"\bukuleles?\b|\bcavaquinhos?\b",
    "sopro": r"\bsopros?\b|\bflautas?\b|\bclarinetes?\b|\bsax(?:ofones?)?\b|\btrompetes?\b|\btrombones?\b",
    "cordas_orquestrais": r"\bvioli(?:no|nos)\b|\bvioloncelos?\b|\bcordas orquestrais\b",
}
CATEGORY_LABELS = {
    "violao": "violões", "guitarra": "guitarras", "teclado": "teclados", "bateria": "baterias",
    "baixo": "baixos", "microfone": "microfones", "ukulele": "ukuleles/cavaquinhos",
    "sopro": "instrumentos de sopro", "cordas_orquestrais": "cordas orquestrais",
}

NUMBER_WORDS = {"um": 1, "uma": 1, "dois": 2, "duas": 2, "tres": 3, "quatro": 4, "cinco": 5,
                "seis": 6, "sete": 7, "oito": 8, "nove": 9, "dez": 10}
ORDINALS = {"primeir": 1, "segund": 2, "terceir": 3, "quart": 4, "quint": 5}
ORD_RE = re.compile(r"\b(primeir[oa]|segund[oa]|terceir[oa]|quart[oa]|quint[oa])\b(?:\s+mais)?\s*(caro|cara|barato|barata)?")
QTY_RE = re.compile(r"\b(\d+|" + "|".join(NUMBER_WORDS) + r")\b")

STATUS_LABELS = {"discontinued": "Produto descontinuado (não faz mais parte do catálogo).",
                 "coming_soon": "Lançamento em breve — ainda não disponível para venda."}

POLICY_TOPICS = {
    "garantia": {"trigger": r"\bgarantia\b|\bassistencia\b",
                 "terms": ["garantia"]},
    "troca": {"trigger": r"\btroc(?:a|as|ar|ado)\b|\bsubstitui\w*|\bdefeito\b|\bquebrou\b|\boutro modelo\b|\bpreferencia\b",
              "terms": ["troca", "trocar", "substituicao", "defeito", "preferencia"]},
    "devolucao": {"trigger": r"\bdevolu\w*|\bdevolv\w*|\breembolso\b|\barrepend\w*|\bcancel\w*",
                  "terms": ["devolucao", "reembolso", "arrependimento", "cancelamento"]},
    "pagamento": {"trigger": r"\bpagamento\w*|\bpix\b|\bcart(?:ao|oes)\b|\bparcel\w*|\bboleto\b|\bcredito\b|\bdebito\b",
                  "terms": ["pagamento", "pix", "cartao", "parcelamento", "boleto"]},
    "entrega": {"trigger": r"\bentrega\w*|\bfrete\b|\benvio\b|\benviam\b|\bcorreios\b|\bsedex\b|\bpac\b|\bjadlog\b",
                "terms": ["entrega", "frete", "envio"]},
    "avaria": {"trigger": r"\bdanific\w*|\bavaria\w*|\bchegou (?:quebrad\w*|amassad\w*|riscad\w*)|\bchegar (?:quebrad\w*|danific\w*)",
               "terms": ["avaria", "recusar"]},
    "rastreio": {"trigger": r"\brastre\w*|\bcodigo de rastr\w*",
                 "terms": ["rastreamento", "codigo de rastreamento"]},
    "desconto": {"trigger": r"\bdesconto\w*|\bpromoc\w*|\bcupom\b|\bcupons\b",
                 "terms": ["desconto", "promocao", "cupom"]},
}


# ============================================================
# NORMALIZAÇÃO E PARSING
# ============================================================

def normalize_text(value):
    if pd.isna(value):
        return ""
    text = str(value).strip().lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(char for char in text if not unicodedata.combining(char))
    return re.sub(r"\s+", " ", text)


def normalize_column_name(value):
    return re.sub(r"[^a-z0-9]+", "_", normalize_text(value)).strip("_")


def find_column(df, candidates):
    normalized_columns = {normalize_column_name(c): c for c in df.columns}
    for candidate in candidates:
        cand_norm = normalize_column_name(candidate)
        if cand_norm in normalized_columns:
            return normalized_columns[cand_norm]
    return None


def format_brl(value):
    try:
        value = float(value)
    except (TypeError, ValueError):
        return "preço não disponível"
    formatted = f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {formatted}"


def parse_brl(value):
    if pd.isna(value):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace("R$", "").replace(" ", "")
    if not text:
        return None
    if "," in text:
        text = text.replace(".", "").replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return None


def parse_price_from_question(question):
    text = normalize_text(question)
    patterns = [
        r"r\$\s*(\d[\d.]*(?:,\d{1,2})?)",
        r"(?<![\w.])(\d{1,3}(?:\.\d{3})+,\d{1,2})(?!\w)",
        r"(?<![\w.])(\d+,\d{1,2})(?!\w)",
        r"(?<![\w.])(\d+)(?![\w.])",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            raw = match.group(1)
            if "," in raw:
                raw = raw.replace(".", "").replace(",", ".")
            elif "." in raw and re.fullmatch(r"\d{1,3}(?:\.\d{3})+", raw):
                raw = raw.replace(".", "")
            try:
                return float(raw)
            except ValueError:
                continue
    return None


def extract_quantity_from_question(question):
    """Primeira quantidade como PALAVRA INTEIRA (evita 'um' dentro de 'instrumento')."""
    text = normalize_text(question)
    unit_match = re.search(r"\b(\d+|" + "|".join(NUMBER_WORDS) + r")\s+unidades?\b", text)
    match = unit_match or QTY_RE.search(text)
    if not match:
        return None
    token = match.group(1)
    return int(token) if token.isdigit() else NUMBER_WORDS[token]


# ============================================================
# CARREGAMENTO DE ARQUIVOS
# ============================================================

def locate_file(candidates):
    for directory in DATA_DIRS:
        for filename in candidates:
            path = directory / filename
            if path.exists():
                return path
    return None


def read_csv_flexible(path):
    if path is None:
        return None
    last_error = None
    for encoding in ["utf-8-sig", "utf-8", "latin-1"]:
        try:
            with open(path, encoding=encoding) as fh:
                header = fh.readline()
            sep = ";" if header.count(";") > header.count(",") else ","
            return pd.read_csv(path, sep=sep, encoding=encoding)
        except Exception as error:
            last_error = error
    raise ValueError(f"Não foi possível ler {path.name}: {last_error}")


def load_categories():
    path = locate_file(CATEGORY_FILE_NAMES)
    if path is None:
        return None
    try:
        return read_csv_flexible(path)
    except Exception:
        return None


def load_products():
    path = locate_file(PRODUCT_FILE_NAMES)
    if path is None:
        return None, None
    df = read_csv_flexible(path)
    if df is None or df.empty:
        return df, path

    name_col = find_column(df, ["product_name", "name", "product", "nome", "nome_produto", "produto"])
    price_col = find_column(df, ["price_brl", "price", "preco", "preco_brl", "valor", "unit_price", "sale_price"])
    if name_col is None or price_col is None:
        raise ValueError("O catálogo precisa ter colunas de nome e preço.")

    df = df.copy()
    df["_name"] = df[name_col].fillna("").astype(str)
    df["_normalized_name"] = df["_name"].apply(normalize_text)
    df["_price"] = df[price_col].apply(parse_brl)

    stock_col = find_column(df, ["stock_quantity", "quantity_in_stock", "stock", "quantity", "estoque", "quantidade_estoque", "quantidade"])
    df["_stock"] = pd.to_numeric(df[stock_col], errors="coerce") if stock_col is not None else float("nan")

    # Marca e descrição (podem existir como colunas separadas)
    brand_col = find_column(df, ["brand", "marca", "brand_name", "fabricante", "manufacturer"])
    df["_brand"] = df[brand_col].fillna("").astype(str).apply(normalize_text) if brand_col else ""
    status_col = find_column(df, ["status", "situacao"])
    df["_status"] = df[status_col].fillna("active").astype(str).str.strip().str.lower() if status_col else "active"

    category_col = find_column(df, ["category_name", "category", "categoria", "nome_categoria", "tipo"])
    df["_category"] = df[category_col].fillna("").astype(str) if category_col is not None else ""

    categories = load_categories()
    if categories is not None and not categories.empty:
        prod_cat_id = find_column(df, ["category_id", "id_categoria"])
        cat_id = find_column(categories, ["category_id", "id_categoria", "id"])
        cat_name = find_column(categories, ["category_name", "name", "nome", "categoria"])
        if prod_cat_id and cat_id and cat_name:
            lookup = categories[[cat_id, cat_name]].copy()
            lookup["_key"] = lookup[cat_id].astype(str)
            lookup["_val"] = lookup[cat_name].fillna("").astype(str)
            df["_key"] = df[prod_cat_id].astype(str)
            cat_map = lookup.drop_duplicates("_key").set_index("_key")["_val"]
            mapped = df["_key"].map(cat_map)
            df["_category"] = df["_category"].where(df["_category"].str.strip().ne(""), mapped.fillna(""))

    return df, path


# ============================================================
# PDF DE POLÍTICAS
# ============================================================

def locate_pdf():
    path = locate_file(PDF_FILE_NAMES)
    if path is not None:
        return path
    for directory in DATA_DIRS:
        if directory.exists():
            pdfs = list(directory.glob("*.pdf"))
            if pdfs:
                return pdfs[0]
    return None


@st.cache_data(show_spinner=False)
def load_and_chunk_pdf():
    pdf_path = locate_pdf()
    if pdf_path is None:
        return [], 0
    try:
        doc = fitz.open(str(pdf_path))
        text_pages = [page.get_text("text", sort=True) for page in doc]
        doc.close()
        full_text = "\n\n".join(text_pages)
        # remove cabeçalho/rodapé repetidos de cada página
        full_text = re.sub(r"(?m)^\s*Página \d+\s*$", "", full_text)
        full_text = re.sub(r"(?m)^\s*Empório da Música\s+Manual de Políticas e Procedimentos\s*$", "", full_text)
        full_text = re.sub(r"\n{3,}", "\n\n", full_text)
        sections = re.split(r"(?m)(?=^\s*\d+(?:\.\d+)*\.?\s+[A-ZÁÉÍÓÚÂÊÔÃÕÇ])", full_text)
        chunks = [s.strip() for s in sections if s.strip()]
        if not chunks:
            chunks = [full_text.strip()]
        return chunks, len(chunks)
    except Exception:
        return [], 0


def extract_elapsed_days(q):
    """Dias desde a compra/recebimento citados na pergunta (ex.: 'há 10 dias', 'ontem')."""
    if re.search(r"\bontem\b", q):
        return 1
    if re.search(r"\bhoje\b", q):
        return 0
    m = re.search(r"\b(\d+|" + "|".join(NUMBER_WORDS) + r")\s+dias?\b", q)
    if m:
        t = m.group(1)
        return int(t) if t.isdigit() else NUMBER_WORDS[t]
    if re.search(r"\buma semana\b", q):
        return 7
    return None


def evaluate_return_case(question):
    """Combina prazo informado + regras do manual (4.1, 4.2, 4.3 e 8.1). None se não for caso de devolução/troca."""
    q = normalize_text(question)
    regret = bool(re.search(r"\barrepend\w*|\bdevolv\w*|\bdevolu\w*|\bdesist\w*|\breembolso\b", q))
    defect = bool(re.search(r"\bdefeito\b|\bquebrou\b|\bnao funciona\b|\bparou de funcionar\b|\bdefeituos\w*", q))
    swap = bool(re.search(r"\btroc(?:a|ar|o)\b", q)) and not defect
    shipping = bool(re.search(r"\bfrete\b", q))
    days = extract_elapsed_days(q)
    if not (regret or defect or swap):
        return None
    in_store = bool(re.search(r"\b(na loja|presencial\w*|fisica)\b", q)) and not re.search(r"\bonline\b|\binternet\b|\bsite\b|\bapp\b", q)

    # Frete da devolução (sem prazo informado)
    if shipping and regret and days is None:
        return ("Em caso de **arrependimento**, o **frete de devolução é por conta da loja**. "
                "Lembrando: o pedido de devolução deve ser feito em até 7 dias corridos após o recebimento, com o produto "
                "na embalagem original, sem sinais de uso e com todos os acessórios e manuais. (Manual, seção 4.1)")
    if days is None:
        return None  # sem prazo informado: segue para a busca normal no manual
    dias = f"{days} dia" if days == 1 else f"{days} dias"

    if defect:
        if days <= 30:
            return (f"Como o instrumento veio com defeito de fabricação e você está a {dias} da compra, "
                    "ele está **dentro do prazo de 30 dias corridos para troca por defeito**. Entre em contato com nossa equipe "
                    "para dar andamento. Danos por mau uso, quedas, umidade excessiva ou modificações não autorizadas não são cobertos. (Manual, seção 4.2)")
        return (f"Passaram {days} dias, então o prazo de **30 dias para troca por defeito já terminou**. Ainda assim você conta com a "
                "**garantia**: a garantia legal é de 90 dias contra defeitos de fabricação (a partir do recebimento) e muitos "
                "fabricantes oferecem garantia própria. Nós podemos intermediar com o fabricante, se você pedir. (Manual, seções 4.2 e 8)")

    if regret and not swap:
        if in_store:
            return ("O direito de arrependimento de 7 dias vale para **compras online**. Para compras presenciais, o manual prevê "
                    "**troca por preferência (cor, modelo, tamanho) em até 7 dias**, mediante disponibilidade do produto desejado e com o item "
                    "em perfeito estado e na embalagem original. Fale com nossa equipe para ver o seu caso. (Manual, seções 4.1 e 4.3)")
        if days <= 7:
            return (f"Sim! Você está **dentro do prazo**: o direito de arrependimento em compras online é de até 7 dias corridos após o recebimento, "
                    f"e já se passaram {dias} desde o recebimento. O produto deve estar na embalagem original, sem sinais de uso e com todos os acessórios e manuais. "
                    "O reembolso é feito na mesma forma de pagamento em até 10 dias úteis, e o **frete de devolução é por conta da loja**. (Manual, seção 4.1)")
        return (f"Pelo nosso manual, o prazo para devolução por arrependimento em compras online é de até **7 dias corridos** após o recebimento. "
                f"Como você recebeu há {days} dias, esse prazo **já passou**. 😕 Recomendo falar com nossa equipe para verificar se há alguma alternativa "
                "para o seu caso, mas não consigo garantir nenhuma exceção. Se o motivo for defeito de fabricação, o prazo de troca é de 30 dias. (Manual, seções 4.1 e 4.2)")

    if swap:
        if days <= 7:
            return (f"Dá, sim! Trocas por preferência (cor, modelo, tamanho) são permitidas em até 7 dias, e você está a {dias}. "
                    "Depende da disponibilidade do produto desejado, e o item deve estar em perfeito estado e na embalagem original. "
                    "Diferenças de valor são cobradas ou reembolsadas. (Manual, seção 4.3)")
        return (f"O prazo para troca por preferência é de 7 dias, e já se passaram {days}. Se houver defeito de fabricação, "
                "o prazo é de 30 dias corridos. Fale com nossa equipe para avaliar seu caso. (Manual, seções 4.2 e 4.3)")
    return None


def detect_policy_topics(q):
    return [t for t, cfg in POLICY_TOPICS.items() if re.search(cfg["trigger"], q)]


def _is_customer_section(chunk):
    """Só seções numeradas e que não sejam diretrizes internas (7) ou disposições finais (10)."""
    m = re.match(r"\s*(\d+)(?:\.\d+)*\.?\s", chunk)
    return bool(m) and m.group(1) not in {"7", "10"}


def score_chunks(question, chunks):
    """Retorna [(score, índice, chunk)]. Título da seção pesa mais que o corpo."""
    q = normalize_text(question)
    topics = detect_policy_topics(q)
    if not topics:
        return []
    scored = []
    for idx, chunk in enumerate(chunks):
        if not _is_customer_section(chunk):
            continue
        norm = normalize_text(chunk)
        if len(norm.split()) < 15:
            continue
        heading = normalize_text(chunk.splitlines()[0])
        score = 0
        for topic in topics:
            for term in POLICY_TOPICS[topic]["terms"]:
                if term in heading:
                    score += 5
                score += min(norm.count(term), 3)
        if score > 0:
            if re.search(r"\bcampo grande\b|\bregiao metropolitana\b", q) and "metropolitana" in heading:
                score += 10
            if re.search(r"\boutras? cidades?\b|\bcorreios\b|\bsedex\b|\bpac\b|\bjadlog\b|\bfora\b|\binterior\b", q) and "outras cidades" in heading:
                score += 10
            scored.append((score, idx, chunk))
    scored.sort(key=lambda item: item[0], reverse=True)
    return scored


def has_pickup_policy(chunks):
    """True só se alguma seção para clientes menciona retirada presencial."""
    return any(_is_customer_section(c) and re.search(r"\bretirad\w*|\bretirar\b", normalize_text(c)) for c in chunks)


QUESTION_STOP = {"qual", "quais", "quanto", "quantos", "como", "para", "posso", "voces", "sobre", "tem", "que",
                 "acontece", "uma", "por", "com", "dos", "das", "nao", "mais", "foi", "ser", "meu", "minha", "instrumento", "produto", "pedido", "compra", "loja", "fazer", "preciso", "quero"}


def _question_words(question):
    return {w for w in re.findall(r"[a-z0-9]+", normalize_text(question)) if len(w) >= 3 and w not in QUESTION_STOP}


def extract_relevant(question, chunk, max_full=700, max_paras=3):
    """Devolve o título da seção + só os parágrafos que respondem à pergunta.
    Seções curtas voltam inteiras; se nenhum parágrafo pontuar, devolve a seção toda."""
    if len(chunk) <= max_full:
        return chunk
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", chunk) if p.strip()]
    if len(paragraphs) <= 2:
        return chunk
    heading, body = paragraphs[0], paragraphs[1:]
    topics = detect_policy_topics(normalize_text(question))
    terms = {t for topic in topics for t in POLICY_TOPICS[topic]["terms"]}
    words = _question_words(question)
    scored = []
    for i, para in enumerate(body):
        norm = normalize_text(para)
        score = sum(2 for t in terms if t in norm) + sum(3 for w in words if w in norm)
        if score > 0:
            scored.append((score, i, para))
    if not scored:
        return chunk
    best = max(sc for sc, _, _ in scored)
    keep = sorted([(i, p) for sc, i, p in scored if sc >= 0.5 * best][:max_paras])
    return heading + "\n\n" + "\n\n".join(p for _, p in keep)


def retrieve_pdf_best_chunk(question, chunks, max_chars=2200):
    """Escolhe até 3 subseções próximas do melhor score e extrai só os trechos relevantes."""
    scored = score_chunks(question, chunks) if chunks else []
    if not scored:
        return ""
    best = scored[0][0]
    picked = sorted([(i, c) for sc, i, c in scored if sc >= 0.6 * best][:3])
    text = "\n\n".join(extract_relevant(question, c) for _, c in picked)
    return text if len(text) <= max_chars else text[:max_chars].rsplit(" ", 1)[0] + "…"


# ============================================================
# FUNÇÕES DE CATÁLOGO
# ============================================================

def has_stock_information(df):
    return df["_stock"].notna().any()


def in_stock(df):
    """Vendável = status 'active' E estoque > 0."""
    if not has_stock_information(df):
        return df.iloc[0:0].copy()
    return df[(df["_stock"] > 0) & (df["_status"] == "active")].copy()


def get_stock_description(product):
    status = product.get("_status", "active")
    if status in STATUS_LABELS:
        return STATUS_LABELS[status]
    if pd.isna(product["_stock"]):
        return "Estoque não informado no catálogo."
    quantity = int(product["_stock"])
    if quantity <= 0:
        return "Produto sem estoque no momento."
    return f"Estoque: {quantity} {'unidade' if quantity == 1 else 'unidades'}."


def get_available_products(df):
    available = in_stock(df)
    return available if available.empty else available.sort_values("_name")


def product_lines(df, limit=10, with_stock=True):
    lines = []
    for _, p in df.head(limit).iterrows():
        extra = f" ({get_stock_description(p)})" if with_stock else ""
        lines.append(f"- **{p['_name']}** — {format_brl(p['_price'])}{extra}")
    if len(df) > limit:
        lines.append(f"- … e mais {len(df) - limit} opções. Me diga o modelo ou a faixa de preço para eu filtrar.")
    return "\n".join(lines)


def detect_category(q):
    for key, pattern in CATEGORY_PATTERNS.items():
        if re.search(pattern, q):
            return key
    return None


def filter_category(df, key):
    """Prioriza a categoria oficial (categories.csv); usa o nome só se a categoria estiver vazia."""
    pattern = re.compile(CATEGORY_PATTERNS[key])
    cat_norm = df["_category"].apply(normalize_text)
    mask_cat = cat_norm.apply(lambda s: bool(pattern.search(s)))
    mask_name = df["_normalized_name"].apply(lambda s: bool(pattern.search(s))) & cat_norm.eq("")
    return df[mask_cat | mask_name].copy()


def known_brands(df):
    brands = set(KNOWN_BRANDS)
    for n in df["_normalized_name"]:
        first = n.split(" ")[0] if n else ""
        if first and first not in {"bateria", "teclado", "violao", "guitarra", "baixo", "ukulele", "contrabaixo"}:
            brands.add(first)
    return sorted(brands, key=len, reverse=True)


def detect_brand(q, df):
    for brand in known_brands(df):
        if re.search(rf"\b{re.escape(brand)}\b", q):
            return brand
    return None


def filter_brand(df, brand):
    """Marca só no NOME (as descrições do CSV às vezes citam outra marca)."""
    return df[df["_normalized_name"].str.contains(rf"\b{re.escape(brand)}\b", regex=True, na=False)].copy()


def sort_by_price(df, direction, only_in_stock=True):
    candidates = df.dropna(subset=["_price"]).copy()
    if only_in_stock and has_stock_information(candidates):
        candidates = in_stock(candidates)
    return candidates.sort_values(["_price", "_name"], ascending=[direction == "barato", True])


def cheapest_above(df, minimum_price):
    candidates = df.dropna(subset=["_price"]).copy()
    candidates = candidates[candidates["_price"] > minimum_price]
    if has_stock_information(df):
        candidates = in_stock(candidates)
    if candidates.empty:
        return None
    return candidates.sort_values(["_price", "_name"]).iloc[0]


def products_below_price(df, maximum_price, inclusive=False):
    candidates = df.dropna(subset=["_price"]).copy()
    candidates = candidates[candidates["_price"] <= maximum_price] if inclusive else candidates[candidates["_price"] < maximum_price]
    return in_stock(candidates).sort_values(["_price", "_name"]) if has_stock_information(df) else candidates


def find_exact_price(df, target_price):
    candidates = df.dropna(subset=["_price"]).copy()
    matches = candidates[(candidates["_price"] * 100).round() == round(target_price * 100)].copy()
    if has_stock_information(df):
        available = in_stock(matches)
        if not available.empty:
            matches = available
    return matches


SEARCH_IGNORED = {
    "voces", "tem", "tenho", "quero", "gostaria", "comprar", "disponivel", "disponiveis", "produto",
    "produtos", "catalogo", "preco", "quanto", "custa", "qual", "quais", "por", "favor", "me", "o",
    "a", "os", "as", "de", "do", "da", "um", "uma", "posso", "unidade", "unidades", "mesmo",
    "instrumento", "instrumentos", "pedido", "estoque", "ter", "para", "em", "no", "na", "marca",
    "marcas", "modelo", "modelos", "quantas", "quantos", "temos", "vendem", "levar", "valor",
}


def search_terms(question, drop_categories=False):
    query = normalize_text(question)
    ignored = SEARCH_IGNORED | set(NUMBER_WORDS)
    terms = [t for t in re.findall(r"[a-z0-9]+", query) if len(t) > 1 and t not in ignored and not t.isdigit()]
    if drop_categories:
        terms = [t for t in terms if detect_category(t) is None]
    return terms


def search_products(question, df):
    terms = search_terms(question)
    if not terms:
        return df.iloc[0:0].copy()
    matches = df[df["_normalized_name"].apply(lambda n: all(term in n for term in terms))]
    if not matches.empty:
        return matches
    scored = df.copy()
    scored["_score"] = scored["_normalized_name"].apply(lambda n: sum(t in n for t in terms))
    return scored[scored["_score"] >= max(1, len(terms) // 2)].drop(columns=["_score"])


def model_terms(question, df, brand=None):
    """Termos que identificam um MODELO (sem marca, categoria ou palavras genéricas)."""
    terms = search_terms(question, drop_categories=True)
    if brand:
        brand_words = set(brand.split())
        terms = [t for t in terms if t not in brand_words]
    vocab = set(" ".join(df["_normalized_name"]).split())
    return [t for t in terms if t in vocab or any(t in v for v in vocab)]


def resolve_product(question, df, brand=None):
    """('none'|'one'|'many', resultado). Só considera termos que existem no catálogo."""
    terms = model_terms(question, df, brand)
    if not terms:
        return "none", None
    matches = df[df["_normalized_name"].apply(lambda n: all(term in n for term in terms))]
    if brand:
        matches = matches[matches["_normalized_name"].str.contains(rf"\b{re.escape(brand)}\b", regex=True)]
    if len(matches) == 1:
        return "one", matches.iloc[0]
    if len(matches) > 1:
        return "many", matches
    return "none", None


# ============================================================
# MOTOR DE RESPOSTAS (com contexto de conversa)
# ============================================================

def answer_question(question, products_df, policy_chunks, state=None, promotions_df=None):
    """`state` é um dict persistente (st.session_state.ctx) com o contexto anterior:
    categoria e direção (caro/barato) da última consulta, usado em perguntas como
    'E o segundo mais caro?'."""
    if state is None:
        state = {}
    q = normalize_text(question)

    if products_df is None or products_df.empty:
        return "Não consegui carregar o catálogo de produtos."

    # 1. Escopo: acessórios (palavras inteiras)
    if re.search(r"\b(cordas?|palhetas?|cabos?|cases?|pedal|pedais|amplificador(?:es)?)\b", q):
        return (
            "A Empório da Música trabalha **exclusivamente com instrumentos musicais** "
            "e infelizmente não comercializamos acessórios como cordas, palhetas, cabos, "
            "cases, pedais ou amplificadores. Caso precise, recomendamos procurar "
            "lojas parceiras especializadas!"
        )

    # 2. Escopo: serviços / usados
    if re.search(r"\b(conserto\w*|consert\w*|repar\w*|luthier|manutencao|usados?)\b", q):
        return (
            "A Empório da Música é especializada exclusivamente na **venda de instrumentos musicais** "
            "novos e originais. Infelizmente não dispomos de oficina de luthieria própria e "
            "não realizamos serviços de conserto ou manutenção em instrumentos usados."
        )

    # 2c. Aplica prazos do manual ao caso do cliente (devolução, defeito, troca)
    case = evaluate_return_case(question)
    if case:
        return case

    promo_q = bool(re.search(r"\bpromoc\w*|\bofertas?\b|\bliquidacao\b", q)) and promotions_df is not None

    # 2b. Retirada na loja: só responde se o manual realmente tiver a informação
    if re.search(r"\bretir\w*|\bbuscar (?:na|o|meu)\b", q) and re.search(r"\bloja\b|\bpedido\b|\bpessoalmente\b|\bpresencial\w*|\bcompra\b", q):
        if not has_pickup_policy(policy_chunks):
            return ("Sobre **retirada na loja**, não encontrei essa informação no nosso manual de atendimento, "
                    "então prefiro não te passar nada incorreto. 🙏 Por favor, confirme com a equipe pelo "
                    "**WhatsApp (67) 3341-4444**, de segunda a sexta (9h às 18h) e aos sábados (9h às 13h).")

    # 3. Políticas (RAG) — só dispara com tópico explícito, não com "prazo" solto
    if detect_policy_topics(q) and not promo_q:
        chunk = retrieve_pdf_best_chunk(question, policy_chunks)
        if chunk:
            return f"📄 **Baseado no manual oficial da Empório da Música:**\n\n{chunk}"
        return "Não encontrei essa informação no manual oficial."

    if re.fullmatch(r"(oi+|ola|opa|e ai|bom dia|boa tarde|boa noite|tudo bem\??)[!. ]*", q):
        return "Oi! 🎶 Que bom ter você por aqui. Posso te ajudar com instrumentos, preços, estoque, pagamento, trocas, entrega ou horários. O que você procura?"

    words = q.split()
    explicit_cat = detect_category(q)
    price_value = parse_price_from_question(question)
    has_cheap = bool(re.search(r"\bbarat\w*|\bmenor preco\b", q))
    has_expensive = bool(re.search(r"\bcar[oa]s?\b|\bmaior preco\b|\bpreco mais alto\b", q))
    direction = "barato" if has_cheap and not has_expensive else "caro" if has_expensive and not has_cheap else None

    limit_below = any(t in q for t in ["menos de", "abaixo de", "inferior a", "por menos que", "custando menos"])
    limit_upto = bool(re.search(r"\b(ate|no maximo)\b", q)) and price_value is not None
    limit_above = any(t in q for t in ["mais de", "acima de", "superior a", "acima do valor"])
    ord_match = ORD_RE.search(q)

    # O contexto anterior só é herdado em perguntas de RANKING/faixa de preço
    ranking_like = bool(ord_match) or direction or limit_below or limit_upto or limit_above
    category = explicit_cat
    inherited = None
    generic = re.search(r"\b(instrumentos?|produtos?|catalogo|loja)\b", q)
    if category is None and ranking_like and not generic and (q.startswith("e ") or ord_match):
        inherited = state.get("category")
    scope_cat = explicit_cat or inherited
    scope_df = filter_category(products_df, scope_cat) if scope_cat else products_df
    scope_label = CATEGORY_LABELS.get(scope_cat, "instrumentos") if scope_cat else "instrumentos"

    # 3b. Promoções ativas (promotions.csv) — nunca prometer desconto vencido
    if promo_q:
        act_col = find_column(promotions_df, ["is_active", "active", "ativa"])
        active = promotions_df[promotions_df[act_col] == 1] if act_col else promotions_df.iloc[0:0]
        if active.empty:
            return ("No momento **não há promoções ativas** no nosso sistema. 😕 "
                    "Fazemos campanhas ao longo do ano (como Black Friday, em novembro) — fique de olho nas redes sociais! "
                    "Lembrando que pagando no **PIX à vista** você tem 5% de desconto sobre o preço de tabela (exceto itens já em promoção).")
        pid = find_column(promotions_df, ["product_id"]); pct = find_column(promotions_df, ["discount_percent"])
        lines = []
        for _, r in active.iterrows():
            prod = products_df[products_df["product_id"] == r[pid]] if "product_id" in products_df.columns else products_df.iloc[0:0]
            if not prod.empty and prod.iloc[0]["_status"] == "active":
                p = prod.iloc[0]
                promo = p["_price"] * (1 - r[pct] / 100)
                lines.append(f"- **{p['_name']}** — de {format_brl(p['_price'])} por **{format_brl(promo)}** ({int(r[pct])}% off)")
        if lines:
            return "Promoções ativas agora:\n\n" + "\n".join(lines)
        return "No momento não há promoções ativas para produtos disponíveis."

    # 4a. Ordinal: "o segundo mais caro?" / "e o terceiro?"
    if ord_match and not limit_below and not limit_above and not limit_upto:
        position = ORDINALS[ord_match.group(1)[:-1]]
        dir_word = ord_match.group(2)
        dir_ = ("barato" if dir_word.startswith("barat") else "caro") if dir_word else (direction or state.get("order"))
        if dir_ is None:
            return "Você quer o N-ésimo mais **caro** ou mais **barato**? Pode me dizer também a categoria (ex.: violões)."
        ranked = sort_by_price(scope_df, dir_)
        state.update({"category": scope_cat, "order": dir_})
        if len(ranked) < position:
            return f"Só encontrei {len(ranked)} {scope_label} disponíveis em estoque."
        p = ranked.iloc[position - 1]
        return (f"O **{position}º mais {dir_}** entre os {scope_label} disponíveis "
                f"é o **{p['_name']}**, por **{format_brl(p['_price'])}**. {get_stock_description(p)}")

    # 4a2. Faixa "entre X e Y"
    rng = re.search(r"\bentre\s+(?:r\$\s*)?(\d[\d.]*(?:,\d{1,2})?)\s+e\s+(?:r\$\s*)?(\d[\d.]*(?:,\d{1,2})?)", q)
    if rng:
        lo, hi = sorted([parse_brl(rng.group(1)), parse_brl(rng.group(2))])
        state["category"] = scope_cat
        cand = in_stock(scope_df.dropna(subset=["_price"]))
        cand = cand[(cand["_price"] >= lo) & (cand["_price"] <= hi)].sort_values(["_price", "_name"])
        if cand.empty:
            return f"Não encontrei {scope_label} disponíveis entre {format_brl(lo)} e {format_brl(hi)}."
        return f"Opções de {scope_label} entre {format_brl(lo)} e {format_brl(hi)}:\n\n" + product_lines(cand)

    # 4b. Faixa de preço
    if limit_below or limit_upto:
        if price_value is None:
            return "Pode informar o limite de preço? Exemplo: R$ 500,00."
        state["category"] = scope_cat
        matches = products_below_price(scope_df, price_value, inclusive=limit_upto and not limit_below)
        word = "por menos de" if limit_below else "até"
        if matches.empty:
            return f"Não encontrei {scope_label} disponíveis em estoque {word} {format_brl(price_value)}."
        return f"Opções de {scope_label} disponíveis {word} {format_brl(price_value)}:\n\n" + product_lines(matches)

    if direction == "barato" and limit_above:
        if price_value is None:
            return "Não consegui identificar o valor limite. Exemplo: acima de R$ 2.000,00?"
        state["category"] = scope_cat
        prod = cheapest_above(scope_df, price_value)
        if prod is None:
            return f"Não encontrei {scope_label} em estoque acima de {format_brl(price_value)}."
        return f"O mais barato acima de {format_brl(price_value)} é o **{prod['_name']}**, custando **{format_brl(prod['_price'])}**. {get_stock_description(prod)}"

    if any(t in q for t in ["exatamente", "igual a", "mesmo preco", "preco exato", "custando", "valor exato"]) and not limit_above:
        if price_value is None:
            return "Não consegui identificar o valor. Exemplo: R$ 579,90?"
        matches = find_exact_price(products_df, price_value)
        if matches.empty:
            return f"Não encontrei nenhum produto custando exatamente {format_brl(price_value)}."
        return f"Sim! Encontrei estes produtos custando {format_brl(price_value)}:\n\n" + product_lines(matches)

    # 4c. Top N (plural) ou extremo único (singular)
    if direction:
        plural = bool(re.search(r"\b(barat|car)[oa]s\b", q))
        qty = extract_quantity_from_question(question)
        include_out = any(t in q for t in ["sem estoque", "incluindo", "todos os produtos", "todo o catalogo"])
        ranked = sort_by_price(scope_df, direction, only_in_stock=not include_out)
        state.update({"category": scope_cat, "order": direction})
        if ranked.empty:
            return f"Não encontrei {scope_label} disponíveis em estoque no momento."
        if plural:
            n = qty if qty and qty <= 10 else 3
            top = ranked.head(n)
            fem = scope_label in {"guitarras", "baterias", "cordas orquestrais"}
            art = "as" if fem else "os"
            adj = ("baratas" if fem else "baratos") if direction == "barato" else ("caras" if fem else "caros")
            return f"{'Estas' if fem else 'Estes'} são {art} {len(top)} {scope_label} mais {adj} disponíveis:\n\n" + product_lines(top)
        p = ranked.iloc[0]
        return f"O mais {direction} entre os {scope_label} disponíveis é o **{p['_name']}**, por **{format_brl(p['_price'])}**. {get_stock_description(p)}"

    # 4d. Comprar acima do estoque (pergunta geral, sem modelo)
    if re.search(r"\b(mais|alem|acima)\b.{0,30}\b(que|do|de)\b.{0,15}\bestoque\b|\bestoque\b.{0,25}\b(insuficiente|nao (for|der|baste|chegar))", q):
        return ("Não — só conseguimos vender até a quantidade que temos em **estoque**, e não fazemos reserva "
                "de itens esgotados. Se você me disser o **modelo** e a quantidade que precisa, eu confiro o estoque "
                "atual e, se faltar, sugiro modelos semelhantes que estejam disponíveis. 🎸")

    # 4e. Produtos esgotados / indisponíveis
    if re.search(r"\b(esgotad\w*|sem estoque|fora de estoque|indisponiveis?|acabou|acabaram)\b", q):
        out = products_df[(products_df["_status"] == "active") & (products_df["_stock"].fillna(0) <= 0)]
        parts = []
        if not out.empty:
            parts.append("Estão **sem estoque** no momento:\n\n" + product_lines(out, 15, with_stock=False))
        other = products_df[products_df["_status"] != "active"]
        if not other.empty:
            parts.append("Também **não estão à venda**:\n\n" + "\n".join(
                f"- **{p['_name']}** — {STATUS_LABELS.get(p['_status'], p['_status'])}" for _, p in other.iterrows()))
        if not parts:
            return "No momento todos os produtos do catálogo estão com estoque disponível. 🎶"
        return "\n\n".join(parts) + "\n\nPosso sugerir alternativas parecidas que estejam disponíveis, se quiser!"

    # 5. Contato
    if re.search(r"\be-?mail\b", q):
        return "📧 O e-mail de contato oficial da loja é **contato@emporiodamusica.com.br**."
    if re.search(r"\b(whatsapp|zap|watsap|telefone|contato|ligar)\b", q):
        return ("Sim! Você pode entrar em contato conosco diretamente pelo **WhatsApp: (67) 3341-4444** "
                "ou através do e-mail **contato@emporiodamusica.com.br**. Nosso atendimento funciona de "
                "segunda a sexta-feira, das 09:00 às 18:00, e aos sábados das 09:00 às 13:00.")

    # 6. Endereço
    if re.search(r"\b(endereco|onde fica|localizada|localizacao|cidade)\b", q):
        return "📍 Nosso endereço é **Rua 14 de Maio, 3200 — Centro, Campo Grande - MS, 79202-333**."

    # 7. Horários
    if re.search(r"\b(domingos?|abre|abrem|horarios?|funciona|funcionam|funcionamento|sabados?|feriados?)\b", q):
        if "domingo" in q or "feriado" in q:
            return "Não 😊 A loja fica fechada aos domingos e feriados. Nosso atendimento funciona de segunda a sexta, das 9h às 18h, e aos sábados, das 9h às 13h."
        if "sabado" in q:
            return "Aos sábados, funcionamos das 09:00 às 13:00."
        return ("Nosso horário de funcionamento presencial e via WhatsApp é de **segunda a sexta-feira, das 09:00 às 18:00**, "
                "e aos **sábados, das 09:00 às 13:00**. Aos domingos e feriados ficamos fechados.")

    # 8. Compra de várias unidades — exige um modelo definido
    brand = detect_brand(q, products_df)
    qty = extract_quantity_from_question(question)
    if qty and re.search(r"\b(unidades?|comprar|pedido|levar)\b", q) and not re.search(r"\bquais\b", q):
        status, result = resolve_product(question, products_df, brand)
        if status == "none":
            return (f"Para verificar {qty} unidades preciso saber **qual modelo** você quer. "
                    "Pode me dizer o nome ou modelo do instrumento?")
        if status == "many":
            return "Encontrei mais de um modelo com esse nome:\n\n" + product_lines(result, 8, with_stock=False) + "\n\nQual deles você quer?"
        p = result
        if p["_status"] != "active":
            return f"**{p['_name']}**: {STATUS_LABELS.get(p['_status'], 'indisponível para venda')}"
        stock_qty = int(p["_stock"]) if pd.notna(p["_stock"]) else 0
        if stock_qty >= qty:
            return (f"Temos {stock_qty} unidades de **{p['_name']}** em estoque, então a quantidade pedida ({qty}) "
                    "está disponível. A confirmação final da venda segue as regras comerciais da loja.")
        if stock_qty == 0:
            return f"No momento o **{p['_name']}** está **sem estoque**. Posso sugerir modelos semelhantes que estejam disponíveis?"
        return f"Infelizmente não temos estoque suficiente. **{p['_name']}** possui apenas {stock_qty} unidade(s) no momento."

    # 9. Modelo específico (ex.: "Yamaha C40") tem prioridade sobre a listagem da marca
    if model_terms(question, products_df, brand):
        status, result = resolve_product(question, products_df, brand)
        if status == "one":
            p = result
            return f"Encontrei no catálogo:\n\n### 🎸 {p['_name']}\n**Preço:** {format_brl(p['_price'])}\n\n**Situação:** {get_stock_description(p)}"
        if status == "many":
            return "Encontrei algumas opções:\n\n" + product_lines(result, 8, with_stock=False) + "\n\nQual modelo você quer consultar?"

    # 10. Marca (pelo nome do produto)
    if brand:
        all_brand = filter_brand(products_df, brand)
        if all_brand.empty:
            return f"Não encontrei produtos da marca **{brand.title()}** no nosso catálogo."
        if explicit_cat:
            all_brand = filter_category(all_brand, explicit_cat)
        avail = get_available_products(all_brand)
        if avail.empty:
            if all_brand.empty:
                return f"Não encontrei {scope_label} da marca **{brand.title()}** no catálogo."
            return f"Temos produtos **{brand.title()}** no catálogo, mas nenhum disponível em estoque no momento."
        return f"Estes são os produtos da marca **{brand.title()}** disponíveis em estoque:\n\n" + product_lines(avail)

    # 11. Listagem por categoria
    if explicit_cat:
        state["category"] = explicit_cat
        avail = get_available_products(scope_df)
        if avail.empty:
            return f"Não encontrei {scope_label} disponíveis em estoque no momento."
        return f"Opções de {scope_label} disponíveis em estoque:\n\n" + product_lines(avail, 15)

    # 12. Listagem geral
    if re.search(r"\b(quais|listar|mostrar|vendem|disponiveis|catalogo)\b", q):
        avail = get_available_products(products_df)
        if avail.empty:
            return "Atualmente não temos produtos disponíveis em estoque."
        return "Aqui estão alguns dos instrumentos disponíveis em estoque:\n\n" + product_lines(avail) + "\n\nQual modelo gostaria de explorar melhor?"

    # 13. Fallback
    return ("Hmm, isso foge do que eu consigo ajudar por aqui 😅. Sou o assistente da Empório da Música e posso falar de "
            "**instrumentos, preços, estoque, formas de pagamento, trocas, garantia, entrega e horários**. "
            "Se preferir, reformule a pergunta ou consulte a aba **Catálogo**.")


# ============================================================
# DADOS NA INTERFACE
# ============================================================

@st.cache_data(show_spinner=False)
def load_all_data():
    products, p_path = load_products()
    data_dict = {
        "products": products,
        "categories": load_categories(),
        "promotions": read_csv_flexible(locate_file(PROMOTION_FILE_NAMES)),
        "orders": read_csv_flexible(locate_file(ORDER_FILE_NAMES)),
        "order_items": read_csv_flexible(locate_file(ORDER_ITEM_FILE_NAMES)),
        "customers": read_csv_flexible(locate_file(CUSTOMER_FILE_NAMES)),
    }
    policy_chunks, pdf_count = load_and_chunk_pdf()
    return products, p_path, data_dict, policy_chunks, pdf_count


products_df, product_path, loaded_data, policy_chunks, pdf_count = load_all_data()

WELCOME = {"role": "assistant", "content": "Olá! Seja bem-vindo(a) à Empório da Música 🎶. Como posso te ajudar hoje?"}

with st.sidebar:
    st.markdown("### 🎸 Empório da Música")
    st.caption("Assistente virtual • Protótipo")
    page = st.radio("Navegação", ["💬 Atendimento", "🎼 Catálogo", "📊 Dados", "ℹ️ Sobre"], label_visibility="collapsed")
    st.divider()
    st.markdown("**Fontes carregadas**")
    for alias, df in loaded_data.items():
        label = alias.replace("_", " ").title()
        if df is not None and not df.empty:
            st.write(f"🟢 **{label}** · {len(df):,} linhas")
        else:
            st.write(f"🔴 **{label}** · ausente")
    st.write(f"🟢 **Políticas PDF** · ({pdf_count} seções)" if pdf_count > 0 else "🔴 **Políticas PDF** · ausente")
    st.divider()
    if st.button("Limpar conversa", use_container_width=True):
        st.session_state.messages = [WELCOME]
        st.session_state.ctx = {}
        st.rerun()

if page == "💬 Atendimento":
    st.markdown("""
    <div class="hero">
      <div class="eyebrow">Atendimento com cuidado e conhecimento musical</div>
      <h1 style="margin:.3rem 0; color: #f4f4ec;">Encontre o som certo. 🎶</h1>
      <p class="sub">Consulte o catálogo da Empório da Música em uma interface simples, acolhedora e organizada.</p>
      <span class="pill">CATÁLOGO CONECTADO</span><span class="pill">CONTEXTO DE CONVERSA</span>
    </div>
    """, unsafe_allow_html=True)

    if "messages" not in st.session_state:
        st.session_state.messages = [WELCOME]
    if "ctx" not in st.session_state:
        st.session_state.ctx = {}

    st.subheader("💬 Converse com a loja")
    st.caption("Faça qualquer pergunta livremente sobre instrumentos, regras ou localização.")

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("Digite sua dúvida livremente..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        with st.chat_message("assistant"):
            with st.spinner("Analisando sua pergunta..."):
                response = answer_question(prompt, products_df, policy_chunks, st.session_state.ctx, loaded_data.get("promotions"))
                st.markdown(response)
        st.session_state.messages.append({"role": "assistant", "content": response})
        st.rerun()

elif page == "🎼 Catálogo":
    st.subheader("🎼 Catálogo de instrumentos")
    if products_df is None or products_df.empty:
        st.error("O arquivo products.csv não foi carregado.")
    else:
        query = st.text_input("Buscar por nome, marca ou modelo", placeholder="Ex.: Yamaha C40")
        result = search_products(query, products_df) if query else products_df.copy()
        c1, c2, c3 = st.columns(3)
        c1.metric("Produtos encontrados", f"{len(result):,}")
        stock = pd.to_numeric(result["_stock"], errors="coerce").fillna(0)
        c2.metric("Com estoque", f"{int((stock > 0).sum()):,}")
        prices = pd.to_numeric(result["_price"], errors="coerce")
        c3.metric("Preço médio", format_brl(prices.mean()) if prices.notna().any() else "—")
        display_df = result[["_name", "_category", "_price", "_stock", "_status"]].copy()
        display_df.columns = ["Produto", "Categoria", "Preço (R$)", "Estoque", "Status"]
        display_df["Preço (R$)"] = display_df["Preço (R$)"].apply(lambda v: format_brl(v) if pd.notna(v) else "Não informado")
        st.dataframe(display_df, use_container_width=True, hide_index=True)

elif page == "📊 Dados":
    st.subheader("📊 Visão geral dos arquivos")
    cards = st.columns(3)
    for i, (name, df) in enumerate(loaded_data.items()):
        with cards[i % 3]:
            st.metric(name.replace("_", " ").title(), f"{len(df):,} linhas" if df is not None and not df.empty else "Não carregado")
    selected = st.selectbox("Inspecionar arquivo", list(loaded_data.keys()))
    df_sel = loaded_data[selected]
    if df_sel is not None and not df_sel.empty:
        st.write("**Colunas:**", ", ".join(map(str, df_sel.columns)))
        st.dataframe(df_sel.head(100), use_container_width=True, hide_index=True)
    else:
        st.warning("Este arquivo não foi carregado ou está vazio.")

    st.divider()
    st.subheader("🔎 Diagnóstico")
    with st.expander("Categorias de produtos no CSV (validar classificação)"):
        if products_df is not None and not products_df.empty:
            st.dataframe(products_df["_category"].value_counts().rename("qtd").reset_index(), hide_index=True)
    with st.expander("Seções do PDF e teste de recuperação"):
        test_q = st.text_input("Pergunta de teste", "Qual o prazo de garantia?")
        for score, _idx, chunk in score_chunks(test_q, policy_chunks)[:3]:
            st.markdown(f"**Score {score}**")
            st.code(chunk[:600])
        st.caption(f"{len(policy_chunks)} seções extraídas do PDF.")
        for i, chunk in enumerate(policy_chunks):
            st.text(f"[{i}] {chunk[:80].splitlines()[0] if chunk else ''}")

else:
    st.subheader("ℹ️ Sobre o protótipo")
    st.write("Protótipo para o desafio técnico de atendimento da Empório da Música.")
    st.markdown("""**Implementado**
- Interface Streamlit (Dark Mode & Hero Banner).
- Leitura flexível de CSVs (encoding, separador, nomes de colunas).
- Categorias com padrões estritos (palavras inteiras) + coluna de categoria do CSV.
- Busca por marca na coluna de marca, no nome e na descrição, distinguindo inexistente de sem estoque.
- RAG de políticas por tópico, com peso extra para o título da seção.
- Compra de várias unidades: pede o modelo antes de verificar estoque.
- Contexto de conversa: 'E o segundo mais caro?' reaproveita categoria e direção anteriores.""")