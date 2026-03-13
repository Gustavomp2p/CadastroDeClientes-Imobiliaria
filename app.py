from flask import Flask, render_template, request, redirect, url_for, flash
import pymysql.cursors
import os # Importar para usar variáveis de ambiente

app = Flask(__name__)
# É crucial usar uma chave secreta forte e preferencialmente carregada de variáveis de ambiente
# para segurança em produção.
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'sua_chave_secreta_padrao_muito_forte_aqui')

# Configurações do Banco de Dados MySQL
# Recomenda-se usar variáveis de ambiente para credenciais em produção
DB_CONFIG = {
    'host': os.environ.get('DB_HOST', 'localhost'),
    'user': os.environ.get('DB_USER', 'root'),
    'password': os.environ.get('DB_PASSWORD', 'unesc'),
    'db': os.environ.get('DB_NAME', 'imobiliaria'),
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor # Retorna resultados como dicionários
}

def get_db_connection():
    """
    Estabelece uma conexão com o banco de dados.
    Retorna o objeto de conexão ou None em caso de falha.
    """
    try:
        return pymysql.connect(**DB_CONFIG)
    except pymysql.Error as e:
        # Em um ambiente de produção, você usaria um sistema de logging robusto aqui.
        print(f"Erro ao conectar ao banco de dados: {e}")
        flash('Erro ao conectar com o banco de dados.', 'error')
        return None


# ======================
#   ROTA PRINCIPAL (Index) COM ORDENAÇÃO
# ======================
@app.route('/')
def index():

    ordenar = request.args.get('ordenar')

    # Whitelist (para evitar SQL Injection)
    colunas_validas = {
        'nome': 'nome_cliente',
        'email': 'email_cliente',
        'telefone': 'telefone_cliente',
        'cpf': 'cpf_cliente'
    }

    coluna_ordenar = colunas_validas.get(ordenar)
    """Exibe a lista de todos os clientes."""
    conn = get_db_connection()
    cliente = []

    if conn:
        try:
            with conn.cursor() as cursor:
                if coluna_ordenar:
                    # É uma boa prática selecionar apenas as colunas necessárias
                    sql = f"""
                        SELECT id_cliente, nome_cliente, email_cliente, telefone_cliente, cpf_cliente
                        FROM cliente
                        ORDER BY {coluna_ordenar} ASC
                    """
                else:
                    sql = "SELECT id_cliente, nome_cliente, email_cliente, telefone_cliente, cpf_cliente FROM cliente"

                cursor.execute(sql)
                cliente = cursor.fetchall() # fetchall() retorna uma lista de dicionários

        except pymysql.Error as e:
            print(f"Erro ao buscar clientes: {e}")
            flash('Erro ao carregar clientes.', 'error')
        finally:
            conn.close() # Sempre fechar a conexão

    return render_template('index.html', cliente=cliente)



# ======================
#   ADICIONAR CLIENTE
# ======================
@app.route('/add', methods=('GET', 'POST'))
def add_cliente():
    """Adiciona um novo cliente ao banco de dados."""
    if request.method == 'POST':
        nome_cliente = request.form['nome_cliente'].strip() # .strip() remove espaços em branco extras
        email_cliente = request.form['email_cliente'].strip()
        telefone_cliente = request.form['telefone_cliente'].strip()
        cpf_cliente = request.form['cpf_cliente'].strip()

        if not nome_cliente or not email_cliente or not telefone_cliente or not cpf_cliente:
            flash('Nome, email, telefone e cpf são obrigatórios!', 'error')
        else:
            conn = get_db_connection()
            if conn:
                try:
                    with conn.cursor() as cursor:
                        # O uso de placeholders (%s) previne SQL Injection.
                        sql = "INSERT INTO cliente (nome_cliente, email_cliente, telefone_cliente, cpf_cliente) VALUES (%s, %s, %s, %s)"
                        cursor.execute(sql, (nome_cliente, email_cliente, telefone_cliente, cpf_cliente))
                        conn.commit() # Confirma as alterações no banco de dados
                    flash('cliente adicionado com sucesso!', 'success')
                    return redirect(url_for('index'))
                except pymysql.Error as e:
                    flash(f'Erro ao adicionar cliente: {e}', 'error')
                finally:
                    conn.close()

    return render_template('add.html')



