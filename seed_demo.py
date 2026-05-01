"""Script para popular o banco de dados com dados de demonstração."""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from database import init_db, get_connection, proximo_numero_venda
from datetime import datetime, timedelta

init_db()
conn = get_connection()

# ─── PRODUTOS ─────────────────────────────────────────────────────────────────
produtos = [
    ("PRD-00001", "Arroz Tipo 1 5kg", "Alimentos", "Grãos e Cereais", 150, 20, 12.50, 18.90, "UN"),
    ("PRD-00002", "Feijão Carioca 1kg", "Alimentos", "Grãos e Cereais", 200, 30, 5.80, 8.90, "UN"),
    ("PRD-00003", "Óleo de Soja 900ml", "Alimentos", "Óleos e Gorduras", 80, 15, 6.20, 9.50, "UN"),
    ("PRD-00004", "Açúcar Cristal 1kg", "Alimentos", "Açúcar e Adoçantes", 120, 20, 3.40, 5.90, "UN"),
    ("PRD-00005", "Café Torrado 500g", "Alimentos", "Bebidas", 60, 10, 14.00, 22.90, "UN"),
    ("PRD-00006", "Macarrão Espaguete 500g", "Alimentos", "Massas", 180, 25, 2.80, 4.90, "UN"),
    ("PRD-00007", "Leite Integral 1L", "Alimentos", "Laticínios", 100, 30, 4.50, 6.90, "UN"),
    ("PRD-00008", "Sabão em Pó 1kg", "Limpeza", "Lavanderia", 45, 10, 8.90, 14.90, "UN"),
    ("PRD-00009", "Detergente 500ml", "Limpeza", "Cozinha", 90, 15, 1.80, 3.50, "UN"),
    ("PRD-00010", "Papel Higiênico 4un", "Higiene", "Papel", 70, 12, 5.20, 8.90, "UN"),
    ("PRD-00011", "Shampoo 400ml", "Higiene", "Cabelos", 35, 8, 9.50, 16.90, "UN"),
    ("PRD-00012", "Refrigerante 2L", "Bebidas", "Refrigerantes", 8, 20, 5.80, 9.90, "UN"),  # Estoque baixo
    ("PRD-00013", "Biscoito Recheado 130g", "Alimentos", "Biscoitos", 3, 15, 2.10, 3.90, "UN"),  # Estoque baixo
    ("PRD-00014", "Azeite Extra Virgem 500ml", "Alimentos", "Óleos e Gorduras", 25, 5, 18.00, 32.90, "UN"),
    ("PRD-00015", "Queijo Mussarela 1kg", "Alimentos", "Laticínios", 15, 5, 35.00, 52.90, "KG"),
]

for p in produtos:
    try:
        conn.execute("""
            INSERT OR IGNORE INTO produtos
            (codigo, nome, categoria, descricao, quantidade, quantidade_minima, preco_custo, preco_venda, unidade, ativo)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
        """, p)
    except Exception as e:
        print(f"Erro produto {p[0]}: {e}")

# ─── CLIENTES ─────────────────────────────────────────────────────────────────
clientes = [
    ("Maria Silva Santos", "123.456.789-00", "(11) 98765-4321", "maria@email.com",
     "Rua das Flores, 123", "São Paulo", "SP", "01310-100", 2000.00),
    ("João Carlos Oliveira", "987.654.321-00", "(11) 91234-5678", "joao@email.com",
     "Av. Paulista, 456", "São Paulo", "SP", "01310-200", 1500.00),
    ("Ana Paula Ferreira", "456.789.123-00", "(21) 99876-5432", "ana@email.com",
     "Rua do Comércio, 789", "Rio de Janeiro", "RJ", "20040-020", 3000.00),
    ("Carlos Eduardo Lima", "321.654.987-00", "(31) 98765-1234", "carlos@email.com",
     "Rua Minas Gerais, 321", "Belo Horizonte", "MG", "30130-110", 1000.00),
    ("Fernanda Costa Souza", "654.321.987-00", "(41) 97654-3210", "fernanda@email.com",
     "Rua das Araucárias, 654", "Curitiba", "PR", "80010-010", 2500.00),
    ("Roberto Alves Pereira", "789.123.456-00", "(51) 96543-2109", "roberto@email.com",
     "Av. Ipiranga, 987", "Porto Alegre", "RS", "90010-000", 800.00),
]

for c in clientes:
    try:
        conn.execute("""
            INSERT OR IGNORE INTO clientes
            (nome, cpf_cnpj, telefone, email, endereco, cidade, estado, cep, limite_credito, ativo)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
        """, c)
    except Exception as e:
        print(f"Erro cliente {c[0]}: {e}")

