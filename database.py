import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "loja_pdv.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    # Tabela de produtos/estoque
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS produtos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo TEXT UNIQUE NOT NULL,
            nome TEXT NOT NULL,
            descricao TEXT,
            categoria TEXT,
            quantidade INTEGER NOT NULL DEFAULT 0,
            quantidade_minima INTEGER NOT NULL DEFAULT 5,
            preco_custo REAL NOT NULL DEFAULT 0.0,
            preco_venda REAL NOT NULL DEFAULT 0.0,
            unidade TEXT DEFAULT 'UN',
            ativo INTEGER DEFAULT 1,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Tabela de clientes
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS clientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            cpf_cnpj TEXT,
            telefone TEXT,
            email TEXT,
            endereco TEXT,
            cidade TEXT,
            estado TEXT,
            cep TEXT,
            limite_credito REAL DEFAULT 0.0,
            credito_utilizado REAL DEFAULT 0.0,
            ativo INTEGER DEFAULT 1,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Tabela de vendas
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS vendas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero_venda TEXT UNIQUE NOT NULL,
            cliente_id INTEGER,
            tipo_pagamento TEXT NOT NULL DEFAULT 'dinheiro',
            subtotal REAL NOT NULL DEFAULT 0.0,
            desconto REAL NOT NULL DEFAULT 0.0,
            total REAL NOT NULL DEFAULT 0.0,
            status TEXT DEFAULT 'concluida',
            observacoes TEXT,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (cliente_id) REFERENCES clientes(id)
        )
    """)

    # Tabela de itens da venda
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS itens_venda (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            venda_id INTEGER NOT NULL,
            produto_id INTEGER NOT NULL,
            quantidade INTEGER NOT NULL,
            preco_unitario REAL NOT NULL,
            desconto_item REAL DEFAULT 0.0,
            subtotal REAL NOT NULL,
            FOREIGN KEY (venda_id) REFERENCES vendas(id),
            FOREIGN KEY (produto_id) REFERENCES produtos(id)
        )
    """)

    # Tabela de crediário (parcelas)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS crediario (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            venda_id INTEGER NOT NULL,
            cliente_id INTEGER NOT NULL,
            numero_parcela INTEGER NOT NULL,
            total_parcelas INTEGER NOT NULL,
            valor_parcela REAL NOT NULL,
            data_vencimento DATE NOT NULL,
            data_pagamento DATE,
            status TEXT DEFAULT 'pendente',
            observacoes TEXT,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (venda_id) REFERENCES vendas(id),
            FOREIGN KEY (cliente_id) REFERENCES clientes(id)
        )
    """)

    # Tabela de configurações
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS configuracoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chave TEXT UNIQUE NOT NULL,
            valor TEXT,
            descricao TEXT
        )
    """)

    # Inserir configurações padrão
    configs_padrao = [
        ("nome_loja", "Minha Loja", "Nome da loja"),
        ("cnpj_loja", "", "CNPJ da loja"),
        ("endereco_loja", "", "Endereço da loja"),
        ("telefone_loja", "", "Telefone da loja"),
        ("email_loja", "", "E-mail da loja"),
        ("taxa_juros_crediario", "0", "Taxa de juros mensal do crediário (%)"),
        ("contador_venda", "0", "Contador de vendas para numeração"),
    ]
    for chave, valor, descricao in configs_padrao:
        cursor.execute("""
            INSERT OR IGNORE INTO configuracoes (chave, valor, descricao)
            VALUES (?, ?, ?)
        """, (chave, valor, descricao))

    conn.commit()
    conn.close()


def get_config(chave):
    conn = get_connection()
    row = conn.execute(
        "SELECT valor FROM configuracoes WHERE chave = ?", (chave,)
    ).fetchone()
    conn.close()
    return row["valor"] if row else None


def set_config(chave, valor):
    conn = get_connection()
    conn.execute(
        "UPDATE configuracoes SET valor = ? WHERE chave = ?", (valor, chave)
    )
    conn.commit()
    conn.close()


def proximo_numero_venda():
    conn = get_connection()
    row = conn.execute(
        "SELECT valor FROM configuracoes WHERE chave = 'contador_venda'"
    ).fetchone()
    contador = int(row["valor"]) + 1 if row else 1
    conn.execute(
        "UPDATE configuracoes SET valor = ? WHERE chave = 'contador_venda'",
        (str(contador),)
    )
    conn.commit()
    conn.close()
    return f"VND-{contador:06d}"