# ======================
#   EDITAR CLIENTE
# ======================
@app.route('/edit/<int:id_cliente>', methods=('GET', 'POST'))
def edit_cliente(id_cliente):
    """
    Exibe um formulário pré-preenchido para editar um cliente existente
    e processa a submissão do formulário para atualizar o cliente.
    """
    conn = get_db_connection()
    cliente_i = None

    if conn:
        try:
            with conn.cursor() as cursor:
                sql = "SELECT nome_cliente, email_cliente, telefone_cliente, cpf_cliente FROM cliente WHERE id_cliente = %s"
                cursor.execute(sql, (id_cliente,)) # Busca o cliente pelo ID
                cliente_i = cursor.fetchone() # Pega apenas um resultado (dicionário)

            if not cliente_i:
                flash('Cliente não encontrado para edição.', 'error')
                return redirect(url_for('index'))

            if request.method == 'POST':
                nome_cliente = request.form['nome_cliente'].strip()
                email_cliente = request.form['email_cliente'].strip()
                telefone_cliente = request.form['telefone_cliente'].strip()
                cpf_cliente = request.form['cpf_cliente'].strip()

                if not nome_cliente or not email_cliente or not telefone_cliente or not cpf_cliente:
                    flash('Nome, email, telefone e cpf são obrigatórios!', 'error')
                else:
                    try:
                        with conn.cursor() as cursor:
                            # SQL de UPDATE com placeholders para segurança
                            sql = """
                                UPDATE cliente
                                SET nome_cliente = %s, email_cliente = %s, telefone_cliente = %s, cpf_cliente = %s
                                WHERE id_cliente = %s
                            """
                            cursor.execute(sql, (nome_cliente, email_cliente, telefone_cliente, cpf_cliente, id_cliente))
                            conn.commit() # Confirma a atualização
                        flash('Cliente atualizado com sucesso!', 'success')
                        return redirect(url_for('index'))
                    except pymysql.Error as e:
                        flash(f'Erro ao atualizar cliente: {e}', 'error')

        except pymysql.Error as e:
            print(f"Erro no processo de edição: {e}")
            flash('Ocorreu um erro ao tentar editar o cliente.', 'error')
        finally:
            conn.close()
    
    # Se GET, ou se houve erro no POST (e a conexão foi reaberta para o GET), exibe o formulário de edição
    # O objeto 'user' será passado para o template para pré-preencher os campos.
    return render_template('edit.html', cliente_i=cliente_i)



# ======================
#   EXCLUIR CLIENTE
# ======================
@app.route('/delete/<int:id_cliente>', methods=('POST',)) # Apenas aceita requisições POST para segurança
def delete_cliente(id_cliente):
    conn = get_db_connection()
    if conn:
        try:
            with conn.cursor() as cursor:
                 # SQL de DELETE com placeholder para segurança
                sql = "DELETE FROM cliente WHERE id_cliente = %s"
                rows_affected = cursor.execute(sql, (id_cliente,)) # Retorna o número de linhas afetadas
                conn.commit() # Confirma a exclusão

            if rows_affected > 0:
                flash('Cliente excluído com sucesso!', 'success')
            else:
                flash('Cliente não encontrado para exclusão.', 'error')

        except pymysql.Error as e:
            flash(f'Erro ao excluir cliente: {e}', 'error')
        finally:
            conn.close()

    return redirect(url_for('index')) # Redireciona para a página inicial



if __name__ == '__main__':
    # Em produção, debug=False e as chaves secretas devem ser gerenciadas com segurança.
    app.run(debug=True)