conn.commit()

# ─── VENDAS DE DEMONSTRAÇÃO ───────────────────────────────────────────────────
# Buscar IDs
prod_ids = {row["codigo"]: row["id"] for row in conn.execute("SELECT id, codigo FROM produtos").fetchall()}
cli_ids = {row["nome"]: row["id"] for row in conn.execute("SELECT id, nome FROM clientes").fetchall()}

def criar_venda(cliente_nome, tipo_pag, itens_lista, dias_atras=0, num_parcelas=None, taxa_juros=0):
    """itens_lista: [(codigo_prod, qtd), ...]"""
    numero = proximo_numero_venda()
    cliente_id = cli_ids.get(cliente_nome)

    subtotal = 0
    itens = []
    for cod, qtd in itens_lista:
        pid = prod_ids.get(cod)
        if not pid:
            continue
        preco = conn.execute("SELECT preco_venda FROM produtos WHERE id=?", (pid,)).fetchone()["preco_venda"]
        sub = qtd * preco
        subtotal += sub
        itens.append({
            "produto_id": pid, "quantidade": qtd,
            "preco_unitario": preco, "desconto_item": 0.0, "subtotal": sub
        })

    total = subtotal
    data_venda = (datetime.now() - timedelta(days=dias_atras)).strftime("%Y-%m-%d %H:%M:%S")

    cursor = conn.execute("""
        INSERT INTO vendas (numero_venda, cliente_id, tipo_pagamento, subtotal, desconto, total, status, criado_em)
        VALUES (?, ?, ?, ?, 0, ?, 'concluida', ?)
    """, (numero, cliente_id, tipo_pag, subtotal, total, data_venda))
    venda_id = cursor.lastrowid

    for item in itens:
        conn.execute("""
            INSERT INTO itens_venda (venda_id, produto_id, quantidade, preco_unitario, desconto_item, subtotal)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (venda_id, item["produto_id"], item["quantidade"],
              item["preco_unitario"], item["desconto_item"], item["subtotal"]))
        conn.execute(
            "UPDATE produtos SET quantidade = MAX(0, quantidade - ?) WHERE id = ?",
            (item["quantidade"], item["produto_id"])
        )

    # Crediário
    if tipo_pag == "crediario" and num_parcelas and cliente_id:
        valor_parc = total / num_parcelas
        for i in range(num_parcelas):
            data_venc = (datetime.now() - timedelta(days=dias_atras) + timedelta(days=30*(i+1))).strftime("%Y-%m-%d")
            status_parc = "pago" if i < 1 and dias_atras > 30 else "pendente"
            conn.execute("""
                INSERT INTO crediario (venda_id, cliente_id, numero_parcela, total_parcelas,
                valor_parcela, data_vencimento, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (venda_id, cliente_id, i+1, num_parcelas, round(valor_parc, 2), data_venc, status_parc))

        conn.execute(
            "UPDATE clientes SET credito_utilizado = credito_utilizado + ? WHERE id = ?",
            (total, cliente_id)
        )

    return venda_id


# Criar vendas variadas
try:
    criar_venda("Maria Silva Santos", "dinheiro",
                [("PRD-00001", 2), ("PRD-00002", 3), ("PRD-00009", 2)], dias_atras=0)
    criar_venda("João Carlos Oliveira", "pix",
                [("PRD-00005", 1), ("PRD-00007", 4), ("PRD-00004", 2)], dias_atras=1)
    criar_venda("Ana Paula Ferreira", "cartao_credito",
                [("PRD-00011", 2), ("PRD-00010", 3), ("PRD-00008", 1)], dias_atras=2)
    criar_venda("Carlos Eduardo Lima", "crediario",
                [("PRD-00014", 1), ("PRD-00015", 2), ("PRD-00003", 3)], dias_atras=45,
                num_parcelas=3)
    criar_venda("Fernanda Costa Souza", "crediario",
                [("PRD-00001", 5), ("PRD-00006", 4), ("PRD-00007", 6)], dias_atras=15,
                num_parcelas=4)
    criar_venda(None, "dinheiro",
                [("PRD-00013", 2), ("PRD-00012", 1)], dias_atras=0)
    criar_venda("Roberto Alves Pereira", "cartao_debito",
                [("PRD-00002", 2), ("PRD-00004", 1), ("PRD-00006", 3)], dias_atras=3)
    criar_venda("Maria Silva Santos", "crediario",
                [("PRD-00005", 2), ("PRD-00011", 1)], dias_atras=60,
                num_parcelas=2)
except Exception as e:
    print(f"Erro ao criar vendas: {e}")

conn.commit()
conn.close()
print("✅ Dados de demonstração inseridos com sucesso!")
